"""
Endpoints para configuración y gestión de modelos LLM
"""
import os
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from models.schemas.llm import (
    LLMProvider,
    LLMModelList,
    LLMConfigRequest,
    LLMConfigResponse,
    LLMModelInfo,
    LLMDynamicCredentials,
    LLMModelRole,
    LLMConfigRequestWithRole,
    LLMModelSelectionConfig,
    LLMBatchConfigRequest
)
from services.llm import get_llm_service, get_default_llm_service
from middleware.auth_middleware import get_current_user_optional
from services.workspace_llm_config_service import workspace_llm_config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Config"])


@router.get("/models", response_model=LLMModelList)
async def get_available_models(
    provider: LLMProvider = None,
    credentials: LLMDynamicCredentials = None,
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene la lista de modelos disponibles del proveedor específico o de todos.

    Si el usuario está autenticado, usa automáticamente las credenciales guardadas del workspace.

    Args:
        provider: Proveedor específico (opcional)
        credentials: Credenciales dinámicas para probar conexión (opcional, sobrescribe las guardadas)
    """
    default_provider = LLMProvider(os.getenv("DEFAULT_LLM_PROVIDER", "ollama"))
    default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    if provider:
        # Obtener modelos de un proveedor específico
        try:
            service = get_llm_service(provider)

            # Prioridad de credenciales:
            # 1. Credenciales proporcionadas en la request (para probar nuevas credenciales)
            # 2. Credenciales guardadas del workspace
            # 3. Sin credenciales (solo modelos disponibles globalmente)

            provider_creds = None
            if credentials and provider.value in credentials.__fields_set__:
                # Usar credenciales proporcionadas en la request
                provider_creds_dict = getattr(credentials, provider.value)
                if provider_creds_dict:
                    provider_creds = provider_creds_dict
            elif current_user and current_user.workspace_id:
                # Usar credenciales guardadas del workspace
                workspace_config = await workspace_llm_config_service.get_workspace_config(
                    str(current_user.workspace_id),
                    provider.value
                )
                if workspace_config and workspace_config.get("apiKey"):
                    provider_creds = {
                        "apiKey": workspace_config.get("apiKey"),
                        "apiEndpoint": workspace_config.get("apiEndpoint")
                    }

            models = await service.get_available_models(provider_creds)

            model_list = [
                LLMModelInfo(
                    id=model,
                    provider=provider,
                    name=model,
                    description=f"Modelo {model} de {provider.value}"
                )
                for model in models
            ]

            return LLMModelList(
                models=model_list,
                default_provider=default_provider,
                default_model=default_model
            )
        except Exception as e:
            logger.error(f"Error getting models for {provider}: {e}")
            # Retornar lista vacía en caso de error
            return LLMModelList(
                models=[],
                default_provider=default_provider,
                default_model=default_model
            )
    else:
        # Obtener modelos de todos los proveedores
        all_models = []
        for prov in LLMProvider:
            try:
                service = get_llm_service(prov)

                # Usar credenciales del workspace si están disponibles
                provider_creds = None
                if current_user and current_user.workspace_id:
                    workspace_config = await workspace_llm_config_service.get_workspace_config(
                        str(current_user.workspace_id),
                        prov.value
                    )
                    if workspace_config and workspace_config.get("apiKey"):
                        provider_creds = {
                            "apiKey": workspace_config.get("apiKey"),
                            "apiEndpoint": workspace_config.get("apiEndpoint")
                        }

                models = await service.get_available_models(provider_creds)

                for model in models:
                    all_models.append(
                        LLMModelInfo(
                            id=model,
                            provider=prov,
                            name=model,
                            description=f"Modelo {model} de {prov.value}"
                        )
                    )
            except Exception as e:
                logger.warning(f"Could not get models for {prov}: {e}")
                continue

        return LLMModelList(
            models=all_models,
            default_provider=default_provider,
            default_model=default_model
        )


@router.get("/models/saved", response_model=LLMModelList)
async def get_saved_models(
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene todos los modelos de proveedores que tienen credenciales guardadas.
    Usado al inicio para cargar los modelos disponibles sin tener que probar conexión.
    """
    try:
        if not current_user or not current_user.workspace_id:
            return LLMModelList(models=[], default_provider="ollama", default_model="qwen2.5:3b")

        workspace_id = str(current_user.workspace_id)
        all_models = []

        # Obtener todas las configs del workspace
        configs = await workspace_llm_config_service.get_all_workspace_configs(workspace_id)

        for config in configs:
            if not config["hasCredentials"]:
                continue

            provider = LLMProvider(config["provider"])
            service = get_llm_service(provider)

            # Obtener credenciales completas del workspace
            # Usar get_any_config_with_credentials que no prioriza is_default
            full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                workspace_id,
                provider.value
            )

            if full_config and full_config.get("apiKey"):
                provider_creds = {
                    "apiKey": full_config.get("apiKey"),
                    "apiEndpoint": full_config.get("apiEndpoint")
                }

                # Obtener modelos para este proveedor
                models = await service.get_available_models(provider_creds)

                # Convertir a LLMModelInfo
                for model in models:
                    all_models.append(
                        LLMModelInfo(
                            id=model,
                            provider=provider,
                            name=model,
                            description=f"Modelo {model} de {provider.value}"
                        )
                    )

        default_provider = LLMProvider(os.getenv("DEFAULT_LLM_PROVIDER", "ollama"))
        default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

        return LLMModelList(
            models=all_models,
            default_provider=default_provider,
            default_model=default_model
        )

    except Exception as e:
        logger.error(f"Error getting saved models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo modelos guardados: {str(e)}"
        )


