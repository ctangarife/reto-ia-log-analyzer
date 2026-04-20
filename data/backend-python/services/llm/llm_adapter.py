"""
Adaptador para compatibilidad entre BaseLLMService y LLMClientInterface
"""
import logging
from typing import List, Optional

from ..interfaces.llm_client_interface import LLMClientInterface
from .base_llm_service import BaseLLMService

logger = logging.getLogger(__name__)


class LLMServiceAdapter(LLMClientInterface):
    """
    Adaptador que implementa LLMClientInterface usando BaseLLMService.
    Permite que los nuevos servicios multi-proveedor sean compatibles con
    la arquitectura existente que espera LLMClientInterface.
    """

    def __init__(
        self,
        llm_service: BaseLLMService,
        provider: str,
        model: Optional[str] = None,
        credentials: Optional[dict] = None
    ):
        """
        Inicializa el adaptador.

        Args:
            llm_service: Instancia del servicio LLM (BaseLLMService)
            provider: Nombre del proveedor (para logging)
            model: Modelo a usar (opcional)
            credentials: Credenciales dinámicas (opcional)
        """
        self.llm_service = llm_service
        self.provider = provider
        self.model = model
        self.credentials = credentials

        logger.info(f"LLMServiceAdapter creado para {provider}")

    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Genera una respuesta usando el servicio LLM subyacente"""
        try:
            return await self.llm_service.generate_response(
                prompt=prompt,
                context=context,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model=self.model,
                credentials=self.credentials
            )
        except Exception as e:
            logger.error(f"Error en LLMServiceAdapter.generate_response: {e}")
            raise

    async def generate_response_streaming(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Genera una respuesta en streaming.

        NOTA: No todos los proveedores soportan streaming.
        Para los que no soportan, genera la respuesta completa y la yield.
        """
        try:
            # Most providers don't support streaming in the new interface yet
            # Generate full response and yield it as single chunk
            response = await self.llm_service.generate_response(
                prompt=prompt,
                context=context,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model=self.model,
                credentials=self.credentials
            )
            yield response
        except Exception as e:
            logger.error(f"Error en LLMServiceAdapter.generate_response_streaming: {e}")
            raise

    async def check_available(self) -> bool:
        """Verifica si el servicio LLM está disponible"""
        try:
            return await self.llm_service.check_available(self.credentials)
        except Exception as e:
            logger.error(f"Error verificando disponibilidad: {e}")
            return False
