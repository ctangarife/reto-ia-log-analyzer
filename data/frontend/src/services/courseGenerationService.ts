/**
 * Course Generation Service v2
 * Handles dynamic course generation and workflow
 *
 * New structure:
 * - courses: Main entity with name, status, version
 * - course_modules: Children of courses (4 fixed modules)
 * - course_lessons: Children of modules
 */
import api from './api'

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

export interface CourseLimitsCheck {
  can_create: boolean
  reason?: string
  current_counts: {
    published: number
    draft: number
    pending: number
    total: number
  }
}

export interface LogTypeInfo {
  format_type: string
  timestamp_format?: string
  has_structured_data: boolean
  typical_fields: string[]
  sample_entries: string[]
}

export interface LogSourceInfo {
  service_name: string
  log_count: number
  anomaly_count: number
  example_entries: string[]
}

export interface ProjectAnalysis {
  project_id: string
  project_name: string
  total_logs: number
  total_anomalies: number
  anomaly_categories: Record<string, number>
  anomaly_severity_distribution: Record<string, number>
  log_formats: string[]
  log_type_info?: LogTypeInfo
  log_sources: LogSourceInfo[]
  anomaly_density: number
  predominant_log_level?: string
  date_range: { start: string; end: string }
  can_generate_course: boolean
  min_anomalies_required: number
  top_anomalies: Array<{
    id: string
    type: string
    score: number
    log_entry: string
    explanation: string
  }>
}

export interface CoursePreviewResponse {
  analysis: ProjectAnalysis
  suggested_modules: string[]
}

export interface CourseUpdateRequest {
  name?: string  // Changed from 'title'
  description?: string
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
  archive_existing?: boolean  // For publish: whether to archive existing published course
}

export interface ReviewActionResponse {
  course_id: string
  status: string
  message: string
  archived_course_id?: string  // Present if a course was archived during publish
}

export interface PendingCourse {
  id: string
  name: string  // Changed from 'title'
  description: string
  status: string
  created_at: string
  created_by: string
  creator_email: string
  project_name: string
  project_id: string
  module_count?: number
  lesson_count?: number
  version_number?: number
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

export interface CourseModule {
  id: string
  module_order: number
  title: string
  description: string
}

export interface Lesson {
  id: string
  module_id: string
  lesson_order: number
  title: string
  content: string
  exercise_data: any
  is_dynamic: boolean
  module_title: string
  module_order: number
}

export interface CourseContent {
  course: {
    id: string
    name: string
    description: string
    status: string
    scope: string
    version_number: number
    created_at: string
    project_id: string
    workspace_id: string
  }
  modules: CourseModule[]
  lessons: Lesson[]
}

class CourseGenerationService {
  private baseUrl = '/course-generation'

  /**
   * Check if a course can be generated for the project
   */
  async canGenerate(projectId: string): Promise<{ can_generate: boolean; reason?: string; current_counts?: any }> {
    const response = await api.get(`${this.baseUrl}/projects/${projectId}/can-generate`)
    return response.data
  }

  /**
   * Get course limits for a project
   */
  async getCourseLimits(projectId: string, targetStatus: string = 'draft'): Promise<CourseLimitsCheck> {
    const response = await api.get(`${this.baseUrl}/projects/${projectId}/limits`, {
      params: { target_status: targetStatus }
    })
    return response.data
  }

  /**
   * Preview project data before generating course
   */
  async preview(projectId: string): Promise<CoursePreviewResponse> {
    const response = await api.get(`${this.baseUrl}/projects/${projectId}/preview`)
    return response.data
  }

  /**
   * Generate a new course for the project
   */
  async generate(projectId: string, data: CourseGenerateRequest): Promise<CourseGenerateResponse> {
    const response = await api.post(`${this.baseUrl}/projects/${projectId}/generate`, data)
    return response.data
  }

  /**
   * Regenerate course with new project data
   */
  async regenerate(projectId: string, data: CourseRegenerateRequest): Promise<CourseRegenerateResponse> {
    const response = await api.post(`${this.baseUrl}/projects/${projectId}/regenerate`, data)
    return response.data
  }

