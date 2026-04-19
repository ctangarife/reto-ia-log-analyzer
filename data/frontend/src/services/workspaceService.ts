/**
 * Servicio para gestión de Workspaces
 */
import api from './api'

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

export interface WorkspaceCreate {
  name: string
  description?: string | null
  slug?: string | null
}

export interface WorkspaceUpdate {
  name?: string
  description?: string | null
  is_active?: boolean
}

export interface WorkspaceDeleteResponse {
  message: string
  workspace_id: string
}

/**
 * Obtener todos los workspaces accesibles
 */
export async function getWorkspaces(): Promise<Workspace[]> {
  try {
    const response = await api.get<Workspace[]>('/workspaces')
    return response.data
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error('No autenticado')
    }
    throw new Error('Error al cargar workspaces')
  }
}

/**
 * Obtener un workspace por ID
 */
export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  try {
    const response = await api.get<Workspace>(`/workspaces/${workspaceId}`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 404) {
      throw new Error('Workspace no encontrado')
    } else if (error.response?.status === 403) {
      throw new Error('No tienes acceso a este workspace')
    }
    throw new Error('Error al cargar el workspace')
  }
}

/**
 * Crear un nuevo workspace (solo super admin)
 */
export async function createWorkspace(data: WorkspaceCreate): Promise<Workspace> {
  try {
    const response = await api.post<Workspace>('/workspaces', data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('No tienes permisos para crear workspaces')
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail || 'Datos inválidos'
      throw new Error(detail)
    }
    throw new Error('Error al crear el workspace')
  }
}

/**
 * Actualizar un workspace
 */
export async function updateWorkspace(
  workspaceId: string,
  data: WorkspaceUpdate
): Promise<Workspace> {
  try {
    const response = await api.put<Workspace>(`/workspaces/${workspaceId}`, data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('No tienes permisos para editar este workspace')
    } else if (error.response?.status === 404) {
      throw new Error('Workspace no encontrado')
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail || 'Datos inválidos'
      throw new Error(detail)
    }
    throw new Error('Error al actualizar el workspace')
  }
}

/**
 * Desactivar un workspace (soft delete)
 */
export async function deactivateWorkspace(workspaceId: string): Promise<WorkspaceDeleteResponse> {
  try {
    const response = await api.delete<WorkspaceDeleteResponse>(`/workspaces/${workspaceId}`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('No tienes permisos para desactivar este workspace')
    } else if (error.response?.status === 404) {
      throw new Error('Workspace no encontrado')
    }
    throw new Error('Error al desactivar el workspace')
  }
}
