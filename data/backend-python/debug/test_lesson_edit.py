"""
Tests for Lesson Edit Service
Tests granular lesson editing with change tracking
"""
import pytest
import asyncio
from uuid import uuid4, UUID

from tests.conftest import client, test_db, test_user
from services.lesson_edit_service import lesson_edit_service
from services.course_generation_service import course_generation_service
from models.learning_models import Course, CourseModule, CourseLesson, LessonChangeHistory


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
async def test_workspace(test_db):
    """Create a test workspace"""
    workspace_id = uuid4()
    async with test_db.acquire() as conn:
        await conn.execute("""
            INSERT INTO auth.workspaces (id, name, created_by)
            VALUES ($1, 'Test Workspace', $2)
        """, workspace_id, test_user)
    return workspace_id


@pytest.fixture
async def test_project(test_db, test_workspace):
    """Create a test project with mock data"""
    project_id = uuid4()
    async with test_db.acquire() as conn:
        await conn.execute("""
            INSERT INTO auth.projects (id, workspace_id, name, created_by)
            VALUES ($1, $2, 'Test Project', $3)
        """, project_id, test_workspace, test_user)

        # Add mock jobs and anomalies
        job_id = uuid4()
        await conn.execute("""
            INSERT INTO processing.jobs (id, project_id, status, total_chunks,
                                       completed_chunks, total_anomalies)
            VALUES ($1, $2, 'completed', 10, 10, 25)
        """, job_id, project_id)

    return project_id


@pytest.fixture
async def test_course(test_db, test_project, test_workspace):
    """Create a test course with modules and lessons"""
    # Initialize RBAC first
    from services.course_rbac_service import course_rbac_service
    try:
        await course_rbac_service.initialize_course_permissions()
    except Exception:
        pass

    # Generate a course
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    return result["course_id"]


@pytest.fixture
async def test_lesson(test_db, test_course):
    """Get a static lesson from the test course"""
    async with test_db.acquire() as conn:
        lesson = await conn.fetchrow("""
            SELECT l.* FROM learning.course_lessons l
            JOIN learning.course_modules m ON l.module_id = m.id
            WHERE m.course_id = $1 AND l.is_dynamic = FALSE
            LIMIT 1
        """, test_course)

    return lesson["id"]


@pytest.fixture
async def published_course(test_db, test_course):
    """Publish a test course for editing tests"""
    async with test_db.acquire() as conn:
        # Update course to published
        await conn.execute("""
            UPDATE learning.courses
            SET status = 'published', published_at = NOW()
            WHERE id = $1
        """, test_course)

        # Update modules to published
        await conn.execute("""
            UPDATE learning.course_modules
            SET status = 'published'
            WHERE course_id = $1
        """, test_course)

    return test_course


# ============================================
# TESTS: MINOR EDIT DETECTION
# ============================================

@pytest.mark.asyncio
async def test_minor_edit_small_change(test_db):
    """Test that small changes are detected as minor edits"""
    old_content = "Este es el contenido original de la lección."
    new_content = "Este es el contenido modificado de la lección."

    is_minor = lesson_edit_service._is_minor_change(old_content, new_content)

    assert is_minor is True


@pytest.mark.asyncio
async def test_minor_edit_exactly_10_percent(test_db):
    """Test that exactly 10% change is still minor"""
    old_content = "a" * 1000  # 1000 characters
    new_content = "a" * 1100  # 1100 characters (10% increase)

    is_minor = lesson_edit_service._is_minor_change(old_content, new_content)

    assert is_minor is True


@pytest.mark.asyncio
async def test_minor_edit_over_10_percent(test_db):
    """Test that changes over 10% are NOT minor"""
    old_content = "a" * 1000
    new_content = "a" * 1200  # 20% increase

    is_minor = lesson_edit_service._is_minor_change(old_content, new_content)

    assert is_minor is False


@pytest.mark.asyncio
async def test_minor_edit_over_500_chars(test_db):
    """Test that changes over 500 chars are NOT minor even if ratio is small"""
    old_content = "a" * 10000
    new_content = "a" * 10501  # Only 5% but over 500 chars

    is_minor = lesson_edit_service._is_minor_change(old_content, new_content)

    assert is_minor is False


@pytest.mark.asyncio
async def test_minor_edit_exactly_500_chars(test_db):
    """Test that exactly 500 chars change is still minor"""
    old_content = "a" * 10000
    new_content = "a" * 10500  # Exactly 500 chars

    is_minor = lesson_edit_service._is_minor_change(old_content, new_content)

    assert is_minor is True


