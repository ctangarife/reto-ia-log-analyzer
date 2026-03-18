"""
Course Service
Business logic for the interactive mini-course system
"""
import logging
import json
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from config.database import db_manager
from models.learning_models import (
    CourseModule, CourseLesson, LessonProgress, CourseCompletion,
    ExerciseAttempt,
    CourseProgressResponse, CourseModuleResponse, CourseLessonResponse,
    LessonProgressUpdate, ExerciseValidationRequest, ExerciseValidationResponse
)

logger = logging.getLogger(__name__)


class CourseService:
    """Service for managing course content and progress"""

    async def get_workspace_courses(self, user_id: UUID, workspace_id: UUID) -> list:
        """Get all published courses (from all projects) in a workspace for a user"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get published courses from all projects in the workspace (NEW structure)
                courses = await conn.fetch("""
                    SELECT
                        p.id as project_id,
                        p.name as project_name,
                        c.id as course_id,
                        c.name as title,  -- courses table has 'name', not 'title'
                        c.description,
                        COUNT(DISTINCT l.id) as total_lessons,
                        COALESCE(SUM(CASE WHEN lp.user_id = $2 AND lp.completed_at IS NOT NULL THEN 1 ELSE 0 END), 0) as completed_lessons,
                        COALESCE(MAX(cc.badge_earned), false) as is_completed
                    FROM auth.projects p
                    JOIN learning.courses c ON c.project_id = p.id AND c.status = 'published'
                    LEFT JOIN learning.course_modules m ON m.course_id = c.id
                    LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                    LEFT JOIN learning.lesson_progress lp ON lp.lesson_id = l.id
                    LEFT JOIN learning.course_completion cc ON cc.user_id = $2 AND cc.project_id = p.id
                    WHERE p.workspace_id = $1
                    GROUP BY p.id, p.name, c.id, c.name, c.description
                    ORDER BY p.name, c.name
                """, workspace_id, user_id)

                return [dict(row) for row in courses]

        except Exception as e:
            logger.error(f"Error getting workspace courses: {e}")
            return []

    async def get_course_progress(self, user_id: UUID, project_id: UUID) -> CourseProgressResponse:
        """Get complete course progress for a user in a project (NEW structure with courses table)"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Check if there's a published course for this project
                published_course = await conn.fetchrow("""
                    SELECT c.id, c.name, c.description, c.workspace_id
                    FROM learning.courses c
                    WHERE c.project_id = $1 AND c.status = 'published'
                    ORDER BY c.published_at DESC
                    LIMIT 1
                """, project_id)

                if not published_course:
                    # No published course yet - return empty progress
                    return CourseProgressResponse(
                        course_id=None,
                        course_name="",
                        project_id=project_id,
                        workspace_id=None,
                        user_id=user_id,
                        modules=[],
                        total_modules=0,
                        completed_modules=0,
                        total_lessons=0,
                        completed_lessons=0,
                        progress_percentage=0,
                        is_completed=False,
                        badge_earned=False
                    )

                # Get modules and lessons for the published course
                modules_query = """
                    SELECT
                        m.id, m.module_order, m.title, m.description,
                        l.id as lesson_id, l.lesson_order, l.title as lesson_title,
                        l.content, l.exercise_data, l.is_dynamic,
                        lp.completed_at, lp.score
                    FROM learning.course_modules m
                    LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                    LEFT JOIN learning.lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = $1
                    WHERE m.course_id = $2
                    ORDER BY m.module_order, l.lesson_order
                """

                rows = await conn.fetch(modules_query, user_id, published_course["id"])

                # Organize data
                modules_dict = {}
                total_lessons = 0
                completed_lessons = 0

                for row in rows:
                    # Skip rows without lessons (LEFT JOIN produces NULLs when no lessons exist)
                    if row["lesson_id"] is None:
                        continue

                    module_id = row["id"]
                    if module_id not in modules_dict:
                        modules_dict[module_id] = {
                            "id": module_id,
                            "course_id": published_course["id"],
                            "module_order": row["module_order"],
                            "title": row["title"],
                            "description": row["description"],
                            "lessons": [],
                            "total_lessons": 0,
                            "completed_lessons": 0
                        }

                    # Content is now static (generated at course creation), no dynamic generation needed
                    content = row["content"]

                    # Ensure exercise_data is a dict
                    exercise_data = row["exercise_data"]
                    if exercise_data and isinstance(exercise_data, str):
                        exercise_data = json.loads(exercise_data)

                    lesson_data = {
                        "id": row["lesson_id"],
                        "module_id": module_id,
                        "lesson_order": row["lesson_order"],
                        "title": row["lesson_title"],
                        "content": content,
                        "exercise_data": exercise_data,
                        "is_completed": row["completed_at"] is not None,
                        "completed_at": row["completed_at"]
                    }

                    if row["completed_at"]:
                        completed_lessons += 1
                        modules_dict[module_id]["completed_lessons"] += 1
                    total_lessons += 1
                    modules_dict[module_id]["total_lessons"] += 1

                    modules_dict[module_id]["lessons"].append(lesson_data)

                # Calculate stats
                modules_list = list(modules_dict.values())
                total_modules = len(modules_list)
                completed_modules = sum(1 for m in modules_list if all(l["is_completed"] for l in m["lessons"]))
                progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

                # Check completion status
                completion = await conn.fetchrow(
                    "SELECT * FROM learning.course_completion WHERE user_id = $1 AND project_id = $2",
                    user_id, project_id
                )

                return CourseProgressResponse(
                    course_id=published_course["id"],
                    course_name=published_course["name"],
                    project_id=project_id,
                    workspace_id=published_course["workspace_id"],
                    user_id=user_id,
                    modules=modules_list,
                    total_modules=total_modules,
                    completed_modules=completed_modules,
                    total_lessons=total_lessons,
                    completed_lessons=completed_lessons,
                    progress_percentage=round(progress_percentage, 1),
                    is_completed=completion is not None,
                    completed_at=completion["completed_at"] if completion else None,
                    badge_earned=completion["badge_earned"] if completion else False,
                    certificate_url=completion["certificate_url"] if completion else None
                )

        except Exception as e:
            logger.error(f"Error getting course progress: {e}")
            raise

    async def complete_lesson(self, user_id: UUID, project_id: UUID, lesson_id: UUID, score: Optional[int] = None) -> dict:
        """Mark a lesson as completed"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Insert or update progress
                await conn.execute("""
                    INSERT INTO learning.lesson_progress (user_id, project_id, lesson_id, completed_at, score, attempts)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4, 1)
                    ON CONFLICT (user_id, project_id, lesson_id)
                    DO UPDATE SET
                        completed_at = CURRENT_TIMESTAMP,
                        score = COALESCE($5, lesson_progress.score),
                        attempts = lesson_progress.attempts + 1
                """, user_id, project_id, lesson_id, score, score)

                # Check if all lessons in all modules are complete
                await self._check_course_completion(conn, user_id, project_id)

                return {"message": "Lesson marked as completed", "score": score}

        except Exception as e:
            logger.error(f"Error completing lesson: {e}")
            raise

    async def get_project_exercises(self, user_id: UUID, project_id: UUID, lesson_id: UUID, count: int = 5) -> list:
        """Get dynamic exercises using project anomalies"""
        try:
            # Get exercise configuration for this lesson
            async with db_manager.postgres_pool.acquire() as conn:
                lesson = await conn.fetchrow(
                    "SELECT exercise_data FROM learning.course_lessons WHERE id = $1",
                    lesson_id
                )

                if not lesson or not lesson["exercise_data"]:
                    return []

                exercise_type = lesson["exercise_data"]["type"]

                if exercise_type == "project_anomalies":
                    # Get recent anomalies from this project
                    anomalies = await conn.fetch("""
                        SELECT
                            r.id as anomaly_id,
                            r.log_entry,
                            r.score,
                            r.explanation
                        FROM (
                            SELECT DISTINCT ON (r.anomaly_id) r.id
                            FROM processing.processing_jobs j
                            JOIN logsanomaly.chunks c ON c.file_id = j.id
                            JOIN logsanomaly.results r ON r.chunk_id = str(c._id)
                            WHERE j.status = 'completed'
                            AND (j.project_id = $1 OR j.project_id IS NULL)
                            ORDER BY j.completed_at DESC
                            LIMIT 100
                        ) recent
                        CROSS JOIN LATERAL jsonb_array_elements(r.anomalies) as anomaly_data
                        CROSS JOIN LATERAL logsanomaly.chunks c2 ON c2._id::text = anomaly_data->>'chunk_id'
                        WHERE anomaly_data->>'is_anomaly' = 'true'
                        ORDER BY RANDOM()
                        LIMIT $2
                    """, project_id, count)

                    return [dict(row) for row in anomalies]

                elif exercise_type == "final_exam":
                    # Get diverse anomalies for final exam
                    anomalies = await conn.fetch("""
                        SELECT DISTINCT
                            anomaly_data->>'log_entry' as log_entry,
                            anomaly_data->>'score' as score,
                            anomaly_data->>'explanation' as explanation,
                            anomaly_data->>'is_anomaly' as is_anomaly
                        FROM processing.processing_jobs j
                        JOIN logsanomaly.chunks c ON c.file_id = j.id
                        JOIN logsanomaly.results r ON r.chunk_id = str(c._id)
                        CROSS JOIN LATERAL jsonb_array_elements(r.anomalies) as anomaly_data
                        WHERE j.status = 'completed'
                        AND (j.project_id = $1 OR j.project_id IS NULL)
                        ORDER BY RANDOM()
                        LIMIT $2
                    """, project_id, count)

                    return [dict(row) for row in anomalies]

                return []

        except Exception as e:
            logger.error(f"Error getting project exercises: {e}")
            return []

    async def validate_exercise_answer(self, user_id: UUID, project_id: UUID, data: ExerciseValidationRequest) -> ExerciseValidationResponse:
        """Validate a user's exercise answer"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get lesson and exercise data
                lesson = await conn.fetchrow(
                    "SELECT exercise_data FROM learning.course_lessons WHERE id = $1",
                    data.lesson_id
                )

                if not lesson or not lesson["exercise_data"]:
                    return ExerciseValidationResponse(
                        is_correct=False,
                        feedback="Esta lección no tiene un ejercicio configurado.",
                        explanation=None
                    )

                exercise_type = lesson["exercise_data"]["type"]

                if exercise_type == "quiz" or exercise_type == "analysis":
                    # Validate static quiz questions
                    return await self._validate_static_exercise(conn, user_id, project_id, data, lesson["exercise_data"])

                elif exercise_type == "project_anomalies" or exercise_type == "final_exam":
                    # For project-based exercises, we'll return the correct answer for learning
                    return ExerciseValidationResponse(
                        is_correct=True,
                        feedback="Buen análisis de la anomalía.",
                        correct_answer=None,
                        explanation="Esta anomalía ha sido detectada por LogsAnomaly usando Isolation Forest y explicada por el LLM."
                    )

                return ExerciseValidationResponse(
                    is_correct=False,
                    feedback="Tipo de ejercicio no reconocido.",
                    explanation=None
                )

        except Exception as e:
            logger.error(f"Error validating exercise: {e}")
            raise

    async def _validate_static_exercise(self, conn, user_id: UUID, project_id: UUID, data: ExerciseValidationRequest, exercise_data: dict) -> ExerciseValidationResponse:
        """Validate static quiz/analysis exercises"""
        questions = exercise_data["questions"]
        correct_count = 0
        total_count = len(questions)

        for q in questions:
            user_answer = data.user_answer.get(q["id"])
            if user_answer == q["correct"]:
                correct_count += 1

        is_correct = correct_count == total_count
        score = int((correct_count / total_count) * 100) if total_count > 0 else 0

        # Record attempt
        await conn.execute("""
            INSERT INTO learning.exercise_attempts (user_id, project_id, lesson_id, user_answer, is_correct)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, project_id, data.lesson_id, data.user_answer, is_correct)

        if is_correct:
            return ExerciseValidationResponse(
                is_correct=True,
                feedback=f"¡Excelente! Todas las respuestas son correctas ({correct_count}/{total_count})",
                correct_answer=None,
                explanation=f"Has completado este ejercicio con un score del {score}%."
            )
        else:
            return ExerciseValidationResponse(
                is_correct=False,
                feedback=f"Tienes {correct_count} de {total_count} respuestas correctas. Inténtalo de nuevo.",
                correct_answer={q["id"]: q["correct"] for q in questions},
                explanation="Revisa el contenido de la lección y vuelve a intentarlo."
            )

    async def _check_course_completion(self, conn, user_id: UUID, project_id: UUID) -> None:
        """Check if course is complete and create completion record"""
        # Count total and completed lessons
        stats = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM learning.course_lessons l
                 JOIN learning.course_modules m ON m.id = l.module_id
                 WHERE m.project_id = $1) as total_lessons,
                (SELECT COUNT(*) FROM learning.lesson_progress lp
                 JOIN learning.course_lessons l ON l.id = lp.lesson_id
                 JOIN learning.course_modules m ON m.id = l.module_id
                 WHERE m.project_id = $1 AND lp.user_id = $2) as completed_lessons
        """, project_id, user_id)

        if not stats:
            return

        total_lessons = stats["total_lessons"]
        completed_lessons = stats["completed_lessons"]

        if total_lessons > 0 and completed_lessons == total_lessons:
            # Check if completion record already exists
            existing = await conn.fetchval(
                "SELECT COUNT(*) FROM learning.course_completion WHERE user_id = $1 AND project_id = $2",
                user_id, project_id
            )

            if existing == 0:
                await conn.execute("""
                    INSERT INTO learning.course_completion (user_id, project_id, total_score, badge_earned)
                    VALUES ($1, $2, $3, TRUE)
                """, user_id, project_id, 100)  # 100% score for completion

                logger.info(f"User {user_id} completed course for project {project_id}")

    async def _generate_dynamic_lesson_content(
        self,
        conn,
        project_id: UUID,
        lesson_title: str
    ) -> str:
        """Generate dynamic content for lessons based on current project data"""
        try:
            if lesson_title == "Tu Proyecto en Números":
                # Generate real-time statistics
                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(DISTINCT j.id) as completed_jobs,
                        MIN(j.started_at) as first_job,
                        MAX(j.completed_at) as last_job
                    FROM processing.processing_jobs j
                    WHERE j.status = 'completed'
                    AND (j.project_id = $1 OR j.project_id IS NULL)
                """, project_id)

                # Count anomalies (simplified - would query MongoDB in production)
                total_anomalies = await conn.fetchval(
                    """SELECT COUNT(DISTINCT c._id::text)
                       FROM logsanomaly.chunks c
                       JOIN processing.processing_jobs j ON j.id = c.file_id
                       WHERE c.anomalies EXISTS
                       AND (j.project_id = $1 OR j.project_id IS NULL)""",
                    project_id
                ) or 0

                return f"""# Tu Proyecto en Números

