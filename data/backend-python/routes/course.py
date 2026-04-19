"""
Course Routes
API endpoints for the interactive mini-course system
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from uuid import UUID

from middleware.auth_middleware import get_current_user, CurrentUser
from services.course_service import course_service
from models.learning_models import (
    CourseProgressResponse, LessonProgressUpdate,
    ExerciseValidationRequest, ExerciseValidationResponse,
    FinalExamSubmissionRequest, FinalExamValidationResponse,
    CertificateRequest, CertificateResponse,
    WorkspaceCoursesResponse
)
from config.database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/course", tags=["course"])


@router.get("/progress", response_model=CourseProgressResponse)
async def get_course_progress(
    project_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get complete course progress for the current user in a project"""
    try:
        logger.info(f"[get_course_progress] Called with project_id={project_id}, user_id={current_user.user_id}")
        # Get progress - NO auto-initialization
        # Courses should only be created when explicitly requested
        result = await course_service.get_course_progress(current_user.user_id, project_id)
        logger.info(f"[get_course_progress] Returning course_id={result.course_id}, course_name={result.course_name}")
        return result
    except Exception as e:
        logger.error(f"[get_course_progress] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(
    project_id: UUID,
    lesson_id: UUID,
    data: LessonProgressUpdate,
    current_user = Depends(get_current_user)
):
    """Mark a lesson as completed"""
    try:
        return await course_service.complete_lesson(current_user.user_id, project_id, lesson_id, data.score)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exercises")
async def get_exercises(
    project_id: UUID,
    lesson_id: UUID,
    count: int = 5,
    current_user = Depends(get_current_user)
):
    """Get dynamic exercises using project anomalies"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_exercises called: project_id={project_id}, lesson_id={lesson_id}, count={count}, user_id={current_user.user_id}")
    try:
        exercises = await course_service.get_project_exercises(
            current_user.user_id, project_id, lesson_id, count
        )
        logger.info(f"get_exercises returning {len(exercises)} exercises")
        return {"exercises": exercises}
    except Exception as e:
        logger.error(f"get_exercises error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exercises/validate", response_model=ExerciseValidationResponse)
async def validate_exercise(
    project_id: UUID,
    data: ExerciseValidationRequest,
    current_user = Depends(get_current_user)
):
    """Validate a user's exercise answer"""
    try:
        return await course_service.validate_exercise_answer(
            current_user.user_id, project_id, data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/final-exam/submit", response_model=FinalExamValidationResponse)
async def submit_final_exam(
    project_id: UUID,
    data: FinalExamSubmissionRequest,
    current_user = Depends(get_current_user)
):
    """Submit and validate final exam with scoring

    Returns:
        - passed: Whether user passed (70% required)
        - score: Final score (0-100)
        - results: Detailed results per question
        - certificate_earned: Whether certificate is earned
    """
    try:
        return await course_service.validate_final_exam(
            current_user.user_id, project_id, data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certificate", response_model=CertificateResponse)
async def get_certificate(
    project_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get certificate data (URL to badge and download)"""
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            completion = await conn.fetchrow(
                "SELECT * FROM learning.course_completion WHERE user_id = $1 AND project_id = $2",
                current_user.user_id, project_id
            )

            if not completion or not completion["badge_earned"]:
                raise HTTPException(status_code=404, detail="Certificate not earned yet")

            # Generate URLs
            badge_url = f"/api/projects/{project_id}/course/badge/{current_user.user_id}"
            download_url = f"/api/projects/{project_id}/course/certificate/{current_user.user_id}/download"

            return CertificateResponse(
                certificate_url=f"/certificates/{project_id}_{current_user.user_id}.json",
                download_url=download_url,
                issued_at=completion["completed_at"],
                badge_url=badge_url
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/badge/{user_id}")
async def get_badge(
    project_id: UUID,
    user_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get badge image for user (SVG)"""

    badge_svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="80" viewBox="0 0 200 80" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="200" height="80" rx="10" fill="url(#grad)"/>
  <text x="100" y="25" font-family="Arial, sans-serif" font-size="12" fill="white" text-anchor="middle">LogsAnomaly</text>
  <text x="100" y="45" font-family="Arial, sans-serif" font-size="10" fill="white" text-anchor="middle">Curso Completado</text>
  <text x="100" y="62" font-family="Arial, sans-serif" font-size="8" fill="rgba(255,255,255,0.8)" text-anchor="middle">Experto en Análisis</text>
</svg>"""

    return Response(content=badge_svg, media_type="image/svg+xml")


# Workspace-scoped course listing endpoint
workspace_router = APIRouter(prefix="/workspaces", tags=["workspace-courses"])


@workspace_router.get("/{workspace_id}/courses", response_model=WorkspaceCoursesResponse)
async def get_workspace_courses_list(
    workspace_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get all courses in a workspace and its projects"""
    try:
        courses = await course_service.get_workspace_courses(current_user.user_id, workspace_id)
        return WorkspaceCoursesResponse(
            workspace_id=workspace_id,
            courses=[{
                "project_id": c["project_id"],
                "project_name": c["project_name"],
                "course_id": c["course_id"],
                "title": c["title"],
                "description": c["description"],
                "total_lessons": c["total_lessons"],
                "completed_lessons": c["completed_lessons"],
                "is_completed": c["is_completed"]
            } for c in courses]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CertificateRequest(BaseModel):
    """Request to generate certificate"""
    user_name: str
