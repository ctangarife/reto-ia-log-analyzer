"""
Tests for Course Generation Service
Tests course generation, versioning, and dynamic/static lessons
"""
import pytest
import asyncio
from uuid import uuid4, UUID

from tests.conftest import client, test_db, test_user
from services.course_generation_service import course_generation_service
from models.learning_models import Course, CourseModule, CourseLesson


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
    """Create a test project with some mock data"""
    project_id = uuid4()
    async with test_db.acquire() as conn:
        await conn.execute("""
            INSERT INTO auth.projects (id, workspace_id, name, created_by)
            VALUES ($1, $2, 'Test Project', $3)
        """, project_id, test_workspace, test_user)

        # Add some mock jobs and anomalies
        job_id = uuid4()
        await conn.execute("""
            INSERT INTO processing.jobs (id, project_id, status, total_chunks,
                                       completed_chunks, total_anomalies)
            VALUES ($1, $2, 'completed', 10, 10, 25)
        """, job_id, project_id)

    return project_id


@pytest.fixture
async def initialized_rbac(test_db):
    """Initialize course RBAC before tests"""
    from services.course_rbac_service import course_rbac_service
    try:
        await course_rbac_service.initialize_course_permissions()
    except Exception as e:
        print(f"RBAC already initialized or error: {e}")


# ============================================
# TESTS: CAN GENERATE CHECKS
# ============================================

@pytest.mark.asyncio
async def test_can_generate_no_jobs(test_db, test_project):
    """Test that can_generate returns false when project has no completed jobs"""
    # Project exists but has no completed jobs (we'll add a failed one)
    async with test_db.acquire() as conn:
        job_id = uuid4()
        await conn.execute("""
            INSERT INTO processing.jobs (id, project_id, status, total_chunks,
                                       completed_chunks, total_anomalies)
            VALUES ($1, $2, 'failed', 10, 5, 0)
        """, job_id, test_project)

    result = await course_generation_service.can_generate_course(test_project)

    assert result["can_generate"] is False
    assert "No hay análisis completados" in result["reason"]


@pytest.mark.asyncio
async def test_can_generate_no_anomalies(test_db, test_project):
    """Test that can_generate returns false when not enough anomalies"""
    # Add a job with very few anomalies
    async with test_db.acquire() as conn:
        job_id = uuid4()
        await conn.execute("""
            INSERT INTO processing.jobs (id, project_id, status, total_chunks,
                                       completed_chunks, total_anomalies)
            VALUES ($1, $2, 'completed', 10, 10, 2)
        """, job_id, test_project)

    result = await course_generation_service.can_generate_course(test_project)

    assert result["can_generate"] is False
    assert "no suficientes anomalías" in result["reason"].lower()


@pytest.mark.asyncio
async def test_can_generate_success(test_db, test_project):
    """Test that can_generate returns true when conditions are met"""
    result = await course_generation_service.can_generate_course(test_project)

    assert result["can_generate"] is True
    assert result["anomaly_count"] >= 5


# ============================================
# TESTS: COURSE GENERATION
# ============================================

@pytest.mark.asyncio
async def test_generate_course_basic(test_db, test_project, test_workspace, initialized_rbac):
    """Test basic course generation"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    assert result["status"] == "success"
    assert result["course_id"] is not None
    assert result["total_modules"] == 4
    assert result["total_lessons"] == 10


@pytest.mark.asyncio
async def test_generate_course_with_custom_name(test_db, test_project, test_workspace, initialized_rbac):
    """Test course generation with custom name"""
    custom_name = "Curso Personalizado de Análisis"

    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project",
        name=custom_name
    )

    assert result["status"] == "success"

    # Verify the course has the custom name
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT title FROM learning.courses WHERE id = $1
        """, result["course_id"])

    assert course["title"] == custom_name


@pytest.mark.asyncio
async def test_generate_workspace_scoped_course(test_db, test_project, test_workspace, initialized_rbac):
    """Test workspace-scoped course generation"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="workspace"
    )

    assert result["status"] == "success"

    # Verify scope is workspace
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT scope FROM learning.courses WHERE id = $1
        """, result["course_id"])

    assert course["scope"] == "workspace"


@pytest.mark.asyncio
async def test_generated_course_initial_status(test_db, test_project, test_workspace, initialized_rbac):
    """Test that generated course starts in draft status"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    # Check course status
    async with test_db.acquire() as conn:
        course = await conn.fetchrow("""
            SELECT status FROM learning.courses WHERE id = $1
        """, result["course_id"])

    assert course["status"] == "draft"


# ============================================
# TESTS: DYNAMIC vs STATIC LESSONS
# ============================================

@pytest.mark.asyncio
async def test_module_1_is_dynamic(test_db, test_project, test_workspace, initialized_rbac):
    """Test that Module 1 lessons are marked as dynamic"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    # Get Module 1 lessons
    async with test_db.acquire() as conn:
        lessons = await conn.fetch("""
            SELECT l.is_dynamic, l.content
            FROM learning.course_lessons l
            JOIN learning.course_modules m ON l.module_id = m.id
            WHERE m.course_id = $1 AND m.module_order = 1
            ORDER BY l.lesson_order
        """, result["course_id"])

    # Module 1 should have dynamic lessons with NULL content
    assert len(lessons) == 3
    for lesson in lessons:
        assert lesson["is_dynamic"] is True
        assert lesson["content"] is None  # Dynamic lessons have no stored content


