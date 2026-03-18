/**
 * Course Generation Service
 * Handles dynamic course generation and workflow
 */

export interface CourseGenerateRequest {
  scope: 'project' | 'workspace'
  name?: string
}

export interface CourseGenerateResponse {
  course_id: string
  status: string
  modules_created: number
  lessons_created: number
  message: string
}

export interface ProjectAnalysis {
  project_id: string
  project_name: string
  total_logs: number
  total_anomalies: number
  anomaly_categories: Record<string, number>
  anomaly_severity_distribution: Record<string, number>
  log_formats: string[]
  date_range: { start: string; end: string }
  can_generate_course: boolean
  min_anomalies_required: number
  top_anomalies: Array<{
    id: string
    type: string
    score: number
    log_entry: string
  }>
}

export interface CoursePreviewResponse {
  analysis: ProjectAnalysis
  suggested_modules: string[]
}

export interface CourseUpdateRequest {
  title?: string
  description?: string
  status?: string
  scope?: string
  change_description?: string
}

export interface CourseUpdateResponse {
  course_id: string
  status: string
  message: string
}

export interface SubmitForReviewRequest {
  comments?: string
}

export interface ReviewActionRequest {
  comments?: string
}

export interface ReviewActionResponse {
  course_id: string
  status: string
  message: string
}

export interface PendingCourse {
  id: string
  title: string
  description: string
  status: string
  created_at: string
  created_by: string
  creator_email: string
  project_name: string
  project_id: string
}

export interface PendingCoursesResponse {
  workspace_id: string
  courses: PendingCourse[]
}

export interface CourseRegenerateRequest {
  change_description?: string
}

export interface CourseRegenerateResponse {
  new_course_id: string
  version_number: number
  modules_created: number
  lessons_created: number
  message: string
}

class CourseGenerationService {
  private baseUrl = '/api/course-generation'

  /**
   * Check if a course can be generated for the project
   */
  async canGenerate(projectId: string): Promise<{ can_generate: boolean; reason?: string }> {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}/can-generate`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to check if course can be generated')
    return response.json()
  }

  /**
   * Preview project data before generating course
   */
  async preview(projectId: string): Promise<CoursePreviewResponse> {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}/preview`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to preview course')
    return response.json()
  }

  /**
   * Generate a new course for the project
   */
  async generate(projectId: string, data: CourseGenerateRequest): Promise<CourseGenerateResponse> {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}/generate`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to generate course')
    return response.json()
  }

  /**
   * Regenerate course with new project data
   */
  async regenerate(projectId: string, data: CourseRegenerateRequest): Promise<CourseRegenerateResponse> {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}/regenerate`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to regenerate course')
    return response.json()
  }

  /**
   * Update a course
   */
  async updateCourse(courseId: string, data: CourseUpdateRequest): Promise<CourseUpdateResponse> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to update course')
    return response.json()
  }

  /**
   * Submit course for review
   */
  async submitForReview(courseId: string, data?: SubmitForReviewRequest): Promise<CourseUpdateResponse> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}/submit-for-review`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data || {})
    })
    if (!response.ok) throw new Error('Failed to submit course for review')
    return response.json()
  }

  /**
   * Get pending courses for review
   */
  async getPendingCourses(workspaceId: string): Promise<PendingCoursesResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/courses/pending`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get pending courses')
    return response.json()
  }

  /**
   * Get draft courses for the current user
   */
  async getDraftCourses(workspaceId: string): Promise<PendingCoursesResponse> {
    const response = await fetch(`${this.baseUrl}/workspaces/${workspaceId}/courses/draft`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get draft courses')
    return response.json()
  }

  /**
   * Get course content with modules and lessons (for previewing draft courses)
   */
  async getCourseContent(courseId: string): Promise<{
    course: {
      id: string
      title: string
      description: string
      status: string
      scope: string
      module_order: number
      created_at: string
      project_id: string | null
      workspace_id: string | null
    }
    modules: Array<{
      id: string
      module_order: number
      title: string
      description: string
      status: string
    }>
    lessons: Array<{
      id: string
      module_id: string
      lesson_order: number
      title: string
      content: string
      exercise_data: any
      is_dynamic: boolean
      module_title: string
      module_order: number
    }>
  }> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}/content`, {
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to get course content')
    return response.json()
  }

  /**
   * Delete a course
   */
  async deleteCourse(courseId: string): Promise<{ message: string; course_id: string }> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to delete course')
    return response.json()
  }

  /**
   * Approve a course
   */
  async approveCourse(courseId: string, data?: ReviewActionRequest): Promise<ReviewActionResponse> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}/approve`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data || {})
    })
    if (!response.ok) throw new Error('Failed to approve course')
    return response.json()
  }

  /**
   * Reject a course
   */
  async rejectCourse(courseId: string, data: ReviewActionRequest): Promise<ReviewActionResponse> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}/reject`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data)
    })
    if (!response.ok) throw new Error('Failed to reject course')
    return response.json()
  }

  /**
   * Publish a course
   */
  async publishCourse(courseId: string): Promise<ReviewActionResponse> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}/publish`, {
      method: 'POST',
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to publish course')
    return response.json()
  }

  /**
   * Archive a course
   */
  async archiveCourse(courseId: string): Promise<ReviewActionResponse> {
    const response = await fetch(`${this.baseUrl}/courses/${courseId}/archive`, {
      method: 'POST',
      headers: this.getHeaders()
    })
    if (!response.ok) throw new Error('Failed to archive course')
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

export const courseGenerationService = new CourseGenerationService()
