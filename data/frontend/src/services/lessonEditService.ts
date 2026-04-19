/**
 * Lesson Edit Service
 * Handles granular lesson editing with change tracking
 */
import api from './api'

export interface LessonUpdateRequest {
  title?: string
  content?: string
  exercise_data?: Record<string, any>
  is_minor_edit: boolean
  change_description?: string
}

export interface LessonUpdateResponse {
  lesson_id: string
  status: string
  message: string
  course_status?: string
}

export interface ExerciseUpdateRequest {
  exercise_data: Record<string, any>
  change_description?: string
}

export interface ExerciseUpdateResponse {
  lesson_id: string
  message: string
}

export interface LessonChange {
  id: string
  lesson_id: string
  changed_by: string
  changed_at: string
  change_type: 'content' | 'title' | 'exercise' | 'minor_edit'
  change_description?: string
  is_minor_edit: boolean
  changed_by_email?: string
  first_name?: string
  last_name?: string
}

export interface LessonHistoryResponse {
  lesson_id: string
  changes: LessonChange[]
}

export interface LessonDiffResponse {
  change: LessonChange
  diff: string[]
}

class LessonEditService {
  private baseUrl = '/lessons'

  /**
   * Get a single lesson
   */
  async getLesson(lessonId: string): Promise<any> {
    const response = await api.get(`${this.baseUrl}/${lessonId}`)
    return response.data
  }

  /**
   * Update a lesson
   */
  async updateLesson(lessonId: string, data: LessonUpdateRequest): Promise<LessonUpdateResponse> {
    const response = await api.put(`${this.baseUrl}/${lessonId}`, data)
    return response.data
  }

  /**
   * Update only the exercise data
   */
  async updateExercise(lessonId: string, data: ExerciseUpdateRequest): Promise<ExerciseUpdateResponse> {
    const response = await api.put(`${this.baseUrl}/${lessonId}/exercise`, data)
    return response.data
  }

  /**
   * Get lesson change history
   */
  async getHistory(lessonId: string, limit = 50): Promise<LessonHistoryResponse> {
    const response = await api.get(`${this.baseUrl}/${lessonId}/history`, {
      params: { limit }
    })
    return response.data
  }

  /**
   * Get diff for a specific change
   */
  async getDiff(lessonId: string, changeId: string): Promise<LessonDiffResponse> {
    const response = await api.get(`${this.baseUrl}/${lessonId}/history/${changeId}/diff`)
    return response.data
  }

  /**
   * Restore lesson to a previous version
   */
  async restoreVersion(lessonId: string, changeId: string): Promise<{ message: string }> {
    const response = await api.post(`${this.baseUrl}/${lessonId}/restore/${changeId}`)
    return response.data
  }
}

export const lessonEditService = new LessonEditService()