@router.post("/config", response_model=LLMConfigResponse)
async def configure_llm(
    config: LLMConfigRequest,
    current_user = Depends(get_current_user_optional)
):
    """
    Configura el proveedor y modelo LLM a usar.

    Si el usuario está autenticado y tiene workspace_id, guarda las credenciales y modelo en la BD del workspace.
    Si no está autenticado, solo verifica la configuración (modo temporal).

    NOTA: Las API keys nunca se retornan al frontend por seguridad.
    """
    try:
        service = get_llm_service(config.provider)

        # Obtener credenciales del proveedor específico
        credentials_to_use = None
        new_api_key = None

        if config.credentials:
            provider_creds = getattr(config.credentials, config.provider.value)
            if provider_creds:
                new_api_key = provider_creds.get("apiKey")
                credentials_to_use = provider_creds

        # Si el usuario está autenticado y tiene workspace, guardar configuración
        if current_user and current_user.workspace_id:
            # Verificar si hay configuración existente
            existing = await workspace_llm_config_service.get_workspace_config(
                str(current_user.workspace_id),
                config.provider.value
            )

            # Determinar qué valores guardar
            api_key_to_save = None
            api_endpoint_to_save = None

            if new_api_key:
                # Nueva API key proporcionada
                api_key_to_save = new_api_key
                api_endpoint_to_save = credentials_to_use.get("apiEndpoint") if credentials_to_use else None
            elif existing:
                # Mantener credenciales existentes, actualizar modelo
                api_key_to_save = existing.get("apiKey")
                api_endpoint_to_save = existing.get("apiEndpoint") or (
                    credentials_to_use.get("apiEndpoint") if credentials_to_use else None
                )
                # Usar credenciales existentes para verificar disponibilidad
                credentials_to_use = {
                    "apiKey": existing.get("apiKey"),
                    "apiEndpoint": existing.get("apiEndpoint")
                }

            # Guardar o actualizar configuración (solo si hay credenciales o si ya existe configuración)
            # Usar setAsDefault del request, por defecto True para compatibilidad con UI antigua
            is_default = config.setAsDefault if config.setAsDefault is not None else True

            if api_key_to_save or existing:
                await workspace_llm_config_service.save_workspace_config(
                    workspace_id=str(current_user.workspace_id),
                    provider=config.provider.value,
                    api_key=api_key_to_save,
                    api_endpoint=api_endpoint_to_save,
                    model=config.model,
                    is_default=is_default
                )

        # Verificar disponibilidad
        is_available = await service.check_available(credentials_to_use)

        # Obtener modelos disponibles
        available_models = await service.get_available_models(credentials_to_use)

        return LLMConfigResponse(
            provider=config.provider,
            model=config.model,
            is_available=is_available,
            available_models=available_models
        )

    except Exception as e:
        logger.error(f"Error configuring LLM: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error configurando LLM: {str(e)}"
        )


