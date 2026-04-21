"""
Constructor de prompts - Principio de Responsabilidad Única (SRP)
Responsabilidad: Construir prompts para el LLM
"""
import logging
from typing import List, Tuple
from ..log_analysis.log_parser import LogMetadata

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Constructor de prompts - Responsabilidad Única: Crear prompts estructurados.
    No conoce nada sobre cómo se envía al LLM o cómo se procesa la respuesta.
    """
    
    SYSTEM_PROMPT = """Eres un experto en análisis de logs de sistemas. 
Analiza logs de manera concisa y técnica, identificando:
- Patrones anómalos específicos
- Posibles amenazas de seguridad
- Recomendaciones de acción

Responde en español de forma clara y directa."""
    
    def build_single_prompt(self, log_metadata: LogMetadata, score: float) -> str:
        """
        Construye un prompt para analizar una sola anomalía.

        Args:
            log_metadata: Metadatos del log parseado
            score: Score de anomalía

        Returns:
            Prompt formateado para el LLM
        """
        prompt = f"""Eres un experto en análisis de logs de sistemas. Explica lo que está pasando usando analogías simples y ejemplos cotidianos.

INFORMACIÓN DEL LOG:
- Log: {log_metadata.raw_entry}
- Timestamp: {log_metadata.timestamp or 'No detectado'}
- Nivel: {log_metadata.level or 'No detectado'}
- Servicio: {log_metadata.service or 'No detectado'}
- Score de anomalía: {score:.3f}

INSTRUCCIONES:
1. Explica QUÉ está pasando usando una analogía simple (ej: restaurante, casa, oficina)
2. Explica POR QUÉ es importante
3. Explica QUÉ puede pasar si no se soluciona
4. Sugiere QUÉ hacer para solucionarlo
5. Sé conciso pero informativo

FORMATO DE RESPUESTA (OBLIGATORIO):
- • **Qué pasó**: [descripción con analogía]
- • **Por qué importa**: [explicación]
- • **Qué hacer**: [sugerencia]

Ejemplo:
- • **Qué pasó**: Es como si la puerta del restaurante estuviera abierta pero el personal no puede entrar a la cocina
- • **Por qué importa**: Los clientes hacen pedidos pero nunca llegan a prepararse
- • **Qué hacer**: Verificar que el pasillo entre la puerta y la cocina esté desbloqueado

ANALIZA ESTE LOG:"""

        return prompt
    
    def build_batch_prompt(
        self,
        anomalies: List[Tuple[LogMetadata, float]],
        repetition_summary: str = ""
    ) -> str:
        """
        Construye un prompt para analizar múltiples anomalías.

        Args:
            anomalies: Lista de tuplas (LogMetadata, score)
            repetition_summary: Resumen de anomalías repetitivas (opcional)

        Returns:
            Prompt formateado para el LLM
        """
        prompt = f"""Eres un experto en análisis de logs. Analiza estas {len(anomalies)} anomalías y explica QUÉ ESTÁ PASANDO en cada una de forma clara y directa.

INSTRUCCIONES:
1. Explica QUÉ está pasando en cada log
2. Explica POR QUÉ es un problema
3. Explica QUÉ puede pasar si no se soluciona
4. Usa un lenguaje claro y accesible
5. Máximo 3 oraciones por anomalía
6. Sé conciso pero informativo

IMPORTANTE - Anomalías Repetitivas:
Si notas patrones que se repiten (como "workerEnv.init() ok" o "mod_jk child workerEnv in error state"):
- Menciona explícitamente: "Este patrón se repite X veces en el log"
- Da una sola explicación que aplique a todas las ocurrencias
- Indica si es un problema recurrente o un evento único
- No repitas la misma explicación para cada anomalía similar

FORMATO DE RESPUESTA:
Para cada anomalía, responde en una línea separada:
ANOMALÍA 1: [explicación]
ANOMALÍA 2: [explicación]
ANOMALÍA 3: [explicación]
...

ANOMALÍAS A ANALIZAR:"""

        for i, (log_metadata, score) in enumerate(anomalies, 1):
            prompt += f"\n\nANOMALÍA {i} (Score: {score:.3f}):\n{log_metadata.raw_entry}"

        # Agregar resumen de repeticiones si existe
        if repetition_summary:
            prompt += repetition_summary

        return prompt
    
    def get_system_prompt(self) -> str:
        """Retorna el prompt del sistema por defecto."""
        return self.SYSTEM_PROMPT
