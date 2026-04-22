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
from typing import Optional, List, Dict
from uuid import UUID, uuid4

from config.database import db_manager
from models.learning_models import (
    Course, ProjectAnalysis,
    CourseGenerateResponse, CoursePreviewResponse,
    CourseRegenerateResponse, CourseLimitsCheck,
    LogTypeInfo, LogSourceInfo
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
                        MAX(j.completed_at) as last_job,
                        SUM(j.total_chunks) as total_chunks
                       FROM processing.processing_jobs j
                       WHERE j.status = 'completed'
                       AND (j.project_id = $1 OR j.project_id IS NULL)""",
                    project_id
                )

                # Get anomalies from MongoDB
                anomalies_data = await self._get_anomalies_analysis(conn, project_id)

                # Get detailed log type information
                sample_logs = await self._get_sample_log_entries(conn, project_id, limit=20)
                log_type_info = self._analyze_log_type_detailed(sample_logs)

                # Detect log sources (Apache, OPNsense, Android, etc.)
                source_detection = self._detect_log_sources(sample_logs)

                # Update log_type_info with source detection
                log_type_info.detected_sources = source_detection.get("detected_sources", [])
                log_type_info.primary_source = source_detection.get("primary_source")
                log_type_info.confidence = source_detection.get("confidence", "low")

                # Get log sources (services/components) - legacy method for specific service names
                log_sources = await self._identify_log_sources(conn, project_id, sample_logs)

                # Get log formats (legacy)
                log_formats = await self._get_log_formats(conn, project_id)

                # Calculate anomaly density
                # Porcentaje de chunks que contienen al menos una anomalía
                # Nota: No podemos calcular exactamente sin procesar todos los chunks
                total_chunks = stats["total_chunks"] if stats and stats["total_chunks"] else 1

                if anomalies_data["total"] > 0 and total_chunks > 0:
                    # Estimar: si hay X anomalías distribuidas en Y chunks
                    # Asumimos una anomalía por chunk como máximo para el cálculo
                    estimated_chunks_with_anomalies = min(anomalies_data["total"], total_chunks)
                    anomaly_density = round((estimated_chunks_with_anomalies / total_chunks) * 100, 1)
                else:
                    anomaly_density = 0.0

                # Get predominant log level
                predominant_log_level = self._get_predominant_log_level(sample_logs)

                total_anomalies = anomalies_data["total"]

                return ProjectAnalysis(
                    project_id=project_id,
                    project_name=project["name"],
                    total_logs=stats["completed_jobs"] if stats else 0,
                    total_anomalies=total_anomalies,
                    anomaly_categories=anomalies_data["categories"],
                    anomaly_severity_distribution=anomalies_data["severity"],
                    log_formats=log_formats,
                    log_type_info=log_type_info,
                    log_sources=log_sources,
                    anomaly_density=round(anomaly_density, 2),
                    predominant_log_level=predominant_log_level,
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
            logger.info(f"Starting course generation for project_id={project_id}, workspace_id={workspace_id}, created_by={created_by}, scope={scope}, name={name}")

            # Check if course can be generated
            check = await self.can_generate_course(project_id)
            if not check.get("can_generate"):
                logger.warning(f"Cannot generate course for project {project_id}: {check.get('reason')}")
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
                logger.info(f"Project analysis complete: total_anomalies={analysis.total_anomalies}, total_logs={analysis.total_logs}")

                # Get sample log entries from the project
                sample_logs = await self._get_sample_log_entries(conn, project_id, limit=5)
                logger.info(f"Retrieved {len(sample_logs)} sample logs")

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
                logger.info(f"Creating Module 1 for course {course_id}")
                lessons_m1 = await self._create_module_1_introduction(
                    conn, course_id, analysis, sample_logs, module_order=1
                )
                total_lessons += lessons_m1
                logger.info(f"Module 1 created with {lessons_m1} lessons")

                # Module 2: Tipos de Anomalías Detectadas
                logger.info(f"Creating Module 2 for course {course_id}")
                lessons_m2 = await self._create_module_2_categories(
                    conn, course_id, analysis, module_order=2
                )
                total_lessons += lessons_m2
                logger.info(f"Module 2 created with {lessons_m2} lessons")

                # Module 3: Análisis Práctico
                logger.info(f"Creating Module 3 for course {course_id}")
                lessons_m3 = await self._create_module_3_practical(
                    conn, course_id, project_id, module_order=3
                )
                total_lessons += lessons_m3
                logger.info(f"Module 3 created with {lessons_m3} lessons")

                # Module 4: Evaluación Final
                logger.info(f"Creating Module 4 for course {course_id}")
                lessons_m4 = await self._create_module_4_evaluation(
                    conn, course_id, project_id, module_order=4
                )
                total_lessons += lessons_m4
                logger.info(f"Module 4 created with {lessons_m4} lessons")

                logger.info(f"Course {course_id} generated with {total_lessons} lessons total")

                response = CourseGenerateResponse(
                    course_id=course_id,
                    status="draft",
                    modules_created=4,
                    lessons_created=total_lessons,
                    message=f"Curso generado exitosamente con {total_lessons} lecciones en 4 módulos."
                )
                logger.info(f"Returning response: course_id={response.course_id}, status={response.status}, modules_created={response.modules_created}, lessons_created={response.lessons_created}, message={response.message}")
                return response

        except Exception as e:
            import traceback
            logger.error(f"Error generating course: {e}\n{traceback.format_exc()}")
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

        # Build log type information section
        log_type_section = ""
        if analysis.log_type_info:
            log_type_section = f"""
## Tipo de Log Detectado

**Formato**: {analysis.log_type_info.format_type}
"""
            if analysis.log_type_info.timestamp_format:
                log_type_section += f"\n**Formato de Timestamp**: {analysis.log_type_info.timestamp_format}"
            if analysis.log_type_info.typical_fields:
                log_type_section += f"\n**Campos Típicos**: {', '.join(analysis.log_type_info.typical_fields[:5])}"
            if analysis.anomaly_density > 0:
                log_type_section += f"\n**Densidad de Anomalías**: {analysis.anomaly_density:.1f}% de los logs contienen anomalías"
            if analysis.predominant_log_level:
                log_type_section += f"\n**Nivel de Log Predominante**: {analysis.predominant_log_level}"

        # Build log sources section
        log_sources_section = ""
        if analysis.log_sources:
            log_sources_section = "\n## Fuentes de Log Detectadas\n\n"
            for source in analysis.log_sources[:3]:
                log_sources_section += f"- **{source.service_name}** ({source.log_count} entradas)\n"

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

## Análisis de tu Proyecto

Tu proyecto ha generado **{analysis.total_logs}** entradas de log con **{analysis.total_anomalies} anomalías detectadas**.
{log_type_section}
{log_sources_section}
## Ejemplos de Logs de tu Proyecto

Aquí tienes algunos ejemplos reales:

{sample_log_text}

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
        Real anomaly examples from the project with TYPE VARIETY
        """
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (course_id, module_order, title, description)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, course_id, module_order, "Análisis Práctico",
           "Casos reales de anomalías detectadas en tu proyecto con análisis detallado.")

        # Get more anomalies to ensure variety, then filter by type
        all_anomalies = await self._get_sample_anomalies(project_id, count=50)  # Get more to filter

        lesson_count = 0
        if not all_anomalies:
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
            # Filter to ensure variety: max 2 per type, then randomize
            import random
            random.shuffle(all_anomalies)

            # Group by type and select max 2 from each
            type_counts = {"Seguridad": 0, "Performance": 0, "Red": 0, "Comportamiento": 0, "General": 0}
            selected_anomalies = []

            for anomaly in all_anomalies:
                anomaly_type = anomaly.get("type", "General")
                if type_counts.get(anomaly_type, 0) < 2:  # Max 2 per type
                    selected_anomalies.append(anomaly)
                    type_counts[anomaly_type] = type_counts.get(anomaly_type, 0) + 1

                if len(selected_anomalies) >= 8:
                    break

            # Sort by type for organization, then by score
            selected_anomalies.sort(key=lambda x: (x.get("type", "General"), x.get("score", 0)))

            for idx, anomaly in enumerate(selected_anomalies, 1):
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
            anomaly_type = anomaly.get("type", self._infer_anomaly_type(anomaly))
            anomaly_score = anomaly.get("score", 0.5)
            chunk_id = anomaly.get("chunk_id", "unknown")
            log_entry = anomaly.get("log_entry", "")
            explanation = anomaly.get("explanation", "")

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
            # Usar la MISMA query que _get_anomalies_analysis para consistencia
            job_ids = await conn.fetch(
                """SELECT id FROM processing.processing_jobs
                   WHERE status = 'completed'
                   AND (project_id = $1 OR project_id IS NULL)""",
                project_id
            )

            if not job_ids:
                logger.warning(f"No completed jobs found for project {project_id}")
                return 0

            file_ids = [str(job["id"]) for job in job_ids]
            logger.info(f"Checking anomalies for project {project_id}, file_ids: {file_ids}")

            # Pipeline simplificado sin conversión a ObjectId
            # NOTA: chunk_id en results tiene formato "job_id_chunk_id"
            # necesitamos extraer solo el chunk_id para el lookup
            # Usar $group como en _get_anomalies_analysis para consistencia
            pipeline = [
                {
                    "$addFields": {
                        "pure_chunk_id": {
                            "$arrayElemAt": [
                                {"$split": ["$chunk_id", "_"]},
                                -1  # Tomar el último elemento después del último "_"
                            ]
                        }
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "pure_chunk_id",  # UUID sin prefijo
                        "foreignField": "_id",           # UUID sin prefijo
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
                        "total": {"$sum": 1}
                    }
                }
            ]

            # Execute the aggregation pipeline
            result = await db_manager.mongodb_db["results"].aggregate(pipeline).to_list(length=1)
            count = result[0]["total"] if result and len(result) > 0 else 0
            logger.info(f"Anomalies count for project {project_id}: {count} (file_ids: {file_ids})")
            return count

        except Exception as e:
            import traceback
            logger.error(f"Error counting anomalies: {e}\n{traceback.format_exc()}")
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
            # NOTA: chunk_id en results tiene formato "job_id_chunk_id"
            pipeline_stats = [
                {
                    "$addFields": {
                        "pure_chunk_id": {
                            "$arrayElemAt": [
                                {"$split": ["$chunk_id", "_"]},
                                -1  # Tomar el último elemento después del último "_"
                            ]
                        }
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "pure_chunk_id",  # UUID sin prefijo
                        "foreignField": "_id",           # UUID sin prefijo
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
            # FILTRO: Solo anomalías con explicaciones LLM válidas
            pipeline_samples = [
                {
                    "$addFields": {
                        "pure_chunk_id": {
                            "$arrayElemAt": [
                                {"$split": ["$chunk_id", "_"]},
                                -1  # Tomar el último elemento después del último "_"
                            ]
                        }
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "pure_chunk_id",  # UUID sin prefijo
                        "foreignField": "_id",           # UUID sin prefijo
                        "as": "chunk"
                    }
                },
                {"$unwind": "$chunk"},
                {"$match": {"chunk.file_id": {"$in": file_ids}}},
                {"$match": {"anomalies": {"$exists": True, "$ne": None}}},
                {"$unwind": "$anomalies"},
                {"$match": {"anomalies.is_anomaly": True}},
                {
                    "$match": {
                        "anomalies.explanation": {
                            "$not": {
                                "$regex": "^(Anomalía detectada - análisis detallado no disponible|Método de detección: keyword_analysis|⚠️ Este patrón se repite)"
                            }
                        }
                    }
                },
                {"$sort": {"anomalies.score": 1}},
                {"$limit": 100},  # Get more to filter in Python
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
            # Filtrar para solo incluir anomalías con explicaciones válidas
            async for doc in db_manager.mongodb_db["results"].aggregate(pipeline_samples):
                anomaly = doc.get("anomalies", {})
                explanation = anomaly.get("explanation", "")

                # Doble check: explicación debe tener contenido significativo
                if len(explanation) >= 100 and "keyword_analysis" not in explanation.lower():
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

            # Pipeline simplificado para extraer chunk_id puro
            # NOTA: chunk_id en results tiene formato "job_id_chunk_id"
            # FILTRO: Solo anomalías con explicaciones LLM válidas
            pipeline = [
                {
                    "$addFields": {
                        "pure_chunk_id": {
                            "$arrayElemAt": [
                                {"$split": ["$chunk_id", "_"]},
                                -1  # Tomar el último elemento después del último "_"
                            ]
                        }
                    }
                },
                {
                    "$lookup": {
                        "from": "chunks",
                        "localField": "pure_chunk_id",  # UUID sin prefijo
                        "foreignField": "_id",           # UUID sin prefijo
                        "as": "chunk"
                    }
                },
                {"$unwind": "$chunk"},
                {"$match": {"chunk.file_id": {"$in": file_ids}}},
                {"$match": {"anomalies": {"$exists": True, "$ne": None}}},
                {"$unwind": "$anomalies"},
                {"$match": {"anomalies.is_anomaly": True}},
                {
                    "$match": {
                        "anomalies.explanation": {
                            "$not": {
                                "$regex": "^(Anomalía detectada - análisis detallado no disponible|Método de detección: keyword_analysis|⚠️ Este patrón se repite)"
                            }
                        }
                    }
                },
                {"$sort": {"anomalies.score": 1}},  # Sort by score ascending (most anomalous first)
                {"$skip": offset},
                {"$limit": count * 3}  # Get more to filter in Python
            ]

            samples = []
            async for doc in db_manager.mongodb_db["results"].aggregate(pipeline):
                anomaly = doc.get("anomalies", {})

                # Extraer datos de la anomalía
                log_entry = anomaly.get("log_entry", "")
                explanation = anomaly.get("explanation", "")
                score = anomaly.get("score", 0)

                # Doble check: explicación debe tener contenido significativo del LLM
                if len(explanation) < 100 or "keyword_analysis" in explanation.lower():
                    continue

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

                if len(samples) >= count:
                    break

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
        """Infer anomaly category using scoring system for better variety"""
        explanation = anomaly.get("explanation", "").lower()
        log_entry = anomaly.get("log_entry", "").lower()
        combined = explanation + " " + log_entry

        # Scoring system - each category gets points based on keyword matches
        scores = {
            "Seguridad": 0,
            "Performance": 0,
            "Red": 0,
            "Comportamiento": 0,
            "General": 0
        }

        # Security keywords (specific attacks get higher points)
        if any(kw in combined for kw in ["attack", "malware", "intrusion", "breach", "exploit"]):
            scores["Seguridad"] += 3
        if any(kw in combined for kw in ["unauthorized", "injection", "xss", "csrf", "sql injection"]):
            scores["Seguridad"] += 2
        if "brute force" in combined or "dictionary" in combined:
            scores["Seguridad"] += 3

        # Performance keywords
        perf_words = ["slow", "timeout", "latency", "response time", "performance",
                      "degradation", "bottleneck", "high load", "resource", "memory", "cpu"]
        for word in perf_words:
            if word in combined:
                scores["Performance"] += 1

        # Network keywords
        net_words = ["connection refused", "packet loss", "tcp", "udp", "port", "firewall",
                     "routing", "dns", "subnet", "gateway"]
        for word in net_words:
            if word in combined:
                scores["Red"] += 1

        # Behavior keywords
        beh_words = ["exception", "crash", "stack trace", "null pointer",
                     "segmentation fault", "panic", "fatal", "unexpected"]
        for word in beh_words:
            if word in combined:
                scores["Comportamiento"] += 1

        # Score-based fallback
        score = anomaly.get("score", 0)
        if score < -0.5:
            scores["Seguridad"] += 1
        elif score > 0.3:
            scores["General"] += 1

        # Find category with highest score
        max_score = 0
        result_type = "General"
        for category, category_score in scores.items():
            if category_score > max_score:
                max_score = category_score
                result_type = category

        return result_type

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

    # ==================== ENHANCED LOG ANALYSIS METHODS ====================

    def _analyze_log_type_detailed(self, log_entries: List[str]) -> LogTypeInfo:
        """Analyze log entries to determine detailed type information (dynamic)"""
        if not log_entries:
            return LogTypeInfo(
                format_type="No estructurado",
                has_structured_data=False,
                typical_fields=[],
                sample_entries=[]
            )

        # Analyze structure dynamically from actual logs
        structure_analysis = self._analyze_log_structure(log_entries)
        timestamp_analysis = self._analyze_timestamps(log_entries)
        fields_analysis = self._extract_fields_dynamically(log_entries)

        sample_entries = log_entries[:3]

        # Build format type description from detected patterns
        format_type = self._describe_format_type(structure_analysis)

        # Build timestamp format from actual examples
        timestamp_format = timestamp_analysis.get("description") if timestamp_analysis else None

        return LogTypeInfo(
            format_type=format_type,
            timestamp_format=timestamp_format,
            has_structured_data=structure_analysis.get("has_structure", False),
            typical_fields=fields_analysis[:10],  # Top 10 most common fields
            sample_entries=sample_entries
        )

    def _analyze_log_structure(self, log_entries: List[str]) -> dict:
        """Dynamically analyze the structure of log entries"""
        structure_info = {
            "has_structure": False,
            "patterns_found": [],
            "separators": [],
            "has_json": False,
            "has_brackets": False,
            "has_timestamp_prefix": False,
            "has_ip": False
        }

        for entry in log_entries[:50]:
            entry = entry.strip()

            # Detect JSON
            if entry.startswith('{') and ('"' in entry or '"' in entry):
                structure_info["has_json"] = True
                structure_info["has_structure"] = True
                structure_info["patterns_found"].append("json")
                continue

            # Detect IP address at start (common in web server logs)
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', entry):
                structure_info["has_ip"] = True
                structure_info["has_structure"] = True

            # Detect brackets [timestamp] or [component]
            if '[' in entry[:50] and ']' in entry[:100]:
                structure_info["has_brackets"] = True
                structure_info["patterns_found"].append("brackets")

            # Detect separators
            if entry.count('|') >= 3:
                structure_info["separators"].append("pipe")
            if entry.count(',') >= 5:
                structure_info["separators"].append("comma")
            if entry.count('\t') >= 3:
                structure_info["separators"].append("tab")

            # Detect timestamp prefix
            if re.match(r'^\d{4}-\d{2}-\d{2}', entry) or re.match(r'^\d{2}/\w{3}/\d{4}', entry):
                structure_info["has_timestamp_prefix"] = True

        return structure_info

    def _analyze_timestamps(self, log_entries: List[str]) -> dict:
        """Extract and analyze timestamp formats from actual logs"""
        timestamp_examples = []
        formats_found = []

        for entry in log_entries[:30]:
            entry = entry.strip()

            # ISO8601: 2024-01-15T10:30:45Z or 2024-01-15 10:30:45
            iso_match = re.search(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', entry)
            if iso_match:
                timestamp_examples.append(iso_match.group(0))
                if "ISO8601" not in formats_found:
                    formats_found.append("ISO8601")

            # Apache: 15/Jan/2024:10:30:45
            apache_match = re.search(r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}', entry)
            if apache_match:
                timestamp_examples.append(apache_match.group(0))
                if "Apache" not in formats_found:
                    formats_found.append("Apache")

            # Unix timestamp: 1705315845 or 1705315845.123
            unix_match = re.search(r'\b\d{10}\.?\d{0,3}\b', entry)
            if unix_match and int(unix_match.group(0)[:10]) > 1000000000:
                timestamp_examples.append(unix_match.group(0))
                if "Unix" not in formats_found:
                    formats_found.append("Unix")

        if not timestamp_examples:
            return {}

        # Build description from actual examples
        most_common = max(set(timestamp_examples), key=timestamp_examples.count) if timestamp_examples else ""
        return {
            "description": f"Ejemplo detectado: {most_common}",
            "formats_found": formats_found,
            "examples": timestamp_examples[:3]
        }

    def _extract_fields_dynamically(self, log_entries: List[str]) -> List[str]:
        """Extract field names dynamically from actual log patterns"""
        field_counts = {}

        for entry in log_entries[:50]:
            entry = entry.strip()

            # JSON fields
            if entry.startswith('{'):
                fields = self._extract_json_fields(entry)
                for field in fields:
                    field_counts[field] = field_counts.get(field, 0) + 1

            # Key-value pairs: key=value or key: value
            kv_pattern = re.findall(r'(\w+)[:=]\s*([^\s,]+|"[^"]*")', entry)
            for key, _ in kv_pattern:
                if len(key) > 2 and len(key) < 30:  # Reasonable field name length
                    field_counts[key] = field_counts.get(key, 0) + 1

            # Bracket patterns: [field_name]
            bracket_fields = re.findall(r'\[([\w\-\.]+)\]', entry)
            for field in bracket_fields:
                # Filter out non-field patterns
                if not any(x in field.lower() for x in ["error", "warn", "info", "debug"]):
                    field_counts[field] = field_counts.get(field, 0) + 1

        # Sort by frequency and return top fields
        sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
        return [field for field, count in sorted_fields]

    def _describe_format_type(self, structure_analysis: dict) -> str:
        """Generate format description from detected patterns"""
        parts = []

        if structure_analysis.get("has_json"):
            parts.append("Estructurado JSON")

        if structure_analysis.get("has_ip"):
            parts.append("Con dirección IP al inicio")

        if structure_analysis.get("has_timestamp_prefix"):
            parts.append("Con timestamp al inicio")

        if "pipe" in structure_analysis.get("separators", []):
            parts.append("Campos separados por |")

        if "comma" in structure_analysis.get("separators", []):
            parts.append("Campos separados por coma")

        if "tab" in structure_analysis.get("separators", []):
            parts.append("Campos separados por tabulador")

        if structure_analysis.get("has_brackets"):
            parts.append("Con campos entre corchetes")

        if not parts:
            return "Texto plano / Sin estructura detectada"

        return " | ".join(parts) if len(parts) <= 2 else "Formato mixto con múltiples patrones"

    def _extract_json_fields(self, json_entry: str) -> List[str]:
        """Extract field names from a JSON log entry"""
        try:
            import json
            data = json.loads(json_entry)
            return list(data.keys())
        except:
            return []

    async def _identify_log_sources(
        self,
        conn,
        project_id: UUID,
        sample_logs: List[str]
    ) -> List[LogSourceInfo]:
        """Identify the main sources of logs (services, components) dynamically"""
        sources = {}

        for entry in sample_logs[:30]:
            # Extract all possible source names
            extracted_names = self._extract_all_source_names(entry)

            for name in extracted_names:
                if name:
                    if name not in sources:
                        sources[name] = {
                            "service_name": name,
                            "log_count": 0,
                            "anomaly_count": 0,
                            "example_entries": []
                        }
                    sources[name]["log_count"] += 1
                    if len(sources[name]["example_entries"]) < 2:
                        sources[name]["example_entries"].append(entry[:100])

        # Convert to list and sort by log count
        source_list = [
            LogSourceInfo(
                service_name=v["service_name"],
                log_count=v["log_count"],
                anomaly_count=v["anomaly_count"],  # Would need MongoDB query
                example_entries=v["example_entries"]
            )
            for v in sources.values()
        ]
        source_list.sort(key=lambda x: x.log_count, reverse=True)

        return source_list[:5]  # Top 5 sources

    # ==================== LOG SOURCE DETECTION ====================

    def _detect_log_sources(self, log_entries: List[str]) -> dict:
        """
        Detect the specific source/system that generated the logs - DYNAMIC.
        Analyzes patterns, keywords, and structures to infer the source.
        """
        # 1. Extract unique identifiers and patterns from logs
        signatures = self._extract_log_signatures(log_entries)

        # 2. Group similar signatures
        signature_groups = self._group_similar_signatures(signatures)

        # 3. Identify the most likely source based on patterns
        detected_source = self._infer_source_from_patterns(signature_groups, log_entries)

        return detected_source

    def _extract_log_signatures(self, log_entries: List[str]) -> List[dict]:
        """Extract unique signatures/identifiers from log entries"""
        signatures = []

        for entry in log_entries[:50]:
            entry = entry.strip()
            if not entry:
                continue

            signature = {
                "original": entry,
                "patterns": {
                    "bracket_content": [],
                    "colon_prefix": [],
                    "product_names": [],
                    "error_keywords": [],
                    "unique_strings": []
                }
            }

            # Extract content between brackets
            brackets = re.findall(r'\[([^\]]+)\]', entry)
            signature["patterns"]["bracket_content"] = brackets

            # Extract prefixes before colons (service names)
            colon_matches = re.finditer(r'^([\w\.\-]+):\s*', entry)
            for match in colon_matches:
                prefix = match.group(1)
                if len(prefix) > 2 and len(prefix) < 30:
                    signature["patterns"]["colon_prefix"].append(prefix)

            # Extract common product/service names (capitalized words)
            words = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', entry)
            signature["patterns"]["product_names"] = list(set(words))

            # Extract error keywords
            error_keywords = re.findall(r'\b(error|failed|denied|timeout|exception|fatal|critical)\b', entry, re.IGNORECASE)
            signature["patterns"]["error_keywords"] = list(set(error_keywords))

            # Extract file extensions (.php, .js, etc.)
            extensions = re.findall(r'\b\.\w{2,5}\b', entry)
            signature["patterns"]["extensions"] = list(set(extensions))

            signatures.append(signature)

        return signatures

    def _group_similar_signatures(self, signatures: List[dict]) -> dict:
        """Group similar signatures and identify common patterns"""
        groups = {
            "bracket_content": {},
            "colon_prefix": {},
            "product_names": {},
            "extensions": {}
        }

        for sig in signatures:
            # Count bracket contents
            for content in sig["patterns"]["bracket_content"]:
                groups["bracket_content"][content] = groups["bracket_content"].get(content, 0) + 1

            # Count colon prefixes
            for prefix in sig["patterns"]["colon_prefix"]:
                groups["colon_prefix"][prefix] = groups["colon_prefix"].get(prefix, 0) + 1

            # Count product names
            for name in sig["patterns"]["product_names"]:
                if len(name) > 3:  # Ignore short words
                    groups["product_names"][name] = groups["product_names"].get(name, 0) + 1

            # Count extensions
            for ext in sig["patterns"]["extensions"]:
                groups["extensions"][ext] = groups["extensions"].get(ext, 0) + 1

        return groups

    def _infer_source_from_patterns(self, groups: dict, log_entries: List[str]) -> dict:
        """Infer the most likely source based on detected patterns"""
        detected_sources = []
        primary_source = "Fuente genérica"
        confidence = "low"
        details = []

        # Check for product names that indicate specific sources
        product_names = sorted(groups["product_names"].items(), key=lambda x: x[1], reverse=True)
        if product_names:
            top_products = product_names[:5]
            for name, count in top_products:
                detected_sources.append(f"{name} ({count} menciones)")

        # Check for bracket patterns
        bracket_patterns = sorted(groups["bracket_content"].items(), key=lambda x: x[1], reverse=True)
        if bracket_patterns:
            top_brackets = bracket_patterns[:3]
            for content, count in top_brackets:
                if len(content) < 50:  # Reasonable length
                    detected_sources.append(f"[{content}] ({count} veces)")

        # Check for colon prefixes (likely service names)
        colon_prefixes = sorted(groups["colon_prefix"].items(), key=lambda x: x[1], reverse=True)
        if colon_prefixes:
            for prefix, count in colon_prefixes[:3]:
                if prefix and not prefix.lower().startswith(("time", "date", "level")):
                    detected_sources.append(f"{prefix} ({count} veces)")

        # Check for file extensions (indicates language/platform)
        extensions = sorted(groups["extensions"].items(), key=lambda x: x[1], reverse=True)
        if extensions:
            ext_info = {
                ".php": "PHP",
                ".js": "JavaScript/Node.js",
                ".py": "Python",
                ".java": "Java",
                ".exe": "Windows/Ejecutable",
                ".dll": "Windows/DLL",
                ".so": "Linux/Shared Library",
            }
            for ext, count in extensions[:5]:
                if ext in ext_info:
                    detected_sources.append(f"{ext_info[ext]} (extensión {ext})")

        # Determine primary source
        if colon_prefixes:
            # Most frequent colon prefix is likely the service name
            primary_source = colon_prefixes[0][0]
            confidence = "medium" if colon_prefixes[0][1] > 3 else "low"
        elif product_names:
            primary_source = product_names[0][0]
            confidence = "medium" if product_names[0][1] > 3 else "low"

        # Build details description
        if detected_sources:
            details = f"Fuentes detectadas: {', '.join(detected_sources[:3])}"
        else:
            details = "No se detectaron patrones característicos de una fuente específica"

        return {
            "detected_sources": detected_sources[:5],
            "primary_source": primary_source,
            "confidence": confidence,
            "details": details
        }

    def _generate_source_description(self, sources_found: dict, log_entries: List[str]) -> str:
        """Generate a human-readable description of detected sources"""
        if not sources_found or not any(sources_found.values()):
            return "Los logs no contienen patrones característicos de ningún sistema o aplicación específica."

        # Find the most common pattern
        all_patterns = []
        for category, patterns in sources_found.items():
            for pattern, count in patterns.items():
                all_patterns.append((pattern, count, category))

        if not all_patterns:
            return "No se detectaron patrones específicos."

        # Sort by count
        all_patterns.sort(key=lambda x: x[1], reverse=True)
        top_pattern = all_patterns[0]

        pattern, count, category = top_pattern

        # Map category to description
        category_descriptions = {
            "bracket_content": "entre corchetes",
            "colon_prefix": "como prefijo de servicio",
            "product_names": "como nombre de producto",
            "extensions": "como extensión de archivo"
        }

        return f"La fuente más detectada es **\"{pattern}\"** ({category_descriptions.get(category, '')}, {count} menciones)."

    def _extract_all_source_names(self, log_entry: str) -> List[str]:
        """Extract all possible source/service names from a log entry"""
        names = []
        entry = log_entry.strip()

        # Pattern 1: [ServiceName] or [Service] at any position
        bracket_matches = re.findall(r'\[([\w\-\.]+)\]', entry)
        for match in bracket_matches:
            # Filter out obvious non-service patterns
            if not any(x in match.lower() for x in ["error", "warn", "info", "debug", "client", "thread", "date", "time"]):
                names.append(match)

        # Pattern 2: ServiceName: at the beginning
        colon_match = re.match(r'^([\w\-\.]+):\s', entry)
        if colon_match:
            names.append(colon_match.group(1))

        # Pattern 3: "service": "..." in JSON
        if entry.startswith('{'):
            service_match = re.search(r'"(service|component|logger|source|app|application)":\s*"([^"]+)"', entry, re.IGNORECASE)
            if service_match:
                names.append(service_match.group(2))

        # Pattern 4: ServiceName surrounded by common separators
        separator_matches = re.findall(r'[\s|,\t]+([\w\-\.]+)(?=\s*[\[\|:,]|\s+[A-Z]{3,}\s)', entry)
        for match in separator_matches:
            if len(match) > 2 and len(match) < 30:
                names.append(match)

        # Deduplicate while preserving order
        seen = set()
        unique_names = []
        for name in names:
            if name.lower() not in seen:
                seen.add(name.lower())
                unique_names.append(name)

        return unique_names[:3]  # Max 3 names per entry

    def _get_predominant_log_level(self, log_entries: List[str]) -> Optional[str]:
        """Determine the predominant log level in the sample"""
        level_counts = {}

        for entry in log_entries:
            entry_upper = entry.upper()

            # Common log levels
            for level in ["TRACE", "DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL", "FATAL", "PANIC"]:
                # Match as whole word or at start
                if re.search(r'\b' + level + r'\b', entry_upper) or entry_upper.startswith(level + " "):
                    level_counts[level] = level_counts.get(level, 0) + 1

        # Handle WARN/WARNING grouping
        if "WARN" in level_counts and "WARNING" in level_counts:
            level_counts["WARN"] += level_counts.pop("WARNING")

        if not level_counts:
            return None

        # Find predominant level
        max_count = max(level_counts.values())
        for level, count in level_counts.items():
            if count == max_count:
                return level

        return None


# Singleton instance
course_generation_service = CourseGenerationService()
