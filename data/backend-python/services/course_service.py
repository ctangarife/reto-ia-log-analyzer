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
    LessonProgressUpdate, ExerciseValidationRequest, ExerciseValidationResponse,
    FinalExamSubmissionRequest, FinalExamValidationResponse,
    FinalExamAnswerResult
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
        """Get dynamic exercises using project anomalies from MongoDB"""
        logger.info(f"get_project_exercises: user_id={user_id}, project_id={project_id}, lesson_id={lesson_id}, count={count}")
        try:
            # Get exercise configuration for this lesson
            async with db_manager.postgres_pool.acquire() as conn:
                lesson = await conn.fetchrow(
                    "SELECT exercise_data FROM learning.course_lessons WHERE id = $1",
                    lesson_id
                )

                logger.info(f"Lesson query result: lesson_found={lesson is not None}, exercise_data={lesson['exercise_data'] if lesson else 'N/A'}")

                if not lesson or not lesson["exercise_data"]:
                    logger.warning("No lesson or exercise_data found, returning []")
                    return []

                # Parse exercise_data if it's a string (JSONB from PostgreSQL)
                exercise_data = lesson["exercise_data"]
                if isinstance(exercise_data, str):
                    exercise_data = json.loads(exercise_data)

                exercise_type = exercise_data.get("type")
                logger.info(f"Exercise type: {exercise_type}")

            # Get job IDs from PostgreSQL first
            async with db_manager.postgres_pool.acquire() as conn:
                job_ids = await conn.fetch(
                    """SELECT id FROM processing.processing_jobs
                       WHERE status = 'completed'
                       AND (project_id = $1 OR project_id IS NULL)
                       ORDER BY completed_at DESC
                       LIMIT 100""",
                    project_id
                )

                if not job_ids:
                    return []

                file_ids = [str(job["id"]) for job in job_ids]

            # Now query MongoDB directly using AsyncIOMotorClient
            exercises = []

            if exercise_type == "project_anomalies":
                # Get chunks from MongoDB for these file_ids
                chunks = await db_manager.mongodb_db["chunks"].find({
                    "file_id": {"$in": file_ids}
                }).to_list(length=100)

                chunk_ids = [str(c.get("_id", "")) for c in chunks]

                # Get results from MongoDB
                cursor = db_manager.mongodb_db["results"].find({
                    "chunk_id": {"$in": chunk_ids}
                })

                async for result in cursor:
                    anomalies_list = result.get("anomalies", [])
                    for anomaly in anomalies_list:
                        if anomaly.get("is_anomaly") == True:
                            exercises.append({
                                "anomaly_id": str(result.get("_id", "")) + "-" + str(anomaly.get("chunk_id", "")),
                                "log_entry": anomaly.get("log_entry", ""),
                                "score": anomaly.get("score", 0),
                                "explanation": anomaly.get("explanation", "")
                            })
                            if len(exercises) >= count:
                                break
                    if len(exercises) >= count:
                        break

            elif exercise_type == "final_exam":
                # Get diverse anomalies for final exam from MongoDB
                cursor = db_manager.mongodb_db["results"].find({
                    "chunk_id": {"$in": await self._get_chunk_ids_for_project(file_ids)}
                })

                async for result in cursor:
                    anomalies_list = result.get("anomalies", [])
                    for anomaly in anomalies_list:
                        if anomaly.get("is_anomaly") == True:
                            exercises.append({
                                "anomaly_id": str(result.get("_id", "")) + "-" + str(anomaly.get("chunk_id", "")),
                                "log_entry": anomaly.get("log_entry", ""),
                                "score": anomaly.get("score", 0),
                                "explanation": anomaly.get("explanation", "")
                            })
                            if len(exercises) >= count:
                                break
                    if len(exercises) >= count:
                        break

            # Randomize and limit
            import random
            random.shuffle(exercises)
            return exercises[:count]

        except Exception as e:
            logger.error(f"Error getting project exercises: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def _get_chunk_ids_for_project(self, file_ids: list) -> list:
        """Helper to get chunk_ids for given file_ids"""
        chunks = await db_manager.mongodb_db["chunks"].find({
            "file_id": {"$in": file_ids}
        }).to_list(length=500)
        return [str(c.get("_id", "")) for c in chunks]

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

                # Parse exercise_data if it's a string (JSONB from PostgreSQL)
                exercise_data = lesson["exercise_data"]
                if isinstance(exercise_data, str):
                    exercise_data = json.loads(exercise_data)

                exercise_type = exercise_data.get("type")

                if exercise_type == "quiz" or exercise_type == "analysis":
                    # Validate static quiz questions
                    return await self._validate_static_exercise(conn, user_id, project_id, data, exercise_data)

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
        # Count total and completed lessons using the new course structure
        stats = await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM learning.course_lessons l
                 JOIN learning.course_modules m ON m.id = l.module_id
                 JOIN learning.courses c ON c.id = m.course_id
                 WHERE c.project_id = $1 AND c.status = 'published') as total_lessons,
                (SELECT COUNT(*) FROM learning.lesson_progress lp
                 JOIN learning.course_lessons l ON l.id = lp.lesson_id
                 JOIN learning.course_modules m ON m.id = l.module_id
                 JOIN learning.courses c ON c.id = m.course_id
                 WHERE c.project_id = $1 AND c.status = 'published' AND lp.user_id = $2) as completed_lessons
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

    async def validate_final_exam(
        self,
        user_id: UUID,
        project_id: UUID,
        data: FinalExamSubmissionRequest
    ) -> FinalExamValidationResponse:
        """Validate final exam submission with scoring

        Each anomaly answer is scored as follows:
        - Correct type: 10 points
        - Correct severity: 10 points
        - Total per anomaly: 20 points
        - 5 anomalies = 100 points maximum

        Passing score: 70%
        """
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get lesson and exercise_data
                lesson = await conn.fetchrow("""
                    SELECT l.id, l.title, l.exercise_data, l.module_id,
                           m.course_id, m.project_id
                    FROM learning.course_lessons l
                    JOIN learning.course_modules m ON m.id = l.module_id
                    WHERE l.id = $1
                """, data.lesson_id)

                if not lesson:
                    raise ValueError("Lección no encontrada")

                # Parse exercise_data if it's a string (JSONB from PostgreSQL)
                exercise_data = lesson["exercise_data"]
                if isinstance(exercise_data, str):
                    exercise_data = json.loads(exercise_data)

                if not exercise_data or exercise_data.get("type") != "final_exam":
                    raise ValueError("Esta lección no es un examen final")

                passing_score = exercise_data.get("passing_score", 70)

                # Get the anomalies for this exam from exercise_data
                exam_anomaly_ids = [a["id"] for a in exercise_data.get("anomalies", [])]

                # Build a map of user answers by anomaly_id
                user_answers_map = {ans.anomaly_id: ans for ans in data.answers}

                # Get actual anomalies from MongoDB to validate against
                from config.database import db_manager as db_mgr

                results = []
                total_points = 0
                max_points = len(exam_anomaly_ids) * 20  # 20 points per anomaly

                for idx, anomaly_id in enumerate(exam_anomaly_ids):
                    # The frontend sends anomaly_id in format "result_id-chunk_id"
                    # We need to find the user answer by matching the chunk_id part (second part after "-")
                    user_answer = None
                    for user_anomaly_id, user_ans in user_answers_map.items():
                        # Extract chunk_id from the compound ID (second part after "-")
                        user_chunk_id = user_anomaly_id.split("-")[1] if "-" in user_anomaly_id else user_anomaly_id
                        if user_chunk_id == anomaly_id or user_anomaly_id == anomaly_id:
                            user_answer = user_ans
                            break

                    # Get anomaly data from MongoDB
                    mongo_db = db_mgr.mongodb_db
                    anomaly_data = await mongo_db.results.find_one(
                        {"chunk_id": anomaly_id},
                        {"anomalies": 1}
                    )

                    # Extract first anomaly from chunk
                    if anomaly_data and anomaly_data.get("anomalies"):
                        anomaly_info = anomaly_data["anomalies"][0]
                        log_entry = anomaly_info.get("log_entry", "N/A")
                        score = anomaly_info.get("score", 0)
                        explanation = anomaly_info.get("explanation", "")

                        # Infer correct type and severity from log entry and score
                        correct_type = self._infer_anomaly_type_from_log(log_entry)
                        correct_severity = self._infer_severity_from_score(score)

                        # Score user's answer
                        points = 0
                        is_correct_type = False
                        is_correct_severity = False

                        if user_answer:
                            # Check type (10 points)
                            if user_answer.anomaly_type.lower() == correct_type.lower():
                                points += 10
                                is_correct_type = True

                            # Check severity (10 points)
                            if user_answer.severity.lower() == correct_severity.lower():
                                points += 10
                                is_correct_severity = True

                        total_points += points

                        results.append(FinalExamAnswerResult(
                            anomaly_id=anomaly_id,
                            log_entry=log_entry[:200] + "..." if len(log_entry) > 200 else log_entry,
                            user_type=user_answer.anomaly_type if user_answer else "Sin respuesta",
                            correct_type=correct_type,
                            user_severity=user_answer.severity if user_answer else "Sin respuesta",
                            correct_severity=correct_severity,
                            is_correct_type=is_correct_type,
                            is_correct_severity=is_correct_severity,
                            points=points
                        ))

                # Calculate final score (0-100)
                final_score = int((total_points / max_points) * 100) if max_points > 0 else 0
                passed = final_score >= passing_score

                # Generate feedback
                if passed:
                    feedback = f"¡Felicitaciones! Has aprobado el examen final con un score de {final_score}%. "
                    feedback += "Has demostrado un buen entendimiento de la detección de anomalías."
                else:
                    feedback = f"Tu score es {final_score}%, necesitas al menos {passing_score}% para aprobar. "
                    feedback += "Revisa los módulos anteriores y vuelve a intentarlo."

                # Check if user can retake (no previous passing attempts)
                previous_passing = await conn.fetchval("""
                    SELECT COUNT(*) FROM learning.exercise_attempts
                    WHERE user_id = $1 AND project_id = $2 AND lesson_id = $3 AND is_correct = TRUE
                """, user_id, project_id, data.lesson_id)

                can_retake = previous_passing == 0

                # Record attempt
                await conn.execute("""
                    INSERT INTO learning.exercise_attempts (user_id, project_id, lesson_id, user_answer, is_correct)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, project_id, data.lesson_id,
                    json.dumps({"answers": [a.model_dump() for a in data.answers], "score": final_score}),
                    passed)

                # If passed, mark lesson as complete
                if passed:
                    await conn.execute("""
                        INSERT INTO learning.lesson_progress (user_id, lesson_id, project_id, completed_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (user_id, lesson_id) DO UPDATE
                        SET completed_at = $4, score = $5
                    """, user_id, data.lesson_id, project_id, datetime.utcnow(), final_score)

                    # Check if course is complete
                    await self._check_course_completion(conn, user_id, project_id)

                return FinalExamValidationResponse(
                    passed=passed,
                    score=final_score,
                    passing_score=passing_score,
                    feedback=feedback,
                    results=results,
                    can_retake=can_retake,
                    certificate_earned=passed
                )

        except Exception as e:
            logger.error(f"Error validating final exam: {e}")
            raise

    def _infer_anomaly_type_from_log(self, log_entry: str) -> str:
        """Infer anomaly type from log entry content"""
        log_lower = log_entry.lower()

        # Security keywords
        security_keywords = ["login", "auth", "attack", "malware", "injection", "xss", "csrf", "unauthorized", "forbidden"]
        if any(kw in log_lower for kw in security_keywords):
            return "Seguridad"

        # Performance keywords
        perf_keywords = ["slow", "latency", "timeout", "response time", "delay", "performance"]
        if any(kw in log_lower for kw in perf_keywords):
            return "Performance"

        # Network keywords
        net_keywords = ["network", "connection", "tcp", "udp", "packet", "dns", "socket"]
        if any(kw in log_lower for kw in net_keywords):
            return "Red"

        # Behavior keywords
        beh_keywords = ["error", "exception", "crash", "failure", "bug"]
        if any(kw in log_lower for kw in beh_keywords):
            return "Comportamiento"

        return "General"

    def _infer_severity_from_score(self, score: float) -> str:
        """Infer severity from anomaly score

        Isolation Forest scores: negative values indicate anomalies
        More negative = more anomalous = higher severity
        """
        if score <= -0.6:
            return "Critical"
        elif score <= -0.3:
            return "High"
        elif score <= -0.1:
            return "Medium"
        else:
            return "Low"


# Singleton instance
course_service = CourseService()
