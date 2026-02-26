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
        prompt = f"""Eres un experto en análisis de logs de sistemas. Analiza este log y explica QUÉ ESTÁ PASANDO de manera simple y clara para una persona sin conocimientos técnicos.

INFORMACIÓN DEL LOG:
- Log: {log_metadata.raw_entry}
- Timestamp: {log_metadata.timestamp or 'No detectado'}
- Nivel: {log_metadata.level or 'No detectado'}
- Servicio: {log_metadata.service or 'No detectado'}
- Score de anomalía: {score:.3f}

INSTRUCCIONES:
1. Explica QUÉ está pasando en términos simples
2. Explica POR QUÉ es un problema
3. Explica QUÉ puede pasar si no se soluciona
4. Sugiere QUÉ hacer para solucionarlo
5. Usa un lenguaje claro y comprensible para cualquier persona
6. Máximo 3 oraciones, sé conciso pero informativo

FORMATO DE RESPUESTA:
Problema: [Qué está pasando]
Impacto: [Por qué es importante]
Solución: [Qué hacer]

Ejemplo:
Problema: El servidor web no puede comunicarse con la base de datos
Impacto: Los usuarios no podrán acceder a la aplicación
Solución: Verificar que la base de datos esté funcionando y revisar la configuración de conexión

ANALIZA ESTE LOG:"""
        
        return prompt
    
    def build_batch_prompt(
        self, 
        anomalies: List[Tuple[LogMetadata, float]]
    ) -> str:
        """
        Construye un prompt para analizar múltiples anomalías.
        
        Args:
            anomalies: Lista de tuplas (LogMetadata, score)
            
        Returns:
            Prompt formateado para el LLM
        """
        prompt = f"""Eres un experto en análisis de logs. Analiza estas {len(anomalies)} anomalías y explica QUÉ ESTÁ PASANDO en cada una de manera simple y clara.

INSTRUCCIONES:
1. Explica QUÉ está pasando en cada log
2. Explica POR QUÉ es un problema
3. Explica QUÉ puede pasar si no se soluciona
4. Usa un lenguaje claro y comprensible
5. Máximo 3 oraciones por anomalía
6. Sé conciso pero informativo
7. Explica a una persona sin conocimientos técnicos

FORMATO DE RESPUESTA:
Para cada anomalía, responde en una línea separada:
ANOMALÍA 1: [explicación]
ANOMALÍA 2: [explicación]
ANOMALÍA 3: [explicación]
...

ANOMALÍAS A ANALIZAR:"""
        
        for i, (log_metadata, score) in enumerate(anomalies, 1):
            prompt += f"\n\nANOMALÍA {i} (Score: {score:.3f}):\n{log_metadata.raw_entry}"
        
        return prompt
    
    def get_system_prompt(self) -> str:
        """Retorna el prompt del sistema por defecto."""
        return self.SYSTEM_PROMPT
