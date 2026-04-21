"""
Prompts para Evaluadores LLM
"""
from typing import List


class EvaluatorPrompts:
    """Prompts especializados para cada paso de evaluación"""

    @staticmethod
    def get_severity_classification_prompt(log_entry: str, score: float, explanation: str) -> str:
        """
        Prompt para clasificar la severidad de una anomalía.
        """
        return f"""Eres un experto en seguridad informática clasificando anomalías en logs.

**Log anómalo** (score: {score}):
```
{log_entry}
```

**Explicación**:
```
{explanation}
```

**Clasifica la severidad en una de estas categorías**:
- **critical**: Ataque activo confirmado (SQL Injection, XSS, Command Injection, exploit, malware, intrusión)
- **high**: Indicador fuerte de compromiso (intentos de ataque, accesos no autorizados, anomalías severas)
- **medium**: Actividad sospechosa que requiere investigación (errores raros, patrones inusuales)
- **low**: Evento informativo o falso positivo, bajo riesgo

**Responde SOLO en este formato**:
```
SEVERITY: [critical/high/medium/low]
```

Clasifica:"""

    @staticmethod
    def get_verification_prompt(log_entry: str, score: float, explanation: str) -> str:
        """
        Prompt para verificar precisión técnica de la explicación.
        """
        return f"""Eres un experto en logs de sistemas y seguridad informática.

Tu tarea es verificar si la siguiente explicación es técnicamente correcta.

**Log anómalo** (score: {score}):
```
{log_entry}
```

**Explicación a verificar**:
```
{explanation}
```

**Instrucciones**:
1. Verifica que la explicación identifique correctamente el tipo de log
2. Verifica que el análisis técnico sea preciso
3. Verifica que la interpretación del campo de anomalía sea correcta

**Responde en este formato exacto**:
```
CORRECTA: [si/no]
ERROR: [descripción del error si es incorrecta, vacío si es correcta]
CONFIDENCE: [alta/media/baja]
```

Analiza y responde:"""

    @staticmethod
    def get_regeneration_prompt(log_entry: str, score: float, error_description: str) -> str:
        """
        Prompt para re-generar explicación con corrección.
        """
        return f"""Eres un experto en logs de sistemas y seguridad informática.

Genera una explicación técnica para este log anómalo.

**Log anómalo** (score: {score}):
```
{log_entry}
```

**Contexto importante**:
{error_description}

**Instrucciones**:
1. Identifica el tipo de log (auth, web server, application, etc.)
2. Extrae información relevante (IP, user, timestamp, status code, etc.)
3. Explica QUÉ hace anómalo a este log
4. Usa lenguaje técnico pero claro

**Genera la explicación**:"""

    @staticmethod
    def get_comparison_prompt(log_entry: str, score: float, explanations: List[str]) -> str:
        """
        Prompt para comparar múltiples explicaciones y elegir la mejor.
        """
        explanations_text = "\n\n".join([
            f"**Explicación {i+1}**:\n{exp}"
            for i, exp in enumerate(explanations)
        ])

        return f"""Eres un experto analizando logs anómalos.

Compara estas explicaciones y elige la mejor.

**Log anómalo** (score: {score}):
```
{log_entry}
```

{explanations_text}

**Criterios de evaluación**:
1. Precisión técnica: ¿Identifica correctamente el problema?
2. Claridad: ¿Es fácil de entender?
3. Completitud: ¿Cubre todos los aspectos relevantes?
4. Acción: ¿Sugiere qué hacer?

**Responde en este formato exacto**:
```
BEST: [1/2/3]
REASON: [razón de por qué es la mejor]
SCORE: [puntuación de 1-10 de la mejor]
```

Analiza y responde:"""

    @staticmethod
    def get_improvement_prompt(log_entry: str, score: float, explanation: str) -> str:
        """
        Prompt para mejorar la explicación para no técnicos.
        """
        return f"""Eres un experto en seguridad informática que sabe explicar conceptos técnicos a personas NO técnicas.

Mejora la siguiente explicación para que sea entendible por alguien sin conocimientos técnicos.

**Log anómalo** (score: {score}):
```
{log_entry}
```

**Explicación técnica original**:
```
{explanation}
```

**Instrucciones**:
1. **Lenguaje simple**: Evita jerga técnica (HTTP status codes, SQL syntax, etc.)
2. **Explica QUÉ pasó**: En palabras sencillas, qué ocurrió
3. **Explica POR QUÉ es un problema**: Por qué debería importarle
4. **Sugiere QUÉ hacer** (opcional): Qué puede hacer al respecto
5. **Usa analogías** cuando sea útil

**Formato de respuesta**:
Usa viñetas para facilitar lectura:
- • **Qué pasó**: [descripción]
- • **Por qué importa**: [explicación]
- • **Qué hacer**: [sugerencia]

**Mejora la explicación**:"""

    @staticmethod
    def get_system_prompt() -> str:
        """Prompt del sistema para evaluadores"""
        return """Eres un asistente experto en análisis de logs y seguridad informática.

Tu rol es evaluar, comparar y mejorar explicaciones de anomalías en logs.

Directrices:
- Ser preciso y técnicamente correcto
- Ser claro y conciso
- Considerar el nivel de conocimiento del público objetivo
- Mantener el contexto de seguridad informática"""
