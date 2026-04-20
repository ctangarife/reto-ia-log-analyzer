"""
Módulo de servicios LLM multi-proveedor
"""
# Mantener compatibilidad con el código existente
from .ollama_client_wrapper import OllamaClientWrapper

# Nuevos servicios multi-proveedor
from .base_llm_service import BaseLLMService
from .ollama_service import OllamaService
from .zai_service import ZaiService
from .minimax_service import MiniMaxService
from .llm_factory import get_llm_service, get_default_llm_service, get_llm_service_with_fallback
from .llm_adapter import LLMServiceAdapter

__all__ = [
    # Compatibilidad hacia atrás
    'OllamaClientWrapper',
    # Nuevos servicios
    'BaseLLMService',
    'OllamaService',
    'ZaiService',
    'MiniMaxService',
    'get_llm_service',
    'get_default_llm_service',
    'get_llm_service_with_fallback',
    'LLMServiceAdapter',
]
