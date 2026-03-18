"""
Course RBAC Routes
API endpoints for managing course roles and permissions
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel

from middleware.auth_middleware import get_current_user, CurrentUser
from services.course_rbac_service import course_rbac_service
from services.permission_service import check_user_permission

router = APIRouter(prefix="/course-rbac", tags=["course-rbac"])


# ============================================
# Request/Response Models
# ============================================

class AssignRoleRequest(BaseModel):
    """Request to assign a course role to a user"""
    user_id: UUID
    role_name: str  # course_creator, course_reviewer, course_admin


class RemoveRoleRequest(BaseModel):
    """Request to remove a course role from a user"""
    user_id: UUID
    role_name: str


class RoleAssignmentResponse(BaseModel):
    """Response from role assignment/removal"""
    status: str
    message: str


class UserCoursePermissionsResponse(BaseModel):
    """Response with user's course permissions"""
    user_id: UUID
    workspace_id: UUID
    roles: List[dict]
    permissions: List[str]


class WorkspaceMembersResponse(BaseModel):
    """Response with workspace members having course roles"""
    workspace_id: UUID
    members: List[dict]


class RoleDetailsResponse(BaseModel):
    """Response with role and permission details"""
    roles: dict
    permissions: dict


class InitResponse(BaseModel):
    """Response from initialization"""
    status: str
    permissions_created: List[str]
    roles_created: List[str]
    message: str


# ============================================
# Admin Endpoints
# ============================================

@router.post("/initialize", response_model=InitResponse)
async def initialize_course_rbac(current_user = Depends(get_current_user)):
    """
    Initialize all course permissions and roles.
    Should be called once during setup.
    Requires super admin or workspace admin.
    """
    try:
        # Only super admin can initialize
        if not current_user.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="Only super admin can initialize course RBAC"
            )

        result = await course_rbac_service.initialize_course_permissions()
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles/details", response_model=RoleDetailsResponse)
async def get_role_details(current_user = Depends(get_current_user)):
    """Get details of all course roles and their permissions"""
    try:
        details = await course_rbac_service.get_course_role_details()
        return RoleDetailsResponse(**details)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Workspace Management Endpoints
# ============================================

