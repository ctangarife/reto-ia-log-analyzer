/**
 * Course Progress Service
 * Handles user-facing course progress and completion
 */
import api from './api'

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

export interface FinalExamAnswer {
  anomaly_id: string
  anomaly_type: string
  severity: string
  action: string
}

export interface FinalExamSubmissionRequest {
  lesson_id: string
  answers: FinalExamAnswer[]
}

export interface FinalExamAnswerResult {
  anomaly_id: string
  log_entry: string
  user_type: string
  correct_type: string
  user_severity: string
  correct_severity: string
  is_correct_type: boolean
  is_correct_severity: boolean
  points: number
}

export interface FinalExamValidationResponse {
  passed: boolean
  score: number
  passing_score: number
  feedback: string
  results: FinalExamAnswerResult[]
  can_retake: boolean
  certificate_earned: boolean
}

export interface CertificateResponse {
  certificate_url: string
  download_url: string
  issued_at: string
  badge_url: string
}

class CourseProgressService {
  private baseUrl = '/projects'

  /**
   * Get complete course progress for a project
   */
  async getProgress(projectId: string): Promise<CourseProgressResponse> {
    const response = await api.get(`${this.baseUrl}/${projectId}/course/progress`)
    return response.data
  }

  /**
   * Mark a lesson as completed
   */
  async completeLesson(projectId: string, lessonId: string, data?: LessonCompleteRequest): Promise<{ message: string; score?: number }> {
    const response = await api.post(`${this.baseUrl}/${projectId}/course/lessons/${lessonId}/complete`, data || {})
    return response.data
  }

  /**
   * Get exercises for a lesson
   */
  async getExercises(projectId: string, lessonId: string, count = 5): Promise<{ exercises: Exercise[] }> {
    const response = await api.get(`${this.baseUrl}/${projectId}/course/exercises`, {
      params: { lesson_id: lessonId, count: count }
    })
    return response.data
  }

  /**
   * Validate exercise answer
   */
  async validateExercise(projectId: string, data: ExerciseValidationRequest): Promise<ExerciseValidationResponse> {
    const response = await api.post(`${this.baseUrl}/${projectId}/course/exercises/validate`, data)
    return response.data
  }

  /**
   * Submit final exam with all answers
   */
  async submitFinalExam(projectId: string, data: FinalExamSubmissionRequest): Promise<FinalExamValidationResponse> {
    const response = await api.post(`${this.baseUrl}/${projectId}/course/final-exam/submit`, data)
    return response.data
  }

  /**
   * Get certificate data
   */
  async getCertificate(projectId: string): Promise<CertificateResponse> {
    const response = await api.get(`${this.baseUrl}/${projectId}/course/certificate`)
    return response.data
  }

  /**
   * Get badge URL
   */
  getBadgeUrl(projectId: string): string {
    return `/api/${this.baseUrl}/${projectId}/course/badge/current`
  }
}

export const courseProgressService = new CourseProgressService()
