"""
Servicio de explicaciones - Orquestador principal
Principio de Responsabilidad Única: Orquestar la generación de explicaciones
Usa composición de servicios especializados en lugar de hacer todo internamente
"""
import os
import logging
from typing import List, Tuple, Optional

from .interfaces import LLMClientInterface
from .llm import OllamaClientWrapper
from .log_analysis import LogParser, LogMetadata
from .prompts import PromptBuilder
from .explanation import ResponseParser, FallbackExplanationGenerator

logger = logging.getLogger(__name__)


class ExplanationService:
    """
    Servicio de explicaciones - Responsabilidad Única: Orquestar la generación de explicaciones.
    
    Usa composición de servicios especializados:
    - LogParser: Extrae información de logs
    - PromptBuilder: Construye prompts
    - LLMClientInterface: Comunica con el LLM (abstracción)
    - ResponseParser: Parsea respuestas
    - FallbackExplanationGenerator: Genera explicaciones de respaldo
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClientInterface] = None,
        log_parser: Optional[LogParser] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        fallback_generator: Optional[FallbackExplanationGenerator] = None
    ):
        """
        Inicializa el servicio de explicaciones con dependencias inyectadas.
        
        Args:
            llm_client: Cliente LLM (si None, crea OllamaClientWrapper)
            log_parser: Parser de logs (si None, crea uno nuevo)
            prompt_builder: Constructor de prompts (si None, crea uno nuevo)
            response_parser: Parser de respuestas (si None, crea uno nuevo)
            fallback_generator: Generador de fallback (si None, crea uno nuevo)
        """
        # Inyección de dependencias - permite testing y flexibilidad
        self.llm_client = llm_client or self._create_llm_client()
        self.log_parser = log_parser or LogParser()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_parser = response_parser or ResponseParser()
        self.fallback_generator = fallback_generator or FallbackExplanationGenerator()
        
        # Configuración desde variables de entorno
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "200"))
        
        logger.info("ExplanationService inicializado con servicios especializados")
    
    def _create_llm_client(self) -> LLMClientInterface:
        """Crea el cliente LLM por defecto (Ollama Cloud)."""
        try:
            return OllamaClientWrapper()
        except (ValueError, ImportError) as e:
            logger.warning(f"No se pudo crear cliente Ollama: {e}")
            logger.warning("Se usará fallback para todas las explicaciones")
            return None
    
    async def get_llm_explanation(self, log_entry: str, score: float) -> str:
        """
        Obtiene una explicación inteligente del LLM para un log anómalo.
        
        Args:
            log_entry: Entrada de log
            score: Score de anomalía
            
        Returns:
            Explicación generada
        """
        try:
            logger.debug(f"Generando explicación para log: {log_entry[:100]}...")
            
            # 1. Parsear el log (responsabilidad delegada)
            log_metadata = self.log_parser.parse(log_entry)
            
            # 2. Construir el prompt (responsabilidad delegada)
            prompt = self.prompt_builder.build_single_prompt(log_metadata, score)
            system_prompt = self.prompt_builder.get_system_prompt()
            
            logger.debug("Prompt construido, llamando al LLM")
            
            # 3. Llamar al LLM (responsabilidad delegada)
            if self.llm_client:
                try:
                    response = await self.llm_client.generate_response(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    
                    # 4. Limpiar la respuesta (responsabilidad delegada)
                    cleaned_response = self.response_parser.clean_response(response)
                    
                    if cleaned_response:
                        logger.info(f"Explicación generada por LLM: {cleaned_response[:100]}...")
                        return cleaned_response
                except Exception as e:
                    logger.error(f"Error llamando al LLM: {e}")
            
            # 5. Fallback si el LLM falla (responsabilidad delegada)
            logger.warning("Usando explicación de fallback")
            return self.fallback_generator.generate(log_entry, score)
            
        except Exception as e:
            logger.error(f"Error obteniendo explicación del LLM: {e}")
            return self.fallback_generator.generate(log_entry, score)
    
    async def get_batch_explanations(
        self, 
        anomaly_batch: List[Tuple[str, float]]
    ) -> List[str]:
        """
        Obtiene explicaciones para un lote de anomalías de una vez.
        
        Args:
            anomaly_batch: Lista de tuplas (log_entry, score)
            
        Returns:
            Lista de explicaciones
        """
        try:
            if not anomaly_batch:
                return []
            
            logger.info(f"Procesando lote de {len(anomaly_batch)} anomalías con LLM")
            
            # 1. Parsear todos los logs (responsabilidad delegada)
            parsed_anomalies = [
                (self.log_parser.parse(log_entry), score)
                for log_entry, score in anomaly_batch
            ]
            
            # 2. Construir prompt de batch (responsabilidad delegada)
            prompt = self.prompt_builder.build_batch_prompt(parsed_anomalies)
            system_prompt = self.prompt_builder.get_system_prompt()
            
            # 3. Llamar al LLM (responsabilidad delegada)
            if self.llm_client:
                try:
                    response = await self.llm_client.generate_response(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens * len(anomaly_batch)  # Más tokens para batch
                    )
                    
                    # 4. Parsear respuesta de batch (responsabilidad delegada)
                    explanations = self.response_parser.parse_batch_response(
                        response, 
                        len(anomaly_batch)
                    )
                    
                    logger.info(f"Explicaciones generadas para lote: {len(explanations)}")
                    return explanations
                    
                except Exception as e:
                    logger.error(f"Error procesando lote con LLM: {e}")
            
            # 5. Fallback individual si falla el batch
            logger.warning("LLM no respondió, usando fallback individual")
            return [
                self.fallback_generator.generate(log_entry, score)
                for log_entry, score in anomaly_batch
            ]
            
        except Exception as e:
            logger.error(f"Error procesando lote de anomalías: {e}")
            return [
                self.fallback_generator.generate(log_entry, score)
                for log_entry, score in anomaly_batch
            ]
    
    async def get_detailed_explanation(self, log_entry: str, score: float) -> str:
        """
        Obtiene una explicación detallada para una anomalía individual.
        Alias para get_llm_explanation para mantener compatibilidad.
        
        Args:
            log_entry: Entrada de log
            score: Score de anomalía
            
        Returns:
            Explicación generada
        """
        return await self.get_llm_explanation(log_entry, score)
    
    async def check_llm_available(self) -> bool:
        """
        Verifica si el LLM está disponible.
        
        Returns:
            True si está disponible, False en caso contrario
        """
        if not self.llm_client:
            return False
        
        try:
            return await self.llm_client.check_available()
        except Exception as e:
            logger.error(f"Error verificando disponibilidad del LLM: {e}")
            return False


# Instancia global del servicio (se inicializa con valores por defecto)
explanation_service = ExplanationService()
