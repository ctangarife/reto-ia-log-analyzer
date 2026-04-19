/**
 * Servicio para gestión de Proyectos
 */
import api from './api'

export interface Project {
  id: string
  project_id: string // mismo que id, por compatibilidad
  workspace_id: string
  name: string
  slug: string
  description: string | null
  is_active: boolean
  role?: string // solo en lista: rol del usuario en este proyecto
  created_at: string | null
  updated_at: string | null
  created_by?: string | null // solo en detalle/creación
}

export interface ProjectCreate {
  name: string
  description?: string | null
  slug?: string | null
}

export interface ProjectUpdate {
  name?: string
  description?: string | null
  is_active?: boolean
}

export interface ProjectDeleteResponse {
  message: string
  project_id: string
}

/**
 * Obtener proyectos de un workspace
 */
export async function getWorkspaceProjects(workspaceId: string): Promise<Project[]> {
  try {
    const response = await api.get<Project[]>(`/workspaces/${workspaceId}/projects`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error('No autenticado')
    }
    if (error.response?.status === 404) {
      throw new Error('Workspace no encontrado')
    }
    throw new Error('Error al cargar proyectos')
  }
}

/**
 * Obtener un proyecto por ID
 */
export async function getProject(projectId: string): Promise<Project> {
  try {
    const response = await api.get<Project>(`/projects/${projectId}`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 404) {
      throw new Error('Proyecto no encontrado')
    } else if (error.response?.status === 403) {
      throw new Error('No tienes acceso a este proyecto')
    }
    throw new Error('Error al cargar el proyecto')
  }
}

/**
 * Crear un nuevo proyecto en un workspace
 */
export async function createProject(
  workspaceId: string,
  data: ProjectCreate
): Promise<Project> {
  try {
    const response = await api.post<Project>(`/workspaces/${workspaceId}/projects`, data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('No tienes permisos para crear proyectos')
    } else if (error.response?.status === 404) {
      throw new Error('Workspace no encontrado')
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail || 'Datos inválidos'
      throw new Error(detail)
    }
    throw new Error('Error al crear el proyecto')
  }
}

/**
 * Actualizar un proyecto
 */
export async function updateProject(
  projectId: string,
  data: ProjectUpdate
): Promise<Project> {
  try {
    const response = await api.put<Project>(`/projects/${projectId}`, data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('No tienes permisos para editar este proyecto')
    } else if (error.response?.status === 404) {
      throw new Error('Proyecto no encontrado')
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail || 'Datos inválidos'
      throw new Error(detail)
    }
    throw new Error('Error al actualizar el proyecto')
  }
}

/**
 * Desactivar un proyecto (soft delete)
 */
export async function deactivateProject(projectId: string): Promise<ProjectDeleteResponse> {
  try {
    const response = await api.delete<ProjectDeleteResponse>(`/projects/${projectId}`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 403) {
      throw new Error('No tienes permisos para desactivar este proyecto')
    } else if (error.response?.status === 404) {
      throw new Error('Proyecto no encontrado')
    }
    throw new Error('Error al desactivar el proyecto')
  }
}
