/**
 * Course Store
 * Manages course-related state across the application
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useAuthStore } from './authStore'

export interface CourseModule {
  id: string
  project_id: string
  workspace_id?: string
  module_order: number
  title: string
  description?: string
  status: 'draft' | 'pending' | 'approved' | 'published' | 'archived'
  scope: 'project' | 'workspace'
  completed_lessons: number
  total_lessons: number
  lessons: CourseLesson[]
}

export interface CourseLesson {
  id: string
  module_id: string
  lesson_order: number
  title: string
  content?: string
  exercise_data?: any
  is_completed: boolean
  completed_at?: string
  is_dynamic?: boolean
}

export interface Course {
  id: string
  project_id: string
  project_name?: string
  title: string
  description?: string
  status: CourseModule['status']
  scope: CourseModule['scope']
  version_number: number
  modules: CourseModule[]
  total_lessons: number
  completed_lessons: number
  progress_percentage: number
  created_at: string
  published_at?: string
}

export const useCourseStore = defineStore('course', () => {
  // State
  const currentCourse = ref<Course | null>(null)
  const courses = ref<Course[]>([])
  const pendingCourses = ref<Course[]>([])
  const loading = ref(false)
  const error = ref('')

  // Computed - synced with authStore
  const authStore = useAuthStore()

  const userPermissions = computed(() => {
    if (authStore.isSuperAdmin) {
      return [
        'courses:create',
        'courses:edit',
        'courses:edit_own',
        'courses:edit_lessons',
        'courses:minor_edit',
        'courses:review',
        'courses:delete',
        'courses:publish',
        'courses:view_draft',
        'courses:view_pending'
      ]
    }
    // Transform learning: permissions to courses: permissions for compatibility
    const rawPerms = authStore.getCoursePermissions?.() || []
    return rawPerms.map((p: string) => p.replace('learning:', 'courses:'))
  })

  const userRoles = computed(() => {
    return authStore.getCourseRoles?.() || []
  })

  const canGenerateCourse = computed(() => {
    return userPermissions.value.includes('courses:create')
  })

  const canReviewCourses = computed(() => {
    return userPermissions.value.includes('courses:review')
  })

  const canEditCourses = computed(() => {
    return userPermissions.value.includes('courses:edit') ||
           userPermissions.value.includes('courses:edit_own')
  })

  const canMinorEdit = computed(() => {
    return userPermissions.value.includes('courses:minor_edit')
  })

  const isCourseCreator = computed(() => {
    return userRoles.value.includes('course_creator')
  })

  const isCourseReviewer = computed(() => {
    return userRoles.value.includes('course_reviewer')
  })

  const isCourseAdmin = computed(() => {
    return userRoles.value.includes('course_admin')
  })

  // Actions
  const setLoading = (value: boolean) => {
    loading.value = value
  }

  const setError = (value: string) => {
    error.value = value
  }

  const setCurrentCourse = (course: Course) => {
    currentCourse.value = course
  }

  const setCourses = (courseList: Course[]) => {
    courses.value = courseList
  }

  const setPendingCourses = (courseList: Course[]) => {
    pendingCourses.value = courseList
  }

  const clearCurrentCourse = () => {
    currentCourse.value = null
  }

  const addCourse = (course: Course) => {
    courses.value.push(course)
  }

  const updateCourse = (courseId: string, updates: Partial<Course>) => {
    const index = courses.value.findIndex(c => c.id === courseId)
    if (index !== -1) {
      courses.value[index] = { ...courses.value[index], ...updates }
    }
  }

  const removeCourse = (courseId: string) => {
    courses.value = courses.value.filter(c => c.id !== courseId)
  }

  const updateCourseStatus = (courseId: string, status: CourseModule['status']) => {
    const index = courses.value.findIndex(c => c.id === courseId)
    if (index !== -1) {
      courses.value[index].status = status
    }

    // Also update pending courses if needed
    const pendingIndex = pendingCourses.value.findIndex(c => c.id === courseId)
    if (pendingIndex !== -1) {
      if (status !== 'pending') {
        pendingCourses.value.splice(pendingIndex, 1)
      }
    }
  }

  const clearAll = () => {
    currentCourse.value = null
    courses.value = []
    pendingCourses.value = []
    error.value = ''
  }

  return {
    // State
    currentCourse,
    courses,
    pendingCourses,
    userPermissions,
    userRoles,
    loading,
    error,

    // Computed
    canGenerateCourse,
    canReviewCourses,
    canEditCourses,
    canMinorEdit,
    isCourseCreator,
    isCourseReviewer,
    isCourseAdmin,

    // Actions
    setLoading,
    setError,
    setCurrentCourse,
    setCourses,
    setPendingCourses,
    clearCurrentCourse,
    addCourse,
    updateCourse,
    removeCourse,
    updateCourseStatus,
    clearAll
  }
})
