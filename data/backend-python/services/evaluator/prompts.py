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
        Prompt para mejorar la explicación para audiencia general.
        """
        return f"""Eres un experto en seguridad informática que explica conceptos técnicos de forma clara usando analogías y ejemplos cotidianos.

Mejora la siguiente explicación para hacerla más clara y comprensible.

**Log anómalo** (score: {score}):
```
{log_entry}
```

**Explicación original**:
```
{explanation}
```

**Instrucciones**:
1. **Usa analogías cotidianas**: Compara con situaciones de la vida real (ej: restaurante, oficina, casa)
2. **Simplifica jerga**: Evita términos técnicos (HTTP status codes, SQL syntax, etc.) o explicalos simplemente
3. **Estructura en viñetas**: Usa el formato de abajo para facilitar lectura
4. **Sé directo y claro**

**Formato de respuesta** (OBLIGATORIO):
- • **Qué pasó**: [descripción simple con analogía]
- • **Por qué importa**: [explicación de por qué es relevante]
- • **Qué hacer**: [sugerencias prácticas]

**IMPORTANTE**:
- NO agregues prefacios como "Aquí tienes la explicación mejorada..."
- Comienza DIRECTO con la primera viñeta: • **Qué pasó**:

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