  /**
   * Update a course
   */
  async updateCourse(courseId: string, data: CourseUpdateRequest): Promise<CourseUpdateResponse> {
    const response = await api.put(`${this.baseUrl}/courses/${courseId}`, data)
    return response.data
  }

  /**
   * Submit course for review
   */
  async submitForReview(courseId: string, data?: SubmitForReviewRequest): Promise<CourseUpdateResponse> {
    const response = await api.post(`${this.baseUrl}/courses/${courseId}/submit-for-review`, data || {})
    return response.data
  }

  /**
   * Get pending courses for review
   */
  async getPendingCourses(workspaceId: string, projectId?: string): Promise<PendingCoursesResponse> {
    const params: any = {}
    if (projectId) params.project_id = projectId
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/courses/pending`, { params })
    return response.data
  }

  /**
   * Get draft courses for the current user
   */
  async getDraftCourses(workspaceId: string, projectId?: string): Promise<PendingCoursesResponse> {
    const params: any = {}
    if (projectId) params.project_id = projectId
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/courses/draft`, { params })
    return response.data
  }

  /**
   * Get course content with modules and lessons (for previewing draft courses)
   */
  async getCourseContent(courseId: string): Promise<CourseContent> {
    const response = await api.get(`${this.baseUrl}/courses/${courseId}/content`)
    return response.data
  }

  /**
   * Delete a course
   */
  async deleteCourse(courseId: string): Promise<{ message: string; course_id: string }> {
    const response = await api.delete(`${this.baseUrl}/courses/${courseId}`)
    return response.data
  }

  /**
   * Approve a course
   */
  async approveCourse(courseId: string, data?: ReviewActionRequest): Promise<ReviewActionResponse> {
    const response = await api.post(`${this.baseUrl}/courses/${courseId}/approve`, data || {})
    return response.data
  }

  /**
   * Reject a course
   */
  async rejectCourse(courseId: string, data: ReviewActionRequest): Promise<ReviewActionResponse> {
    const response = await api.post(`${this.baseUrl}/courses/${courseId}/reject`, data)
    return response.data
  }

  /**
   * Publish a course
   * If archive_existing is true, will archive any existing published course first
   */
  async publishCourse(courseId: string, archiveExisting: boolean = false): Promise<ReviewActionResponse> {
    const response = await api.post(`${this.baseUrl}/courses/${courseId}/publish`, {
      archive_existing: archiveExisting
    })
    return response.data
  }

  /**
   * Archive a course
   */
  async archiveCourse(courseId: string): Promise<ReviewActionResponse> {
    const response = await api.post(`${this.baseUrl}/courses/${courseId}/archive`)
    return response.data
  }

  /**
   * Get approved courses (ready to publish)
   */
  async getApprovedCourses(workspaceId: string, projectId?: string): Promise<PendingCoursesResponse> {
    const params: any = {}
    if (projectId) params.project_id = projectId
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/courses/approved`, { params })
    return response.data
  }

  /**
   * Get published courses
   */
  async getPublishedCourses(workspaceId: string): Promise<PendingCoursesResponse> {
    const response = await api.get(`${this.baseUrl}/workspaces/${workspaceId}/courses/published`)
    return response.data
  }

  /**
   * Get archived courses
   * Can filter by project_id or workspace_id
   */
  async getArchivedCourses(projectId?: string, workspaceId?: string): Promise<PendingCoursesResponse> {
    const params: any = {}
    if (projectId) params.project_id = projectId
    if (workspaceId) params.workspace_id = workspaceId

    const response = await api.get(`${this.baseUrl}/courses/archived`, { params })
    return response.data
  }

  /**
   * Republish an archived course
   * If another course is already published, it will be archived first
   */
  async republishCourse(courseId: string): Promise<ReviewActionResponse> {
    const response = await api.post(`${this.baseUrl}/courses/${courseId}/republish`)
    return response.data
  }
}

export const courseGenerationService = new CourseGenerationService()
