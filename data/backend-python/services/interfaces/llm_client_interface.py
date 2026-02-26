"""
Interfaz para clientes LLM - Principio de Segregación de Interfaces (ISP)
"""
from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator


class LLMClientInterface(ABC):
    """
    Interfaz base para clientes LLM.
    Segregación de Interfaces: Define solo los métodos necesarios para generar explicaciones.
    """
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Genera una respuesta completa del modelo LLM.
        
        Args:
            prompt: Prompt principal
            context: Contexto adicional (RAG)
            system_prompt: Prompt del sistema
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens a generar
            
        Returns:
            Respuesta generada por el modelo
        """
        pass
    
    @abstractmethod
    async def generate_response_streaming(
        self,
        prompt: str,
        context: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        Genera una respuesta en streaming del modelo LLM.
        
        Args:
            prompt: Prompt principal
            context: Contexto adicional (RAG)
            system_prompt: Prompt del sistema
            temperature: Temperatura para la generación
            max_tokens: Máximo de tokens a generar
            
        Yields:
            Chunks de la respuesta generada
        """
        pass
    
    @abstractmethod
    async def check_available(self) -> bool:
        """
        Verifica si el cliente LLM está disponible.
        
        Returns:
            True si está disponible, False en caso contrario
        """
        pass
