"""
Servicio de Evaluadores LLM

Responsabilidad: Orquestar el proceso de evaluación de explicaciones en 3 pasos:
1. Verificar precisión técnica
2. Comparar con fallbacks
3. Mejorar para no técnicos

Usa RabbitMQ para enviar mensajes de progreso.
"""
import logging
import os
import json
import re
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

from services.llm import get_llm_service
from services.workspace_llm_config_service import workspace_llm_config_service
from .prompts import EvaluatorPrompts

logger = logging.getLogger(__name__)


class EvaluatorService:
    """Servicio para orquestar evaluaciones de explicaciones LLM"""

    def __init__(self, workspace_id: Optional[str] = None):
        """
        Inicializa el servicio de evaluadores.

        Args:
            workspace_id: ID del workspace (para usar configuración LLM)
        """
        self.workspace_id = workspace_id
        self.enabled = os.getenv("ENABLE_EVALUATORS", "true").lower() == "true"
        self.timeout = int(os.getenv("EVALUATOR_TIMEOUT", "30"))

        logger.info(f"EvaluatorService inicializado (enabled={self.enabled})")

    async def _classify_severity(
        self,
        log_entry: str,
        score: float,
        explanation: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Paso 1: Clasifica la severidad de la anomalía usando LLM.

        Returns:
            Dict con severity: critical, high, medium, low
        """
        await self._send_progress(job_id, 10, "Clasificando severidad...")

        try:
            # Obtener modelos evaluadores configurados
            evaluators = await workspace_llm_config_service.get_models_by_role(
                self.workspace_id, "evaluator"
            )

            if not evaluators:
                logger.warning("No hay evaluadores configurados, clasificando por score")
                # Clasificación fallback basada en score
                if score < -0.7:
                    severity = "critical"
                elif score < -0.5:
                    severity = "high"
                elif score < -0.3:
                    severity = "medium"
                else:
                    severity = "low"
                return {
                    "step": "classify_severity",
                    "severity": severity,
                    "method": "score_based",
                    "progress": 10
                }

            # Usar el primer evaluador disponible
            evaluator_config = evaluators[0]
            llm_service = get_llm_service(
                __import__('models.schemas.llm', fromlist=['LLMProvider']).LLMProvider(evaluator_config['provider'])
            )

            # Obtener credenciales
            full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                self.workspace_id, evaluator_config['provider']
            )

            credentials = None
            if full_config and full_config.get('apiKey'):
                credentials = {
                    'apiKey': full_config['apiKey'],
                    'apiEndpoint': full_config.get('apiEndpoint')
                }

            # Construir prompt de clasificación
            prompt = EvaluatorPrompts.get_severity_classification_prompt(log_entry, score, explanation)
            system_prompt = EvaluatorPrompts.get_system_prompt()

            # Llamar al LLM
            response = await llm_service.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                credentials=credentials,
                model=evaluator_config['model'],  # Usar el modelo configurado en la BD
                temperature=0.3,  # Baja temperatura para respuestas deterministas
                max_tokens=50
            )

            # Parsear respuesta para extraer severidad
            severity_match = re.search(r'SEVERITY:\s*(critical|high|medium|low)', response, re.IGNORECASE)
            if severity_match:
                severity = severity_match.group(1).lower()
            else:
                # Fallback si no se pudo parsear
                logger.warning(f"No se pudo parsear severidad de: {response}")
                severity = "medium"

            await self._send_progress(job_id, 20, f"Severidad clasificada: {severity}")

            return {
                "step": "classify_severity",
                "severity": severity,
                "method": "llm_based",
                "progress": 20,
                "evaluator_used": evaluator_config['provider']
            }

        except Exception as e:
            logger.error(f"Error clasificando severidad: {e}")
            # Fallback a clasificación por score
            if score < -0.7:
                severity = "critical"
            elif score < -0.5:
                severity = "high"
            elif score < -0.3:
                severity = "medium"
            else:
                severity = "low"
            return {
                "step": "classify_severity",
                "severity": severity,
                "method": "score_fallback",
                "progress": 20,
                "error": str(e)
            }

    async def evaluate_explanation(
        self,
        log_entry: str,
        score: float,
        initial_explanation: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evalúa y mejora una explicación en 4 pasos.

        Args:
            log_entry: Entrada de log
            score: Score de anomalía
            initial_explanation: Explicación generada por el default
            job_id: ID único del job (para tracking)

        Returns:
            Dict con:
                - explanation: Explicación final mejorada
                - severity: Severidad clasificada (critical, high, medium, low)
                - steps: Lista de pasos realizados
                - duration: Tiempo total en segundos
        """
        import time
        start_time = time.time()

        if not self.enabled:
            logger.info("Evaluadores deshabilitados, retornando explicación inicial")
            return {
                "explanation": initial_explanation,
                "severity": "medium",  # Default si evaluadores deshabilitados
                "steps": [],
                "duration": 0
            }

        job_id = job_id or str(uuid4())
        steps = []

        try:
            # Paso 1: Clasificar severidad
            step1_result = await self._classify_severity(
                log_entry, score, initial_explanation, job_id
            )
            steps.append(step1_result)
            severity = step1_result.get("severity", "medium")

            # Paso 2: Verificar precisión técnica
            step2_result = await self._verify_technical_accuracy(
                log_entry, score, initial_explanation, job_id
            )
            steps.append(step2_result)

            # Si la explicación es incorrecta, re-generar
            current_explanation = initial_explanation
            if not step2_result["is_correct"]:
                logger.info("Explicación incorrecta, re-generando...")
                current_explanation = await self._regenerate_with_correction(
                    log_entry, score, step2_result["error_description"], job_id
                )

            # Paso 3: Comparar con fallbacks (si existen)
            step3_result = await self._compare_with_fallbacks(
                log_entry, score, current_explanation, job_id
            )
            steps.append(step3_result)

            # Si hay una mejor, usarla
            if step3_result["better_explanation"]:
                current_explanation = step3_result["better_explanation"]

            # Paso 4: Mejorar para no técnicos
            step4_result = await self._improve_for_non_technical(
                log_entry, score, current_explanation, job_id
            )
            steps.append(step4_result)

            final_explanation = step4_result["improved_explanation"]

            duration = time.time() - start_time

            return {
                "explanation": final_explanation,
                "severity": severity,
                "steps": steps,
                "duration": duration
            }

        except Exception as e:
            logger.error(f"Error en evaluación: {e}", exc_info=True)
            # En caso de error, retornar explicación inicial con severidad medium
            return {
                "explanation": initial_explanation,
                "severity": "medium",
                "steps": steps,
                "error": str(e),
                "duration": time.time() - start_time
            }

    async def _verify_technical_accuracy(
        self,
        log_entry: str,
        score: float,
        explanation: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Paso 1: Verifica que la explicación sea técnicamente correcta.
        """
        await self._send_progress(job_id, 25, "Verificando precisión técnica...")

        try:
            # Obtener modelos evaluadores configurados
            evaluators = await workspace_llm_config_service.get_models_by_role(
                self.workspace_id, "evaluator"
            )

            if not evaluators:
                logger.warning("No hay evaluadores configurados, asumiendo explicación correcta")
                return {
                    "step": "verify_technical_accuracy",
                    "is_correct": True,
                    "error_description": None,
                    "progress": 25
                }

            # Usar el primer evaluador disponible
            evaluator_config = evaluators[0]
            llm_service = get_llm_service(
                __import__('models.schemas.llm', fromlist=['LLMProvider']).LLMProvider(evaluator_config['provider'])
            )

            # Obtener credenciales
            full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                self.workspace_id, evaluator_config['provider']
            )

            credentials = None
            if full_config and full_config.get('apiKey'):
                credentials = {
                    'apiKey': full_config['apiKey'],
                    'apiEndpoint': full_config.get('apiEndpoint')
                }

            # Construir prompt
            prompt = EvaluatorPrompts.get_verification_prompt(log_entry, score, explanation)
            system_prompt = EvaluatorPrompts.get_system_prompt()

            # Llamar al LLM
            response = await llm_service.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                credentials=credentials,
                model=evaluator_config['model'],  # Usar el modelo configurado en la BD
                temperature=0.3  # Baja temperatura para respuestas más deterministas
            )

            # Parsear respuesta
            is_correct = "CORRECTA: si" in response or "CORRECTA: true" in response.lower()
            error_match = re.search(r'ERROR:\s*(.+?)(?:\n|CONFIDENCE:|$)', response, re.IGNORECASE)
            error_description = error_match.group(1).strip() if error_match else None

            return {
                "step": "verify_technical_accuracy",
                "is_correct": is_correct,
                "error_description": error_description,
                "progress": 25,
                "evaluator_used": evaluator_config['provider']
            }

        except Exception as e:
            logger.error(f"Error verificando precisión: {e}")
            # En caso de error, asumir correcta para no bloquear
            return {
                "step": "verify_technical_accuracy",
                "is_correct": True,
                "error_description": None,
                "progress": 25,
                "error": str(e)
            }

    async def _regenerate_with_correction(
        self,
        log_entry: str,
        score: float,
        error_description: str,
        job_id: str
    ) -> str:
        """
        Re-genera la explicación con corrección del error detectado.
        """
        await self._send_progress(job_id, 35, "Re-generando con corrección...")

        try:
            # Usar el modelo default para regenerar
            from services.workspace_llm_config_service import workspace_llm_config_service
            config = await workspace_llm_config_service.get_model_selection_config(self.workspace_id)

            if not config.get('default'):
                logger.warning("No hay modelo default configurado")
                return ""

            llm_service = get_llm_service(
                __import__('models.schemas.llm', fromlist=['LLMProvider']).LLMProvider(config['default']['provider'])
            )

            # Obtener credenciales
            full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                self.workspace_id, config['default']['provider']
            )

            credentials = None
            if full_config and full_config.get('apiKey'):
                credentials = {
                    'apiKey': full_config['apiKey'],
                    'apiEndpoint': full_config.get('apiEndpoint')
                }

            # Usar prompt original de explicación con contexto del error
            from services.prompts.prompt_builder import PromptBuilder
            from services.log_analysis.log_parser import LogParser

            log_parser = LogParser()
            log_metadata = log_parser.parse(log_entry)
            prompt_builder = PromptBuilder()

            prompt = prompt_builder.build_single_prompt(log_metadata, score)
            # Agregar contexto del error
            prompt = f"""{prompt}

**NOTA IMPORTANTE - Corrección requerida**:
{error_description}

Por favor, genera la explicación considerando esta corrección."""

            system_prompt = prompt_builder.get_system_prompt()

            response = await llm_service.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                credentials=credentials,
                model=config['default']['model']  # Usar el modelo default del workspace
            )

            return response

        except Exception as e:
            logger.error(f"Error regenerando: {e}")
            return ""

    async def _compare_with_fallbacks(
        self,
        log_entry: str,
        score: float,
        explanation: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Paso 2: Compara la explicación con las de fallbacks y elige la mejor.
        """
        await self._send_progress(job_id, 50, "Comparando alternativas...")

        try:
            # Obtener modelos fallback configurados
            fallbacks = await workspace_llm_config_service.get_models_by_role(
                self.workspace_id, "fallback"
            )

            if not fallbacks:
                logger.info("No hay fallbacks configurados")
                return {
                    "step": "compare_with_fallbacks",
                    "better_explanation": None,
                    "reason": "No hay fallbacks configurados",
                    "progress": 50
                }

            # Generar explicaciones con cada fallback
            explanations_to_compare = [explanation]  # Incluir la default
            fallback_providers = []

            for fb in fallbacks:
                try:
                    llm_service = get_llm_service(
                        __import__('models.schemas.llm', fromlist=['LLMProvider']).LLMProvider(fb['provider'])
                    )

                    full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                        self.workspace_id, fb['provider']
                    )

                    if not full_config or not full_config.get('apiKey'):
                        continue

                    credentials = {
                        'apiKey': full_config['apiKey'],
                        'apiEndpoint': full_config.get('apiEndpoint')
                    }

                    # Generar explicación con este fallback
                    from services.explanation.prompts import PromptBuilder
                    from services.explanation.log_analysis import LogParser

                    log_parser = LogParser()
                    log_metadata = log_parser.parse(log_entry)
                    prompt_builder = PromptBuilder()
                    prompt = prompt_builder.build_single_prompt(log_metadata, score)
                    system_prompt = prompt_builder.get_system_prompt()

                    response = await llm_service.generate_response(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        credentials=credentials,
                        model=fb['model']  # Usar el modelo fallback configurado
                    )

                    explanations_to_compare.append(response)
                    fallback_providers.append(fb['provider'])

                except Exception as e:
                    logger.error(f"Error generando con fallback {fb['provider']}: {e}")
                    continue

            # Si hay múltiples explicaciones, usar evaluador para comparar
            if len(explanations_to_compare) > 1:
                evaluators = await workspace_llm_config_service.get_models_by_role(
                    self.workspace_id, "evaluator"
                )

                if evaluators:
                    evaluator_config = evaluators[0]  # Usar primer evaluador
                    llm_service = get_llm_service(
                        __import__('models.schemas.llm', fromlist=['LLMProvider']).LLMProvider(evaluator_config['provider'])
                    )

                    full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                        self.workspace_id, evaluator_config['provider']
                    )

                    if full_config and full_config.get('apiKey'):
                        credentials = {
                            'apiKey': full_config['apiKey'],
                            'apiEndpoint': full_config.get('apiEndpoint')
                        }

                        # Pedir comparación
                        prompt = EvaluatorPrompts.get_comparison_prompt(log_entry, score, explanations_to_compare)
                        system_prompt = EvaluatorPrompts.get_system_prompt()

                        response = await llm_service.generate_response(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            credentials=credentials,
                            model=evaluator_config['model'],  # Usar el modelo evaluador configurado
                            temperature=0.3
                        )

                        # Parsear respuesta para elegir la mejor
                        best_match = re.search(r'BEST:\s*(\d+)', response, re.IGNORECASE)
                        if best_match:
                            best_index = int(best_match.group(1)) - 1  # Convertir a 0-based
                            if 0 <= best_index < len(explanations_to_compare):
                                reason_match = re.search(r'REASON:\s*(.+?)(?:\n|SCORE:|$)', response, re.IGNORECASE)
                                reason = reason_match.group(1).strip() if reason_match else "No especificada"

                                return {
                                    "step": "compare_with_fallbacks",
                                    "better_explanation": explanations_to_compare[best_index],
                                    "reason": reason,
                                    "progress": 50
                                }

            return {
                "step": "compare_with_fallbacks",
                "better_explanation": None,
                "reason": "La explicación default es adecuada",
                "progress": 50
            }

        except Exception as e:
            logger.error(f"Error comparando fallbacks: {e}")
            return {
                "step": "compare_with_fallbacks",
                "better_explanation": None,
                "reason": f"Error en comparación: {str(e)}",
                "progress": 50
            }

    async def _compare_with_fallbacks(
        self,
        log_entry: str,
        score: float,
        explanation: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Paso 2: Compara la explicación con las de fallbacks y elige la mejor.
        """
        # TODO: Implementar comparación con fallbacks
        # Por ahora no hay mejor (placeholder)
        return {
            "step": "compare_with_fallbacks",
            "better_explanation": None,
            "reason": "No hay fallbacks configurados",
            "progress": 50
        }

    async def _improve_for_non_technical(
        self,
        log_entry: str,
        score: float,
        explanation: str,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Paso 3: Mejora la explicación para personas no técnicas.
        """
        await self._send_progress(job_id, 75, "Mejorando explicación...")

        try:
            # Obtener modelos evaluadores configurados
            evaluators = await workspace_llm_config_service.get_models_by_role(
                self.workspace_id, "evaluator"
            )

            if not evaluators:
                logger.warning("No hay evaluadores configurados, retornando explicación original")
                return {
                    "step": "improve_for_non_technical",
                    "improved_explanation": explanation,
                    "changes": [],
                    "progress": 100
                }

            # Usar el primer evaluador (o el segundo si hay varios)
            evaluator_config = evaluators[1] if len(evaluators) > 1 else evaluators[0]
            llm_service = get_llm_service(
                __import__('models.schemas.llm', fromlist=['LLMProvider']).LLMProvider(evaluator_config['provider'])
            )

            # Obtener credenciales
            full_config = await workspace_llm_config_service.get_any_config_with_credentials(
                self.workspace_id, evaluator_config['provider']
            )

            credentials = None
            if full_config and full_config.get('apiKey'):
                credentials = {
                    'apiKey': full_config['apiKey'],
                    'apiEndpoint': full_config.get('apiEndpoint')
                }

            # Construir prompt de mejora
            prompt = EvaluatorPrompts.get_improvement_prompt(log_entry, score, explanation)
            system_prompt = EvaluatorPrompts.get_system_prompt()

            # Llamar al LLM
            response = await llm_service.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                credentials=credentials,
                model=evaluator_config['model'],  # Usar el modelo evaluador configurado
                temperature=0.7  # Temperatura más alta para creatividad
            )

            await self._send_progress(job_id, 100, "Explicación lista")

            return {
                "step": "improve_for_non_technical",
                "improved_explanation": response,
                "changes": ["Simplificada para no técnicos", "Agregado contexto", "Agregadas sugerencias"],
                "progress": 100,
                "evaluator_used": evaluator_config['provider']
            }

        except Exception as e:
            logger.error(f"Error mejorando explicación: {e}")
            await self._send_progress(job_id, 100, "Explicación lista")
            # En caso de error, retornar explicación original
            return {
                "step": "improve_for_non_technical",
                "improved_explanation": explanation,
                "changes": [],
                "progress": 100,
                "error": str(e)
            }

    async def _send_progress(self, job_id: str, progress: int, message: str):
        """
        Envía mensaje de progreso a RabbitMQ.

        Args:
            job_id: ID del job
            progress: Porcentaje (0-100)
            message: Mensaje descriptivo
        """
        # TODO: Implementar envío a RabbitMQ
        logger.info(f"[{job_id}] {progress}% - {message}")


# Instancia global
evaluator_service = EvaluatorService()
