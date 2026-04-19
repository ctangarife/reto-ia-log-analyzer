"""
Course Generation Service v2
Dynamically generates courses based on project anomalies and logs

New Structure:
- courses table: Main course entity
- course_modules table: 4 fixed modules per course
- course_lessons table: Lessons within modules

Course Structure:
1. Module 1: Introducción a los Logs (2 fixed lessons)
2. Module 2: Tipos de Anomalías Detectadas (1 lesson per category)
3. Module 3: Análisis Práctico (5-10 real cases)
4. Module 4: Evaluación Final (exam with 5 new anomalies)
"""
import logging
import json
import random
import re
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from config.database import db_manager
from models.learning_models import (
    Course, ProjectAnalysis,
    CourseGenerateResponse, CoursePreviewResponse,
    CourseRegenerateResponse, CourseLimitsCheck
)
from .llm import OllamaClientWrapper

logger = logging.getLogger(__name__)


class CourseGenerationService:
    """Service for generating dynamic courses based on project data"""

    MIN_ANOMALIES_REQUIRED = 10  # Minimum anomalies to generate a course

    # Course limits per project
    MAX_PUBLISHED = 1
    MAX_DRAFT = 3
    MAX_PENDING = 3

    async def check_course_limits(
        self,
        project_id: UUID,
        target_status: str = "draft"
    ) -> CourseLimitsCheck:
        """Check if a new course can be created based on limits"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Count courses by status
                published_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM learning.courses WHERE project_id = $1 AND status = 'published'",
                    project_id
                )
                draft_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM learning.courses WHERE project_id = $1 AND status = 'draft'",
                    project_id
                )
                pending_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM learning.courses WHERE project_id = $1 AND status = 'pending'",
                    project_id
                )

                current_counts = {
                    "published": published_count,
                    "draft": draft_count,
                    "pending": pending_count,
                    "total": published_count + draft_count + pending_count
                }

                # Validate limits
                if target_status == "published" and published_count >= self.MAX_PUBLISHED:
                    return CourseLimitsCheck(
                        can_create=False,
                        reason=f"Ya existe un curso publicado. Máximo permitido: {self.MAX_PUBLISHED}",
                        current_counts=current_counts
                    )
                elif target_status == "draft" and draft_count >= self.MAX_DRAFT:
                    return CourseLimitsCheck(
                        can_create=False,
                        reason=f"Máximo de cursos en borrador alcanzado ({self.MAX_DRAFT})",
                        current_counts=current_counts
                    )
                elif target_status == "pending" and pending_count >= self.MAX_PENDING:
                    return CourseLimitsCheck(
                        can_create=False,
                        reason=f"Máximo de cursos pendientes alcanzado ({self.MAX_PENDING})",
                        current_counts=current_counts
                    )

                return CourseLimitsCheck(
                    can_create=True,
                    reason=None,
                    current_counts=current_counts
                )

        except Exception as e:
            logger.error(f"Error checking course limits: {e}")
            return CourseLimitsCheck(
                can_create=False,
                reason=f"Error al verificar límites: {str(e)}",
                current_counts={}
            )

    async def can_generate_course(self, project_id: UUID) -> dict:
        """Check if there's enough data to generate a course"""
        try:
            # Check limits
            limits = await self.check_course_limits(project_id, "draft")
            if not limits.can_create:
                return {
                    "can_generate": False,
                    "reason": limits.reason,
                    "current_counts": limits.current_counts
                }

            async with db_manager.postgres_pool.acquire() as conn:
                # Check for completed processing jobs
                completed_jobs = await conn.fetchval(
                    """SELECT COUNT(*) FROM processing.processing_jobs
                       WHERE (project_id = $1 OR project_id IS NULL) AND status = 'completed'""",
                    project_id
                )

                if completed_jobs == 0:
                    return {
                        "can_generate": False,
                        "reason": "No hay trabajos de procesamiento completados. Primero analiza logs del proyecto."
                    }

                # Count anomalies from MongoDB
                total_anomalies = await self._count_project_anomalies(conn, project_id)

                if total_anomalies < self.MIN_ANOMALIES_REQUIRED:
                    return {
                        "can_generate": False,
                        "reason": f"Se requieren al menos {self.MIN_ANOMALIES_REQUIRED} anomalías. Actualmente: {total_anomalies}"
                    }

                return {
                    "can_generate": True,
                    "anomalies_count": total_anomalies
                }

        except Exception as e:
            logger.error(f"Error checking if course can be generated: {e}")
            return {"can_generate": False, "reason": str(e)}

    async def preview_course_data(self, project_id: UUID) -> ProjectAnalysis:
        """Preview project data before course generation"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get project info
                project = await conn.fetchrow(
                    "SELECT name, workspace_id FROM auth.projects WHERE id = $1",
                    project_id
                )

                if not project:
                    raise ValueError("Project not found")

                # Get processing stats
                stats = await conn.fetchrow(
                    """SELECT
                        COUNT(DISTINCT j.id) as completed_jobs,
                        MIN(j.started_at) as first_job,
                        MAX(j.completed_at) as last_job
                       FROM processing.processing_jobs j
                       WHERE j.status = 'completed'
                       AND (j.project_id = $1 OR j.project_id IS NULL)""",
                    project_id
                )

                # Get anomalies from MongoDB
                anomalies_data = await self._get_anomalies_analysis(conn, project_id)

                # Get log formats
                log_formats = await self._get_log_formats(conn, project_id)

                total_anomalies = anomalies_data["total"]

                return ProjectAnalysis(
                    project_id=project_id,
                    project_name=project["name"],
                    total_logs=stats["completed_jobs"] if stats else 0,
                    total_anomalies=total_anomalies,
                    anomaly_categories=anomalies_data["categories"],
                    anomaly_severity_distribution=anomalies_data["severity"],
                    log_formats=log_formats,
                    date_range={
                        "start": str(stats["first_job"]) if stats and stats["first_job"] else "N/A",
                        "end": str(stats["last_job"]) if stats and stats["last_job"] else "N/A"
                    },
                    can_generate_course=total_anomalies >= self.MIN_ANOMALIES_REQUIRED,
                    min_anomalies_required=self.MIN_ANOMALIES_REQUIRED,
                    top_anomalies=anomalies_data["top_anomalies"]
                )

        except Exception as e:
            logger.error(f"Error previewing course data: {e}")
            raise

    async def generate_course(
        self,
        project_id: UUID,
        workspace_id: UUID,
        created_by: UUID,
        scope: str = "project",
        name: Optional[str] = None
    ) -> CourseGenerateResponse:
        """Generate a new course based on project analysis"""
        try:
            # Check if course can be generated
            check = await self.can_generate_course(project_id)
            if not check.get("can_generate"):
                return CourseGenerateResponse(
                    course_id=uuid4(),
                    status="error",
                    modules_created=0,
                    lessons_created=0,
                    message=check.get("reason", "Cannot generate course")
                )

            async with db_manager.postgres_pool.acquire() as conn:
                # Analyze project data
                analysis = await self.preview_course_data(project_id)

                # Get sample log entries from the project
                sample_logs = await self._get_sample_log_entries(conn, project_id, limit=5)

                # Create course name if not provided
                course_name = name or f"Curso de Análisis de Logs - {analysis.project_name}"

                # Create the course record
                course_id = await conn.fetchval("""
                    INSERT INTO learning.courses
                    (project_id, workspace_id, name, description, status, scope, created_by)
                    VALUES ($1, $2, $3, $4, 'draft', $5, $6)
                    RETURNING id
                """, project_id, workspace_id, course_name,
                   f"Curso generado dinámicamente basado en {analysis.total_anomalies} anomalías detectadas.",
                   scope, created_by)

                logger.info(f"Course {course_id} created for project {project_id}")

                # Generate the 4 fixed modules
                total_lessons = 0

                # Module 1: Introducción a los Logs
                lessons_m1 = await self._create_module_1_introduction(
                    conn, course_id, analysis, sample_logs, module_order=1
                )
                total_lessons += lessons_m1

                # Module 2: Tipos de Anomalías Detectadas
                lessons_m2 = await self._create_module_2_categories(
                    conn, course_id, analysis, module_order=2
                )
                total_lessons += lessons_m2

                # Module 3: Análisis Práctico
                lessons_m3 = await self._create_module_3_practical(
                    conn, course_id, project_id, module_order=3
                )
                total_lessons += lessons_m3

                # Module 4: Evaluación Final
                lessons_m4 = await self._create_module_4_evaluation(
                    conn, course_id, project_id, module_order=4
                )
                total_lessons += lessons_m4

                logger.info(f"Course {course_id} generated with {total_lessons} lessons")

                return CourseGenerateResponse(
                    course_id=course_id,
                    status="draft",
                    modules_created=4,
                    lessons_created=total_lessons,
                    message=f"Curso generado exitosamente con {total_lessons} lecciones en 4 módulos."
                )

        except Exception as e:
            logger.error(f"Error generating course: {e}")
            raise

    async def regenerate_course(
        self,
        project_id: UUID,
        workspace_id: UUID,
        created_by: UUID,
        change_description: Optional[str] = None
    ) -> CourseRegenerateResponse:
        """Regenerate course with new project data (creates new version)"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get existing published course
                existing = await conn.fetchrow(
                    """SELECT id, version_number, status
                       FROM learning.courses
                       WHERE project_id = $1 AND status = 'published'
                       ORDER BY created_at DESC LIMIT 1""",
                    project_id
                )

                new_version = (existing["version_number"] + 1) if existing else 1

                # Generate new course
                result = await self.generate_course(
                    project_id, workspace_id, created_by, "project",
                    f"Curso de Análisis v{new_version}"
                )

                # Update version number
                await conn.execute(
                    "UPDATE learning.courses SET version_number = $1 WHERE id = $2",
                    new_version, result.course_id
                )

                return CourseRegenerateResponse(
                    new_course_id=result.course_id,
                    version_number=new_version,
                    modules_created=result.modules_created,
                    lessons_created=result.lessons_created,
                    message=f"Curso regenerado (v{new_version}). El curso anterior sigue publicado hasta que se apruebe esta versión."
                )

        except Exception as e:
            logger.error(f"Error regenerating course: {e}")
            raise

    # ==================== MODULE CREATION METHODS ====================

    async def _create_module_1_introduction(
        self,
        conn,
        course_id: UUID,
        analysis: ProjectAnalysis,
        sample_logs: List[str],
        module_order: int
    ) -> int:
        """
        Create Module 1: Introducción a los Logs
        Fixed structure with 2 lessons about logs in general,
        but using examples from the project
        """
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (course_id, module_order, title, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, course_id, module_order, "Introducción a los Logs",
           "Fundamentos de los logs: qué son, cómo leerlos y por qué son importantes.")

        # Lesson 1: ¿Qué es un Log?
        sample_log_text = "\n".join([f"```\n{log}\n```" for log in sample_logs[:3]])
        content_lesson_1 = f"""# ¿Qué es un Log?

Un **log** (o registro) es un archivo generado por sistemas informáticos que registra eventos y actividades que ocurren durante su funcionamiento. Los logs son fundamentales para:

- **Monitoreo**: Seguir el estado del sistema en tiempo real
- **Auditoría**: Mantener un registro de actividades para cumplimiento
- **Debugging**: Identificar y resolver problemas
- **Análisis de Seguridad**: Detectar accesos no autorizados o ataques

## Tipos de Logs Comunes

Los logs pueden venir en diferentes formatos:

- **Logs de Aplicación**: Generados por software específico
- **Logs de Sistema**: Del sistema operativo
- **Logs de Red**: De firewalls, routers, switches
- **Logs de Seguridad**: De sistemas de autenticación y control de acceso

## Ejemplos de Logs de tu Proyecto

Tu proyecto ha generado {analysis.total_logs} entradas de log. Aquí tienes algunos ejemplos:

{sample_log_text}

## Formato Detectado

Los logs de tu proyecto están principalmente en formato: **{", ".join(analysis.log_formats)}**

## ¿Por Qué Analizar Logs?

Analizar logs permite:
1. Detectar comportamientos anómalos que podrían indicar problemas de seguridad
2. Identificar cuellos de botella en el rendimiento
3. Prevenir fallos antes de que afecten a los usuarios
4. Cumplir con requisitos de auditoría y normativa

En los siguientes módulos aprenderás a interpretar los logs de tu proyecto y detectar anomalías automáticamente usando técnicas de Machine Learning.
"""

        await conn.execute("""
            INSERT INTO learning.course_lessons
            (module_id, lesson_order, title, content)
            VALUES ($1, $2, $3, $4)
        """, module_id, 1, "¿Qué es un Log?", content_lesson_1)

        # Lesson 2: Cómo Leer Logs
        sample_log_for_reading = sample_logs[0] if sample_logs else "Ejemplo de log no disponible"
        content_lesson_2 = f"""# Cómo Leer Logs

Saber leer un log es una habilidad esencial para cualquier profesional de IT. En esta lección aprenderás a interpretar la información contenida en los logs.

## Estructura Básica de un Log

La mayoría de los logs siguen un formato similar:

```
[FECHA HORA] [NIVEL] [FUENTE] MENSAJE
```

## Análisis de un Log Real

Tomemos como ejemplo este log de tu proyecto:

```
{sample_log_for_reading}
```

**Desglose:**
- **Timestamp**: Indica cuándo ocurrió el evento
- **Origen**: Qué servicio o componente generó el log
- **Mensaje**: La información específica del evento

## Niveles de Severidad Comunes

Los logs suelen incluir niveles de severidad:

| Nivel | Significado | Ejemplo |
|-------|-------------|---------|
| **DEBUG** | Información detallada para debugging | "Variable x = 5" |
| **INFO** | Información general | "Servicio iniciado" |
| **WARNING** | Algo inesperado pero no crítico | "Timeout, reintentando..." |
| **ERROR** | Error que no impide la operación | "Falló conexión a DB" |
| **CRITICAL** | Error grave que requiere atención | "Servidor caído" |

## Patrones a Buscar

Cuando leas logs, busca patrones como:

1. **Repeticiones**: El mismo error muchas veces indica un problema sistemático
2. **Cambios de Comportamiento**: Un patrón que cambia repentinamente
3. **Valores Inusuales**: Tiempos de respuesta extremadamente largos
4. **Eventos de Seguridad**: Intentos de login fallidos, accesos denegados

## Anomalías en tus Logs

En este proyecto se han detectado **{analysis.total_anomalies} anomalías**. Aprenderás a identificarlas en los módulos siguientes.

## Consejos Prácticos

- **Usa herramientas de búsqueda**: grep, regex, o herramientas especializadas
- **Agrupa por tiempo**: Los eventos relacionados suelen ocurrir cerca en el tiempo
- **Cruza fuentes**: Un error en una parte puede afectar a otra
- **Documenta patrones**: Crea tu propia biblioteca de patrones conocidos
"""

        await conn.execute("""
            INSERT INTO learning.course_lessons
            (module_id, lesson_order, title, content)
            VALUES ($1, $2, $3, $4)
        """, module_id, 2, "Cómo Leer Logs", content_lesson_2)

        return 2

    async def _create_module_2_categories(
        self,
        conn,
        course_id: UUID,
        analysis: ProjectAnalysis,
        module_order: int
    ) -> int:
        """
        Create Module 2: Tipos de Anomalías Detectadas
        One lesson per detected category with theory + project examples
        """
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (course_id, module_order, title, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, course_id, module_order, "Tipos de Anomalías Detectadas",
           "Análisis de las diferentes categorías de anomalías encontradas en tu proyecto.")

        lesson_count = 0
        lesson_order = 1

        # Create lessons for each category with anomalies
        for category, count in analysis.anomaly_categories.items():
            if count > 0:
                content = self._generate_category_lesson_content(category, count, analysis)
                await conn.execute("""
                    INSERT INTO learning.course_lessons
                    (module_id, lesson_order, title, content)
                    VALUES ($1, $2, $3, $4)
                """, module_id, lesson_order, f"Anomalías de {category}", content)
                lesson_count += 1
                lesson_order += 1

        return lesson_count

    async def _create_module_3_practical(
        self,
        conn,
        course_id: UUID,
        project_id: UUID,
        module_order: int
    ) -> int:
        """
        Create Module 3: Análisis Práctico
        Real anomaly examples from the project
        """
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (course_id, module_order, title, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, course_id, module_order, "Análisis Práctico",
           "Casos reales de anomalías detectadas en tu proyecto con análisis detallado.")

        # Get sample anomalies from MongoDB
        sample_anomalies = await self._get_sample_anomalies(project_id, count=8)

        lesson_count = 0
        if not sample_anomalies:
            # Create a default lesson when no anomalies are available
            content = """# Análisis de Anomalías

No se encontraron anomalías específicas en este proyecto todavía.

## Instrucciones

Cuando se generen anomalías, podrás:
1. Ver el log original
2. Analizar la explicación del LLM
3. Interpretar el score de anomalía
4. Identificar el tipo de anomalía

**Nota**: Este contenido se actualizará automáticamente cuando se procesen más logs.
"""
            await conn.execute("""
                INSERT INTO learning.course_lessons
                (module_id, lesson_order, title, content)
                VALUES ($1, $2, $3, $4)
            """, module_id, 1, "Análisis de Anomalías", content)
            lesson_count = 1
        else:
            for idx, anomaly in enumerate(sample_anomalies, 1):
                content = self._generate_practical_lesson_content(anomaly, idx)
                await conn.execute("""
                    INSERT INTO learning.course_lessons
                    (module_id, lesson_order, title, content, exercise_data)
                    VALUES ($1, $2, $3, $4, $5)
                """, module_id, idx, f"Caso Práctico {idx}: {anomaly.get('type', 'Anomalía')}",
                   content, json.dumps({
                       "type": "project_anomalies",
                       "anomaly_id": anomaly.get("id"),
                       "dynamic": True
                   }))
                lesson_count += 1

        return lesson_count

    async def _create_module_4_evaluation(
        self,
        conn,
        course_id: UUID,
        project_id: UUID,
        module_order: int
    ) -> int:
        """
        Create Module 4: Evaluación Final
        Uses LLM to generate unique questions for each anomaly
        """
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (course_id, module_order, title, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, course_id, module_order, "Evaluación Final",
           "Demuestra tu conocimiento analizando nuevas anomalías.")

        # Get evaluation anomalies (different from module 3)
        eval_anomalies = await self._get_sample_anomalies(project_id, count=5, offset=8)

        # Initialize LLM client
        try:
            llm_client = OllamaClientWrapper()
        except Exception as e:
            logger.warning(f"Could not initialize LLM for exam generation: {e}")
            llm_client = None

        questions_by_anomaly = []

        # Generate unique questions for each anomaly using LLM
        for idx, anomaly in enumerate(eval_anomalies, 1):
            anomaly_type = self._infer_anomaly_type(anomaly)
            anomaly_score = anomaly.get("anomaly_score", 0.5)
            chunk_id = anomaly.get("chunk_id", "unknown")
            log_entry = anomaly.get("log_entry", anomaly.get("log_line", ""))
            explanation = anomaly.get("anomalies", {}).get("explanation", "")

            # Determine severity level
            if anomaly_score > 0.7:
                severity = "CRÍTICA"
            elif anomaly_score > 0.5:
                severity = "ALTA"
            else:
                severity = "MEDIA"

            # Generate questions using LLM
            if llm_client:
                try:
                    exam_prompt = f"""Eres un experto en análisis de logs y detección de anomalías.

Genera 2 preguntas de opción múltiple para la siguiente anomalía.

**Anomalía {idx}:**
- Tipo: {anomaly_type}
- Severidad: {severity}
- Score: {anomaly_score:.2f}
- Log: {log_entry[:500]}
- Explicación: {explanation[:500]}

Requisitos:
1. Cada pregunta debe tener 4 opciones (A, B, C, D)
2. Solo UNA opción es correcta
3. Las opciones incorrectas deben ser plausibles pero claramente erróneas
4. Una pregunta sobre diagnóstico/identificación
5. Una pregunta sobre acción/recomendación
6. Específicas a ESTA anomalía, no genéricas

Responde SOLO en formato JSON:
{{
    "questions": [
        {{
            "question": "texto de la pregunta 1",
            "options": [
                {{"letter": "A", "text": "opción A", "correct": true}},
                {{"letter": "B", "text": "opción B", "correct": false}},
                {{"letter": "C", "text": "opción C", "correct": false}},
                {{"letter": "D", "text": "opción D", "correct": false}}
            ]
        }},
        {{
            "question": "texto de la pregunta 2",
            "options": [
                {{"letter": "A", "text": "opción A", "correct": false}},
                {{"letter": "B", "text": "opción B", "correct": true}},
                {{"letter": "C", "text": "opción C", "correct": false}},
                {{"letter": "D", "text": "opción D", "correct": false}}
            ]
        }}
    ]
}}"""

                    response = await llm_client.generate_response(
                        prompt=exam_prompt,
                        system_prompt="Eres un experto instructor en análisis de logs. Genera preguntas de opción múltiple con exactamente una respuesta correcta.",
                        temperature=0.8
                    )

                    # Parse JSON response
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        questions_data = json.loads(json_match.group())
                        questions = questions_data.get("questions", [])
                    else:
                        # Fallback if JSON parsing fails
                        questions = self._generate_fallback_questions(anomaly_type, log_entry)
                except Exception as e:
                    logger.warning(f"LLM question generation failed for anomaly {idx}: {e}")
                    # Fallback questions
                    questions = self._generate_fallback_questions(anomaly_type, log_entry)
            else:
                # Fallback when LLM is not available
                questions = self._generate_fallback_questions(anomaly_type, log_entry)

            questions_by_anomaly.append({
                "index": idx,
                "chunk_id": chunk_id,
                "type": anomaly_type,
                "severity": severity,
                "score": anomaly_score,
                "questions": questions,
                "log_entry": log_entry[:200],
                "explanation": explanation[:300]
            })

        # Build exam content - ONLY instructions, no questions (shown by frontend)
        content_parts = ["# Evaluación Final\n\n"]
        content_parts.append("¡Has llegado al final del curso! A continuación analizarás **5 anomalías reales** de tu proyecto. ")
        content_parts.append("Cada una tiene **preguntas de opción múltiple** generadas específicamente por IA.\n\n")
        content_parts.append("## Criterios de Evaluación\n\n")
        content_parts.append("- Necesitas al menos **70% de respuestas correctas** para aprobar\n")
        content_parts.append("- Cada anomalía tiene 2 preguntas (5 puntos cada una = 10 puntos por anomalía)\n")
        content_parts.append("- Selecciona la opción correcta (A, B, C o D) para cada pregunta\n")
        content_parts.append("- Las preguntas fueron generadas por IA basándose en el contenido específico de cada anomalía\n\n")
        content_parts.append("## Instrucciones\n\n")
        content_parts.append("1. Lee cuidadosamente cada log presentado\n")
        content_parts.append("2. Analiza las opciones disponibles antes de responder\n")
        content_parts.append("3. Una vez enviadas las respuestas, verás tu calificación y el feedback\n\n")
        content_parts.append("---\n\n")
        content_parts.append("*Las preguntas específicas se muestran a continuación en formato interactivo.*\n\n")

        content = "".join(content_parts)

        exercise_data = {
            "type": "final_exam",
            "passing_score": 70,
            "anomalies": [{"id": a.get("id")} for a in eval_anomalies],
            "questions_by_anomaly": questions_by_anomaly,
            "generated_at": datetime.now().isoformat(),
            "llm_generated": llm_client is not None
        }

        await conn.execute("""
            INSERT INTO learning.course_lessons
            (module_id, lesson_order, title, content, exercise_data)
            VALUES ($1, $2, $3, $4, $5)
        """, module_id, 1, "Examen Práctico", content, json.dumps(exercise_data))

        return 1

    def _generate_fallback_questions(self, anomaly_type: str, log_entry: str) -> list:
        """Generate fallback multiple choice questions when LLM fails"""
        log_preview = log_entry[:100] if log_entry else "log no disponible"

        return [
            {
                "question": f"¿Qué tipo de anomalía representa el siguiente log: '{log_preview}'?",
                "options": [
                    {"letter": "A", "text": f"Anomalía de {anomaly_type}", "correct": True},
                    {"letter": "B", "text": "Anomalía de Seguridad", "correct": False},
                    {"letter": "C", "text": "Anomalía de Red", "correct": False},
                    {"letter": "D", "text": "Anomalía de Performance", "correct": False}
                ]
            },
            {
                "question": f"¿Cuál sería la acción recomendada para este tipo de anomalía de {anomaly_type}?",
                "options": [
                    {"letter": "A", "text": "Ignorar el evento, es normal", "correct": False},
                    {"letter": "B", "text": "Revisar logs relacionados y monitorear", "correct": True},
                    {"letter": "C", "text": "Reiniciar el servidor inmediatamente", "correct": False},
                    {"letter": "D", "text": "Eliminar el archivo de log", "correct": False}
                ]
            }
        ]

    # ==================== PRIVATE HELPER METHODS ====================

    async def _count_project_anomalies(self, conn, project_id: UUID) -> int:
        """Count total anomalies in project from MongoDB results collection"""
        try:
            job_ids = await conn.fetch(
                """SELECT id FROM processing.processing_jobs
                   WHERE (project_id = $1 OR project_id IS NULL) AND status = 'completed'""",
                project_id
            )

            if not job_ids:
                return 0

            file_ids = [str(job["id"]) for job in job_ids]

            pipeline = [
                {
                    "$addFields": {
                        "chunk_object_id": {"$toObjectId": "$chunk_id"}
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "chunk_object_id",
                        "foreignField": "_id",
                        "as": "chunk"
                    }
                },
                {"$unwind": "$chunk"},
                {"$match": {"chunk.file_id": {"$in": file_ids}}},
                {"$match": {"anomalies": {"$exists": True, "$ne": None}}},
                {"$unwind": "$anomalies"},
                {"$match": {"anomalies.is_anomaly": True}},
                {
                    "$count": "total"
                }
            ]

            result = await db_manager.mongodb_db["results"].aggregate(pipeline).to_list(length=1)
            return result[0]["total"] if result else 0

        except Exception as e:
            logger.error(f"Error counting anomalies: {e}")
            return 0

    async def _get_anomalies_analysis(self, conn, project_id: UUID) -> dict:
        """Get detailed anomaly analysis from MongoDB results"""
        try:
            job_ids = await conn.fetch(
                """SELECT id FROM processing.processing_jobs
                   WHERE status = 'completed'
                   AND (project_id = $1 OR project_id IS NULL)""",
                project_id
            )

            if not job_ids:
                return {"total": 0, "categories": {}, "severity": {}, "top_anomalies": []}

            file_ids = [str(job["id"]) for job in job_ids]

            # Pipeline para obtener estadísticas SIN guardar documentos completos
            # Esto evita el límite de 16MB de BSON
            pipeline_stats = [
                {
                    "$addFields": {
                        "chunk_object_id": {"$toObjectId": "$chunk_id"}
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "chunk_object_id",
                        "foreignField": "_id",
                        "as": "chunk"
                    }
                },
                {"$unwind": "$chunk"},
                {"$match": {"chunk.file_id": {"$in": file_ids}}},
                {"$match": {"anomalies": {"$exists": True, "$ne": None}}},
                {"$unwind": "$anomalies"},
                {"$match": {"anomalies.is_anomaly": True}},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "high_severity": {
                            "$sum": {"$cond": [{"$lte": ["$anomalies.score", -0.3]}, 1, 0]}
                        },
                        "medium_severity": {
                            "$sum": {"$cond": [{"$and": [{"$gt": ["$anomalies.score", -0.3]}, {"$lte": ["$anomalies.score", 0]}]}, 1, 0]}
                        },
                        "low_severity": {
                            "$sum": {"$cond": [{"$gt": ["$anomalies.score", 0]}, 1, 0]}
                        }
                    }
                }
            ]

            # Pipeline para obtener solo datos ESPECÍFICOS de las top anomalías
            # NO usamos $$ROOT, solo los campos necesarios
            pipeline_samples = [
                {
                    "$addFields": {
                        "chunk_object_id": {"$toObjectId": "$chunk_id"}
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "chunk_object_id",
                        "foreignField": "_id",
                        "as": "chunk"
                    }
                },
                {"$unwind": "$chunk"},
                {"$match": {"chunk.file_id": {"$in": file_ids}}},
                {"$match": {"anomalies": {"$exists": True, "$ne": None}}},
                {"$unwind": "$anomalies"},
                {"$match": {"anomalies.is_anomaly": True}},
                {"$sort": {"anomalies.score": 1}},
                {"$limit": 50},  # Solo 50, solo necesitamos top 5 para mostrar
                {
                    "$project": {
                        "_id": 1,
                        "chunk_id": 1,
                        "anomalies.score": 1,
                        "anomalies.log_entry": 1,
                        "anomalies.explanation": 1,
                        "anomalies.features": 1
                    }
                }
            ]

            # Ejecutar pipelines
            stats_result = None
            anomalies_list = []

            async for result in db_manager.mongodb_db["results"].aggregate(pipeline_stats):
                stats_result = result
                break

            # Obtener samples uno por uno para agruparlos en Python
            async for doc in db_manager.mongodb_db["results"].aggregate(pipeline_samples):
                anomalies_list.append(doc)

            if not stats_result:
                return {"total": 0, "categories": {}, "severity": {}, "top_anomalies": []}

            total = stats_result.get("total", 0)
            categories = self._categorize_anomalies(anomalies_list)

            # Top 5 anomalías
            top_anomalies = anomalies_list[:5]
            top_anomalies_formatted = [
                {
                    "id": str(a.get("_id", "")),
                    "chunk_id": a.get("chunk_id", ""),
                    "type": self._infer_anomaly_type(a.get("anomalies", {})),
                    "score": a.get("anomalies", {}).get("score", 0),
                    "log_entry": a.get("anomalies", {}).get("log_entry", ""),
                    "explanation": a.get("anomalies", {}).get("explanation", "")
                }
                for a in top_anomalies
            ]

            return {
                "total": total,
                "categories": categories,
                "severity": {
                    "high": stats_result.get("high_severity", 0),
                    "medium": stats_result.get("medium_severity", 0),
                    "low": stats_result.get("low_severity", 0)
                },
                "top_anomalies": top_anomalies_formatted
            }

        except Exception as e:
            logger.error(f"Error getting anomalies analysis: {e}")
            return {"total": 0, "categories": {}, "severity": {}, "top_anomalies": []}

    async def _get_sample_log_entries(
        self,
        conn,
        project_id: UUID,
        limit: int = 5
    ) -> List[str]:
        """Get sample log entries from the project"""
        try:
            job_ids = await conn.fetch(
                """SELECT id FROM processing.processing_jobs
                   WHERE (project_id = $1 OR project_id IS NULL) AND status = 'completed'
                   LIMIT 3""",
                project_id
            )

            if not job_ids:
                return [
                    "Ejemplo de log: [2024-01-15 10:30:45] INFO: Connection established from 192.168.1.100",
                    "Ejemplo de log: [2024-01-15 10:31:12] WARNING: High response time detected: 2500ms",
                    "Ejemplo de log: [2024-01-15 10:32:01] ERROR: Database connection failed, retrying..."
                ]

            file_ids = [str(job["id"]) for job in job_ids]

            # Get sample chunks
            chunks = await db_manager.mongodb_db["chunks"].find({
                "file_id": {"$in": file_ids}
            }).limit(limit).to_list(length=limit)

            log_entries = []
            for chunk in chunks:
                data = chunk.get("data", "")
                if data:
                    # Extract first few lines
                    lines = data.split("\n")[:3]
                    log_entries.extend([line.strip() for line in lines if line.strip()])

            return log_entries[:limit] if log_entries else [
                "Ejemplo de log: [2024-01-15 10:30:45] INFO: Connection established",
                "Ejemplo de log: [2024-01-15 10:31:12] WARNING: High response time detected"
            ]

        except Exception as e:
            logger.error(f"Error getting sample log entries: {e}")
            return [
                "Ejemplo de log: [2024-01-15 10:30:45] INFO: Connection established",
                "Ejemplo de log: [2024-01-15 10:31:12] WARNING: High response time detected"
            ]

    async def _get_sample_anomalies(
        self,
        project_id: UUID,
        count: int = 5,
        offset: int = 0
    ) -> List[dict]:
        """
        Get sample anomalies from project from MongoDB
        Uses chunk lookup to find anomalies by project_id
        """
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                job_ids = await conn.fetch(
                    """SELECT id FROM processing.processing_jobs
                       WHERE project_id = $1 AND status = 'completed'""",
                    project_id
                )

                if not job_ids:
                    logger.warning(f"No completed jobs found for project {project_id}")
                    return []

                file_ids = [str(job["id"]) for job in job_ids]
                logger.info(f"Found {len(file_ids)} job_ids for project {project_id}: {file_ids[:3]}...")

            # Pipeline: usar lookup con chunks para filtrar por file_id
            pipeline = [
                {
                    "$addFields": {
                        "chunk_object_id": {"$toObjectId": "$chunk_id"}
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "chunk_object_id",
                        "foreignField": "_id",
                        "as": "chunk"
                    }
                },
                {"$unwind": "$chunk"},
                {"$match": {"chunk.file_id": {"$in": file_ids}}},
                {"$match": {"anomalies": {"$exists": True, "$ne": None}}},
                {"$unwind": "$anomalies"},
                {"$match": {"anomalies.is_anomaly": True}},
                {"$sort": {"anomalies.score": 1}},  # Sort by score ascending (most anomalous first)
                {"$skip": offset},
                {"$limit": count}
            ]

            samples = []
            async for doc in db_manager.mongodb_db["results"].aggregate(pipeline):
                anomaly = doc.get("anomalies", {})

                # Extraer datos de la anomalía
                log_entry = anomaly.get("log_entry", "")
                explanation = anomaly.get("explanation", "")
                score = anomaly.get("score", 0)

                # Crear contenido enriquecido
                sample = {
                    "id": str(doc.get("_id", "")),
                    "chunk_id": doc.get("chunk_id", ""),
                    "type": self._infer_anomaly_type(anomaly),
                    "score": score,
                    "log_entry": log_entry,
                    "explanation": explanation,
                    # Datos adicionales para análisis
                    "features": anomaly.get("features", {}),
                    "is_anomaly": anomaly.get("is_anomaly", True)
                }
                samples.append(sample)

            logger.info(f"Found {len(samples)} sample anomalies for project {project_id} (requested {count}, offset {offset})")
            return samples

        except Exception as e:
            logger.error(f"Error getting sample anomalies: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _get_log_formats(self, conn, project_id: UUID) -> List[str]:
        """Detect log structure characteristics (not server-specific formats)"""
        try:
            sample_logs = await self._get_sample_log_entries(conn, project_id, limit=10)
            return self._detect_log_characteristics(sample_logs)

        except Exception as e:
            logger.error(f"Error detecting log characteristics: {e}")
            return ["No estructurado"]

    def _detect_log_characteristics(self, log_entries: List[str]) -> List[str]:
        """Detect generic log structure characteristics"""
        if not log_entries:
            return ["No estructurado"]

        detected = set()

        for log_entry in log_entries:
            entry = log_entry.strip()

            # JSON structured logs
            if entry.startswith('{') and ('"' in entry or '"' in entry):
                detected.add("Estructurado (JSON)")

            # Pipe-delimited (like Bro/Zeek)
            elif entry.count('|') >= 5:
                detected.add("Campos separados por pipe")

            # Comma-delimited (CSV-like)
            elif entry.count(',') >= 5 and not any(c in entry for c in '{}[]'):
                detected.add("Campos separados por coma")

            # Timestamp-prefixed (common in server logs)
            elif entry[0].isdigit() and ':' in entry[:30]:
                detected.add("Con timestamp al inicio")

            # Brackets with timestamp (Apache/Nginx style)
            elif '[' in entry[:50] and ']' in entry[:100]:
                detected.add("Entre corchetes [timestamp]")

            # Key-value pairs
            elif '=' in entry and ' ' in entry:
                detected.add("Pares clave-valor")

            # Default: plain text
            else:
                detected.add("Texto plano")

        return list(detected) if detected else ["No estructurado"]

    def _infer_anomaly_type(self, anomaly: dict) -> str:
        """Infer anomaly category from explanation and log entry"""
        explanation = anomaly.get("explanation", "").lower()
        log_entry = anomaly.get("log_entry", "").lower()
        combined = explanation + " " + log_entry

        if any(kw in combined for kw in ["login", "password", "auth", "failed", "denied", "security", "attack", "malware"]):
            return "Seguridad"
        elif any(kw in combined for kw in ["response time", "latency", "slow", "timeout", "performance", "delay"]):
            return "Performance"
        elif any(kw in combined for kw in ["network", "connection", "packet", "tcp", "udp", "port", "firewall"]):
            return "Red"
        elif any(kw in combined for kw in ["error", "exception", "crash", "stack", "trace", "null"]):
            return "Comportamiento"
        else:
            return "General"

    def _categorize_anomalies(self, anomalies: List[dict]) -> dict:
        """Categorize anomalies by type"""
        categories = {
            "Seguridad": 0,
            "Performance": 0,
            "Red": 0,
            "Comportamiento": 0,
            "General": 0
        }

        for doc in anomalies:
            anomaly = doc.get("anomalies", {})
            anomaly_type = self._infer_anomaly_type(anomaly)
            if anomaly_type in categories:
                categories[anomaly_type] += 1

        return {k: v for k, v in categories.items() if v > 0}

    def _generate_category_lesson_content(
        self,
        category: str,
        count: int,
        analysis: ProjectAnalysis
    ) -> str:
        """Generate content for category lesson"""
        percentage = (count / max(analysis.total_anomalies, 1)) * 100

        category_info = {
            "Seguridad": {
                "description": "Las anomalías de seguridad representan patrones que podrían indicar accesos no autorizados, ataques, o comportamientos maliciosos en tu sistema.",
                "impact": "compromiso de la seguridad del sistema",
                "examples": "intentos de login fallidos repetidos, accesos desde IPs sospechosas, escaneos de puertos",
                "recommendation": "Revisar políticas de autenticación, configurar firewall, implementar MFA"
            },
            "Performance": {
                "description": "Las anomalías de rendimiento indican que tu sistema no está operando dentro de los parámetros esperados de velocidad o eficiencia.",
                "impact": "degradación del servicio y experiencia del usuario",
                "examples": "tiempos de respuesta excesivos, uso elevado de CPU/memoria, cuellos de botella",
                "recommendation": "Optimizar consultas, escalar infraestructura, implementar caché"
            },
            "Red": {
                "description": "Las anomalías de red señalan problemas en la conectividad, protocolos o comunicaciones entre componentes.",
                "impact": "pérdida de conectividad o comunicaciones intermitentes",
                "examples": "conexiones rechazadas, timeouts de red, paquetes perdidos",
                "recommendation": "Verificar configuración de red, revisar firewalls, monitorear ancho de banda"
            },
            "Comportamiento": {
                "description": "Las anomalías de comportamiento muestran patrones inusuales en la ejecución de aplicaciones, como errores o excepciones inesperadas.",
                "impact": "fallos en la ejecución de la aplicación",
                "examples": "excepciones no manejadas, comportamientos inconsistentes, estados inesperados",
                "recommendation": "Revisar código, agregar manejo de errores, mejorar logs"
            },
            "General": {
                "description": "Anomalías que no encajan en categorías específicas pero que representan patrones inusuales detectados por el sistema.",
                "impact": "comportamiento inesperado del sistema",
                "examples": "patrones complejos, combinaciones de factores",
                "recommendation": "análisis manual detallado del contexto"
            }
        }

        info = category_info.get(category, category_info["General"])

        return f"""# Anomalías de {category}

## ¿Qué son?

{info['description']}

## En tu Proyecto

Se detectaron **{count} anomalías** de esta categoría, lo que representa el **{percentage:.1f}%** del total de anomalías analizadas.

## Ejemplos Típicos

- {info['examples']}

## Impacto Potencial

{info['impact'].capitalize()}

## Recomendaciones

{info['recommendation']}

## Análisis en tu Proyecto

Basado en los datos analizados, tu proyecto muestra patrones de {category.lower()} que requieren atención. En el módulo de **Análisis Práctico** revisarás casos reales de anomalías de esta categoría detectadas en tu proyecto, con el log original y la explicación generada por el sistema.
"""

    def _generate_practical_lesson_content(self, anomaly: dict, index: int) -> str:
        """Generate content for practical lesson using real anomaly data"""
        log_entry = anomaly.get('log_entry', 'Sin información del log')
        explanation = anomaly.get('explanation', 'Sin explicación disponible')
        score = anomaly.get('score', 0)
        anomaly_type = anomaly.get('type', 'General')

        return f"""# Caso Práctico {index}: {anomaly_type}

## Log Original Detectado

```
{log_entry}
```

## Análisis de la Anomalía

**Score de Anomalía:** {score:.2f}
**Tipo:** {anomaly_type}

### Explicación del Sistema

{explanation}

Esta anomalía fue detectada automáticamente por el algoritmo **Isolation Forest** basado en patrones inusuales en los logs, y posteriormente analizada por un modelo de lenguaje para proporcionar contexto.

## Interpreta el Score

El score de anomalía indica qué tan "inusual" es este evento:
- **Scores negativos**: Más anómalo (ej: -0.5 es muy inusual)
- **Scores cercanos a 0**: Normal
- **Scores positivos**: Muy común

## Ejercicios de Análisis

Basado en la información anterior, reflexiona:

1. **Identificación**: ¿Qué patrón específico hace que este log sea considerado una anomalía?

2. **Impacto**: ¿Cuál podría ser el impacto de este tipo de anomalía en tu sistema?

3. **Acción Correctiva**: ¿Qué acción inmediata recomendarías tomar?

4. **Prevención**: ¿Cómo podrías configurar alertas o monitoreo para detectar esto en el futuro?

---
*Este es un caso real detectado en tu proyecto. Analiza cuidadosamente cada aspecto.*
"""


# Singleton instance
course_generation_service = CourseGenerationService()
