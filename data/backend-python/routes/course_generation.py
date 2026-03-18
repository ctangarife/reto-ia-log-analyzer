"""
Course Generation Routes
API endpoints for dynamic course generation and workflow
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID

from middleware.auth_middleware import get_current_user, CurrentUser
from services.course_generation_service import course_generation_service
from models.learning_models import (
    CourseGenerateRequest, CourseGenerateResponse,
    CoursePreviewResponse, ProjectAnalysis,
    CourseUpdateRequest, CourseUpdateResponse,
    SubmitForReviewRequest, ReviewActionRequest, ReviewActionResponse,
    PendingCoursesResponse, CourseRegenerateRequest, CourseRegenerateResponse,
    LessonRefreshRequest, LessonRefreshResponse
)
from services.course_rbac_service import course_rbac_service
from config.database import db_manager

router = APIRouter(prefix="/course-generation", tags=["course-generation"])


async def _check_course_permission(
    user_id: UUID,
    project_id: UUID,
    permission: str
) -> bool:
    """Helper to check course permission for a project"""
    # Get workspace_id from project
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
        # Check permission using course RBAC
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "learning:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        return await course_generation_service.can_generate_course(project_id)
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
        # Check permission using course RBAC
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "learning:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        # Get workspace_id
        async with db_manager.postgres_pool.acquire() as conn:
            workspace_id = await conn.fetchval(
                "SELECT workspace_id FROM auth.projects WHERE id = $1",
                project_id
            )

        analysis = await course_generation_service.preview_course_data(project_id)

        return CoursePreviewResponse(
            analysis=analysis,
            suggested_modules=[
                "Módulo 1: Contexto del Proyecto (dinámico)",
                "Módulo 2: Tipos de Anomalías detectadas",
                "Módulo 3: Análisis Práctico con anomalías reales",
                "Módulo 4: Evaluación Final"
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
        # Check permission using course RBAC
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "learning:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        # Get workspace_id
        async with db_manager.postgres_pool.acquire() as conn:
            workspace_id = await conn.fetchval(
                "SELECT workspace_id FROM auth.projects WHERE id = $1",
                project_id
            )

            # Verify workspace scope permission
            if data.scope == "workspace":
                has_ws_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "learning:create"
                )
                if not has_ws_perm and not current_user.is_super_admin:
                    raise HTTPException(status_code=403, detail="No permission to create workspace courses")

        result = await course_generation_service.generate_course(
            project_id, workspace_id, current_user.user_id, data.scope, data.name
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/regenerate", response_model=CourseRegenerateResponse)
async def regenerate_course(
    project_id: UUID,
    data: CourseRegenerateRequest,
    current_user = Depends(get_current_user)
):
    """Regenerate course with new project data (creates new version)"""
    try:
        # Check permission using course RBAC
        has_perm = await _check_course_permission(
            current_user.user_id, project_id, "learning:create"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to create courses")

        # Get workspace_id
        async with db_manager.postgres_pool.acquire() as conn:
            workspace_id = await conn.fetchval(
                "SELECT workspace_id FROM auth.projects WHERE id = $1",
                project_id
            )

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
    """Update a course"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check permission using course RBAC
            workspace_id = course["workspace_id"]

            if course["created_by"] == current_user.user_id:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "learning:edit_own"
                )
            else:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "learning:edit"
                )

            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to edit this course")

            # Build update query
            updates = []
            values = []
            param_count = 1

            if data.title is not None:
                updates.append(f"title = ${param_count}")
                values.append(data.title)
                param_count += 1

            if data.description is not None:
                updates.append(f"description = ${param_count}")
                values.append(data.description)
                param_count += 1

            if data.status is not None:
                updates.append(f"status = ${param_count}")
                values.append(data.status)
                param_count += 1

            if data.change_description is not None:
                updates.append(f"change_description = ${param_count}")
                values.append(data.change_description)
                param_count += 1

            if updates:
                values.append(course_id)
                await conn.execute(
                    f"UPDATE learning.course_modules SET {', '.join(updates)} WHERE id = ${param_count}",
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
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check permission using course RBAC (creator or editor can submit)
            workspace_id = course["workspace_id"]
            if course["created_by"] != current_user.user_id:
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "learning:edit_own"
                )
                if not has_perm and not current_user.is_super_admin:
                    raise HTTPException(status_code=403, detail="No permission to submit this course")

            # Update status to pending
            await conn.execute(
                """UPDATE learning.course_modules
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
                   JOIN auth.user_roles ur ON ur.user_id = u.id
                   JOIN auth.roles r ON r.id = ur.role_id
                   JOIN auth.role_permissions rp ON rp.role_id = r.id
                   JOIN auth.permissions p ON p.id = rp.permission_id
                   WHERE p.permission_name = 'learning:review'
                   AND u.workspace_id = $1""",
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
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/courses/pending", response_model=PendingCoursesResponse)
async def get_pending_courses(
    workspace_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get pending courses for review"""
    try:
        # Check review permission using course RBAC
        has_perm = await course_rbac_service.check_course_permission(
            current_user.user_id, workspace_id, "learning:review"
        )
        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="No permission to review courses")

        async with db_manager.postgres_pool.acquire() as conn:
            # Reviewers only see courses that are in 'pending' status
            # (courses that have been submitted for review)
            courses = await conn.fetch("""
                SELECT
                    cm.id, cm.title, cm.description, cm.status,
                    cm.created_at, cm.created_by,
                    u.email as creator_email,
                    p.name as project_name
                FROM learning.course_modules cm
                LEFT JOIN auth.users u ON u.id = cm.created_by
                LEFT JOIN auth.projects p ON p.id = cm.project_id
                WHERE cm.status = 'pending'
                AND cm.workspace_id = $1
                ORDER BY cm.created_at DESC
            """, workspace_id)

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
    current_user = Depends(get_current_user)
):
    """Get draft courses for the current user (creator view)"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Show ONLY parent courses (no parent_id) created by the current user
            # Include module/lesson counts
            courses = await conn.fetch("""
                SELECT
                    cm.id, cm.title, cm.description, cm.status,
                    cm.created_at, cm.created_by,
                    u.email as creator_email,
                    p.name as project_name,
                    COUNT(DISTINCT child_modules.id) as module_count,
                    COUNT(DISTINCT child_lessons.id) as lesson_count
                FROM learning.course_modules cm
                LEFT JOIN auth.users u ON u.id = cm.created_by
                LEFT JOIN auth.projects p ON p.id = cm.project_id
                LEFT JOIN learning.course_modules child_modules ON child_modules.parent_id = cm.id
                LEFT JOIN learning.course_lessons child_lessons ON child_lessons.module_id = child_modules.id
                WHERE cm.status = 'draft'
                AND cm.workspace_id = $1
                AND cm.created_by = $2
                AND cm.parent_id IS NULL
                GROUP BY cm.id, cm.title, cm.description, cm.status, cm.created_at, cm.created_by, u.email, p.name
                ORDER BY cm.created_at DESC
            """, workspace_id, current_user.user_id)

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
    """Get course content with modules and lessons (for previewing draft courses)"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course info (parent course)
            course = await conn.fetchrow(
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Get child modules
            child_modules = await conn.fetch("""
                SELECT id, module_order, title, description, status
                FROM learning.course_modules
                WHERE parent_id = $1
                ORDER BY module_order
            """, course_id)

            # Get all lessons for all child modules - simpler approach without dynamic IN clause
            lessons = []
            for module in child_modules:
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
                    "title": course["title"],
                    "description": course["description"],
                    "status": course["status"],
                    "scope": course["scope"],
                    "module_order": course["module_order"],
                    "created_at": str(course["created_at"]),
                    "project_id": str(course["project_id"]) if course["project_id"] else None,
                    "workspace_id": str(course["workspace_id"]) if course["workspace_id"] else None
                },
                "modules": [{
                    "id": str(m["id"]),
                    "module_order": m["module_order"],
                    "title": m["title"],
                    "description": m["description"],
                    "status": m["status"]
                } for m in child_modules],
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
    """Approve a course"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check review permission using course RBAC
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "learning:review"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to review courses")

            # Update status
            await conn.execute(
                """UPDATE learning.course_modules
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

        return ReviewActionResponse(
            course_id=course_id,
            status="approved",
            message="Curso aprobado. Listo para publicar."
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
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check review permission using course RBAC
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "learning:review"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to review courses")

            # Update status back to draft
            await conn.execute(
                """UPDATE learning.course_modules
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
    current_user = Depends(get_current_user)
):
    """Publish a course"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get course
            course = await conn.fetchrow(
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check if approved or user has publish permission using course RBAC
            can_publish = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "learning:publish"
            )

            if course["status"] != "approved" and not can_publish and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Course must be approved first or you need publish permission"
                )

            # Update status
            await conn.execute(
                """UPDATE learning.course_modules
                   SET status = 'published',
                       published_at = CURRENT_TIMESTAMP
                   WHERE id = $1""",
                course_id
            )

            # Notify users in workspace
            # (would be implemented with notification service)

        return ReviewActionResponse(
            course_id=course_id,
            status="published",
            message="Curso publicado. Ahora visible para los usuarios."
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
                "SELECT * FROM learning.course_modules WHERE id = $1",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Course not found")

            # Check permission using course RBAC
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, course["workspace_id"], "learning:delete"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to archive courses")

            # Update status
            await conn.execute(
                """UPDATE learning.course_modules
                   SET status = 'archived',
                       archived_at = CURRENT_TIMESTAMP
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


@router.post("/lessons/{lesson_id}/refresh", response_model=LessonRefreshResponse)
async def refresh_lesson(
    lesson_id: UUID,
    data: LessonRefreshRequest,
    current_user = Depends(get_current_user)
):
    """Refresh lesson content with new anomalies"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get lesson and project
            lesson = await conn.fetchrow(
                """SELECT l.id, l.module_id, cm.project_id, cm.workspace_id
                   FROM learning.course_lessons l
                   JOIN learning.course_modules cm ON cm.id = l.module_id
                   WHERE l.id = $1""",
                lesson_id
            )

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

            # Check permission using course RBAC
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, lesson["workspace_id"], "learning:edit"
            )
            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(status_code=403, detail="No permission to edit lessons")

        result = await course_generation_service.refresh_lesson(
            lesson_id, lesson["project_id"], data.preserve_selection
        )

        return LessonRefreshResponse(
            lesson_id=lesson_id,
            message=result["message"],
            anomalies_updated=0  # Would be calculated from actual refresh
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
                """SELECT cm.id, cm.status, cm.workspace_id, cm.project_id, cm.created_by
                   FROM learning.course_modules cm
                   WHERE cm.id = $1""",
                course_id
            )

            if not course:
                raise HTTPException(status_code=404, detail="Curso no encontrado")

            # Only allow deleting draft/pending courses (not published)
            if course["status"] == "published":
                raise HTTPException(
                    status_code=400,
                    detail="No se puede eliminar un curso publicado. Primero debe archivarse."
                )

            # Check permission (creator or super admin)
            is_creator = str(course["created_by"]) == str(current_user.user_id)
            if not is_creator and not current_user.is_super_admin:
                # Also check workspace admin permission
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, course["workspace_id"], "learning:delete"
                )
                if not has_perm:
                    raise HTTPException(status_code=403, detail="No tienes permiso para eliminar este curso")

            # Delete course (CASCADE will delete lessons)
            await conn.execute(
                "DELETE FROM learning.course_modules WHERE id = $1",
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
