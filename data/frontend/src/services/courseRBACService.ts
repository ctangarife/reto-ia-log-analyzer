/**
 * Course RBAC Service
 * Manages course roles and permissions
 */
import api from './api'

export interface AssignRoleRequest {
  user_id: string
  role_name: 'course_creator' | 'course_reviewer' | 'course_admin'
}

export interface RemoveRoleRequest {
  user_id: string
  role_name: string
}

export interface RoleAssignmentResponse {
  status: string
  message: string
}

export interface UserCoursePermissionsResponse {
  user_id: string
  workspace_id: string
  roles: Array<{
    name: string
    description: string
    is_system_role: boolean
    assigned_at: string
  }>
  permissions: string[]
}

export interface WorkspaceMember {
  id: string
  email: string
  first_name?: string
  last_name?: string
  role_name: string
  role_description: string
}

export interface WorkspaceMembersResponse {
  workspace_id: string
  members: WorkspaceMember[]
}

export interface RoleDetailsResponse {
  roles: Record<string, {
    description: string
    permissions: string[]
  }>
  permissions: Record<string, string>
}

export interface BulkAssignRequest {
  user_ids: string[]
  role_name: string
}

export interface BulkAssignResponse {
  workspace_id: string
  role_name: string
  total: number
  results: Array<{
    user_id: string
    result: RoleAssignmentResponse
  }>
}

class CourseRBACService {
  private baseUrl = '/course-rbac'

  /**
   * Initialize course permissions and roles (admin only)
   */
  async initialize(): Promise<{
    status: string
    permissions_created: string[]
    roles_created: string[]
    message: string
  }> {
    const response = await api.post(`${this.baseUrl}/initialize`)
    return response.data
  }

  /**
   * Get role and permission details
   */
  async getRoleDetails(): Promise<RoleDetailsResponse> {
    const response = await api.get(`${this.baseUrl}/roles/details`)
    return response.data
  }

  /**
   * Assign a course role to a user
   */
  async assignRole(workspaceId: string, data: AssignRoleRequest): Promise<RoleAssignmentResponse> {
    const response = await api.post(`${this.baseUrl}/workspaces/${workspaceId}/roles/assign`, data)
    return response.data
  }

  /**
   * Remove a course role from a user
   */
  async removeRole(workspaceId: string, data: RemoveRoleRequest): Promise<RoleAssignmentResponse> {
    const response = await api.post(`${this.baseUrl}/workspaces/${workspaceId}/roles/remove`, data)
    return response.data
  }

  /**
   * Get all workspace members with course roles
   */
  async getWorkspaceMembers(workspaceId: string, roleFilter?: string): Promise<WorkspaceMembersResponse> {
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/members`, {
      params: roleFilter ? { role: roleFilter } : undefined
    })
    return response.data
  }

  /**
   * Get user's course permissions
   */
  async getUserPermissions(workspaceId: string, userId: string): Promise<UserCoursePermissionsResponse> {
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/users/${userId}/permissions`)
    return response.data
  }

  /**
   * Get current user's course permissions
   */
  async getMyPermissions(workspaceId: string): Promise<UserCoursePermissionsResponse> {
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/users/me/permissions`)
    return response.data
  }

  /**
   * Check if current user has a specific permission
   */
  async checkPermission(workspaceId: string, permission: string): Promise<{ has_permission: boolean }> {
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/check-permission/${permission}`)
    return response.data
  }

  /**
   * Bulk assign roles to multiple users
   */
  async bulkAssign(workspaceId: string, data: BulkAssignRequest): Promise<BulkAssignResponse> {
    const response = await api.post(`${this.baseUrl}/workspaces/${workspaceId}/roles/bulk-assign`, data)
    return response.data
  }

  /**
   * Bulk remove roles from multiple users
   */
  async bulkRemove(workspaceId: string, data: BulkAssignRequest): Promise<BulkAssignResponse> {
    const response = await api.post(`${this.baseUrl}/workspaces/${workspaceId}/roles/bulk-remove`, data)
    return response.data
  }
}

export const courseRBACService = new CourseRBACService()
