"""
Simple tests for Course RBAC Service
These tests call the service directly instead of using HTTP
"""
import pytest
from config.database import db_manager
from services.course_rbac_service import course_rbac_service


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Connect databases before running tests"""
    import asyncio

    async def connect():
        await db_manager.connect_postgres()
        await db_manager.connect_mongodb()

    asyncio.run(connect())

    yield

    async def close():
        await db_manager.postgres_pool.close()
        if db_manager.mongodb_client:
            await db_manager.mongodb_client.close()

    asyncio.run(close())


# ============================================
# TESTS: INITIALIZATION
# ============================================

@pytest.mark.asyncio
async def test_initialize_course_permissions():
    """Test course permissions initialization"""
    result = await course_rbac_service.initialize_course_permissions()

    assert result["status"] == "success"
    assert "permissions_created" in result
    assert "roles_created" in result
    assert len(result["permissions_created"]) == 10
    assert len(result["roles_created"]) == 3


@pytest.mark.asyncio
async def test_get_course_role_details():
    """Test getting role and permission details"""
    # First initialize
    await course_rbac_service.initialize_course_permissions()

    # Get role details
    details = await course_rbac_service.get_course_role_details()

    assert "roles" in details
    assert "permissions" in details

    # Check course_creator role exists
    assert "course_creator" in details["roles"]
    assert "courses:create" in details["roles"]["course_creator"]["permissions"]


# ============================================
# TESTS: PERMISSIONS AND ROLES
# ============================================

@pytest.mark.asyncio
async def test_permission_list_complete():
    """Test that all expected permissions are defined"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()

    # Check all expected permissions exist
    expected_permissions = [
        "courses:create",
        "courses:edit",
        "courses:edit_own",
        "courses:edit_lessons",
        "courses:minor_edit",
        "courses:review",
        "courses:delete",
        "courses:publish",
        "courses:view_draft",
        "courses:view_pending"
    ]

    for perm in expected_permissions:
        assert perm in details["permissions"], f"Permission {perm} not found"


@pytest.mark.asyncio
async def test_role_list_complete():
    """Test that all expected roles are defined"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()

    # Check all expected roles exist
    expected_roles = ["course_creator", "course_reviewer", "course_admin"]

    for role in expected_roles:
        assert role in details["roles"], f"Role {role} not found"


# ============================================
# TESTS: ROLE PERMISSIONS MAPPING
# ============================================

@pytest.mark.asyncio
async def test_course_creator_permissions():
    """Test course_creator has correct permissions"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()
    creator_perms = details["roles"]["course_creator"]["permissions"]

    # Course creator should have these permissions
    assert "courses:create" in creator_perms
    assert "courses:edit_own" in creator_perms
    assert "courses:edit_lessons" in creator_perms
    assert "courses:minor_edit" in creator_perms
    assert "courses:view_draft" in creator_perms

    # Course creator should NOT have these
    assert "courses:edit" not in creator_perms  # Only edit_own
    assert "courses:review" not in creator_perms
    assert "courses:delete" not in creator_perms


@pytest.mark.asyncio
async def test_course_reviewer_permissions():
    """Test course_reviewer has correct permissions"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()
    reviewer_perms = details["roles"]["course_reviewer"]["permissions"]

    # Reviewer should have these
    assert "courses:review" in reviewer_perms
    assert "courses:view_pending" in reviewer_perms
    assert "courses:view_draft" in reviewer_perms
    assert "courses:minor_edit" in reviewer_perms

    # Reviewer should NOT have these
    assert "courses:create" not in reviewer_perms
    assert "courses:edit_own" not in reviewer_perms


@pytest.mark.asyncio
async def test_course_admin_permissions():
    """Test course_admin has all permissions"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()
    admin_perms = details["roles"]["course_admin"]["permissions"]

    # Admin should have ALL course permissions
    assert "courses:create" in admin_perms
    assert "courses:edit" in admin_perms
    assert "courses:review" in admin_perms
    assert "courses:delete" in admin_perms
    assert "courses:publish" in admin_perms

    # Should have at least 9 permissions (all of them)
    assert len(admin_perms) >= 9


# ============================================
# TESTS: PERMISSION DEFINITIONS
# ============================================

@pytest.mark.asyncio
async def test_all_permissions_have_descriptions():
    """Test that all permissions have descriptions"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()

    # Check that each permission has a description
    for perm_name, perm_desc in details["permissions"].items():
        assert perm_name.startswith("courses:")
        assert isinstance(perm_desc, str)
        assert len(perm_desc) > 0


@pytest.mark.asyncio
async def test_all_roles_have_permission_lists():
    """Test that all roles have permission lists"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()

    # Check that each role has a permissions list
    for role_name, role_data in details["roles"].items():
        assert "permissions" in role_data
        assert isinstance(role_data["permissions"], list)
        assert len(role_data["permissions"]) > 0


# ============================================
# TESTS: DATA CONSISTENCY
# ============================================

@pytest.mark.asyncio
async def test_course_admin_has_all_permissions():
    """Test that course_admin role has all course permissions"""
    await course_rbac_service.initialize_course_permissions()

    details = await course_rbac_service.get_course_role_details()

    # Get all course permissions
    all_course_perms = set(details["permissions"].keys())

    # Get course_admin permissions
    admin_perms = set(details["roles"]["course_admin"]["permissions"])

    # Admin should have all permissions
    assert all_course_perms == admin_perms


@pytest.mark.asyncio
async def test_initialize_is_idempotent():
    """Test that initialize can be called multiple times"""
    result1 = await course_rbac_service.initialize_course_permissions()
    result2 = await course_rbac_service.initialize_course_permissions()

    assert result1["status"] == result2["status"] == "success"
