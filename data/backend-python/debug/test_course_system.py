#!/usr/bin/env python
"""
Course System Test Script
Simple script to test course RBAC without pytest
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import db_manager
from services.course_rbac_service import course_rbac_service


async def main():
    """Run course RBAC tests"""
    print("=" * 80)
    print("COURSE RBAC SYSTEM TESTS")
    print("=" * 80)

    # Connect to databases
    print("\n1. Connecting to databases...")
    try:
        await db_manager.connect_postgres()
        await db_manager.connect_mongodb()
        print("✅ Connected to PostgreSQL and MongoDB")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return 1

    tests_passed = 0
    tests_failed = 0

    # Test 1: Initialize permissions
    print("\n2. Testing: Initialize course permissions...")
    try:
        result = await course_rbac_service.initialize_course_permissions()
        assert result["status"] == "success"
        assert len(result["permissions_created"]) == 10
        assert len(result["roles_created"]) == 3
        print(f"   ✅ PASS - Created {len(result['permissions_created'])} permissions, {len(result['roles_created'])} roles")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        tests_failed += 1

    # Test 2: Get role details
    print("\n3. Testing: Get course role details...")
    try:
        details = await course_rbac_service.get_course_role_details()
        assert "roles" in details
        assert "permissions" in details
        assert "course_creator" in details["roles"]
        assert "learning:create" in details["roles"]["course_creator"]["permissions"]
        print(f"   ✅ PASS - Found {len(details['roles'])} roles, {len(details['permissions'])} permissions")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        tests_failed += 1

    # Test 3: Verify course_creator permissions
    print("\n4. Testing: Course creator permissions...")
    try:
        details = await course_rbac_service.get_course_role_details()
        creator_perms = details["roles"]["course_creator"]["permissions"]
        assert "learning:create" in creator_perms
        assert "learning:edit_own" in creator_perms
        assert "learning:minor_edit" in creator_perms
        assert "learning:review" not in creator_perms
        print(f"   ✅ PASS - Course creator has {len(creator_perms)} permissions (correct)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        tests_failed += 1

    # Test 4: Verify course_reviewer permissions
    print("\n5. Testing: Course reviewer permissions...")
    try:
        details = await course_rbac_service.get_course_role_details()
        reviewer_perms = details["roles"]["course_reviewer"]["permissions"]
        assert "learning:review" in reviewer_perms
        assert "learning:view_pending" in reviewer_perms
        assert "learning:create" not in reviewer_perms
        print(f"   ✅ PASS - Course reviewer has {len(reviewer_perms)} permissions (correct)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        tests_failed += 1

    # Test 5: Verify course_admin has all permissions
    print("\n6. Testing: Course admin has all permissions...")
    try:
        details = await course_rbac_service.get_course_role_details()
        admin_perms = details["roles"]["course_admin"]["permissions"]
        all_perms = set(details["permissions"].keys())
        assert set(admin_perms) == all_perms
        print(f"   ✅ PASS - Course admin has all {len(admin_perms)} permissions")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        tests_failed += 1

    # Test 6: Idempotent initialization
    print("\n7. Testing: Initialize is idempotent...")
    try:
        result1 = await course_rbac_service.initialize_course_permissions()
        result2 = await course_rbac_service.initialize_course_permissions()
        assert result1["status"] == result2["status"] == "success"
        print("   ✅ PASS - Can initialize multiple times")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ FAIL - {e}")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Total:  {tests_passed + tests_failed}")

    if tests_failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed")

    # Cleanup
    print("\n8. Closing connections...")
    try:
        await db_manager.postgres_pool.close()
        if db_manager.mongodb_client:
            await db_manager.mongodb_client.close()
        print("✅ Connections closed")
    except Exception as e:
        print(f"⚠️  Warning closing connections: {e}")

    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
