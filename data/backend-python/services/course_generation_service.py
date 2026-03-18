"""
Course Generation Service
Dynamically generates courses based on project anomalies and logs
"""
import logging
import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from config.database import db_manager
from models.learning_models import (
    CourseModule, CourseLesson, ProjectAnalysis,
    CourseGenerateResponse, CoursePreviewResponse,
    CourseRegenerateResponse
)

logger = logging.getLogger(__name__)


class CourseGenerationService:
    """Service for generating dynamic courses based on project data"""

    MIN_ANOMALIES_REQUIRED = 10  # Minimum anomalies to generate a course

    async def can_generate_course(self, project_id: UUID) -> dict:
        """Check if there's enough data to generate a course"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Check if there are completed processing jobs (include NULL for backwards compatibility)
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

                # Check if there's already a draft/pending course - return details for better UX
                existing = await conn.fetchrow(
                    """SELECT id, title, status FROM learning.course_modules
                       WHERE project_id = $1 AND status IN ('draft', 'pending')
                       ORDER BY created_at DESC LIMIT 1""",
                    project_id
                )

                if existing:
                    return {
                        "can_generate": False,
                        "reason": f"Ya existe un curso en borrador/pendiente: '{existing['title']}' (status: {existing['status']}).",
                        "existing_course_id": str(existing["id"]),
                        "existing_status": existing["status"]
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
                    course_id=uuid4(),  # Placeholder
                    status="error",
                    modules_created=0,
                    lessons_created=0,
                    message=check.get("reason", "Cannot generate course")
                )

            async with db_manager.postgres_pool.acquire() as conn:
                # Analyze project data
                analysis = await self.preview_course_data(project_id)

                # Create course name if not provided
                course_name = name or f"Curso de Análisis - {analysis.project_name}"

                # Find the next available module_order to avoid collisions
                max_order = await conn.fetchval(
                    "SELECT COALESCE(MAX(module_order), 0) FROM learning.course_modules WHERE project_id = $1",
                    project_id if scope == "project" else None
                )
                base_order = (max_order // 10 + 1) * 10  # Start at next multiple of 10

                logger.info(f"[DEBUG] Using base module_order={base_order} (max existing={max_order})")

                # Create course module (the course itself)
                logger.info(f"[DEBUG] Creating course with created_by={created_by}, type={type(created_by)}")
                course_id = await conn.fetchval("""
                    INSERT INTO learning.course_modules
                    (project_id, workspace_id, module_order, title, description, status, scope, created_by)
                    VALUES ($1, $2, $3, $4, $5, 'draft', $6, $7)
                    RETURNING id
                """, project_id if scope == "project" else None,
                   workspace_id,  # Always save workspace_id regardless of scope
                   base_order, course_name,
                   f"Curso generado dinámicamente basado en {analysis.total_anomalies} anomalías detectadas.",
                   scope, created_by)
                logger.info(f"[DEBUG] Course created with id={course_id}")

                # Generate modules
                total_lessons = 0

                # Module 1: Project Context (DYNAMIC)
                module1_id = await self._create_module_1_context(conn, course_id, analysis, base_order + 1)
                total_lessons += 2

                # Module 2: Anomaly Categories (STATIC)
                module2_lessons = await self._create_module_2_categories(
                    conn, course_id, analysis, module_order=base_order + 2
                )
                total_lessons += module2_lessons

                # Module 3: Practical Analysis (STATIC)
                module3_lessons = await self._create_module_3_practical(
                    conn, course_id, project_id, module_order=base_order + 3
                )
                total_lessons += module3_lessons

                # Module 4: Final Evaluation (STATIC)
                module4_lessons = await self._create_module_4_evaluation(
                    conn, course_id, project_id, module_order=base_order + 4
                )
                total_lessons += module4_lessons

                logger.info(f"Course {course_id} generated for project {project_id} with {total_lessons} lessons")

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
                # Get existing course
                existing = await conn.fetchrow(
                    """SELECT id, version_number, status
                       FROM learning.course_modules
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
                    "UPDATE learning.course_modules SET version_number = $1 WHERE id = $2",
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

    async def refresh_lesson(
        self,
        lesson_id: UUID,
        project_id: UUID,
        preserve_selection: bool = False
    ) -> dict:
        """Refresh lesson content with new anomalies from project"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get lesson info
                lesson = await conn.fetchrow(
                    """SELECT l.module_id, cm.project_id, l.lesson_order, l.is_dynamic
                       FROM learning.course_lessons l
                       JOIN learning.course_modules cm ON cm.id = l.module_id
                       WHERE l.id = $1""",
                    lesson_id
                )

                if not lesson:
                    raise ValueError("Lesson not found")

                if lesson["is_dynamic"]:
                    return {"message": "Las lecciones dinámicas no necesitan actualización"}

                # Get new anomalies and update content
                # This would be implemented based on lesson type
                await conn.execute(
                    """UPDATE learning.course_lessons
                       SET content = content || '\n\n[Actualizado: ' || CURRENT_TIMESTAMP || ']'
                       WHERE id = $1""",
                    lesson_id
                )

                # Mark course as draft again
                await conn.execute(
                    """UPDATE learning.course_modules
                       SET status = 'draft'
                       WHERE id = $1""",
                    lesson["module_id"]
                )

                return {
                    "lesson_id": str(lesson_id),
                    "message": "Lección actualizada. El curso vuelve a estado borrador y requiere aprobación."
                }

        except Exception as e:
            logger.error(f"Error refreshing lesson: {e}")
            raise

    # ==================== PRIVATE METHODS ====================

    async def _count_project_anomalies(self, conn, project_id: UUID) -> int:
        """Count total anomalies in project from MongoDB results collection"""
        try:
            # Get completed job IDs (include NULL for backwards compatibility)
            job_ids = await conn.fetch(
                """SELECT id FROM processing.processing_jobs
                   WHERE (project_id = $1 OR project_id IS NULL) AND status = 'completed'""",
                project_id
            )

            if not job_ids:
                return 0

            # Get file_id strings from jobs
            file_ids = [str(job["id"]) for job in job_ids]

            # Use aggregation to count anomalies (same logic as _get_anomalies_analysis)
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
            import traceback
            traceback.print_exc()
            return 0

    async def _get_anomalies_analysis(self, conn, project_id: UUID) -> dict:
        """Get detailed anomaly analysis from MongoDB results"""
        try:
            # Get completed job IDs (include jobs without project_id for backwards compatibility)
            job_ids = await conn.fetch(
                """SELECT id FROM processing.processing_jobs
                   WHERE status = 'completed'
                   AND (project_id = $1 OR project_id IS NULL)""",
                project_id
            )

            if not job_ids:
                return {"total": 0, "categories": {}, "severity": {}, "top_anomalies": []}

            # Get file_id strings from jobs
            file_ids = [str(job["id"]) for job in job_ids]
            logger.info(f"[DEBUG] Found {len(file_ids)} job IDs: {file_ids}")

            # Pipeline to aggregate anomaly data from MongoDB results collection
            # Convert chunk_id string to ObjectId for lookup
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
                        },
                        "anomalies": {"$push": "$$ROOT"}
                    }
                }
            ]

            logger.info(f"[DEBUG] Running aggregation pipeline with {len(file_ids)} file IDs")
            result_count = 0
            async for result in db_manager.mongodb_db["results"].aggregate(pipeline):
                result_count += 1
                logger.info(f"[DEBUG] Aggregation result {result_count}: {result.get('total', 0)} total anomalies")
                total = result.get("total", 0)

                # Categorize anomalies by explanation keywords
                categories = self._categorize_anomalies(result.get("anomalies", []))

                # Get top anomalies by score (most negative first)
                top_anomalies = sorted(
                    result.get("anomalies", []),
                    key=lambda x: x.get("anomalies", {}).get("score", 0)
                )[:5]
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

                logger.info(f"[DEBUG] Returning {total} anomalies")
                return {
                    "total": total,
                    "categories": categories,
                    "severity": {
                        "high": result.get("high_severity", 0),
                        "medium": result.get("medium_severity", 0),
                        "low": result.get("low_severity", 0)
                    },
                    "top_anomalies": top_anomalies_formatted
                }

            # If no results found
            logger.info(f"[DEBUG] No aggregation results returned, returning 0 anomalies")
            return {"total": 0, "categories": {}, "severity": {}, "top_anomalies": []}

        except Exception as e:
            logger.error(f"Error getting anomalies analysis: {e}")
            import traceback
            traceback.print_exc()
            return {"total": 0, "categories": {}, "severity": {}, "top_anomalies": []}

    async def _get_log_formats(self, conn, project_id: UUID) -> List[str]:
        """Get detected log formats"""
        try:
            # Check log format from actual anomaly data
            # For now, default to common formats - this could be enhanced
            # by detecting format from the first log entry
            return ["Bro/Zeek"]  # Default format based on the logs shown
        except Exception as e:
            logger.error(f"Error getting log formats: {e}")
            return ["Unknown"]

    async def _create_module_1_context(
        self,
        conn,
        course_id: UUID,
        analysis: ProjectAnalysis,
        module_order: int
    ) -> UUID:
        """Create Module 1: Project Context (DYNAMIC)"""
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (project_id, workspace_id, module_order, title, description, status, scope, created_by, parent_id)
            SELECT project_id, workspace_id, $2, $3, $4, status, scope, created_by, $5
            FROM learning.course_modules WHERE id = $1
            RETURNING id
        """, course_id, module_order, "Contexto del Proyecto",
           "Información general sobre tu proyecto y las anomalías detectadas.", course_id)

        # Lesson 1: Tu proyecto en números (DYNAMIC)
        await conn.execute("""
            INSERT INTO learning.course_lessons
            (module_id, lesson_order, title, content, is_dynamic)
            VALUES ($1, $2, $3, $4, TRUE)
        """, module_id, 1, "Tu Proyecto en Números",
           "Contenido dinámico: Se generará al visualizar la lección.")

        # Lesson 2: Anomalías encontradas (DYNAMIC)
        await conn.execute("""
            INSERT INTO learning.course_lessons
            (module_id, lesson_order, title, content, is_dynamic)
            VALUES ($1, $2, $3, $4, TRUE)
        """, module_id, 2, "Anomalías Encontradas",
           "Contenido dinámico: Se generará al visualizar la lección.")

        return module_id

    async def _create_module_2_categories(
        self,
        conn,
        course_id: UUID,
        analysis: ProjectAnalysis,
        module_order: int
    ) -> int:
        """Create Module 2: Anomaly Categories (STATIC)"""
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (project_id, workspace_id, module_order, title, description, status, scope, created_by, parent_id)
            SELECT project_id, workspace_id, $2, $3, $4, status, scope, created_by, $5
            FROM learning.course_modules WHERE id = $1
            RETURNING id
        """, course_id, module_order, "Tipos de Anomalías",
           "Análisis de las diferentes categorías de anomalías detectadas.", course_id)

        lesson_count = 0
        lesson_order = 1

        # Create lessons for each category with anomalies
        for category, count in analysis.anomaly_categories.items():
            if count > 0:
                content = self._generate_category_lesson_content(category, count, analysis)
                await conn.execute("""
                    INSERT INTO learning.course_lessons
                    (module_id, lesson_order, title, content, is_dynamic)
                    VALUES ($1, $2, $3, $4, FALSE)
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
        """Create Module 3: Practical Analysis with Real Anomalies (STATIC)"""
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (project_id, workspace_id, module_order, title, description, status, scope, created_by, parent_id)
            SELECT project_id, workspace_id, $2, $3, $4, status, scope, created_by, $5
            FROM learning.course_modules WHERE id = $1
            RETURNING id
        """, course_id, module_order, "Análisis Práctico",
           "Ejemplos reales de anomalías detectadas en tu proyecto.", course_id)

        # Get sample anomalies (would query MongoDB in production)
        sample_anomalies = await self._get_sample_anomalies(project_id, count=5)

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
                (module_id, lesson_order, title, content, is_dynamic)
                VALUES ($1, $2, $3, $4, FALSE)
            """, module_id, 1, "Análisis de Anomalías", content)
            lesson_count = 1
        else:
            for idx, anomaly in enumerate(sample_anomalies, 1):
                content = self._generate_practical_lesson_content(anomaly, idx)
                await conn.execute("""
                    INSERT INTO learning.course_lessons
                    (module_id, lesson_order, title, content, exercise_data, is_dynamic)
                    VALUES ($1, $2, $3, $4, $5, FALSE)
                """, module_id, idx, f"Caso Práctico {idx}: {anomaly.get('type', 'Anomalía')}",
                   content, json.dumps({"anomaly_id": anomaly.get("id")}))  # Convert dict to JSON string
                lesson_count += 1

        return lesson_count

    async def _create_module_4_evaluation(
        self,
        conn,
        course_id: UUID,
        project_id: UUID,
        module_order: int
    ) -> int:
        """Create Module 4: Final Evaluation (STATIC)"""
        module_id = await conn.fetchval("""
            INSERT INTO learning.course_modules
            (project_id, workspace_id, module_order, title, description, status, scope, created_by, parent_id)
            SELECT project_id, workspace_id, $2, $3, $4, status, scope, created_by, $5
            FROM learning.course_modules WHERE id = $1
            RETURNING id
        """, course_id, module_order, "Evaluación Final",
           "Demuestra tu conocimiento analizando nuevas anomalías.", course_id)

        # Get evaluation anomalies (different from module 3)
        eval_anomalies = await self._get_sample_anomalies(project_id, count=5, exclude_seen=True)

        content = """# Evaluación Final

Analiza las siguientes 5 anomalías y demuestra tu comprensión.

## Instrucciones

1. Revisa cada anomalía presentada
2. Identifica el tipo y severidad
3. Interpreta qué significa para tu proyecto
4. Necesitas al menos 70% de respuestas correctas para aprobar

"""

        exercise_data = {
            "type": "final_exam",
            "dynamic": True,
            "passing_score": 70,
            "anomalies": [{"id": a.get("id")} for a in eval_anomalies]
        }

        await conn.execute("""
            INSERT INTO learning.course_lessons
            (module_id, lesson_order, title, content, exercise_data, is_dynamic)
            VALUES ($1, $2, $3, $4, $5, FALSE)
        """, module_id, 1, "Examen Práctico", content, json.dumps(exercise_data))

        return 1

    async def _get_sample_anomalies(
        self,
        project_id: UUID,
        count: int = 5,
        exclude_seen: bool = False
    ) -> List[dict]:
        """Get sample anomalies from project from MongoDB"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get completed job IDs
                job_ids = await conn.fetch(
                    "SELECT id FROM processing.processing_jobs WHERE project_id = $1 AND status = 'completed'",
                    project_id
                )

                if not job_ids:
                    return []

                job_id_strs = [str(job["id"]) for job in job_ids]

            # Query MongoDB for sample anomalies, sorted by score
            pipeline = [
                {"$match": {"job_id": {"$in": job_id_strs}, "anomalies": {"$exists": True}}},
                {"$unwind": "$anomalies"},
                {"$sort": {"anomalies.score": -1}},
                {"$limit": count}
            ]

            samples = []
            async for doc in db_manager.mongodb_db["results"].aggregate(pipeline):
                anomaly = doc.get("anomalies", {})
                samples.append({
                    "id": str(doc.get("_id", "")),
                    "chunk_id": doc.get("chunk_id", ""),
                    "job_id": doc.get("job_id", ""),
                    "type": self._infer_anomaly_type(anomaly),
                    "score": anomaly.get("score", 0),
                    "log_entry": anomaly.get("log_entry", ""),
                    "explanation": anomaly.get("explanation", "")
                })

            return samples

        except Exception as e:
            logger.error(f"Error getting sample anomalies: {e}")
            return []

    def _infer_anomaly_type(self, anomaly: dict) -> str:
        """Infer anomaly category from explanation and log entry"""
        explanation = anomaly.get("explanation", "").lower()
        log_entry = anomaly.get("log_entry", "").lower()
        combined = explanation + " " + log_entry

        # Keyword-based classification
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

        # Remove categories with zero count
        return {k: v for k, v in categories.items() if v > 0}

    def _generate_category_lesson_content(
        self,
        category: str,
        count: int,
        analysis: ProjectAnalysis
    ) -> str:
        """Generate content for category lesson"""
        percentage = (count / max(analysis.total_anomalies, 1)) * 100

        # Category-specific content
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

## Próximos Pasos

En el módulo de **Análisis Práctico** revisarás casos reales de anomalías de esta categoría detectadas en tu proyecto, con el log original y la explicación generada por el LLM.
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

### Explicación del LLM

{explanation}

Esta anomalía fue detectada automáticamente por el algoritmo **Isolation Forest** basado en patrones inusuales en los logs, y posteriormente analizada por un modelo de lenguaje para proporcionar contexto.

## Ejercicios de Análisis

Basado en la información anterior, responde:

1. **Identificación**: ¿Qué patrón específico hace que este log sea considerado una anomalía?

2. **Impacto**: ¿Cuál podría ser el impacto de este tipo de anomalía en tu sistema?

3. **Acción Correctiva**: ¿Qué acción inmediata recomendarías tomar?

4. **Prevención**: ¿Cómo podrías configurar alertas o monitoreo para detectar esto en el futuro?

---
*Este es un caso real detectado en tu proyecto. Analiza cuidadosamente cada aspecto.*
"""


# Singleton instance
course_generation_service = CourseGenerationService()
