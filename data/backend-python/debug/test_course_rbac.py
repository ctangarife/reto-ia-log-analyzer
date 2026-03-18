"""
Tests for Course RBAC Service
Tests role assignment, permission checking, and workspace members
"""
import pytest
import asyncio
from uuid import uuid4, UUID

from tests.conftest import client, test_db, test_user
from services.course_rbac_service import course_rbac_service
from models.learning_models import CourseReview, CourseVersion, CourseNotification


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
    """Create a test project"""
    project_id = uuid4()
    async with test_db.acquire() as conn:
        await conn.execute("""
            INSERT INTO auth.projects (id, workspace_id, name, created_by)
            VALUES ($1, $2, 'Test Project', $3)
        """, project_id, test_workspace, test_user)
    return project_id

@pytest.fixture
async def initialized_permissions(test_db):
    """Initialize course permissions before tests"""
    try:
        await course_rbac_service.initialize_course_permissions()
    except Exception as e:
        print(f"Permissions already initialized or error: {e}")


# ============================================
# TESTS: INITIALIZATION
# ============================================

@pytest.mark.asyncio
async def test_initialize_course_permissions(test_db):
    """Test course permissions initialization"""
    result = await course_rbac_service.initialize_course_permissions()

    assert result["status"] == "success"
    assert "courses:create" in result["permissions_created"]
    assert "course_creator" in result["roles_created"]
    assert len(result["permissions_created"]) == 10
    assert len(result["roles_created"]) == 3


@pytest.mark.asyncio
async def test_initialize_idempotent(test_db):
    """Test that initialization can be called multiple times"""
    result1 = await course_rbac_service.initialize_course_permissions()
    result2 = await course_rbac_service.initialize_course_permissions()

    assert result1["status"] == result2["status"] == "success"


# ============================================
# TESTS: ROLE ASSIGNMENT
# ============================================

@pytest.mark.asyncio
async def test_assign_role_to_user(test_db, test_workspace, initialized_permissions):
    """Test assigning a role to a user"""
    user_id = uuid4()
    role_name = "course_creator"

    result = await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, role_name
    )

    assert result["status"] == "success"
    assert "role_name" in result


@pytest.mark.asyncio
async def test_assign_role_already_assigned(test_db, test_workspace, initialized_permissions):
    """Test assigning a role that user already has"""
    user_id = uuid4()
    role_name = "course_creator"

    # First assignment
    await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, role_name
    )

    # Second assignment (should return already_assigned)
    result = await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, role_name
    )

    assert result["status"] == "already_assigned"


@pytest.mark.asyncio
async def test_remove_role_from_user(test_db, test_workspace, initialized_permissions):
    """Test removing a role from a user"""
    user_id = uuid4()
    role_name = "course_creator"

    # First assign
    await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, role_name
    )

    # Then remove
    result = await course_rbac_service.remove_course_role_from_user(
        user_id, test_workspace, role_name
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_remove_nonexistent_role(test_db, test_workspace, initialized_permissions):
    """Test removing a role that user doesn't have"""
    user_id = uuid4()
    role_name = "course_creator"

    result = await course_rbac_service.remove_course_role_from_user(
        user_id, test_workspace, role_name
    )

    assert result["status"] == "not_found"


# ============================================
# TESTS: PERMISSIONS
# ============================================

@pytest.mark.asyncio
async def test_get_user_course_roles(test_db, test_workspace, initialized_permissions):
    """Test getting user's course roles"""
    user_id = uuid4()

    # Assign a role
    await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, "course_creator"
    )

    # Get roles
    roles = await course_rbac_service.get_user_course_roles(user_id, test_workspace)

    assert len(roles) == 1
    assert roles[0]["name"] == "course_creator"


@pytest.mark.asyncio
async def test_get_user_course_permissions(test_db, test_workspace, initialized_permissions):
    """Test getting user's course permissions"""
    user_id = uuid4()

    # Assign admin role (has all permissions)
    await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, "course_admin"
    )

    # Get permissions
    permissions = await course_rbac_service.get_user_course_permissions(user_id, test_workspace)

    assert "courses:create" in permissions
    assert "courses:review" in permissions
    assert "courses:publish" in permissions


@pytest.mark.asyncio
async def test_check_course_permission(test_db, test_workspace, initialized_permissions):
    """Test checking a specific permission"""
    user_id = uuid4()

    # Assign creator role (doesn't have review permission)
    await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, "course_creator"
    )

    # Check permission they have
    has_perm = await course_rbac_service.check_course_permission(
        user_id, test_workspace, "courses:create"
    )
    assert has_perm is True

    # Check permission they don't have
    has_perm = await course_rbac_service.check_course_permission(
        user_id, test_workspace, "courses:review"
    )
    assert has_perm is False


# ============================================
# TESTS: WORKSPACE MEMBERS
# ============================================

@pytest.mark.asyncio
async def test_get_workspace_course_members(test_db, test_workspace, initialized_permissions):
    """Test getting all workspace members with course roles"""
    user_id = uuid4()

    # Assign role to user
    await course_rbac_service.assign_course_role_to_user(
        user_id, test_workspace, "course_creator"
    )

    # Get members
    members = await course_rbac_service.get_workspace_course_members(test_workspace)

    assert len(members) == 1
    assert members[0]["user_id"] == str(user_id)


@pytest.mark.asyncio
async def test_get_workspace_course_members_with_filter(test_db, test_workspace, initialized_permissions):
    """Test filtering members by role"""
    user1 = uuid4()
    user2 = uuid4()

    # Assign different roles
    await course_rbac_service.assign_course_role_to_user(
        user1, test_workspace, "course_creator"
    )
    await course_rbac_service.assign_course_role_to_user(
        user2, test_workspace, "course_reviewer"
    )

    # Get only course_creators
    members = await course_rbac_service.get_workspace_course_members(
        test_workspace, "course_creator"
    )

    assert len(members) == 1
    assert members[0]["user_id"] == str(user1)


# ============================================
# TESTS: ROLE DETAILS
# ============================================

@pytest.mark.asyncio
async def test_get_course_role_details(test_db):
    """Test getting role and permission details"""
    details = await course_rbac_service.get_course_role_details()

    assert "roles" in details
    assert "permissions" in details

    # Check course_creator permissions
    assert "courses:create" in details["roles"]["course_creator"]["permissions"]
    assert "courses:create" in details["permissions"]

    # Check that course_admin has all permissions
    admin_perms = details["roles"]["course_admin"]["permissions"]
    assert len(admin_perms) == 10  # All permissions
