"""
Servicio de explicaciones - Orquestador principal
Principio de Responsabilidad Única: Orquestar la generación de explicaciones
Usa composición de servicios especializados en lugar de hacer todo internamente
"""
import os
import logging
from typing import List, Tuple, Optional, Dict, Any

from .interfaces import LLMClientInterface
from .llm import OllamaClientWrapper, get_default_llm_service, get_llm_service, LLMServiceAdapter, get_llm_service_with_fallback
from models.schemas.llm import LLMProvider
from .log_analysis import LogParser, LogMetadata
from .prompts import PromptBuilder
from .explanation import ResponseParser, FallbackExplanationGenerator
from services.evaluator.evaluator_service import evaluator_service

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
        fallback_generator: Optional[FallbackExplanationGenerator] = None,
        workspace_id: Optional[str] = None
    ):
        """
        Inicializa el servicio de explicaciones con dependencias inyectadas.

        Args:
            llm_client: Cliente LLM (si None, crea OllamaClientWrapper)
            log_parser: Parser de logs (si None, crea uno nuevo)
            prompt_builder: Constructor de prompts (si None, crea uno nuevo)
            response_parser: Parser de respuestas (si None, crea uno nuevo)
            fallback_generator: Generador de fallback (si None, crea uno nuevo)
            workspace_id: ID del workspace (para usar configuración con fallback)
        """
        # Inyección de dependencias - permite testing y flexibilidad
        self.llm_client = llm_client or self._create_llm_client()
        self.log_parser = log_parser or LogParser()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_parser = response_parser or ResponseParser()
        self.fallback_generator = fallback_generator or FallbackExplanationGenerator()
        self.workspace_id = workspace_id

        # Configuración desde variables de entorno
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "200"))

        logger.info("ExplanationService inicializado con servicios especializados")
    
    def _create_llm_client(self) -> LLMClientInterface:
        """
        Crea el cliente LLM por defecto.

        NOTA: Este método siempre devuelve None para forzar el uso de
        _get_llm_client_with_fallback() que obtiene credenciales desde la BD.
        """
        logger.info("LLM client se inicializará con credenciales del workspace")
        return None

    async def _get_llm_client_with_fallback(self) -> Optional[LLMClientInterface]:
        """
        Obtiene el cliente LLM con fallback automático si hay workspace_id configurado.

        Returns:
            Cliente LLM o None si no hay disponibles
        """
        if not self.workspace_id:
            return self.llm_client

        try:
            llm_service, credentials, model_info = await get_llm_service_with_fallback(
                workspace_id=self.workspace_id,
                role="default"
            )

            logger.info(f"get_llm_service_with_fallback retornó: service_type={type(llm_service)}, credentials={bool(credentials)}, model_info={bool(model_info)}")

            # Verificar que todos los componentes necesarios están disponibles
            if not model_info or not llm_service or not credentials:
                logger.warning(f"No hay modelos LLM configurados para workspace {self.workspace_id} (model_info={bool(model_info)}, llm_service={bool(llm_service)}, credentials={bool(credentials)})")
                return None

            adapter = LLMServiceAdapter(
                llm_service=llm_service,
                provider=model_info['provider'],
                model=model_info['model'],
                credentials=credentials
            )
            logger.info(f"LLMServiceAdapter creado con llm_service_type={type(llm_service)}")
            return adapter
        except Exception as e:
            logger.error(f"Error obteniendo cliente LLM con fallback: {e}")
            return self.llm_client
    
    async def get_llm_explanation(self, log_entry: str, score: float, use_evaluators: bool = True) -> str:
        """
        Obtiene una explicación inteligente del LLM para un log anómalo.

        Args:
            log_entry: Entrada de log
            score: Score de anomalía
            use_evaluators: Si es True, usa evaluadores para mejorar la explicación

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

            # 3. Obtener cliente LLM con fallback si hay workspace configurado
            llm_client = await self._get_llm_client_with_fallback()

            # 4. Llamar al LLM (responsabilidad delegada)
            initial_explanation = None
            if llm_client:
                try:
                    response = await llm_client.generate_response(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )

                    # 5. Limpiar la respuesta (responsabilidad delegada)
                    initial_explanation = self.response_parser.clean_response(response)

                    if initial_explanation:
                        logger.info(f"Explicación generada por LLM: {initial_explanation[:100]}...")

                        # 6. Usar evaluadores si está habilitado y hay workspace
                        if use_evaluators and self.workspace_id:
                            try:
                                logger.info("Usando evaluadores para mejorar explicación...")
                                evaluator_result = await evaluator_service.evaluate_explanation(
                                    log_entry=log_entry,
                                    score=score,
                                    initial_explanation=initial_explanation
                                )

                                if evaluator_result.get("explanation"):
                                    logger.info(f"Explicación mejorada por evaluadores (duración: {evaluator_result.get('duration', 0):.2f}s)")
                                    return evaluator_result["explanation"]
                                else:
                                    logger.warning("Evaluadores no retornaron explicación, usando original")
                                    return initial_explanation

                            except Exception as e:
                                logger.error(f"Error en evaluadores, usando explicación original: {e}")
                                return initial_explanation

                        return initial_explanation

                except Exception as e:
                    logger.error(f"Error llamando al LLM: {e}")

            # 7. Fallback si el LLM falla (responsabilidad delegada)
            logger.warning("Usando explicación de fallback")
            return self.fallback_generator.generate(log_entry, score)

        except Exception as e:
            logger.error(f"Error obteniendo explicación del LLM: {e}")
            return self.fallback_generator.generate(log_entry, score)

        except Exception as e:
            logger.error(f"Error obteniendo explicación del LLM: {e}")
            return self.fallback_generator.generate(log_entry, score)
    
    async def get_batch_explanations(
        self,
        anomaly_batch: List[Tuple[str, float]],
        use_evaluators: bool = True
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

            # 3. Obtener cliente LLM con credenciales del workspace
            llm_client = await self._get_llm_client_with_fallback()

            # 4. Llamar al LLM (responsabilidad delegada)
            if llm_client:
                try:
                    response = await llm_client.generate_response(
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

                    # 5. Aplicar evaluadores si está habilitado y hay workspace
                    if use_evaluators and self.workspace_id:
                        try:
                            logger.info("Aplicando evaluadores a las explicaciones del lote...")
                            improved_explanations = []

                            for i, (log_entry, score) in enumerate(anomaly_batch):
                                try:
                                    evaluator_result = await evaluator_service.evaluate_explanation(
                                        log_entry=log_entry,
                                        score=score,
                                        initial_explanation=explanations[i]
                                    )

                                    if evaluator_result.get("explanation"):
                                        improved_explanations.append(evaluator_result["explanation"])
                                        logger.debug(f"Anomalía {i+1}: explicación mejorada por evaluadores (severidad: {evaluator_result.get('severity', 'N/A')})")
                                    else:
                                        logger.warning(f"Evaluadores no retornaron explicación para anomalía {i+1}, usando original")
                                        improved_explanations.append(explanations[i])

                                except Exception as e:
                                    logger.warning(f"Error en evaluador para anomalía {i+1}: {e}")
                                    improved_explanations.append(explanations[i])

                            logger.info(f"Evaluadores aplicados al lote: {len(improved_explanations)} explicaciones procesadas")
                            return improved_explanations

                        except Exception as e:
                            logger.error(f"Error aplicando evaluadores al lote, usando explicaciones originales: {e}")
                            return explanations

                    return explanations
                    
                except Exception as e:
                    logger.error(f"Error procesando lote con LLM: {e}", exc_info=True)
            
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

    def set_llm_provider(
        self,
        provider: LLMProvider,
        model: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None
    ):
        """
        Cambia el proveedor LLM dinámicamente.

        Args:
            provider: Nuevo proveedor LLM
            model: Modelo específico a usar (opcional)
            credentials: Credenciales dinámicas (opcional)
        """
        try:
            llm_service = get_llm_service(provider)

            # Obtener credenciales del proveedor específico si se proporcionan
            provider_creds = None
            if credentials and provider.value in credentials:
                provider_creds = credentials[provider.value]

            # Crear adaptador para compatibilidad con LLMClientInterface
            self.llm_client = LLMServiceAdapter(
                llm_service=llm_service,
                provider=provider.value,
                model=model,
                credentials=provider_creds
            )

            logger.info(f"Proveedor LLM cambiado a {provider.value} (modelo: {model or 'default'})")
        except Exception as e:
            logger.error(f"Error cambiando proveedor LLM: {e}")
            raise

    def set_workspace_id(self, workspace_id: str):
        """
        Establece el workspace_id para usar configuración con fallback.

        Args:
            workspace_id: ID del workspace
        """
        self.workspace_id = workspace_id
        logger.info(f"Workspace ID establecido: {workspace_id}")


# Instancia global del servicio (se inicializa con valores por defecto)
explanation_service = ExplanationService()
