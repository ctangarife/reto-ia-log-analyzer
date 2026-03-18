/**
 * Course Progress Service
 * Handles user-facing course progress and completion
 */

export interface CourseModule {
  id: string
  project_id: string
  module_order: number
  title: string
  description?: string
  completed_lessons: number
  total_lessons: number
  lessons: CourseLesson[]
}

export interface CourseLesson {
  id: string
  module_id: string
  lesson_order: number
  title: string
  content: string
  exercise_data?: Record<string, any>
  is_completed: boolean
  completed_at?: string
}

export interface CourseProgressResponse {
  course_id?: string
  course_name?: string
  project_id: string
  workspace_id?: string
  user_id: string
  modules: CourseModule[]
  total_modules: number
  completed_modules: number
  total_lessons: number
  completed_lessons: number
  progress_percentage: number
  is_completed: boolean
  completed_at?: string
  badge_earned: boolean
  certificate_url?: string
}

export interface LessonCompleteRequest {
  score?: number
}

export interface Exercise {
  anomaly_id: string
  log_entry: string
  score: number
  explanation: string
}

export interface ExerciseValidationRequest {
  lesson_id: string
  anomaly_id: string
  user_answer: Record<string, any>
}

export interface ExerciseValidationResponse {
  is_correct: boolean
  feedback: string
  correct_answer?: Record<string, any>
  explanation: string
}

export interface CertificateResponse {
  certificate_url: string
  download_url: string
  issued_at: string
  badge_url: string
}

class CourseProgressService {
  private baseUrl = '/api/projects'

  /**
   * Get complete course progress for a project
   */
  async getProgress(projectId: string): Promise<CourseProgressResponse> {
    const response = await fetch(`${this.baseUrl}/${projectId}/course/progress`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get course progress')
    return response.json()
  }

  /**
   * Mark a lesson as completed
   */
  async completeLesson(projectId: string, lessonId: string, data?: LessonCompleteRequest): Promise<{ message: string; score?: number }> {
    const response = await fetch(`${this.baseUrl}/${projectId}/course/lessons/${lessonId}/complete`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data || {})
    })
    if (!response.ok) throw new Error('Failed to complete lesson')
    return response.json()
  }

  /**
   * Get exercises for a lesson
   */
  async getExercises(projectId: string, lessonId: string, count = 5): Promise<{ exercises: Exercise[] }> {
    const response = await fetch(`${this.baseUrl}/${projectId}/course/exercises?lesson_id=${lessonId}&count=${count}`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get exercises')
    return response.json()
  }

  /**
   * Validate exercise answer
   */
  async validateExercise(projectId: string, data: ExerciseValidationRequest): Promise<ExerciseValidationResponse> {
    const response = await fetch(`${this.baseUrl}/${projectId}/course/exercises/validate`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to validate exercise')
    return response.json()
  }

  /**
   * Get certificate data
   */
  async getCertificate(projectId: string): Promise<CertificateResponse> {
    const response = await fetch(`${this.baseUrl}/${projectId}/course/certificate`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get certificate')
    return response.json()
  }

  /**
   * Get badge SVG
   */
  async getBadgeUrl(projectId: string): string {
    return `${this.baseUrl}/${projectId}/course/badge/current`
  }

  private getHeaders(): HeadersInit {
    const token = localStorage.getItem('auth_token')
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    }
  }
}

export const courseProgressService = new CourseProgressService()
