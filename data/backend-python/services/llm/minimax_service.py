"""
Servicio LLM para MiniMax
"""
import os
import logging
from typing import List, Optional, Dict, Any

try:
    import httpx
except ImportError:
    httpx = None

from .base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)


class MiniMaxService(BaseLLMService):
    """Servicio LLM usando MiniMax (API Anthropic-compatible)

    Documentación: https://platform.minimaxi.com/docs/api-reference/text-anthropic-api
    """

    def __init__(self):
        super().__init__()
        if httpx is None:
            raise ImportError(
                "httpx no está instalado. "
                "Instala con: pip install httpx"
            )

        # Configuración desde variables de entorno
        self.default_api_key = os.getenv("MINIMAX_API_KEY")
        self.default_base_url = os.getenv(
            "MINIMAX_API_ENDPOINT",
            "https://api.minimaxi.com/v1/chat/completions"
        )
        self.default_model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

        logger.info(f"MiniMaxService inicializado:")
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
        """Genera una respuesta usando MiniMax API"""
        api_key = self._get_api_key(credentials)
        base_url = self._get_base_url(credentials)

        if not api_key:
            raise ValueError("MINIMAX_API_KEY no está configurada")

        model = model or self.default_model

        # Headers formato Anthropic
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }

        # Construir mensajes
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Agregar contexto al prompt si se proporciona
        full_prompt = prompt
        if context:
            context_str = "\n".join(context)
            full_prompt = f"Contexto:\n{context_str}\n\n{prompt}"

        messages.append({"role": "user", "content": full_prompt})

        # Payload
        payload = {
            "model": model,
            "max_tokens": max_tokens or 4096,
            "messages": messages
        }

        try:
            logger.info(f"=== MiniMax API Call ===")
            logger.info(f"Model: {model}")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(base_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                # Respuesta formato Anthropic: content[0].text
                if "content" in data and len(data["content"]) > 0:
                    # Buscar el primer item con 'text'
                    text = None
                    for item in data["content"]:
                        if "text" in item:
                            text = item["text"]
                            break

                    # Si no hay 'text', usar el primer thinking como fallback
                    if text is None:
                        text = data["content"][0].get("thinking", "")

                    return text

                raise ValueError(f"Respuesta inesperada de MiniMax: {data}")

        except Exception as e:
            logger.error(f"Error calling MiniMax: {e}")
            raise

    async def get_available_models(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Retorna la lista de modelos disponibles de MiniMax

        NOTA: MiniMax NO tiene un endpoint /v1/models. Los modelos son estáticos.
        """
        api_key = self._get_api_key(credentials)

        if not api_key:
            logger.warning("No API key provided for MiniMax")
            return []

        # MiniMax no tiene endpoint para listar modelos.
        # Estos son los modelos documentados oficialmente (2026):
        return [
            "MiniMax-M2.5",           # Top performance, 204K context
            "MiniMax-M2.5-highspeed", # M2.5 high-speed version
            "MiniMax-M2.1",           # Multilingual coding, 204K context
            "MiniMax-M2.1-highspeed", # M2.1 high-speed version
            "MiniMax-M2",             # Coding & Agent workflows
        ]

    async def check_available(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Verifica si MiniMax está disponible"""
        api_key = self._get_api_key(credentials)

        if not api_key:
            return False

        # MiniMax está disponible si hay API key
        return True