@pytest.mark.asyncio
async def test_modules_2_4_are_static(test_db, test_project, test_workspace, initialized_rbac):
    """Test that Modules 2-4 lessons are static with content"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    # Get lessons from modules 2, 3, 4
    async with test_db.acquire() as conn:
        lessons = await conn.fetch("""
            SELECT l.is_dynamic, l.content, l.title
            FROM learning.course_lessons l
            JOIN learning.course_modules m ON l.module_id = m.id
            WHERE m.course_id = $1 AND m.module_order IN (2, 3, 4)
            ORDER BY m.module_order, l.lesson_order
        """, result["course_id"])

    # Modules 2-4 should have static lessons with content
    assert len(lessons) == 7  # 3 + 2 + 2 lessons
    for lesson in lessons:
        assert lesson["is_dynamic"] is False
        assert lesson["content"] is not None
        assert len(lesson["content"]) > 0


# ============================================
# TESTS: VERSIONING
# ============================================

@pytest.mark.asyncio
async def test_regenerate_creates_new_version(test_db, test_project, test_workspace, initialized_rbac):
    """Test that regenerating a course creates a new version"""
    # First generation
    result1 = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    # Get first version
    async with test_db.acquire() as conn:
        v1 = await conn.fetchrow("""
            SELECT version_number FROM learning.courses WHERE id = $1
        """, result1["course_id"])

    # Regenerate (simulate by calling again with same project)
    result2 = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    # Get second version
    async with test_db.acquire() as conn:
        v2 = await conn.fetchrow("""
            SELECT version_number FROM learning.courses WHERE id = $1
        """, result2["course_id"])

    # Versions should be different
    assert v2["version_number"] > v1["version_number"]


@pytest.mark.asyncio
async def test_version_history_created(test_db, test_project, test_workspace, initialized_rbac):
    """Test that course versions are tracked in history"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    # Check that version history exists
    async with test_db.acquire() as conn:
        versions = await conn.fetch("""
            SELECT * FROM learning.course_versions
            WHERE course_id = $1
            ORDER BY created_at DESC
        """, result["course_id"])

    assert len(versions) >= 1
    assert versions[0]["version_number"] == 1


# ============================================
# TESTS: MODULE STRUCTURE
# ============================================

@pytest.mark.asyncio
async def test_course_has_4_modules(test_db, test_project, test_workspace, initialized_rbac):
    """Test that generated course has exactly 4 modules"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    async with test_db.acquire() as conn:
        modules = await conn.fetch("""
            SELECT * FROM learning.course_modules
            WHERE course_id = $1
            ORDER BY module_order
        """, result["course_id"])

    assert len(modules) == 4

    # Verify module titles
    assert "Contexto" in modules[0]["title"]
    assert "Anomal" in modules[1]["title"]  # Anomalías
    assert "Análisis" in modules[2]["title"]
    assert "Evaluaci" in modules[3]["title"]  # Evaluación


@pytest.mark.asyncio
async def test_module_lesson_counts(test_db, test_project, test_workspace, initialized_rbac):
    """Test that each module has correct number of lessons"""
    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    async with test_db.acquire() as conn:
        module_lessons = await conn.fetch("""
            SELECT m.module_order, COUNT(l.id) as lesson_count
            FROM learning.course_modules m
            LEFT JOIN learning.course_lessons l ON m.id = l.module_id
            WHERE m.course_id = $1
            GROUP BY m.module_order
            ORDER BY m.module_order
        """, result["course_id"])

    # Module 1: 3 lessons, Module 2: 3 lessons, Module 3: 2 lessons, Module 4: 2 lessons
    assert module_lessons[0]["lesson_count"] == 3
    assert module_lessons[1]["lesson_count"] == 3
    assert module_lessons[2]["lesson_count"] == 2
    assert module_lessons[3]["lesson_count"] == 2


# ============================================
# TESTS: ERROR HANDLING
# ============================================

@pytest.mark.asyncio
async def test_generate_without_permission(test_db, test_project, test_workspace):
    """Test that generation fails when user lacks permission"""
    # User without course_creator role
    unauthorized_user = uuid4()

    result = await course_generation_service.generate_course(
        project_id=test_project,
        workspace_id=test_workspace,
        created_by=unauthorized_user,
        scope="project"
    )

    assert result["status"] == "error"
    assert "permiso" in result["message"].lower()


@pytest.mark.asyncio
async def test_generate_nonexistent_project(test_db, test_workspace, initialized_rbac):
    """Test that generation fails for non-existent project"""
    fake_project_id = uuid4()

    result = await course_generation_service.generate_course(
        project_id=fake_project_id,
        workspace_id=test_workspace,
        created_by=test_user,
        scope="project"
    )

    assert result["status"] == "error"