@router.get("/config/default", response_model=LLMConfigResponse)
async def get_default_config(
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene la configuración default del sistema LLM.

    Si el usuario está autenticado, retorna su configuración guardada.
    Si no, retorna la configuración global del sistema.
    """
    try:
        default_provider = LLMProvider(os.getenv("DEFAULT_LLM_PROVIDER", "ollama"))
        default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        workspace_credentials = None

        logger.info(f"get_default_config - current_user: {current_user is not None}, workspace_id: {current_user.workspace_id if current_user else None}")

        # Si el usuario está autenticado y tiene workspace, intentar obtener configuración guardada
        if current_user and current_user.workspace_id:
            logger.info(f"Buscando configs para workspace: {current_user.workspace_id}")
            workspace_configs = await workspace_llm_config_service.get_all_workspace_configs(str(current_user.workspace_id))
            logger.info(f"Configs encontradas: {len(workspace_configs)} - {workspace_configs}")

            # Buscar configuración default del workspace
            default_config = next((c for c in workspace_configs if c["isDefault"]), None)
            if default_config:
                logger.info(f"Config default encontrada: {default_config}")
                default_provider = LLMProvider(default_config["provider"])
                default_model = default_config.get("model") or default_model

                # Obtener credenciales completas del workspace para verificar disponibilidad
                full_config = await workspace_llm_config_service.get_workspace_config(
                    str(current_user.workspace_id),
                    default_provider.value
                )
                if full_config and full_config.get("apiKey"):
                    logger.info(f"Credenciales encontradas para {default_provider.value}")
                    workspace_credentials = {
                        "apiKey": full_config.get("apiKey"),
                        "apiEndpoint": full_config.get("apiEndpoint")
                    }
                else:
                    logger.warning(f"No se encontraron credenciales para {default_provider.value}")

        # Obtener servicio y verificar disponibilidad con credenciales si existen
        service = get_llm_service(default_provider)
        is_available = await service.check_available(workspace_credentials)
        available_models = await service.get_available_models(workspace_credentials)

        return LLMConfigResponse(
            provider=default_provider,
            model=default_model,
            is_available=is_available,
            available_models=available_models
        )

    except Exception as e:
        logger.error(f"Error getting default LLM config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración default: {str(e)}"
        )


@router.get("/config/saved")
async def get_saved_configs(
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene las configuraciones LLM guardadas del workspace actual.

    NO retorna las API keys (por seguridad), solo indica si están configuradas.
    """
    if not current_user or not current_user.workspace_id:
        return {"configs": []}

    try:
        configs = await workspace_llm_config_service.get_all_workspace_configs(str(current_user.workspace_id))

        # get_all_workspace_configs ya retorna hasApiKey, así que no necesitamos
        # llamar a get_workspace_config que prioriza is_default=True
        # Si hasApiKey es true, significa que hay credenciales guardadas

        return {"configs": configs}

    except Exception as e:
        logger.error(f"Error getting saved configs: {e}")
        return {"configs": []}


@router.get("/providers")
async def get_providers(
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene la lista de proveedores LLM disponibles.
    Incluye información sobre si el workspace actual tiene credenciales guardadas.
    """
    providers = [
        {
            "id": LLMProvider.ollama,
            "name": "Ollama Cloud",
            "description": "Modelos de código abierto vía Ollama Cloud"
        },
        {
            "id": LLMProvider.zai,
            "name": "Z.ai",
            "description": "Modelos GLM de Z.ai (China)"
        },
        {
            "id": LLMProvider.minimax,
            "name": "MiniMax",
            "description": "Modelos MiniMax (China)"
        }
    ]

    # Si el usuario está autenticado y tiene workspace, verificar qué proveedores tiene configurados
    if current_user and current_user.workspace_id:
        try:
            configs = await workspace_llm_config_service.get_all_workspace_configs(str(current_user.workspace_id))
            configured_providers = {c["provider"]: c for c in configs}

            # Agregar flag de configurado
            for provider in providers:
                if provider["id"] in configured_providers:
                    config = configured_providers[provider["id"]]
                    provider["hasCredentials"] = config["hasCredentials"]
                    provider["savedModel"] = config.get("model")
                    provider["isDefault"] = config["isDefault"]
                else:
                    provider["hasCredentials"] = False
                    provider["savedModel"] = None
                    provider["isDefault"] = False
        except Exception as e:
            logger.error(f"Error checking workspace configs: {e}")

    return {
        "providers": providers,
        "default": os.getenv("DEFAULT_LLM_PROVIDER", "ollama")
    }


@router.get("/credentials/{provider}")
async def get_provider_credentials(
    provider: LLMProvider,
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene las credenciales guardadas de un proveedor específico para el workspace actual.

    IMPORTANTE: Solo retorna el API key desencriptado si el usuario está autenticado.
    El API key se retorna parcialmente ofuscado para seguridad en el response.
    """
    if not current_user or not current_user.workspace_id:
        return {"hasCredentials": False}

    try:
        config = await workspace_llm_config_service.get_workspace_config(
            str(current_user.workspace_id),
            provider.value
        )

        if not config:
            return {"hasCredentials": False}

        # Ofuscar API key para mostrar (solo primeros/últimos caracteres)
        api_key = config.get("apiKey")
        if api_key:
            if len(api_key) <= 8:
                masked_key = "*" * len(api_key)
            else:
                masked_key = api_key[:4] + "..." + api_key[-4:]
        else:
            masked_key = None

        return {
            "hasCredentials": True,
            "apiKey": masked_key,  # Parcialmente ofuscado
            "apiEndpoint": config.get("apiEndpoint"),
            "model": config.get("model"),
            "isDefault": config.get("isDefault", False)
        }

    except Exception as e:
        logger.error(f"Error getting provider credentials: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo credenciales: {str(e)}"
        )


@router.get("/config/selection")
async def get_model_selection_config(
    current_user = Depends(get_current_user_optional)
):
    """
    Obtiene la configuración completa de selección de modelos del workspace:
    - default: modelo principal
    - fallback: modelos alternativos
    - evaluators: modelos para evaluación
    """
    if not current_user or not current_user.workspace_id:
        return {"default": None, "fallback": [], "evaluators": []}

    try:
        selection_config = await workspace_llm_config_service.get_model_selection_config(
            str(current_user.workspace_id)
        )

        # Enriquecer con información de disponibilidad
        for model in selection_config.get('fallback', []):
            try:
                service = get_llm_service(LLMProvider(model['provider']))
                full_config = await workspace_llm_config_service.get_workspace_config(
                    str(current_user.workspace_id),
                    model['provider']
                )
                if full_config and full_config.get('apiKey'):
                    credentials = {
                        'apiKey': full_config['apiKey'],
                        'apiEndpoint': full_config.get('apiEndpoint')
                    }
                    model['isAvailable'] = await service.check_available(credentials)
                else:
                    model['isAvailable'] = False
            except:
                model['isAvailable'] = False

        for model in selection_config.get('evaluators', []):
            try:
                service = get_llm_service(LLMProvider(model['provider']))
                full_config = await workspace_llm_config_service.get_workspace_config(
                    str(current_user.workspace_id),
                    model['provider']
                )
                if full_config and full_config.get('apiKey'):
                    credentials = {
                        'apiKey': full_config['apiKey'],
                        'apiEndpoint': full_config.get('apiEndpoint')
                    }
                    model['isAvailable'] = await service.check_available(credentials)
                else:
                    model['isAvailable'] = False
            except:
                model['isAvailable'] = False

        # Enriquecer default model
        if selection_config.get('default'):
            try:
                default_model = selection_config['default']
                service = get_llm_service(LLMProvider(default_model['provider']))
                full_config = await workspace_llm_config_service.get_workspace_config(
                    str(current_user.workspace_id),
                    default_model['provider']
                )
                if full_config and full_config.get('apiKey'):
                    credentials = {
                        'apiKey': full_config['apiKey'],
                        'apiEndpoint': full_config.get('apiEndpoint')
                    }
                    default_model['isAvailable'] = await service.check_available(credentials)
                else:
                    default_model['isAvailable'] = False
            except:
                selection_config['default']['isAvailable'] = False

        return selection_config

    except Exception as e:
        logger.error(f"Error getting model selection config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo configuración de selección: {str(e)}"
        )


@router.post("/config/model")
async def configure_model_with_role(
    config: LLMConfigRequestWithRole,
    current_user = Depends(get_current_user_optional)
):
    """
    Configura un modelo con un rol específico (default/fallback/evaluator).
    Si es fallback, permite especificar priority.

    NOTA: Las API keys nunca se retornan al frontend por seguridad.
    """
    if not current_user or not current_user.workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida"
        )

    try:
        # Obtener credenciales del proveedor específico
        credentials_to_use = None
        new_api_key = None

        if config.credentials:
            provider_creds = getattr(config.credentials, config.provider.value)
            if provider_creds:
                new_api_key = provider_creds.get("apiKey")
                credentials_to_use = provider_creds

        # Verificar configuración existente
        existing = await workspace_llm_config_service.get_workspace_config(
            str(current_user.workspace_id),
            config.provider.value
        )

        # Determinar valores a guardar
        api_key_to_save = None
        api_endpoint_to_save = None

        if new_api_key:
            api_key_to_save = new_api_key
            api_endpoint_to_save = credentials_to_use.get("apiEndpoint") if credentials_to_use else None
        elif existing:
            api_key_to_save = existing.get("apiKey")
            api_endpoint_to_save = existing.get("apiEndpoint") or (
                credentials_to_use.get("apiEndpoint") if credentials_to_use else None
            )

        # Guardar configuración con rol
        await workspace_llm_config_service.save_model_config_with_role(
            workspace_id=str(current_user.workspace_id),
            provider=config.provider.value,
            model=config.model,
            role=config.role.value,
            priority=config.priority,
            api_key=api_key_to_save,
            api_endpoint=api_endpoint_to_save
        )

        # Verificar disponibilidad
        service = get_llm_service(config.provider)
        final_credentials = {
            'apiKey': api_key_to_save,
            'apiEndpoint': api_endpoint_to_save
        } if api_key_to_save else None

        is_available = await service.check_available(final_credentials)
        available_models = await service.get_available_models(final_credentials)

        return LLMConfigResponse(
            provider=config.provider,
            model=config.model,
            is_available=is_available,
            available_models=available_models
        )

    except Exception as e:
        logger.error(f"Error configuring LLM with role: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error configurando LLM: {str(e)}"
        )


@router.delete("/config/model/{provider}/{role}")
async def remove_model_config(
    provider: str,
    role: str,
    current_user = Depends(get_current_user_optional)
):
    """
    Elimina una configuración de modelo específica (provider + role).
    """
    if not current_user or not current_user.workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida"
        )

    try:
        # Validar que role sea válido
        valid_roles = ['default', 'fallback', 'evaluator']
        if role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Rol inválido. Debe ser uno de: {', '.join(valid_roles)}"
            )

        deleted = await workspace_llm_config_service.delete_model_config_by_role(
            workspace_id=str(current_user.workspace_id),
            provider=provider,
            role=role
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Configuración no encontrada"
            )

        return {"message": "Configuración eliminada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing model config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando configuración: {str(e)}"
        )