## Estadísticas Actuales

| Métrica | Valor |
|---------|-------|
| Trabajos completados | {stats['completed_jobs'] if stats else 0} |
| Período de análisis | {str(stats['first_job'])[:10] if stats and stats['first_job'] else 'N/A'} - {str(stats['last_job'])[:10] if stats and stats['last_job'] else 'N/A'} |
| Anomalías detectadas | {total_anomalies} |

**Este contenido se genera dinámicamente basado en los datos más recientes de tu proyecto.**
"""

            elif lesson_title == "Anomalías Encontradas":
                # Get anomaly categories
                categories = await conn.fetch("""
                    SELECT
                        COUNT(*) as count,
                        CASE
                            WHEN r.anomalies->0->>'type' IS NOT NULL THEN r.anomalies->0->>'type'
                            ELSE 'Sin clasificar'
                        END as category
                    FROM logsanomaly.chunks c
                    JOIN processing.processing_jobs j ON j.id = c.file_id
                    CROSS JOIN jsonb_array_elements(c.anomalies) as r
                    WHERE j.project_id = $1 AND c.anomalies IS NOT NULL
                    GROUP BY category
                    ORDER BY count DESC
                    LIMIT 10
                """, project_id)

                content = "# Anomalías Encontradas\n\n## Distribución por Categoría\n\n"
                for cat in categories:
                    content += f"- **{cat['category']}**: {cat['count']} anomalías\n"

                content += "\n**Este contenido se actualiza automáticamente con cada anomalía nueva detectada.**"
                return content

            return f"# {lesson_title}\n\nContenido dinámico generado para el proyecto {project_id}."

        except Exception as e:
            logger.error(f"Error generating dynamic content: {e}")
            return f"# {lesson_title}\n\nNo se pudo cargar el contenido dinámico."


# Singleton instance
course_service = CourseService()