@router.post("/workspaces/{workspace_id}/roles/assign", response_model=RoleAssignmentResponse)
async def assign_course_role(
    workspace_id: UUID,
    data: AssignRoleRequest,
    current_user = Depends(get_current_user)
):
    """
    Assign a course role to a user in a workspace.
    Requires workspace admin permission or user management permission.
    """
    try:
        # Check if user has permission to manage roles in workspace
        has_perm = await check_user_permission(
            current_user.user_id, workspace_id, "users:manage"
        )

        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="No permission to assign roles in this workspace"
            )

        result = await course_rbac_service.assign_course_role_to_user(
            data.user_id, workspace_id, data.role_name
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/roles/remove", response_model=RoleAssignmentResponse)
async def remove_course_role(
    workspace_id: UUID,
    data: RemoveRoleRequest,
    current_user = Depends(get_current_user)
):
    """
    Remove a course role from a user in a workspace.
    Requires workspace admin permission or user management permission.
    """
    try:
        # Check if user has permission to manage roles in workspace
        has_perm = await check_user_permission(
            current_user.user_id, workspace_id, "users:manage"
        )

        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="No permission to remove roles in this workspace"
            )

        result = await course_rbac_service.remove_course_role_from_user(
            data.user_id, workspace_id, data.role_name
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Query Endpoints
# ============================================

@router.get("/workspaces/{workspace_id}/members", response_model=WorkspaceMembersResponse)
async def get_workspace_course_members(
    workspace_id: UUID,
    role: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    Get all users with course roles in a workspace.
    Optionally filter by specific role.
    """
    try:
        # Check user has access to workspace
        has_perm = await check_user_permission(
            current_user.user_id, workspace_id, "workspaces:read"
        )

        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="No access to this workspace"
            )

        members = await course_rbac_service.get_workspace_course_members(
            workspace_id, role
        )

        return WorkspaceMembersResponse(
            workspace_id=workspace_id,
            members=members
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/users/{user_id}/permissions", response_model=UserCoursePermissionsResponse)
async def get_user_course_permissions(
    workspace_id: UUID,
    user_id: UUID,
    current_user = Depends(get_current_user)
):
    """
    Get all course roles and permissions for a user in a workspace.
    Users can view their own permissions; admins can view any user's.
    """
    try:
        # Users can view their own permissions
        if user_id != current_user.user_id:
            # Check if user has permission to view other users' permissions
            has_perm = await check_user_permission(
                current_user.user_id, workspace_id, "users:read"
            )

            if not has_perm and not current_user.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="No permission to view other users' permissions"
                )

        roles = await course_rbac_service.get_user_course_roles(user_id, workspace_id)
        permissions = await course_rbac_service.get_user_course_permissions(user_id, workspace_id)

        return UserCoursePermissionsResponse(
            user_id=user_id,
            workspace_id=workspace_id,
            roles=roles,
            permissions=permissions
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/users/me/permissions", response_model=UserCoursePermissionsResponse)
async def get_my_course_permissions(
    workspace_id: UUID,
    current_user = Depends(get_current_user)
):
    """Get current user's course roles and permissions in a workspace."""
    try:
        roles = await course_rbac_service.get_user_course_roles(
            current_user.user_id, workspace_id
        )
        permissions = await course_rbac_service.get_user_course_permissions(
            current_user.user_id, workspace_id
        )

        return UserCoursePermissionsResponse(
            user_id=current_user.user_id,
            workspace_id=workspace_id,
            roles=roles,
            permissions=permissions
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/check-permission/{permission}")
async def check_course_permission(
    workspace_id: UUID,
    permission: str,
    current_user = Depends(get_current_user)
):
    """
    Check if current user has a specific course permission in workspace.
    Returns boolean result.
    """
    try:
        has_perm = await course_rbac_service.check_course_permission(
            current_user.user_id, workspace_id, permission
        )

        return {
            "user_id": str(current_user.user_id),
            "workspace_id": str(workspace_id),
            "permission": permission,
            "has_permission": has_perm
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Bulk Operations
# ============================================

class BulkAssignRequest(BaseModel):
    """Request to assign roles to multiple users"""
    user_ids: List[UUID]
    role_name: str


@router.post("/workspaces/{workspace_id}/roles/bulk-assign")
async def bulk_assign_course_roles(
    workspace_id: UUID,
    data: BulkAssignRequest,
    current_user = Depends(get_current_user)
):
    """
    Assign a course role to multiple users in a workspace.
    Requires workspace admin permission.
    """
    try:
        # Check permission
        has_perm = await check_user_permission(
            current_user.user_id, workspace_id, "users:manage"
        )

        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="No permission to assign roles in this workspace"
            )

        results = []
        for user_id in data.user_ids:
            result = await course_rbac_service.assign_course_role_to_user(
                user_id, workspace_id, data.role_name
            )
            results.append({
                "user_id": str(user_id),
                "result": result
            })

        return {
            "workspace_id": str(workspace_id),
            "role_name": data.role_name,
            "total": len(data.user_ids),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BulkRemoveRequest(BaseModel):
    """Request to remove roles from multiple users"""
    user_ids: List[UUID]
    role_name: str


@router.post("/workspaces/{workspace_id}/roles/bulk-remove")
async def bulk_remove_course_roles(
    workspace_id: UUID,
    data: BulkRemoveRequest,
    current_user = Depends(get_current_user)
):
    """
    Remove a course role from multiple users in a workspace.
    Requires workspace admin permission.
    """
    try:
        # Check permission
        has_perm = await check_user_permission(
            current_user.user_id, workspace_id, "users:manage"
        )

        if not has_perm and not current_user.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="No permission to remove roles in this workspace"
            )

        results = []
        for user_id in data.user_ids:
            result = await course_rbac_service.remove_course_role_from_user(
                user_id, workspace_id, data.role_name
            )
            results.append({
                "user_id": str(user_id),
                "result": result
            })

        return {
            "workspace_id": str(workspace_id),
            "role_name": data.role_name,
            "total": len(data.user_ids),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
