"""
Course Generation Routes v2
API endpoints for dynamic course generation and workflow

New structure:
- courses table: Main course entity
- course_modules: Children of courses (4 fixed modules)
- course_lessons: Children of modules
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import Optional

from middleware.auth_middleware import get_current_user, get_current_user_optional, CurrentUser
from services.course_generation_service import course_generation_service
from models.learning_models import (
    CourseGenerateRequest, CourseGenerateResponse,
    CoursePreviewResponse, ProjectAnalysis,
    CourseUpdateRequest, CourseUpdateResponse,
    SubmitForReviewRequest, ReviewActionRequest, ReviewActionResponse,
    PendingCoursesResponse, CourseRegenerateRequest, CourseRegenerateResponse,
    CourseResponse, CourseListItem, CourseLimitsCheck
)
from services.course_rbac_service import course_rbac_service
from config.database import db_manager
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/course-generation", tags=["course-generation"])


async def _check_course_permission(
    user_id: UUID,
    project_id: UUID,
    permission: str
) -> bool:
    """Helper to check course permission for a project"""
    async with db_manager.postgres_pool.acquire() as conn:
        workspace_id = await conn.fetchval(
            "SELECT workspace_id FROM auth.projects WHERE id = $1",
            project_id
        )

    if not workspace_id:
        return False

    return await course_rbac_service.check_course_permission(
        user_id, workspace_id, permission
    )


async def _get_workspace_from_project(project_id: UUID) -> Optional[UUID]:
    """Get workspace_id from a project"""
    async with db_manager.postgres_pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT workspace_id FROM auth.projects WHERE id = $1",
            project_id
        )


# ============================================
# Course Generation Endpoints
# ============================================

@router.get("/projects/{project_id}/can-generate")
async def check_can_generate(
    project_id: UUID,
    current_user = Depends(get_current_user)
):
    """Check if a course can be generated for the project"""
    try:
        # Check permission
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "courses:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        return await course_generation_service.can_generate_course(project_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/limits")
async def get_course_limits(
    project_id: UUID,
    target_status: str = "draft",
    current_user = Depends(get_current_user)
):
    """Get current course counts and limits for a project"""
    try:
        # Check permission
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "courses:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        return await course_generation_service.check_course_limits(project_id, target_status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/preview", response_model=CoursePreviewResponse)
async def preview_course(
    project_id: UUID,
    current_user = Depends(get_current_user)
):
    """Preview project data before generating course"""
    try:
        # Check permission
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "courses:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        analysis = await course_generation_service.preview_course_data(project_id)

        return CoursePreviewResponse(
            analysis=analysis,
            suggested_modules=[
                "Módulo 1: Introducción a los Logs (2 lecciones sobre logs en general)",
                "Módulo 2: Tipos de Anomalías Detectadas (teoría + ejemplos por categoría)",
                "Módulo 3: Análisis Práctico (casos reales con anomalías del proyecto)",
                "Módulo 4: Evaluación Final (examen práctico)"
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/generate", response_model=CourseGenerateResponse)
async def generate_course(
    project_id: UUID,
    data: CourseGenerateRequest,
    current_user = Depends(get_current_user)
):
    """Generate a new course for the project"""
    try:
        # Check permission
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "courses:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        # Get workspace_id
        workspace_id = await _get_workspace_from_project(project_id)
        if not workspace_id:
            raise HTTPException(status_code=404, detail="Project not found")

        # Verify workspace scope permission
        if data.scope == "workspace":
            has_ws_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, workspace_id, "courses:create"
            )
            if not has_ws_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to create workspace courses")

        result = await course_generation_service.generate_course(
            project_id, workspace_id, current_user.user_id, data.scope, data.name
        )

        logger.info(f"Course generation result: course_id={result.course_id}, status={result.status}, "
                   f"modules_created={result.modules_created}, lessons_created={result.lessons_created}, "
                   f"message={result.message}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error in generate_course: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/regenerate", response_model=CourseRegenerateResponse)
async def regenerate_course(
    project_id: UUID,
    data: CourseRegenerateRequest,
    current_user = Depends(get_current_user)
):
    """Regenerate course with new project data (creates new version)"""
    try:
        # Check permission
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "courses:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        # Get workspace_id
        workspace_id = await _get_workspace_from_project(project_id)
        if not workspace_id:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await course_generation_service.regenerate_course(
            project_id, workspace_id, current_user.user_id, data.change_description
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Course Management Endpoints
# ============================================

@router.put("/courses/{course_id}", response_model=CourseUpdateResponse)
async def update_course(
    course_id: UUID,
    data: CourseUpdateRequest,
    current_user = Depends(get_current_user)
):
    """Update a course (name, description)"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check permission
            workspace_id = course["workspace_id"]

            if course["created_by"] == current_user.user_id:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "courses:edit_own"
                )
            else:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "courses:edit"
                )

            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to edit this course")

            # Build update query
            updates = []
            values = []
            param_count = 1

            if data.name is not None:
                updates.append(f"name = ${param_count}")
                values.append(data.name)
                param_count += 1

            if data.description is not None:
                updates.append(f"description = ${param_count}")
                values.append(data.description)
                param_count += 1

            if data.change_description is not None:
                updates.append(f"change_description = ${param_count}")
                values.append(data.change_description)
                param_count += 1

            if updates:
                values.append(course_id)
                await conn.execute(
                    f"UPDATE learning.courses SET {', '.join(updates)} WHERE id = ${param_count}",
                    *values
                )

        return CourseUpdateResponse(
            course_id=course_id,
            status="updated",
            message="Curso actualizado exitosamente"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/submit-for-review", response_model=CourseUpdateResponse)
async def submit_for_review(
    course_id: UUID,
    data: SubmitForReviewRequest,
    current_user = Depends(get_current_user)
):
    """Submit course for review"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check if already pending
            if course["status"] == "pending":
                return CourseUpdateResponse(
                    course_id=course_id,
                    status="pending",
                    message="El curso ya está en revisión"
                )

            # Check permission (creator or editor can submit)
            workspace_id = course["workspace_id"]
            if course["created_by"] != current_user.user_id:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "courses:edit_own"
                )
                if not has_perm and not current_user.is_super_admin:
                    raise HTTPException(status_code=403, detail="No permission to submit this course")

            # Check limits for pending courses (only for project-scoped courses)
            if course["project_id"]:
                limits = await course_generation_service.check_course_limits(
                    course["project_id"], "pending"
                )
                if not limits.can_create:
                    raise HTTPException(
                        status_code=409,
                        detail=f"No se puede enviar para revisión: {limits.reason}"
                    )

            # Update status to pending
            await conn.execute(
                """UPDATE learning.courses
                   SET status = 'pending'
                   WHERE id = $1""",
                course_id
            )

            # Create notification for reviewers
            await conn.execute(
                """INSERT INTO learning.course_notifications
                   (workspace_id, user_id, course_id, type)
                   SELECT $1, u.id, $2, 'pending_review'
                   FROM auth.users u
                   JOIN auth.user_workspace_roles uwr ON uwr.user_id = u.id AND uwr.workspace_id = $1
                   JOIN auth.role_permissions rp ON rp.role_id = uwr.role_id
                   JOIN auth.permissions p ON p.id = rp.permission_id
                   JOIN auth.modules m ON m.id = p.module_id
                   WHERE m.name = 'courses'
                   AND p.action = 'review'""",
                course["workspace_id"], course_id
            )

        return CourseUpdateResponse(
            course_id=course_id,
            status="pending",
            message="Curso enviado para revisión"
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error in submit_for_review: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/courses/pending", response_model=PendingCoursesResponse)
async def get_pending_courses(
    workspace_id: UUID,
    project_id: UUID | None = None,
    current_user = Depends(get_current_user)
):
    """Get pending courses for review.
    Can optionally filter by project_id to show only courses for a specific project.
    """
    try:
        # Check review permission
        has_perm = await course_rbac_service.check_course_permission(
            current_user.user_id, workspace_id, "courses:review"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to review courses")

        # Build query with optional project filter
        if project_id:
            where_clause = "WHERE c.status = 'pending' AND c.workspace_id = $1 AND c.project_id = $2"
            params = [workspace_id, project_id]
        else:
            where_clause = "WHERE c.status = 'pending' AND c.workspace_id = $1"
            params = [workspace_id]

        async with db_manager.postgres_pool.acquire() as conn:
            courses = await conn.fetch(f"""
                SELECT
                    c.id, c.name, c.description, c.status,
                    c.created_at, c.created_by, c.version_number,
                    u.email as creator_email,
                    c.project_id,
                    p.name as project_name,
                    COUNT(DISTINCT m.id) as module_count,
                    COUNT(DISTINCT l.id) as lesson_count
                FROM learning.courses c
                LEFT JOIN auth.users u ON u.id = c.created_by
                LEFT JOIN auth.projects p ON p.id = c.project_id
                LEFT JOIN learning.course_modules m ON m.course_id = c.id
                LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                {where_clause}
                GROUP BY c.id, c.name, c.description, c.status, c.created_at, c.created_by, c.version_number, u.email, c.project_id, p.name
                ORDER BY c.created_at DESC
            """, *params)

            return PendingCoursesResponse(
                workspace_id=workspace_id,
                courses=[dict(row) for row in courses]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/courses/draft", response_model=PendingCoursesResponse)
async def get_draft_courses(
    workspace_id: UUID,
    project_id: UUID | None = None,
    current_user = Depends(get_current_user)
):
    """Get draft courses for the current user.
    Can optionally filter by project_id to show only courses for a specific project.
    """
    try:
        # Build query with optional project filter
        if project_id:
            where_clause = "WHERE c.status = 'draft' AND c.workspace_id = $1 AND c.project_id = $2 AND c.created_by = $3"
            params = [workspace_id, project_id, current_user.user_id]
        else:
            where_clause = "WHERE c.status = 'draft' AND c.workspace_id = $1 AND c.created_by = $2"
            params = [workspace_id, current_user.user_id]

        async with db_manager.postgres_pool.acquire() as conn:
            # Show courses created by the current user with module/lesson counts
            courses = await conn.fetch(f"""
                SELECT
                    c.id, c.name, c.description, c.status,
                    c.created_at, c.created_by,
                    u.email as creator_email,
                    c.project_id,
                    p.name as project_name,
                    COUNT(DISTINCT m.id) as module_count,
                    COUNT(DISTINCT l.id) as lesson_count
                FROM learning.courses c
                LEFT JOIN auth.users u ON u.id = c.created_by
                LEFT JOIN auth.projects p ON p.id = c.project_id
                LEFT JOIN learning.course_modules m ON m.course_id = c.id
                LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                {where_clause}
                GROUP BY c.id, c.name, c.description, c.status, c.created_at, c.created_by, u.email, c.project_id, p.name
                ORDER BY c.created_at DESC
            """, *params)

            return PendingCoursesResponse(
                workspace_id=workspace_id,
                courses=[dict(row) for row in courses]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/content")
async def get_course_content(
    course_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get course content with modules and lessons"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course info
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Get modules
            modules = await conn.fetch("""
                SELECT id, module_order, title, description
                FROM learning.course_modules
                WHERE course_id = $1
                ORDER BY module_order
            """, course_id)

            # Get all lessons
            lessons = []
            for module in modules:
                module_lessons = await conn.fetch("""
                    SELECT
                        l.id, l.module_id, l.lesson_order, l.title, l.content,
                        l.exercise_data, l.is_dynamic,
                        m.module_order, m.title as module_title
                    FROM learning.course_lessons l
                    JOIN learning.course_modules m ON m.id = l.module_id
                    WHERE l.module_id = $1
                    ORDER BY l.lesson_order
                """, module["id"])
                lessons.extend(module_lessons)

            return {
                "course": {
                    "id": str(course["id"]),
                    "name": course["name"],
                    "description": course["description"],
                    "status": course["status"],
                    "scope": course["scope"],
                    "version_number": course["version_number"],
                    "created_at": str(course["created_at"]),
                    "project_id": str(course["project_id"]),
                    "workspace_id": str(course["workspace_id"])
                },
                "modules": [{
                    "id": str(m["id"]),
                    "module_order": m["module_order"],
                    "title": m["title"],
                    "description": m["description"]
                } for m in modules],
                "lessons": [{
                    "id": str(l["id"]),
                    "module_id": str(l["module_id"]),
                    "lesson_order": l["lesson_order"],
                    "title": l["title"],
                    "content": l["content"],
                    "exercise_data": l["exercise_data"],
                    "is_dynamic": l["is_dynamic"],
                    "module_title": l["module_title"],
                    "module_order": l["module_order"]
                } for l in lessons]
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/approve", response_model=ReviewActionResponse)
async def approve_course(
    course_id: UUID,
    data: ReviewActionRequest,
    current_user = Depends(get_current_user)
):
    """Approve a course (does NOT publish yet)"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check review permission
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "courses:review"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to review courses")

            # Update status to approved (do NOT archive - that happens on publish)
            await conn.execute(
                """UPDATE learning.courses
                   SET status = 'approved',
                       reviewed_by = $1,
                       reviewed_at = CURRENT_TIMESTAMP
                   WHERE id = $2""",
                current_user.user_id, course_id
            )

            # Create review record
            await conn.execute(
                """INSERT INTO learning.course_reviews
                   (course_id, reviewer_id, status, comments, version_number)
                   VALUES ($1, $2, 'approved', $3, $4)""",
                course_id, current_user.user_id, data.comments, course["version_number"]
            )

        message = "Curso aprobado. Listo para publicar."

        return ReviewActionResponse(
            course_id=course_id,
            status="approved",
            message=message
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/reject", response_model=ReviewActionResponse)
async def reject_course(
    course_id: UUID,
    data: ReviewActionRequest,
    current_user = Depends(get_current_user)
):
    """Reject a course"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check review permission
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "courses:review"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to review courses")

            # Update status back to draft
            await conn.execute(
                """UPDATE learning.courses
                   SET status = 'draft',
                       reviewed_by = $1,
                       reviewed_at = CURRENT_TIMESTAMP,
                       rejection_reason = $2
                   WHERE id = $3""",
                current_user.user_id, data.comments, course_id
            )

            # Create review record
            await conn.execute(
                """INSERT INTO learning.course_reviews
                   (course_id, reviewer_id, status, comments, version_number)
                   VALUES ($1, $2, 'rejected', $3, $4)""",
                course_id, current_user.user_id, data.comments, course["version_number"]
            )

        return ReviewActionResponse(
            course_id=course_id,
            status="rejected",
            message="Curso rechazado. Ha vuelto a estado borrador para correcciones."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/publish", response_model=ReviewActionResponse)
async def publish_course(
    course_id: UUID,
    data: ReviewActionRequest,
    current_user = Depends(get_current_user)
):
    """Publish a course. If another course is already published, archive it first."""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check if approved or user has publish permission
            can_publish = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "courses:publish"
            )

            if course["status"] != "approved" and not can_publish and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Course must be approved first or you need publish permission"
                )

            # Check for existing published course
            existing_published = await conn.fetchrow(
                """SELECT id, name FROM learning.courses
                   WHERE project_id = $1 AND status = 'published' AND id != $2""",
                course["project_id"], course_id
            )

            archived_course_id = None
            if existing_published:
                if not data.archive_existing and not can_publish:
                    # Ask user what to do (return special response)
                    return ReviewActionResponse(
                        course_id=course_id,
                        status="conflict",
                        message=f"Ya existe un curso publicado: '{existing_published['name']}'. "
                               f"Especifica archive_existing=true para archivarlo automáticamente."
                    )
                else:
                    # Archive existing published course
                    await conn.execute(
                        """UPDATE learning.courses
                           SET status = 'archived', archived_at = CURRENT_TIMESTAMP
                           WHERE id = $1""",
                        existing_published["id"]
                    )
                    archived_course_id = existing_published["id"]

            # Publish the new course
            await conn.execute(
                """UPDATE learning.courses
                   SET status = 'published', published_at = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                course_id
            )

        return ReviewActionResponse(
            course_id=course_id,
            status="published",
            message="Curso publicado. Ahora visible para los usuarios." +
                   (f" Curso anterior archivado." if archived_course_id else ""),
            archived_course_id=archived_course_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/archive", response_model=ReviewActionResponse)
async def archive_course(
    course_id: UUID,
    current_user = Depends(get_current_user)
):
    """Archive a course"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check permission
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "courses:delete"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to archive courses")

            # Update status
            await conn.execute(
                """UPDATE learning.courses
                   SET status = 'archived', archived_at = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                course_id
            )

        return ReviewActionResponse(
            course_id=course_id,
            status="archived",
            message="Curso archivado."
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/courses/{course_id}", response_model=dict)
async def delete_course(
    course_id: UUID,
    current_user = Depends(get_current_user)
):
    """Delete a course (only draft/pending courses can be deleted)"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course info
            course = await conn.fetchrow(
                """SELECT c.id, c.status, c.workspace_id, c.project_id, c.created_by
                   FROM learning.courses c
                   WHERE c.id = $1""",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Curso no encontrado")

            # Only allow deleting draft/pending courses
            if course["status"] == "published":
                raise HTTPException(
                    status_code=400,
                    detail="No se puede eliminar un curso publicado. Primero debe archivarse."
                )

            # Check permission (creator or super admin)
            is_creator = str(course["created_by"]) == str(current_user.user_id)
            if not is_creator and not current_user.is_super_admin:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, course["workspace_id"], "courses:delete"
                )
                if not has_perm:
                    raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este curso")

            # Delete course (CASCADE will delete modules and lessons)
            await conn.execute(
                "DELETE FROM learning.courses WHERE id = $1",
                course_id
            )

            return {
                "message": "Curso eliminado correctamente",
                "course_id": str(course_id)
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/courses/approved", response_model=PendingCoursesResponse)
async def get_approved_courses(
    workspace_id: UUID,
    project_id: UUID | None = None,
    current_user = Depends(get_current_user_optional)
):
    """Get approved courses (ready to publish) in a workspace.
    Can optionally filter by project_id to show only courses for a specific project.
    """
    try:
        # Build query with optional project filter
        if project_id:
            where_clause = "WHERE c.workspace_id = $1 AND c.project_id = $2 AND c.status = 'approved'"
            params = [workspace_id, project_id]
        else:
            where_clause = "WHERE c.workspace_id = $1 AND c.status = 'approved'"
            params = [workspace_id]

        async with db_manager.postgres_pool.acquire() as conn:
            courses = await conn.fetch(f"""
                SELECT
                    c.id,
                    c.name,
                    c.description,
                    c.status,
                    c.scope,
                    c.created_at,
                    c.reviewed_at,
                    c.reviewed_by,
                    u.email as reviewer_email,
                    c.project_id,
                    p.name as project_name,
                    COUNT(DISTINCT m.id) as module_count,
                    COUNT(DISTINCT l.id) as lesson_count
                FROM learning.courses c
                JOIN auth.projects p ON c.project_id = p.id
                LEFT JOIN auth.users u ON c.reviewed_by = u.id
                LEFT JOIN learning.course_modules m ON m.course_id = c.id
                LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                {where_clause}
                GROUP BY c.id, c.name, c.description, c.status, c.scope, c.created_at, c.reviewed_at, c.reviewed_by, u.email, c.project_id, p.name
                ORDER BY c.reviewed_at DESC
            """, *params)

            return PendingCoursesResponse(
                workspace_id=workspace_id,
                courses=[{
                    "id": str(row["id"]),
                    "name": row["name"],
                    "description": row["description"] or "",
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                    "created_by": "",  # Not needed for approved courses
                    "creator_email": "",
                    "reviewed_at": str(row["reviewed_at"]) if row["reviewed_at"] else None,
                    "reviewed_by": str(row["reviewed_by"]) if row["reviewed_by"] else None,
                    "reviewer_email": row["reviewer_email"] or "",
                    "project_id": str(row["project_id"]),
                    "project_name": row["project_name"],
                    "module_count": row["module_count"],
                    "lesson_count": row["lesson_count"]
                } for row in courses]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/courses/published", response_model=PendingCoursesResponse)
async def get_published_courses(
    workspace_id: UUID,
    current_user = Depends(get_current_user_optional)
):
    """Get published courses in a workspace"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            courses = await conn.fetch("""
                SELECT
                    c.id,
                    c.name,
                    c.description,
                    c.status,
                    c.scope,
                    c.created_at,
                    c.published_at,
                    c.project_id,
                    p.name as project_name,
                    COUNT(DISTINCT m.id) as module_count,
                    COUNT(DISTINCT l.id) as lesson_count,
                    COALESCE(SUM(CASE WHEN lp.user_id IS NOT NULL THEN 1 ELSE 0 END), 0) as completed_lessons
                FROM learning.courses c
                JOIN auth.projects p ON c.project_id = p.id
                LEFT JOIN learning.course_modules m ON m.course_id = c.id
                LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                LEFT JOIN learning.lesson_progress lp ON lp.lesson_id = l.id AND lp.user_id = $2
                WHERE c.workspace_id = $1
                AND c.status = 'published'
                GROUP BY c.id, c.name, c.description, c.status, c.scope, c.created_at, c.published_at, c.project_id, p.name
                ORDER BY c.published_at DESC
            """, workspace_id, current_user.user_id if current_user else None)

            return PendingCoursesResponse(
                workspace_id=workspace_id,
                courses=[{
                    "id": str(row["id"]),
                    "name": row["name"],
                    "description": row["description"] or "",
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                    "created_by": "",
                    "creator_email": "",
                    "reviewed_at": "",
                    "reviewed_by": "",
                    "reviewer_email": "",
                    "project_id": str(row["project_id"]),
                    "project_name": row["project_name"],
                    "module_count": row["module_count"],
                    "lesson_count": row["lesson_count"],
                    "published_at": str(row["published_at"]) if row["published_at"] else None,
                    "completed_lessons": row["completed_lessons"],
                    "scope": row["scope"]
                } for row in courses]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/archived", response_model=PendingCoursesResponse)
async def get_archived_courses(
    project_id: UUID | None = None,
    workspace_id: UUID | None = None,
    current_user = Depends(get_current_user)
):
    """Get archived courses. Can filter by project_id or workspace_id."""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Build query based on filters
            if project_id:
                # Get archived courses for a specific project
                courses = await conn.fetch("""
                    SELECT
                        c.id,
                        c.name,
                        c.description,
                        c.status,
                        c.created_at,
                        c.archived_at as reviewed_at,
                        c.created_by,
                        u.email as creator_email,
                        c.project_id,
                        p.name as project_name,
                        COUNT(DISTINCT m.id) as module_count,
                        COUNT(DISTINCT l.id) as lesson_count,
                        0 as completed_lessons
                    FROM learning.courses c
                    JOIN auth.projects p ON c.project_id = p.id
                    LEFT JOIN auth.users u ON c.created_by = u.id
                    LEFT JOIN learning.course_modules m ON m.course_id = c.id
                    LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                    WHERE c.project_id = $1
                    AND c.status = 'archived'
                    GROUP BY c.id, c.name, c.description, c.status, c.created_at, c.archived_at, c.created_by, u.email, c.project_id, p.name
                    ORDER BY c.archived_at DESC
                """, project_id)
            elif workspace_id:
                # Get archived courses for a workspace
                courses = await conn.fetch("""
                    SELECT
                        c.id,
                        c.name,
                        c.description,
                        c.status,
                        c.created_at,
                        c.archived_at as reviewed_at,
                        c.created_by,
                        u.email as creator_email,
                        c.project_id,
                        p.name as project_name,
                        COUNT(DISTINCT m.id) as module_count,
                        COUNT(DISTINCT l.id) as lesson_count,
                        0 as completed_lessons
                    FROM learning.courses c
                    JOIN auth.projects p ON c.project_id = p.id
                    LEFT JOIN auth.users u ON c.created_by = u.id
                    LEFT JOIN learning.course_modules m ON m.course_id = c.id
                    LEFT JOIN learning.course_lessons l ON l.module_id = m.id
                    WHERE c.workspace_id = $1
                    AND c.status = 'archived'
                    GROUP BY c.id, c.name, c.description, c.status, c.created_at, c.archived_at, c.created_by, u.email, c.project_id, p.name
                    ORDER BY c.archived_at DESC
                """, workspace_id)
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Must provide either project_id or workspace_id"
                )

            return PendingCoursesResponse(
                workspace_id=workspace_id or UUID("00000000-0000-0000-0000-000000000000"),
                courses=[{
                    "id": str(row["id"]),
                    "name": row["name"],
                    "description": row["description"] or "",
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                    "created_by": str(row["created_by"]) if row["created_by"] else "",
                    "creator_email": row["creator_email"] or "",
                    "reviewed_at": str(row["reviewed_at"]) if row["reviewed_at"] else "",
                    "reviewed_by": "",
                    "reviewer_email": "",
                    "project_id": str(row["project_id"]),
                    "project_name": row["project_name"],
                    "module_count": row["module_count"],
                    "lesson_count": row["lesson_count"],
                    "published_at": None,
                    "completed_lessons": row["completed_lessons"]
                } for row in courses]
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/republish", response_model=ReviewActionResponse)
async def republish_course(
    course_id: UUID,
    current_user = Depends(get_current_user)
):
    """Republish an archived course. If another course is already published, archive it first."""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.courses WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check if it's archived
            if course["status"] != "archived":
                raise HTTPException(
                    status_code=400,
                    detail="Solo se pueden republicar cursos archivados"
                )

            # Check publish permission
            can_publish = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "courses:publish"
            )
            if not can_publish and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permiso para publicar cursos"
                )

            # Check for existing published course in this project
            existing_published = await conn.fetchrow(
                """SELECT id, name FROM learning.courses
                   WHERE project_id = $1 AND status = 'published' AND id != $2""",
                course["project_id"], course_id
            )

            archived_course_id = None
            if existing_published:
                # Archive the currently published course
                await conn.execute(
                    """UPDATE learning.courses
                       SET status = 'archived', archived_at = CURRENT_TIMESTAMP
                       WHERE id = $1""",
                    existing_published["id"]
                )
                archived_course_id = existing_published["id"]

            # Republish the archived course
            await conn.execute(
                """UPDATE learning.courses
                   SET status = 'published',
                       published_at = CURRENT_TIMESTAMP,
                       archived_at = NULL
                   WHERE id = $1""",
                course_id
            )

            return ReviewActionResponse(
                course_id=course_id,
                status="published",
                message=f"Curso '{course['name']}' republicado exitosamente.{f' Curso anterior archivado.' if archived_course_id else ''}",
                archived_course_id=archived_course_id
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
