"""
Servicio LLM para Z.ai
"""
import os
import logging
import asyncio
from typing import List, Optional, Dict, Any

try:
    from zai import ZaiClient
    ZAI_AVAILABLE = True
except ImportError:
    ZaiClient = None
    ZAI_AVAILABLE = False

from .base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)


class ZaiService(BaseLLMService):
    """Servicio LLM usando Z.ai SDK oficial

    Documentación: https://docs.z.ai/guides/develop/python/introduction
    """

    def __init__(self):
        super().__init__()
        if not ZAI_AVAILABLE:
            logger.warning("zai-sdk no está instalado. ZaiService estará limitado.")
            logger.warning("Para habilitar Z.ai: pip install zai-sdk")

        # Configuración desde variables de entorno
        self.default_api_key = os.getenv("ZAI_API_KEY")
        # Para GLM se requiere el endpoint /api/coding/paas/v4/
        self.default_base_url = os.getenv("ZAI_API_ENDPOINT", "https://api.z.ai/api/coding/paas/v4/")
        self.default_model = os.getenv("ZAI_MODEL", "glm-4.6")

        logger.info(f"ZaiService inicializado (disponible: {ZAI_AVAILABLE}):")
        logger.info(f"  - Base URL: {self.default_base_url}")
        logger.info(f"  - Modelo: {self.default_model}")

        # Configuración desde variables de entorno
        self.default_api_key = os.getenv("ZAI_API_KEY")
        # Para GLM se requiere el endpoint /api/coding/paas/v4/
        self.default_base_url = os.getenv("ZAI_API_ENDPOINT", "https://api.z.ai/api/coding/paas/v4/")
        self.default_model = os.getenv("ZAI_MODEL", "glm-4.6")

        logger.info(f"ZaiService inicializado:")
        logger.info(f"  - Base URL: {self.default_base_url}")
        logger.info(f"  - Modelo: {self.default_model}")

    def _normalize_base_url(self, url: Optional[str]) -> Optional[str]:
        """Normaliza la URL base para que no incluya /chat/completions"""
        if url is None:
            return None

        # Remover /chat/completions si está al final
        if url.endswith('/chat/completions'):
            url = url[:-20].rstrip('/')
        elif '/chat/completions/' in url:
            url = url.replace('/chat/completions', '').rstrip('/')

        # Asegurar que termina con /
        if not url.endswith('/'):
            url += '/'

        return url

    def _get_client(self, api_key: str, base_url: Optional[str] = None) -> 'ZaiClient':
        """Crea y retorna un cliente de Z.ai configurado"""
        normalized_url = self._normalize_base_url(base_url or self.default_base_url)
        return ZaiClient(api_key=api_key, base_url=normalized_url)

    def _call_zai_sync(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        api_key: str,
        base_url: Optional[str] = None
    ) -> str:
        """Llamada síncrona a Z.ai SDK (para ejecutar en thread pool)"""
        client = self._get_client(api_key, base_url)

        # Construir mensajes
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            logger.info(f"=== Z.ai SDK Call ===")
            logger.info(f"Model: {model}")

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )

            # Verificar que response no sea None
            if response is None:
                raise ValueError("API returned None response")

            # Extraer contenido de la respuesta
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
            else:
                raise ValueError(f"Unexpected response format: {response}")

            return content

        except Exception as e:
            logger.error(f"Error in Z.ai SDK call: {type(e).__name__}: {e}")
            raise

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
        """Genera una respuesta usando Z.ai"""
        api_key = self._get_api_key(credentials)
        base_url = self._get_base_url(credentials)

        if not api_key:
            raise ValueError("ZAI_API_KEY no está configurada")

        model = model or self.default_model

        # Agregar contexto al prompt si se proporciona
        full_prompt = prompt
        if context:
            context_str = "\n".join(context)
            full_prompt = f"Contexto:\n{context_str}\n\n{prompt}"

        try:
            # Ejecutar llamada síncrona del SDK en thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._call_zai_sync,
                full_prompt,
                system_prompt,
                model,
                api_key,
                base_url
            )

            return response

        except Exception as e:
            logger.error(f"Error calling Z.ai: {type(e).__name__}: {e}")
            raise

    async def get_available_models(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Obtiene la lista de modelos disponibles desde Z.ai API"""
        if not ZAI_AVAILABLE:
            logger.warning("zai-sdk no está instalado")
            return []

        api_key = self._get_api_key(credentials)
        base_url = self._get_base_url(credentials)

        if not api_key:
            logger.warning("No API key provided for Z.ai")
            return []

        try:
            client = self._get_client(api_key, base_url)

            # Ejecutar llamada síncrona en thread pool
            loop = asyncio.get_event_loop()
            models_response = await loop.run_in_executor(
                None,
                client.models.list
            )

            # Extraer lista de modelos desde la respuesta
            if hasattr(models_response, 'data'):
                models = [model.id for model in models_response.data]
            elif isinstance(models_response, dict) and 'data' in models_response:
                models = [model['id'] for model in models_response['data']]
            else:
                logger.warning(f"Unexpected response format: {models_response}")
                models = []

            logger.info(f"Z.ai models found: {models}")
            return models

        except Exception as e:
            logger.error(f"Error getting Z.ai models: {type(e).__name__}: {e}")
            # Retornar lista de modelos comunes conocidos
            return [
                "glm-5",
                "glm-4.7",
                "glm-4.7-flash",
                "glm-4-plus",
                "glm-4-air",
                "glm-4-flash",
            ]

    async def check_available(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Verifica si Z.ai está disponible"""
        if not ZAI_AVAILABLE:
            return False

        api_key = self._get_api_key(credentials)

        if not api_key:
            return False

        try:
            models = await self.get_available_models(credentials)
            return len(models) > 0
        except Exception as e:
            logger.error(f"Error checking Z.ai availability: {e}")
            return False