# ============================================
# TESTS: LESSON CONTENT UPDATES
# ============================================

@pytest.mark.asyncio
async def test_update_lesson_content_minor(test_db, test_lesson, published_course):
    """Test updating lesson content with minor edit flag"""
    new_content = "Contenido actualizado con corrección menor."

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content=new_content,
        is_minor_edit=True,
        changed_by=test_user
    )

    assert result["status"] == "success"
    assert result["is_minor_edit"] is True

    # Verify course is still published
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT status FROM learning.courses WHERE id = $1
        """, published_course)

    assert course["status"] == "published"


@pytest.mark.asyncio
async def test_update_lesson_content_major(test_db, test_lesson, published_course):
    """Test that major edit returns course to draft"""
    new_content = "Este es un contenido completamente nuevo y mucho más largo " * 20

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content=new_content,
        is_minor_edit=False,
        changed_by=test_user
    )

    assert result["status"] == "success"
    assert result["is_minor_edit"] is False

    # Verify course returned to draft
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT status FROM learning.courses WHERE id = $1
        """, published_course)

    assert course["status"] == "draft"


@pytest.mark.asyncio
async def test_update_lesson_title(test_db, test_lesson):
    """Test updating lesson title"""
    new_title = "Nuevo Título de Lección"

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        title=new_title,
        changed_by=test_user
    )

    assert result["status"] == "success"

    # Verify title changed
    async with test_db.acquire() as conn:
        lesson = await conn.fetchrow("""
            SELECT title FROM learning.course_lessons WHERE id = $1
        """, test_lesson)

    assert lesson["title"] == new_title


@pytest.mark.asyncio
async def test_update_both_title_and_content(test_db, test_lesson):
    """Test updating both title and content"""
    new_title = "Título Actualizado"
    new_content = "Contenido actualizado"

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        title=new_title,
        content=new_content,
        changed_by=test_user
    )

    assert result["status"] == "success"

    # Verify both changed
    async with test_db.acquire() as conn:
        lesson = await conn.fetchrow("""
            SELECT title, content FROM learning.course_lessons WHERE id = $1
        """, test_lesson)

    assert lesson["title"] == new_title
    assert lesson["content"] == new_content


# ============================================
# TESTS: CHANGE HISTORY
# ============================================

@pytest.mark.asyncio
async def test_change_history_created(test_db, test_lesson):
    """Test that change history is recorded"""
    original_content = "Contenido original"
    new_content = "Contenido nuevo"

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content=new_content,
        changed_by=test_user
    )

    assert result["status"] == "success"

    # Check change history
    async with test_db.acquire() as conn:
        history = await conn.fetch("""
            SELECT * FROM learning.lesson_change_history
            WHERE lesson_id = $1
            ORDER BY changed_at DESC
        """, test_lesson)

    assert len(history) >= 1
    assert history[0]["change_type"] == "content"
    assert history[0]["old_value"] == original_content
    assert history[0]["new_value"] == new_content
    assert history[0]["changed_by"] == test_user


@pytest.mark.asyncio
async def test_change_history_tracks_minor_edit_flag(test_db, test_lesson):
    """Test that minor edit flag is recorded in history"""
    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content="Contenido con edición menor",
        is_minor_edit=True,
        changed_by=test_user
    )

    async with test_db.acquire() as conn:
        history = await conn.fetchrow("""
            SELECT * FROM learning.lesson_change_history
            WHERE lesson_id = $1
            ORDER BY changed_at DESC
            LIMIT 1
        """, test_lesson)

    assert history["is_minor_edit"] is True


@pytest.mark.asyncio
async def test_change_history_for_title_change(test_db, test_lesson):
    """Test that title changes are tracked separately"""
    new_title = "Título Modificado"

    await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        title=new_title,
        changed_by=test_user
    )

    async with test_db.acquire() as conn:
        history = await conn.fetchrow("""
            SELECT * FROM learning.lesson_change_history
            WHERE lesson_id = $1 AND change_type = 'title'
            ORDER BY changed_at DESC
            LIMIT 1
        """, test_lesson)

    assert history is not None
    assert "Título" in history["old_value"] or history["old_value"] is not None


# ============================================
# TESTS: EXERCISE DATA
# ============================================

