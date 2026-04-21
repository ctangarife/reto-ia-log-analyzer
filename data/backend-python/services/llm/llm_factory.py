"""
Factory Pattern para servicios LLM multi-proveedor
"""
import logging
from typing import Optional, Dict, Any

from models.schemas.llm import LLMProvider
from .base_llm_service import BaseLLMService
from .ollama_service import OllamaService
from .zai_service import ZaiService
from .minimax_service import MiniMaxService

logger = logging.getLogger(__name__)


# Cache de instancias de servicios
_service_instances: Dict[LLMProvider, BaseLLMService] = {}


def get_llm_service(
    provider: LLMProvider,
    credentials: Optional[Dict[str, Any]] = None
) -> BaseLLMService:
    """
    Factory para obtener el servicio LLM correspondiente

    Args:
        provider: Proveedor LLM deseado
        credentials: Credenciales dinámicas (opcional)

    Returns:
        Instancia del servicio LLM correspondiente
    """
    services = {
        LLMProvider.ollama: OllamaService,
        LLMProvider.zai: ZaiService,
        LLMProvider.minimax: MiniMaxService,
    }

    service_class = services.get(provider)
    if not service_class:
        raise ValueError(f"Proveedor LLM no soportado: {provider}")

    # Crear nueva instancia (los servicios manejan credenciales dinámicamente)
    try:
        service = service_class()
        logger.info(f"Servicio LLM creado: {provider}")
        return service
    except Exception as e:
        logger.error(f"Error creando servicio LLM {provider}: {e}")
        raise


def get_default_llm_service() -> BaseLLMService:
    """Retorna el servicio LLM configurado por defecto"""
    import os
    default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "ollama")
    try:
        provider = LLMProvider(default_provider)
        return get_llm_service(provider)
    except ValueError:
        logger.warning(f"Proveedor default inválido: {default_provider}, usando ollama")
        return get_llm_service(LLMProvider.ollama)


async def get_llm_service_with_fallback(
    workspace_id: str,
    role: str = "default"
) -> tuple[BaseLLMService, Optional[Dict[str, Any]], Optional[str]]:
    """
    Obtiene el servicio LLM con fallback automático.

    Intenta en orden:
    1. Modelo default del workspace
    2. Modelos fallback ordenados por priority
    3. Retorna None si no hay disponibles

    Args:
        workspace_id: ID del workspace
        role: Rol a buscar (default para obtener default + fallbacks)

    Returns:
        Tuple (servicio, credenciales, model_info) del primer modelo disponible
        model_info es un dict con {provider, model, role}
    """
    from services.workspace_llm_config_service import workspace_llm_config_service

    # 1. Obtener modelo default
    default_config = await workspace_llm_config_service.get_models_by_role(workspace_id, "default")
    logger.info(f"Default config obtenida: {default_config}")
    if default_config:
        config = default_config[0]
        try:
            # Obtener credenciales completas
            full_config = await workspace_llm_config_service.get_workspace_config(
                workspace_id, config['provider']
            )
            logger.info(f"Full config para {config['provider']}: has_apiKey={bool(full_config and full_config.get('apiKey'))}")
            if full_config and full_config.get('apiKey'):
                provider = LLMProvider(config['provider'])
                service = get_llm_service(provider)
                credentials = {
                    'apiKey': full_config['apiKey'],
                    'apiEndpoint': full_config.get('apiEndpoint')
                }

                # Verificar disponibilidad
                if await service.check_available(credentials):
                    logger.info(f"Usando modelo default: {provider.value}/{config['model']}")
                    return service, credentials, {
                        'provider': config['provider'],
                        'model': config['model'],
                        'role': 'default'
                    }
            else:
                logger.warning(f"No se encontró apiKey en config para {config['provider']}")
        except Exception as e:
            logger.warning(f"Modelo default no disponible: {e}")
    else:
        logger.warning(f"No se encontró config default para workspace {workspace_id}")

    # 2. Intentar fallbacks
    fallback_configs = await workspace_llm_config_service.get_models_by_role(workspace_id, "fallback")
    for config in fallback_configs:
        try:
            full_config = await workspace_llm_config_service.get_workspace_config(
                workspace_id, config['provider']
            )
            if full_config and full_config.get('apiKey'):
                provider = LLMProvider(config['provider'])
                service = get_llm_service(provider)
                credentials = {
                    'apiKey': full_config['apiKey'],
                    'apiEndpoint': full_config.get('apiEndpoint')
                }

                if await service.check_available(credentials):
                    logger.info(f"Usando modelo fallback: {provider.value}/{config['model']} (priority: {config.get('priority')})")
                    return service, credentials, {
                        'provider': config['provider'],
                        'model': config['model'],
                        'role': 'fallback'
                    }
        except Exception as e:
            logger.warning(f"Fallback {config['provider']}/{config['model']} no disponible: {e}")
            continue

    # 3. No hay modelos disponibles
    logger.warning(f"No hay modelos LLM disponibles para workspace {workspace_id}")
    return get_default_llm_service(), None, None
