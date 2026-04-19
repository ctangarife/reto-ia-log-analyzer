/**
 * Store de autenticación y permisos RBAC
 * SEGURIDAD: Token manejado vía httpOnly cookies (no en localStorage)
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { login, logout as apiLogout, getCurrentUser, getStoredUserInfo } from '../services/authService'
import api from '../services/api'
import { canProcessLogs, canViewReports, canAccessMonitoring, hasPermission } from '../utils/permissions'
import type { PermissionModule, PermissionAction } from '../utils/permissions'

export interface Workspace {
  id: string
  workspace_id: string // mismo que id, por compatibilidad
  name: string
  slug: string
  description: string | null
  is_active: boolean
  role?: string // solo en lista: rol del usuario en este workspace
  created_at: string | null
  updated_at: string | null
  created_by?: string | null // solo en detalle/creación
}

export interface Project {
  project_id: string
  name: string
  description?: string
  workspace_id: string
}

export interface ProjectPermissions {
  project_id: string
  permissions: string[]
  roles: Array<{
    role_id: string
    name: string
    permissions: string[]
  }>
}

export interface UserInfo {
  id: string
  username: string
  email: string
  is_super_admin: boolean
  full_name?: string
  is_active: boolean
  // Campos adicionales que el backend puede enviar
  last_login?: string | null
  created_at?: string
  updated_at?: string
}

export const useAuthStore = defineStore('auth', () => {
  // Estado
  const user = ref<UserInfo | null>(null)
  const workspaces = ref<Workspace[]>([])
  const projects = ref<Record<string, Project[]>>({}) // workspace_id -> projects
  const projectPermissions = ref<Record<string, string[]>>({}) // project_id -> permissions
  const coursePermissions = ref<Record<string, string[]>>({}) // workspace_id -> learning permissions
  const courseRoles = ref<Record<string, string[]>>({}) // workspace_id -> roles
  const isLoading = ref(false)
  const isInitialized = ref(false)
  const isAuthChecked = ref(false) // Indica si ya verificamos autenticación con el backend
  const selectedWorkspaceId = ref<string | null>(null)
  const selectedProjectId = ref<string | null>(null)

  // Computed
  const isLoggedIn = computed(() => {
    return user.value !== null && isAuthChecked.value
  })

  const isSuperAdmin = computed(() => user.value?.is_super_admin === true)

  const selectedWorkspace = computed(() => {
    if (!selectedWorkspaceId.value) return null
    return workspaces.value.find(w =>
      (w.workspace_id === selectedWorkspaceId.value) || (w.id === selectedWorkspaceId.value)
    ) || null
  })

  const selectedProject = computed(() => {
    if (!selectedProjectId.value || !selectedWorkspaceId.value) return null
    const workspaceProjects = projects.value[selectedWorkspaceId.value] || []
    return workspaceProjects.find(p => p.project_id === selectedProjectId.value) || null
  })

  const selectedProjectPermissions = computed(() => {
    if (!selectedProjectId.value) return []
    return projectPermissions.value[selectedProjectId.value] || []
  })

  // Acciones
  async function loginUser(username: string, password: string): Promise<void> {
    try {
      isLoading.value = true
      const userInfo = await login({ username, password })
      user.value = userInfo

      // Cargar datos del usuario
      await loadUserData()
    } catch (error) {
      console.error('Error en login:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function logoutUser(): Promise<void> {
    user.value = null
    workspaces.value = []
    projects.value = {}
    projectPermissions.value = {}
    coursePermissions.value = {}
    courseRoles.value = {}
    selectedWorkspaceId.value = null
    selectedProjectId.value = null
    isAuthChecked.value = false

    // Limpiar localStorage
    localStorage.removeItem('selected_workspace_id')
    localStorage.removeItem('selected_project_id')

    await apiLogout()
  }

  async function loadUserData(): Promise<void> {
    try {
      isLoading.value = true

      // Cargar usuario actual si no está cargado
      if (!user.value) {
        const currentUser = await getCurrentUser()
        if (currentUser) {
          user.value = currentUser
        } else {
          // No hay usuario autenticado
          isAuthChecked.value = true
          return
        }
      }

      isAuthChecked.value = true

      // Cargar workspaces
      await loadWorkspaces()

      // Si hay workspace seleccionado, cargar proyectos
      if (selectedWorkspaceId.value) {
        await loadProjects(selectedWorkspaceId.value)
      }
    } catch (error) {
      console.error('Error cargando datos del usuario:', error)
      isAuthChecked.value = true
    } finally {
      isLoading.value = false
    }
  }

  async function loadWorkspaces(): Promise<void> {
    try {
      const response = await api.get<Workspace[]>('/workspaces')
      // Filtrar solo workspaces activos para mostrar en el selector
      workspaces.value = response.data.filter(w => w.is_active)

      // Si no hay workspace seleccionado y hay workspaces disponibles, seleccionar el primero
      if (!selectedWorkspaceId.value && workspaces.value.length > 0) {
        selectedWorkspaceId.value = workspaces.value[0].workspace_id || workspaces.value[0].id
        await loadProjects(selectedWorkspaceId.value)
      }
    } catch (error) {
      console.error('Error cargando workspaces:', error)
      workspaces.value = []
    }
  }

  async function refreshWorkspaces(): Promise<void> {
    await loadWorkspaces()
  }

  async function loadProjects(workspaceId: string): Promise<void> {
    try {
      const response = await api.get<Project[]>(`/workspaces/${workspaceId}/projects`)
      projects.value[workspaceId] = response.data

      // Cargar permisos para cada proyecto
      for (const project of response.data) {
        await loadProjectPermissions(project.project_id)
      }

      // Cargar permisos de cursos del workspace
      await loadCoursePermissions(workspaceId)

      // Si no hay proyecto seleccionado y hay proyectos disponibles, seleccionar el primero
      if (!selectedProjectId.value && response.data.length > 0) {
        selectedProjectId.value = response.data[0].project_id
      }
    } catch (error) {
      console.error('Error cargando proyectos:', error)
      projects.value[workspaceId] = []
    }
  }

  async function loadProjectPermissions(projectId: string): Promise<void> {
    try {
      const response = await api.get<ProjectPermissions>(`/projects/${projectId}/permissions`)
      projectPermissions.value[projectId] = response.data.permissions
    } catch (error) {
      console.error('Error cargando permisos del proyecto:', error)
      projectPermissions.value[projectId] = []
    }
  }

  async function loadCoursePermissions(workspaceId: string): Promise<void> {
    try {
      const response = await api.get<{ permissions: string[]; roles: Array<{ id: string; name: string }> }>(
        `/workspaces/${workspaceId}/course-permissions`
      )
      coursePermissions.value[workspaceId] = response.data.permissions
      courseRoles.value[workspaceId] = response.data.roles?.map(r => r.name) || []
    } catch (error) {
      console.error('Error cargando permisos de cursos:', error)
      coursePermissions.value[workspaceId] = []
      courseRoles.value[workspaceId] = []
    }
  }

  function getCoursePermissions(workspaceId?: string): string[] {
    const targetWorkspaceId = workspaceId || selectedWorkspaceId.value
    if (!targetWorkspaceId) return []
    // Super admin tiene todos los permisos
    if (isSuperAdmin.value) {
      return [
        'courses:create',
        'courses:edit',
        'courses:edit_own',
        'courses:edit_lessons',
        'courses:minor_edit',
        'courses:review',
        'courses:delete',
        'courses:publish',
        'courses:view_draft',
        'courses:view_pending'
      ]
    }
    // Transformar learning:* a courses:* para compatibilidad
    const rawPerms = coursePermissions.value[targetWorkspaceId] || []
    return rawPerms.map((p: string) => p.replace('learning:', 'courses:'))
  }

  function getCourseRoles(workspaceId?: string): string[] {
    const targetWorkspaceId = workspaceId || selectedWorkspaceId.value
    if (!targetWorkspaceId) return []
    return courseRoles.value[targetWorkspaceId] || []
  }

  async function selectWorkspace(workspaceId: string): Promise<void> {
    selectedWorkspaceId.value = workspaceId
    selectedProjectId.value = null
    localStorage.setItem('selected_workspace_id', workspaceId)
    localStorage.removeItem('selected_project_id')
    await loadProjects(workspaceId)
  }

  function selectProject(projectId: string): void {
    selectedProjectId.value = projectId
    localStorage.setItem('selected_project_id', projectId)
    // Cargar permisos si no están cargados
    if (!projectPermissions.value[projectId]) {
      loadProjectPermissions(projectId)
    }
  }

  // Funciones helper de permisos
  function hasPermissionInProject(
    module: PermissionModule,
    action: PermissionAction,
    projectId?: string
  ): boolean {
    const targetProjectId = projectId || selectedProjectId.value
    if (!targetProjectId) return false

    // Super admin tiene todos los permisos
    if (isSuperAdmin.value) return true

    const permissions = projectPermissions.value[targetProjectId] || []
    return hasPermission(permissions, module, action)
  }

  function canProcessLogsInProject(projectId?: string): boolean {
    const targetProjectId = projectId || selectedProjectId.value
    if (!targetProjectId) return false

    if (isSuperAdmin.value) return true

    const permissions = projectPermissions.value[targetProjectId] || []
    return canProcessLogs(permissions)
  }

  function canViewReportsInProject(projectId?: string): boolean {
    const targetProjectId = projectId || selectedProjectId.value
    if (!targetProjectId) return false

    if (isSuperAdmin.value) return true

    const permissions = projectPermissions.value[targetProjectId] || []
    return canViewReports(permissions)
  }

  function canAccessMonitoringDashboard(): boolean {
    if (isSuperAdmin.value) return true

    // Verificar en todos los proyectos si tiene monitoring:read
    for (const permissions of Object.values(projectPermissions.value)) {
      if (canAccessMonitoring(permissions)) {
        return true
      }
    }

    return false
  }

  // Inicializar - verificar autenticación con el backend
  async function initialize(): Promise<void> {
    // Cargar usuario desde localStorage para usar mientras verificamos
    const storedUser = getStoredUserInfo()
    if (storedUser) {
      user.value = storedUser
    }

    // Cargar workspace y proyecto seleccionados desde localStorage
    const storedWorkspaceId = localStorage.getItem('selected_workspace_id')
    const storedProjectId = localStorage.getItem('selected_project_id')
    if (storedWorkspaceId) selectedWorkspaceId.value = storedWorkspaceId
    if (storedProjectId) selectedProjectId.value = storedProjectId

    // Verificar autenticación con el backend
    try {
      const currentUser = await getCurrentUser()
      if (currentUser) {
        user.value = currentUser
        await loadUserData()
      } else {
        // No hay sesión válida
        user.value = null
      }
    } catch (error) {
      // Error verificando sesión, limpiar estado
      console.error('Error verificando sesión:', error)
      user.value = null
    }

    // Marcar como inicializado
    isInitialized.value = true
    isAuthChecked.value = true
  }

  return {
    // Estado
    user,
    workspaces,
    projects,
    projectPermissions,
    coursePermissions,
    courseRoles,
    isLoading,
    isInitialized,
    isAuthChecked,
    selectedWorkspaceId,
    selectedProjectId,

    // Computed
    isLoggedIn,
    isSuperAdmin,
    selectedWorkspace,
    selectedProject,
    selectedProjectPermissions,

    // Acciones
    loginUser,
    logoutUser,
    loadUserData,
    loadWorkspaces,
    loadProjects,
    loadProjectPermissions,
    loadCoursePermissions,
    selectWorkspace,
    selectProject,

    // Helpers de permisos
    hasPermissionInProject,
    canProcessLogsInProject,
    canViewReportsInProject,
    canAccessMonitoringDashboard,
    getCoursePermissions,
    getCourseRoles,

    // Inicialización
    initialize,

    // Refresh
    refreshWorkspaces
  }
})
