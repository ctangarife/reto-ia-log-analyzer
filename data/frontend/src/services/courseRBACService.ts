/**
 * Course RBAC Service
 * Manages course roles and permissions
 */

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
  private baseUrl = '/api/course-rbac'

  /**
   * Initialize course permissions and roles (admin only)
   */
  async initialize(): Promise<{
    status: string
    permissions_created: string[]
    roles_created: string[]
    message: string
  }> {
    const response = await fetch(`${this.baseUrl}/initialize`, {
      method: 'POST',
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to initialize course RBAC')
    return response.json()
  }

  /**
   * Get role and permission details
   */
  async getRoleDetails(): Promise<RoleDetailsResponse> {
    const response = await fetch(`${this.baseUrl}/roles/details`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get role details')
    return response.json()
  }

  /**
   * Assign a course role to a user
   */
  async assignRole(workspaceId: string, data: AssignRoleRequest): Promise<RoleAssignmentResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/roles/assign`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to assign role')
    return response.json()
  }

  /**
   * Remove a course role from a user
   */
  async removeRole(workspaceId: string, data: RemoveRoleRequest): Promise<RoleAssignmentResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/roles/remove`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to remove role')
    return response.json()
  }

  /**
   * Get all workspace members with course roles
   */
  async getWorkspaceMembers(workspaceId: string, roleFilter?: string): Promise<WorkspaceMembersResponse> {
    const url = roleFilter
      ? `${this.baseUrl}/workspaces/${workspaceId}/members?role=${roleFilter}`
      : `${this.baseUrl}/workspaces/${workspaceId}/members`

    const response = await fetch(url, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get workspace members')
    return response.json()
  }

  /**
   * Get user's course permissions
   */
  async getUserPermissions(workspaceId: string, userId: string): Promise<UserCoursePermissionsResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/users/${userId}/permissions`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get user permissions')
    return response.json()
  }

  /**
   * Get current user's course permissions
   */
  async getMyPermissions(workspaceId: string): Promise<UserCoursePermissionsResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/users/me/permissions`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get my permissions')
    return response.json()
  }

  /**
   * Check if current user has a specific permission
   */
  async checkPermission(workspaceId: string, permission: string): Promise<{ has_permission: boolean }> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/check-permission/${permission}`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to check permission')
    return response.json()
  }

  /**
   * Bulk assign roles to multiple users
   */
  async bulkAssign(workspaceId: string, data: BulkAssignRequest): Promise<BulkAssignResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/roles/bulk-assign`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to bulk assign roles')
    return response.json()
  }

  /**
   * Bulk remove roles from multiple users
   */
  async bulkRemove(workspaceId: string, data: BulkAssignRequest): Promise<BulkAssignResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/roles/bulk-remove`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to bulk remove roles')
    return response.json()
  }

  private getHeaders(): HeadersInit {
    const token = localStorage.getItem('auth_token')
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    }
  }
}

export const courseRBACService = new CourseRBACService()
