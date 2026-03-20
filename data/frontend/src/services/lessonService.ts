/**
 * Servicio para edición de lecciones
 */
import api from './api'

export interface LessonUpdateData {
  title?: string
  content?: string
  is_minor_edit: boolean
  change_description: string
}

export interface LessonHistoryEntry {
  id: string
  lesson_id: string
  title: string
  content: string
  change_description: string
  is_minor_edit: boolean
  created_at: string
  created_by: {
    id: string
    username: string
  }
}

export interface LessonHistoryResponse {
  lesson_id: string
  current: {
    id: string
    title: string
    content: string
  }
  history: LessonHistoryEntry[]
}

class LessonService {
  /**
   * Actualiza una lección
   */
  async updateLesson(lessonId: string, data: LessonUpdateData): Promise<void> {
    await api.put(`/lessons/${lessonId}`, data)
  }

  /**
   * Obtiene el historial de cambios de una lección
   */
  async getLessonHistory(lessonId: string): Promise<LessonHistoryResponse> {
    const response = await api.get<LessonHistoryResponse>(`/lessons/${lessonId}/history`)
    return response.data
  }

  /**
   * Restaura una versión anterior de una lección
   */
  async restoreLessonVersion(lessonId: string, changeId: string): Promise<void> {
    await api.post(`/lessons/${lessonId}/restore/${changeId}`)
  }
}

export const lessonService = new LessonService()
