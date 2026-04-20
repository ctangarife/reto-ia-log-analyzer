"""
Servicio LLM para Ollama Cloud
"""
import os
import logging
from typing import List, Optional, Dict, Any

try:
    from ollama_client_lib import OllamaClient
except ImportError:
    OllamaClient = None

from .base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)


class OllamaService(BaseLLMService):
    """Servicio LLM usando ollama-client-lib para Ollama Cloud"""

    def __init__(self):
        super().__init__()
        if OllamaClient is None:
            raise ImportError(
                "ollama-client-lib no está instalado. "
                "Instala con: pip install ollama-client-lib"
            )

        # Configuración desde variables de entorno
        self.default_api_key = os.getenv("OLLAMA_API_KEY")
        self.default_base_url = os.getenv("OLLAMA_URL", "https://ollama.com")
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.timeout = 120.0

        logger.info(f"OllamaService inicializado:")
        logger.info(f"  - Base URL: {self.default_base_url}")
        logger.info(f"  - Modelo: {self.default_model}")

    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> str:
        """Genera una respuesta usando Ollama Cloud"""
        api_key = self._get_api_key(credentials)
        base_url = self._get_base_url(credentials)
        model = model or self.default_model

        if not api_key:
            raise ValueError("OLLAMA_API_KEY no está configurada")

        try:
            client = OllamaClient(
                api_key=api_key,
                base_url=base_url,
                default_model=model,
                timeout=self.timeout
            )

            async with client:
                response = await client.generate_response(
                    prompt=prompt,
                    context=context,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response

        except Exception as e:
            logger.error(f"Error generando respuesta con Ollama: {e}")
            raise

    async def get_available_models(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Obtiene la lista de modelos disponibles desde Ollama Cloud"""
        api_key = self._get_api_key(credentials)
        base_url = self._get_base_url(credentials)

        if not api_key:
            logger.warning("No API key provided for Ollama")
            return []

        try:
            client = OllamaClient(api_key=api_key, base_url=base_url)

            async with client:
                models = await client.list_available_models()

            logger.info(f"Ollama models returned: {models}")
            return models

        except Exception as e:
            logger.error(f"Error getting Ollama models: {e}")
            return []

    async def check_available(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Verifica si Ollama Cloud está disponible"""
        api_key = self._get_api_key(credentials)

        if not api_key:
            return False

        try:
            models = await self.get_available_models(credentials)
            return len(models) > 0
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            return False