@router.post("/config/batch")
async def save_batch_config(
    batch_config: LLMBatchConfigRequest,
    current_user = Depends(get_current_user_optional)
):
    """
    Guarda múltiples configuraciones LLM en una sola llamada.

    Permite configurar:
    - default: modelo principal
    - fallback: modelos alternativos (con prioridad automática)
    - evaluators: modelos evaluadores

    Todas las configuraciones se guardan en una sola transacción.
    """
    if not current_user or not current_user.workspace_id:
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida"
        )

    try:
        # Convertir configs a dict para el servicio
        default_dict = None
        if batch_config.default:
            default_dict = {
                "provider": batch_config.default.provider.value,
                "model": batch_config.default.model,
                "credentials": batch_config.default.credentials.dict() if batch_config.default.credentials else None
            }

        fallback_list = []
        for fb in batch_config.fallback:
            fallback_list.append({
                "provider": fb.provider.value,
                "model": fb.model,
                "credentials": fb.credentials.dict() if fb.credentials else None
            })

        evaluator_list = []
        for ev in batch_config.evaluators:
            evaluator_list.append({
                "provider": ev.provider.value,
                "model": ev.model,
                "credentials": ev.credentials.dict() if ev.credentials else None
            })

        result = await workspace_llm_config_service.save_batch_model_config(
            workspace_id=str(current_user.workspace_id),
            default_config=default_dict,
            fallback_configs=fallback_list,
            evaluator_configs=evaluator_list
        )

        return result

    except Exception as e:
        logger.error(f"Error saving batch config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error guardando configuración: {str(e)}"
        )
