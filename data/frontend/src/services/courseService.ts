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
  exercise_data?: ExerciseData
  is_completed: boolean
  completed_at?: string
}

export interface ExerciseData {
  type: 'quiz' | 'analysis' | 'project_anomalies' | 'final_exam'
  questions?: ExerciseQuestion[]
  log?: string
  dynamic?: boolean
  passing_score?: number
}

export interface ExerciseQuestion {
  id: string
  question: string
  options: string[]
  correct: number
}

export interface CourseProgress {
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

export interface ExerciseAttempt {
  lesson_id: string
  user_answer: Record<string, unknown>
}

export interface ExerciseValidation {
  is_correct: boolean
  feedback: string
  correct_answer?: Record<string, unknown>
  explanation?: string
}

export interface Certificate {
  certificate_url: string
  download_url: string
  issued_at: string
  badge_url: string
}

export const courseService = {
  async getProgress(projectId: string): Promise<CourseProgress> {
    const response = await api.get(`/projects/${projectId}/course/progress`)
    return response.data
  },

  async completeLesson(projectId: string, lessonId: string, score?: number): Promise<void> {
    await api.post(`/projects/${projectId}/course/lessons/${lessonId}/complete`, { score })
  },

  async getExercises(projectId: string, lessonId: string, count = 5): Promise<{ exercises: unknown[] }> {
    console.log('[courseService.getExercises] Called with:', { projectId, lessonId, count })
    try {
      const response = await api.get(`/projects/${projectId}/course/exercises`, {
        params: { lesson_id: lessonId, count }
      })
      console.log('[courseService.getExercises] Response:', response.data)
      return response.data
    } catch (error) {
      console.error('[courseService.getExercises] Error:', error)
      throw error
    }
  },

  async validateExercise(projectId: string, data: ExerciseAttempt): Promise<ExerciseValidation> {
    const response = await api.post(`/projects/${projectId}/course/exercises/validate`, data)
    return response.data
  },

  async getCertificate(projectId: string): Promise<Certificate> {
    const response = await api.get(`/projects/${projectId}/course/certificate`)
    return response.data
  }
}