@pytest.mark.asyncio
async def test_update_exercise_data(test_db, test_lesson):
    """Test updating lesson exercise data"""
    exercise_data = {
        "type": "quiz",
        "questions": [
            {
                "question": "¿Qué es una anomalía?",
                "options": ["A", "B", "C", "D"],
                "correct": 0
            }
        ]
    }

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        exercise_data=exercise_data,
        changed_by=test_user
    )

    assert result["status"] == "success"

    # Verify exercise data was stored
    async with test_db.acquire() as conn:
        lesson = await conn.fetchrow("""
            SELECT exercise_data FROM learning.course_lessons WHERE id = $1
        """, test_lesson)

    assert lesson["exercise_data"] is not None


# ============================================
# TESTS: PERMISSION CHECKS
# ============================================

@pytest.mark.asyncio
async def test_edit_without_permission(test_db, test_lesson, published_course):
    """Test that editing without permission fails"""
    unauthorized_user = uuid4()

    result = await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content="Intento de edición no autorizado",
        changed_by=unauthorized_user
    )

    assert result["status"] == "error"
    assert "permiso" in result["message"].lower()


# ============================================
# TESTS: DYNAMIC LESSON PROTECTION
# ============================================

@pytest.mark.asyncio
async def test_cannot_edit_dynamic_lesson(test_db, test_course):
    """Test that dynamic lessons cannot be edited"""
    # Get a dynamic lesson
    async with test_db.acquire() as conn:
        lesson = await conn.fetchrow("""
            SELECT l.* FROM learning.course_lessons l
            JOIN learning.course_modules m ON l.module_id = m.id
            WHERE m.course_id = $1 AND l.is_dynamic = TRUE
            LIMIT 1
        """, test_course)

    if lesson:
        result = await lesson_edit_service.update_lesson(
            lesson_id=lesson["id"],
            content="Intento de editar lección dinámica",
            changed_by=test_user
        )

        assert result["status"] == "error"
        assert "dinámica" in result["message"].lower()


# ============================================
# TESTS: GET LESSON HISTORY
# ============================================

@pytest.mark.asyncio
async def test_get_lesson_history(test_db, test_lesson):
    """Test retrieving change history for a lesson"""
    # Make some changes
    await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content="Primera edición",
        changed_by=test_user
    )

    await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        title="Título editado",
        changed_by=test_user
    )

    # Get history
    history = await lesson_edit_service.get_lesson_history(test_lesson)

    assert len(history) >= 2
    assert any(h["change_type"] == "content" for h in history)
    assert any(h["change_type"] == "title" for h in history)


@pytest.mark.asyncio
async def test_lesson_history_ordered(test_db, test_lesson):
    """Test that history is ordered by date (newest first)"""
    # Make multiple changes
    for i in range(3):
        await lesson_edit_service.update_lesson(
            lesson_id=test_lesson,
            content=f"Edición {i}",
            changed_by=test_user
        )

    history = await lesson_edit_service.get_lesson_history(test_lesson)

    # Most recent should be first
    assert history[0]["new_value"] == "Edición 2"
    assert history[-1]["new_value"] == "Edición 0"


# ============================================
# TESTS: COURSE STATUS TRANSITIONS
# ============================================

@pytest.mark.asyncio
async def test_draft_course_stays_draft_on_edit(test_db, test_course, test_lesson):
    """Test that editing a draft course keeps it in draft"""
    # Ensure course is in draft
    async with test_db.acquire() as conn:
        await conn.execute("""
            UPDATE learning.courses SET status = 'draft' WHERE id = $1
        """, test_course)

    await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content="Edición en borrador",
        changed_by=test_user
    )

    # Should still be draft
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT status FROM learning.courses WHERE id = $1
        """, test_course)

    assert course["status"] == "draft"


@pytest.mark.asyncio
async def test_pending_course_returns_to_draft_on_edit(test_db, test_course, test_lesson):
    """Test that editing a pending course returns it to draft"""
    # Set course to pending
    async with test_db.acquire() as conn:
        await conn.execute("""
            UPDATE learning.courses SET status = 'pending' WHERE id = $1
        """, test_course)

    await lesson_edit_service.update_lesson(
        lesson_id=test_lesson,
        content="Edición en pendiente",
        changed_by=test_user
    )

    # Should return to draft
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT status FROM learning.courses WHERE id = $1
        """, test_course)

    assert course["status"] == "draft"
