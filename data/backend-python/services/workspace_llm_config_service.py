"""
Servicio para gestión de credenciales LLM de workspaces usando ORM
"""
import logging
import os
from typing import Optional, Dict, Any, List
from uuid import UUID
from cryptography.fernet import Fernet
import base64

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager

logger = logging.getLogger(__name__)

# Clave de encriptación para API keys (desde variable de entorno o generada)
ENCRYPTION_KEY = os.getenv("LLM_ENCRYPTION_KEY", "")
if not ENCRYPTION_KEY:
    # Generar clave solo si no está configurada (NO recomendado para producción)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning("LLM_ENCRYPTION_KEY no configurada - usando clave generada (temporal)")
    logger.warning("Las API keys se perderán al reiniciar el contenedor")
    logger.warning("Configura LLM_ENCRYPTION_KEY en .env para persistencia")
else:
    logger.info("Clave de encriptación cargada desde entorno para API keys LLM")

fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_api_key(api_key: str) -> str:
    """Encripta una API key"""
    if not api_key:
        return ""
    encrypted = fernet.encrypt(api_key.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Desencripta una API key"""
    if not encrypted_key:
        return ""
    try:
        decoded = base64.b64decode(encrypted_key.encode())
        decrypted = fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Error desencriptando API key: {e}")
        return ""


class WorkspaceLLMConfigService:
    """Servicio para gestión de configuraciones LLM de workspaces usando ORM"""

    @staticmethod
    async def save_workspace_config(
        workspace_id: str,
        provider: str,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        model: Optional[str] = None,
        is_default: bool = False
    ) -> Dict[str, Any]:
        """
        Guarda o actualiza la configuración LLM de un workspace usando ORM.

        Args:
            workspace_id: ID del workspace
            provider: Proveedor (ollama, zai, minimax)
            api_key: API key (se encriptará)
            api_endpoint: Endpoint personalizado
            model: Modelo seleccionado
            is_default: Marcar como configuración default

        Returns:
            Configuración guardada
        """
        try:
            async with await db_manager.get_async_session() as session:
                # Importar entidad aquí para evitar dependencia circular
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                # Buscar configuración existente (prioridad: is_default=true, luego cualquiera con API key)
                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider
                    ).order_by(
                        WorkspaceLLMConfigEntity.is_default.desc(),
                        WorkspaceLLMConfigEntity.created_at.desc()
                    ).limit(1)
                )
                existing_config = result.scalar_one_or_none()

                # Encriptar API key si se proporciona
                encrypted_key = encrypt_api_key(api_key) if api_key else None

                if existing_config:
                    # Actualizar configuración existente
                    if encrypted_key is not None:
                        existing_config.api_key = encrypted_key
                    if api_endpoint is not None:
                        existing_config.api_endpoint = api_endpoint
                    if model is not None:
                        existing_config.model = model
                    existing_config.is_default = is_default
                else:
                    # Crear nueva configuración
                    new_config = WorkspaceLLMConfigEntity(
                        workspace_id=UUID(workspace_id),
                        provider=provider,
                        api_key=encrypted_key,
                        api_endpoint=api_endpoint,
                        model=model,
                        model_role="default",  # Este método es para la vista antigua, siempre es default
                        is_default=is_default
                    )
                    session.add(new_config)

                # Si esta es la default, quitar marca de default a OTRAS configs del workspace (todos los providers)
                if is_default:
                    await session.execute(
                        update(WorkspaceLLMConfigEntity)
                        .filter(
                            WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                            WorkspaceLLMConfigEntity.id != (existing_config.id if existing_config else None)
                        )
                        .values(is_default=False)
                    )

                await session.commit()
                logger.info(f"Configuración LLM guardada para workspace {workspace_id}, proveedor {provider}, is_default={is_default}")

            return await WorkspaceLLMConfigService.get_workspace_config(workspace_id, provider)

        except Exception as e:
            logger.error(f"Error guardando configuración LLM: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_workspace_config(
        workspace_id: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración LLM de un workspace para un proveedor usando ORM.

        Prioriza la configuración con is_default=true o model_role='default'.

        Args:
            workspace_id: ID del workspace
            provider: Proveedor

        Returns:
            Configuración con API key desencriptada, o None si no existe
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                # Buscar primero la configuración con is_default=true
                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider,
                        WorkspaceLLMConfigEntity.is_default == True
                    )
                )
                config = result.scalar_one_or_none()

                # Si no hay con is_default=true, buscar cualquiera con API key
                if not config:
                    result = await session.execute(
                        select(WorkspaceLLMConfigEntity).filter(
                            WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                            WorkspaceLLMConfigEntity.provider == provider,
                            WorkspaceLLMConfigEntity.api_key.is_not(None)
                        ).order_by(
                            WorkspaceLLMConfigEntity.created_at.desc()
                        ).limit(1)
                    )
                    config = result.scalar_one_or_none()

                if not config:
                    return None

                # Desencriptar API key
                decrypted_key = decrypt_api_key(config.api_key) if config.api_key else None

                return {
                    'id': str(config.id),
                    'workspace_id': str(config.workspace_id),
                    'provider': config.provider,
                    'apiKey': decrypted_key,
                    'apiEndpoint': config.api_endpoint,
                    'model': config.model,
                    'isDefault': config.is_default
                }
        except Exception as e:
            logger.error(f"Error obteniendo configuración LLM: {e}")
            return None

    @staticmethod
    async def get_any_config_with_credentials(
        workspace_id: str,
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene cualquier configuración LLM de un workspace para un proveedor que tenga API key.

        NO prioriza is_default. Busca cualquiera con API key.

        Args:
            workspace_id: ID del workspace
            provider: Proveedor

        Returns:
            Configuración con API key desencriptada, o None si no existe
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                # Buscar cualquier configuración con API key (sin priorizar is_default)
                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider,
                        WorkspaceLLMConfigEntity.api_key.is_not(None)
                    ).order_by(
                        WorkspaceLLMConfigEntity.created_at.desc()
                    ).limit(1)
                )
                config = result.scalar_one_or_none()

                if not config:
                    return None

                # Desencriptar API key
                decrypted_key = decrypt_api_key(config.api_key) if config.api_key else None

                return {
                    'id': str(config.id),
                    'workspace_id': str(config.workspace_id),
                    'provider': config.provider,
                    'apiKey': decrypted_key,
                    'apiEndpoint': config.api_endpoint,
                    'model': config.model,
                    'isDefault': config.is_default
                }
        except Exception as e:
            logger.error(f"Error obteniendo configuración LLM: {e}")
            return None

    @staticmethod
    async def get_all_workspace_configs(workspace_id: str) -> list[Dict[str, Any]]:
        """
        Obtiene todas las configuraciones LLM de un workspace usando ORM.

        Args:
            workspace_id: ID del workspace

        Returns:
            Lista de configuraciones (sin API keys desencriptadas)
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id)
                    ).order_by(
                        WorkspaceLLMConfigEntity.is_default.desc(),
                        WorkspaceLLMConfigEntity.provider
                    )
                )
                configs = result.scalars().all()

                return [
                    {
                        'id': str(config.id),
                        'workspace_id': str(config.workspace_id),
                        'provider': config.provider,
                        'apiEndpoint': config.api_endpoint,
                        'model': config.model,
                        'isDefault': config.is_default,
                        'hasCredentials': bool(config.api_key)
                    }
                    for config in configs
                ]
        except Exception as e:
            logger.error(f"Error obteniendo configuraciones LLM: {e}")
            return []

    @staticmethod
    async def delete_workspace_config(workspace_id: str, provider: str) -> bool:
        """
        Elimina la configuración LLM de un workspace para un proveedor usando ORM.

        Args:
            workspace_id: ID del workspace
            provider: Proveedor

        Returns:
            True si se eliminó, False si no existía
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider
                    )
                )
                config = result.scalar_one_or_none()

                if config:
                    await session.delete(config)
                    await session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error eliminando configuración LLM: {e}")
            return False

    @staticmethod
    async def save_model_config_with_role(
        workspace_id: str,
        provider: str,
        model: str,
        role: str = "default",
        priority: Optional[int] = None,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guarda o actualiza la configuración LLM con un rol específico.

        Args:
            workspace_id: ID del workspace
            provider: Proveedor (ollama, zai, minimax)
            model: Modelo seleccionado
            role: Rol del modelo (default, fallback, evaluator)
            priority: Prioridad para fallback (menor = mayor prioridad)
            api_key: API key (se encriptará)
            api_endpoint: Endpoint personalizado

        Returns:
            Configuración guardada
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                # Buscar configuración existente con mismo provider y role
                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider,
                        WorkspaceLLMConfigEntity.model_role == role
                    )
                )
                existing_config = result.scalar_one_or_none()

                # Encriptar API key si se proporciona
                encrypted_key = encrypt_api_key(api_key) if api_key else None

                if existing_config:
                    # Actualizar campos específicos
                    if encrypted_key is not None:
                        existing_config.api_key = encrypted_key
                    if api_endpoint is not None:
                        existing_config.api_endpoint = api_endpoint
                    existing_config.model = model
                    existing_config.priority = priority
                    # No cambiar is_default, se maneja aparte
                else:
                    # Crear nueva configuración
                    new_config = WorkspaceLLMConfigEntity(
                        workspace_id=UUID(workspace_id),
                        provider=provider,
                        model=model,
                        model_role=role,
                        priority=priority,
                        api_key=encrypted_key,
                        api_endpoint=api_endpoint,
                        is_default=(role == "default")  # Solo default marca is_default
                    )
                    session.add(new_config)

                await session.commit()
                logger.info(f"Configuración LLM guardada: workspace={workspace_id}, provider={provider}, role={role}")

            return await WorkspaceLLMConfigService.get_workspace_config(workspace_id, provider)

        except Exception as e:
            logger.error(f"Error guardando configuración LLM con rol: {e}", exc_info=True)
            raise

    @staticmethod
    async def get_models_by_role(workspace_id: str, role: str) -> list[Dict[str, Any]]:
        """
        Obtiene todos los modelos de un rol específico.

        Args:
            workspace_id: ID del workspace
            role: Rol del modelo (default, fallback, evaluator)

        Returns:
            Lista de configuraciones ordenadas por priority (para fallback)
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.model_role == role
                    ).order_by(
                        WorkspaceLLMConfigEntity.priority.asc(),  # NULLs last
                        WorkspaceLLMConfigEntity.provider
                    )
                )
                configs = result.scalars().all()

                return [
                    {
                        'id': str(config.id),
                        'provider': config.provider,
                        'model': config.model,
                        'role': config.model_role,
                        'priority': config.priority,
                        'hasApiKey': bool(config.api_key),
                        'apiEndpoint': config.api_endpoint
                    }
                    for config in configs
                ]
        except Exception as e:
            logger.error(f"Error obteniendo modelos por rol {role}: {e}")
            return []

    @staticmethod
    async def get_model_selection_config(workspace_id: str) -> Dict[str, Any]:
        """
        Retorna la configuración completa de selección de modelos del workspace.

        Returns:
            Dict con:
            - default: modelo principal
            - fallback: lista de modelos fallback ordenados por priority
            - evaluators: lista de modelos evaluadores
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                # Buscar modelos con is_default=true (puede haber múltiples por legado)
                # Tomar el primero (el más reciente según created_at)
                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.is_default == True
                    ).order_by(
                        WorkspaceLLMConfigEntity.created_at.desc()
                    ).limit(1)
                )
                default_config = result.scalar_one_or_none()

                default_model = None
                if default_config:
                    default_model = {
                        'id': str(default_config.id),
                        'provider': default_config.provider,
                        'model': default_config.model,
                        'role': default_config.model_role,
                        'priority': default_config.priority,
                        'hasApiKey': bool(default_config.api_key),
                        'apiEndpoint': default_config.api_endpoint
                    }

            # Obtener fallbacks y evaluators
            fallback_models = await WorkspaceLLMConfigService.get_models_by_role(workspace_id, "fallback")
            evaluator_models = await WorkspaceLLMConfigService.get_models_by_role(workspace_id, "evaluator")

            return {
                'default': default_model,
                'fallback': fallback_models,
                'evaluators': evaluator_models
            }
        except Exception as e:
            logger.error(f"Error obteniendo configuración de selección: {e}")
            return {'default': None, 'fallback': [], 'evaluators': []}

    @staticmethod
    async def set_model_priority(workspace_id: str, provider: str, role: str, priority: int) -> None:
        """
        Establece el priority de un modelo.

        Args:
            workspace_id: ID del workspace
            provider: Proveedor
            role: Rol del modelo
            priority: Nueva prioridad
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider,
                        WorkspaceLLMConfigEntity.model_role == role
                    )
                )
                config = result.scalar_one_or_none()

                if config:
                    config.priority = priority
                    await session.commit()
                    logger.info(f"Priority actualizado: workspace={workspace_id}, provider={provider}, role={role}, priority={priority}")
        except Exception as e:
            logger.error(f"Error estableciendo priority: {e}")
            raise

    @staticmethod
    async def delete_model_config_by_role(workspace_id: str, provider: str, role: str) -> bool:
        """
        Elimina una configuración de modelo específica (provider + role).

        Args:
            workspace_id: ID del workspace
            provider: Proveedor
            role: Rol del modelo

        Returns:
            True si se eliminó, False si no existía
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id),
                        WorkspaceLLMConfigEntity.provider == provider,
                        WorkspaceLLMConfigEntity.model_role == role
                    )
                )
                config = result.scalar_one_or_none()

                if config:
                    await session.delete(config)
                    await session.commit()
                    logger.info(f"Configuración eliminada: workspace={workspace_id}, provider={provider}, role={role}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Error eliminando configuración por rol: {e}")
            return False

    @staticmethod
    async def save_batch_model_config(
        workspace_id: str,
        default_config: Optional[Dict[str, Any]] = None,
        fallback_configs: List[Dict[str, Any]] = None,
        evaluator_configs: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Guarda múltiples configuraciones LLM en una sola transacción.

        Args:
            workspace_id: ID del workspace
            default_config: Configuración del modelo default {provider, model, credentials, ...}
            fallback_configs: Lista de configs fallback
            evaluator_configs: Lista de configs evaluadores

        Returns:
            Configuración guardada completa
        """
        try:
            async with await db_manager.get_async_session() as session:
                from models.orm.entities import WorkspaceLLMConfig as WorkspaceLLMConfigEntity

                # Obtener todas las configs actuales del workspace
                result = await session.execute(
                    select(WorkspaceLLMConfigEntity).filter(
                        WorkspaceLLMConfigEntity.workspace_id == UUID(workspace_id)
                    )
                )
                existing_configs = result.scalars().all()

                # Crear set de (provider, role) que se van a guardar
                configs_to_keep = set()

                # Procesar default
                if default_config:
                    provider = default_config.get("provider")
                    model = default_config.get("model")
                    credentials = default_config.get("credentials")
                    role = "default"

                    configs_to_keep.add((provider, role))

                    # Buscar o crear config
                    existing = next(
                        (c for c in existing_configs if c.provider == provider and c.model_role == role),
                        None
                    )

                    # Extraer API key y endpoint de credenciales
                    api_key = None
                    api_endpoint = None
                    if credentials and provider in credentials:
                        provider_creds = credentials[provider]
                        api_key = provider_creds.get("apiKey") if provider_creds else None
                        api_endpoint = provider_creds.get("apiEndpoint") if provider_creds else None

                    encrypted_key = encrypt_api_key(api_key) if api_key else None

                    if existing:
                        existing.model = model
                        existing.priority = None
                        existing.is_default = True
                        if encrypted_key is not None:
                            existing.api_key = encrypted_key
                        if api_endpoint is not None:
                            existing.api_endpoint = api_endpoint
                    else:
                        new_config = WorkspaceLLMConfigEntity(
                            workspace_id=UUID(workspace_id),
                            provider=provider,
                            model=model,
                            model_role=role,
                            priority=None,
                            api_key=encrypted_key,
                            api_endpoint=api_endpoint,
                            is_default=True
                        )
                        session.add(new_config)

                # Procesar fallbacks
                if fallback_configs:
                    for i, fb_config in enumerate(fallback_configs):
                        provider = fb_config.get("provider")
                        model = fb_config.get("model")
                        credentials = fb_config.get("credentials")
                        role = "fallback"
                        priority = i + 1

                        configs_to_keep.add((provider, role))

                        existing = next(
                            (c for c in existing_configs if c.provider == provider and c.model_role == role),
                            None
                        )

                        api_key = None
                        api_endpoint = None
                        if credentials and provider in credentials:
                            provider_creds = credentials[provider]
                            api_key = provider_creds.get("apiKey") if provider_creds else None
                            api_endpoint = provider_creds.get("apiEndpoint") if provider_creds else None

                        encrypted_key = encrypt_api_key(api_key) if api_key else None

                        if existing:
                            existing.model = model
                            existing.priority = priority
                            existing.is_default = False
                            if encrypted_key is not None:
                                existing.api_key = encrypted_key
                            if api_endpoint is not None:
                                existing.api_endpoint = api_endpoint
                        else:
                            new_config = WorkspaceLLMConfigEntity(
                                workspace_id=UUID(workspace_id),
                                provider=provider,
                                model=model,
                                model_role=role,
                                priority=priority,
                                api_key=encrypted_key,
                                api_endpoint=api_endpoint,
                                is_default=False
                            )
                            session.add(new_config)

                # Procesar evaluators
                if evaluator_configs:
                    for eval_config in evaluator_configs:
                        provider = eval_config.get("provider")
                        model = eval_config.get("model")
                        credentials = eval_config.get("credentials")
                        role = "evaluator"

                        configs_to_keep.add((provider, role))

                        existing = next(
                            (c for c in existing_configs if c.provider == provider and c.model_role == role),
                            None
                        )

                        api_key = None
                        api_endpoint = None
                        if credentials and provider in credentials:
                            provider_creds = credentials[provider]
                            api_key = provider_creds.get("apiKey") if provider_creds else None
                            api_endpoint = provider_creds.get("apiEndpoint") if provider_creds else None

                        encrypted_key = encrypt_api_key(api_key) if api_key else None

                        if existing:
                            existing.model = model
                            if encrypted_key is not None:
                                existing.api_key = encrypted_key
                            if api_endpoint is not None:
                                existing.api_endpoint = api_endpoint
                        else:
                            new_config = WorkspaceLLMConfigEntity(
                                workspace_id=UUID(workspace_id),
                                provider=provider,
                                model=model,
                                model_role=role,
                                priority=None,
                                api_key=encrypted_key,
                                api_endpoint=api_endpoint,
                                is_default=False
                            )
                            session.add(new_config)

                # Eliminar configs que no se incluyeron
                for config in existing_configs:
                    if (config.provider, config.model_role) not in configs_to_keep:
                        await session.delete(config)

                await session.commit()
                logger.info(f"Configuración batch guardada para workspace {workspace_id}")

            return await WorkspaceLLMConfigService.get_model_selection_config(workspace_id)

        except Exception as e:
            logger.error(f"Error guardando configuración batch: {e}", exc_info=True)
            raise


workspace_llm_config_service = WorkspaceLLMConfigService()
