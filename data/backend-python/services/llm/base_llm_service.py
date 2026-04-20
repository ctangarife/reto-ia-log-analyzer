"""
Clase base para servicios LLM multi-proveedor
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseLLMService(ABC):
    """Clase base para servicios LLM con interfaz unificada"""

    def __init__(self):
        self.default_api_key: Optional[str] = None
        self.default_base_url: Optional[str] = None
        self.default_model: str = ""

    @abstractmethod
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
        """
        Genera una respuesta completa del modelo LLM.

        Args:
            prompt: Prompt principal
            context: Contexto adicional (RAG)
            system_prompt: Prompt del sistema
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens a generar
            model: Modelo a usar (opcional, usa default si no se especifica)
            credentials: Credenciales dinámicas (opcional)

        Returns:
            Respuesta generada por el modelo
        """
        pass

    @abstractmethod
    async def get_available_models(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Obtiene la lista de modelos disponibles del proveedor.

        Args:
            credentials: Credenciales dinámicas (opcional)

        Returns:
            Lista de nombres de modelos disponibles
        """
        pass

    @abstractmethod
    async def check_available(
        self,
        credentials: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Verifica si el servicio LLM está disponible.

        Args:
            credentials: Credenciales dinámicas (opcional)

        Returns:
            True si está disponible, False en caso contrario
        """
        pass

    def _get_api_key(self, credentials: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Obtiene la API key desde credenciales o configuración default"""
        if credentials and credentials.get("apiKey"):
            return credentials.get("apiKey")
        return self.default_api_key

    def _get_base_url(self, credentials: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Obtiene la base URL desde credenciales o configuración default"""
        if credentials and credentials.get("apiEndpoint"):
            return credentials.get("apiEndpoint")
        return self.default_base_url
