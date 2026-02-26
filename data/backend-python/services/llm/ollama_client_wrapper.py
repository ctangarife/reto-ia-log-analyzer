"""
Wrapper para Ollama usando ollama-client-lib
Responsabilidad Única: Comunicación con Ollama Cloud
"""
import os
import logging
from typing import List, Optional, AsyncIterator

try:
    from ollama_client_lib import OllamaClient
except ImportError:
    OllamaClient = None

from ..interfaces.llm_client_interface import LLMClientInterface

logger = logging.getLogger(__name__)


class OllamaClientWrapper(LLMClientInterface):
    """
    Wrapper para Ollama Cloud usando ollama-client-lib.
    Responsabilidad Única: Gestionar la comunicación con Ollama Cloud.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 120.0
    ):
        """
        Inicializa el cliente de Ollama.
        
        Args:
            api_key: API key de Ollama Cloud (o desde OLLAMA_API_KEY)
            base_url: URL base de Ollama Cloud (default: https://ollama.com)
            default_model: Modelo por defecto (o desde OLLAMA_MODEL/MODEL_NAME)
            timeout: Timeout para peticiones en segundos
        """
        if OllamaClient is None:
            raise ImportError(
                "ollama-client-lib no está instalado. "
                "Instala con: pip install ollama-client-lib"
            )
        
        # Leer configuración desde variables de entorno si no se proporciona
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OLLAMA_API_KEY no está configurada. "
                "Configúrala en .env o como parámetro."
            )
        
        self.base_url = base_url or os.getenv("OLLAMA_URL", "https://ollama.com")
        self.default_model = (
            default_model 
            or os.getenv("OLLAMA_MODEL") 
            or os.getenv("MODEL_NAME", "qwen2.5:3b")
        )
        self.timeout = timeout
        
        logger.info(f"OllamaClientWrapper inicializado:")
        logger.info(f"  - Base URL: {self.base_url}")
        logger.info(f"  - Modelo: {self.default_model}")
        logger.info(f"  - Timeout: {self.timeout}s")
    
    def _create_client(self) -> OllamaClient:
        """
        Crea una nueva instancia del cliente Ollama.
        El cliente se usa como context manager en cada llamada.
        """
        return OllamaClient(
            api_key=self.api_key,
            base_url=self.base_url,
            default_model=self.default_model,
            timeout=self.timeout
        )
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Genera una respuesta completa del modelo LLM."""
        try:
            client = self._create_client()
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
    
    async def generate_response_streaming(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """Genera una respuesta en streaming del modelo LLM."""
        try:
            client = self._create_client()
            async with client:
                async for chunk in client.generate_response_streaming(
                    prompt=prompt,
                    context=context,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    yield chunk
        except Exception as e:
            logger.error(f"Error en streaming con Ollama: {e}")
            raise
    
    async def check_available(self) -> bool:
        """Verifica si el cliente LLM está disponible."""
        try:
            client = self._create_client()
            async with client:
                # Verificar que el modelo esté disponible
                available = await client.check_model_available(self.default_model)
                return available
        except Exception as e:
            logger.error(f"Error verificando disponibilidad de Ollama: {e}")
            return False
