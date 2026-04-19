/**
 * Utilidades para verificación de permisos
 */

export type PermissionModule = 'logs' | 'projects' | 'workspaces' | 'anomalies' | 'users' | 'monitoring'
export type PermissionAction = 'read' | 'write' | 'delete' | 'admin'

export interface UserPermission {
  module: PermissionModule
  action: PermissionAction
}

/**
 * Verifica si un permiso específico está en la lista de permisos
 */
export function hasPermission(
  permissions: string[],
  module: PermissionModule,
  action: PermissionAction
): boolean {
  // Verificar permiso específico
  if (permissions.includes(`${module}:${action}`)) {
    return true
  }

  // Verificar permiso admin del módulo
  if (permissions.includes(`${module}:admin`)) {
    return true
  }

  // Verificar permiso admin global
  if (permissions.includes('*:admin')) {
    return true
  }

  return false
}

/**
 * Verifica si el usuario puede procesar logs en un proyecto
 */
export function canProcessLogs(permissions: string[]): boolean {
  return hasPermission(permissions, 'logs', 'write')
}

/**
 * Verifica si el usuario puede ver reportes
 */
export function canViewReports(permissions: string[]): boolean {
  return hasPermission(permissions, 'logs', 'read')
}

/**
 * Verifica si el usuario puede eliminar recursos
 */
export function canDelete(permissions: string[], module: PermissionModule): boolean {
  return hasPermission(permissions, module, 'delete')
}

/**
 * Verifica si el usuario puede acceder al dashboard de monitoreo
 */
export function canAccessMonitoring(permissions: string[]): boolean {
  return hasPermission(permissions, 'monitoring', 'read')
}

/**
 * Filtra proyectos según permisos de escritura
 */
export function filterProjectsWithWriteAccess(
  projects: any[],
  projectPermissions: Record<string, string[]>
): any[] {
  return projects.filter(project => {
    const permissions = projectPermissions[project.project_id] || []
    return canProcessLogs(permissions)
  })
}
