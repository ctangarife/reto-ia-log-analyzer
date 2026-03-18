"""
Lesson Edit Routes
API endpoints for granular lesson editing with change tracking
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from uuid import UUID
from typing import Optional

from middleware.auth_middleware import get_current_user, CurrentUser
from services.lesson_edit_service import lesson_edit_service
from services.course_rbac_service import course_rbac_service
from models.learning_models import (
    LessonUpdateRequest, LessonUpdateResponse,
    ExerciseUpdateRequest, ExerciseUpdateResponse,
    LessonHistoryResponse
)
from config.database import db_manager

router = APIRouter(prefix="/lessons", tags=["lesson-edit"])


# ============================================
# Lesson Edit Endpoints
# ============================================

@router.put("/{lesson_id}", response_model=LessonUpdateResponse)
async def update_lesson(
    lesson_id: UUID,
    data: LessonUpdateRequest,
    current_user = Depends(get_current_user)
):
    """
    Update a lesson with granular control.

    - is_minor_edit=true: Small corrections that don't require re-approval
    - is_minor_edit=false: Significant changes that require review

    Minor edits allow:
    - Typo corrections
    - Formatting fixes
    - Small clarifications

    Minor edits DO NOT allow:
    - Changing example anomalies
    - Modifying exercise structure
    - Large content changes (>10% or >500 chars)
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get lesson and workspace info
            lesson = await conn.fetchrow("""
                SELECT l.*, cm.workspace_id, cm.project_id, cm.status as course_status
                FROM learning.course_lessons l
                JOIN learning.course_modules cm ON cm.id = l.module_id
                WHERE l.id = $1
            """, lesson_id)

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

            workspace_id = lesson["workspace_id"]

            # Check permission for editing lessons
            has_edit_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, workspace_id, "learning:edit_lessons"
            )

            if not has_edit_perm and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No permission to edit lessons"
                )

            # If minor edit, check additional permission
            if data.is_minor_edit:
                has_minor_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, workspace_id, "learning:minor_edit"
                )

                if not has_minor_perm and not current_user.is_super_admin:
                    raise HTTPException(
                        status_code=403,
                        detail="No permission for minor edits (requires learning:minor_edit)"
                    )

        result = await lesson_edit_service.update_lesson(
            lesson_id=lesson_id,
            title=data.title,
            content=data.content,
            exercise_data=data.exercise_data,
            is_minor_edit=data.is_minor_edit,
            change_description=data.change_description,
            changed_by=current_user.user_id
        )

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return LessonUpdateResponse(
            lesson_id=lesson_id,
            status=result["status"],
            message=result["message"],
            course_status=result.get("course_status")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{lesson_id}/exercise", response_model=ExerciseUpdateResponse)
async def update_lesson_exercise(
    lesson_id: UUID,
    data: ExerciseUpdateRequest,
    current_user = Depends(get_current_user)
):
    """
    Update only the exercise data of a lesson.
    Always returns the course to draft status (requires re-approval).
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get lesson and workspace info
            lesson = await conn.fetchrow("""
                SELECT l.*, cm.workspace_id
                FROM learning.course_lessons l
                JOIN learning.course_modules cm ON cm.id = l.module_id
                WHERE l.id = $1
            """, lesson_id)

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

            workspace_id = lesson["workspace_id"]

            # Check permission
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, workspace_id, "learning:edit_lessons"
            )

            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No permission to edit lessons"
                )

        result = await lesson_edit_service.update_exercise(
            lesson_id=lesson_id,
            exercise_data=data.exercise_data,
            change_description=data.change_description,
            changed_by=current_user.user_id
        )

        return ExerciseUpdateResponse(
            lesson_id=lesson_id,
            message=result["message"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lesson_id}/history", response_model=LessonHistoryResponse)
async def get_lesson_history(
    lesson_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user = Depends(get_current_user)
):
    """Get change history for a lesson"""
    try:
        # Verify lesson exists and user has access
        async with db_manager.postgres_pool.acquire() as conn:
            lesson = await conn.fetchrow("""
                SELECT l.*, cm.workspace_id, cm.project_id
                FROM learning.course_lessons l
                JOIN learning.course_modules cm ON cm.id = l.module_id
                WHERE l.id = $1
            """, lesson_id)

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

            # Check access (user needs view permission on course)
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, lesson["workspace_id"], "learning:view_draft"
            )

            # Or if course is published, anyone with workspace access can view
            if not has_perm and lesson["course_status"] == "published":
                has_perm = await course_rbac_service.check_course_permission(
                    current_user.user_id, lesson["workspace_id"], "workspaces:read"
                )

            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No permission to view this lesson"
                )

        changes = await lesson_edit_service.get_lesson_history(lesson_id, limit)

        return LessonHistoryResponse(
            lesson_id=lesson_id,
            changes=changes
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lesson_id}/history/{change_id}/diff")
async def get_lesson_change_diff(
    lesson_id: UUID,
    change_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get detailed diff for a specific change"""
    try:
        # Verify lesson exists and user has access
        async with db_manager.postgres_pool.acquire() as conn:
            lesson = await conn.fetchrow(
                "SELECT * FROM learning.course_lessons WHERE id = $1",
                lesson_id
            )

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

        diff_data = await lesson_edit_service.get_lesson_diff(lesson_id, change_id)
        return diff_data

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{lesson_id}/restore/{change_id}")
async def restore_lesson_version(
    lesson_id: UUID,
    change_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Restore a lesson to a previous version from change history.
    Creates a new change entry for the restoration and returns course to draft.
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Get lesson and workspace info
            lesson = await conn.fetchrow("""
                SELECT l.*, cm.workspace_id
                FROM learning.course_lessons l
                JOIN learning.course_modules cm ON cm.id = l.module_id
                WHERE l.id = $1
            """, lesson_id)

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

            workspace_id = lesson["workspace_id"]

            # Check permission
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, workspace_id, "learning:edit_lessons"
            )

            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No permission to restore lessons"
                )

        result = await lesson_edit_service.restore_lesson_version(
            lesson_id=lesson_id,
            change_id=change_id,
            restored_by=current_user.user_id
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lesson_id}")
async def get_lesson(
    lesson_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get a single lesson with its current content"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            lesson = await conn.fetchrow("""
                SELECT
                    l.id, l.title, l.content, l.exercise_data, l.is_dynamic,
                    l.lesson_order, l.created_at,
                    cm.id as course_id, cm.title as course_title, cm.status as course_status
                FROM learning.course_lessons l
                JOIN learning.course_modules cm ON cm.id = l.module_id
                WHERE l.id = $1
            """, lesson_id)

            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")

            # Check access
            has_perm = await course_rbac_service.check_course_permission(
                current_user.user_id, lesson["course_workspace_id"] if "course_workspace_id" in lesson else None,
                "learning:view_draft"
            )

            if not has_perm and lesson["course_status"] == "draft":
                raise HTTPException(
                    status_code=403,
                    detail="No permission to view draft lessons"
                )

        return {
            "id": str(lesson["id"]),
            "title": lesson["title"],
            "content": lesson["content"],
            "exercise_data": lesson["exercise_data"],
            "is_dynamic": lesson["is_dynamic"],
            "lesson_order": lesson["lesson_order"],
            "course_id": str(lesson["course_id"]),
            "course_title": lesson["course_title"],
            "course_status": lesson["course_status"],
            "created_at": str(lesson["created_at"])
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
