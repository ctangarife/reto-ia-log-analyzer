<template>
  <div class="course-management-widget">
    <!-- Generate Course Button -->
    <div v-if="canGenerateCourse" class="mb-3">
      <Button
        icon="pi pi-plus"
        label="Generar Curso"
        @click="openGenerateDialog"
        :loading="loading"
      />
    </div>

    <!-- Draft Courses Panel (for creators) -->
    <Card v-if="canGenerateCourse && workspaceId && draftCourses.length > 0" class="mb-3">
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-file-edit"></i>
          <span>Mis Borradores</span>
          <Badge :value="draftCourses.length" severity="info" />
        </div>
      </template>
      <template #content>
        <div class="course-list">
          <div v-for="course in draftCourses" :key="course.id" class="course-item p-3">
            <div class="flex justify-content-between align-items-start">
              <div class="flex-1">
                <h4>{{ course.name }}</h4>
                <p class="text-color-secondary text-sm">
                  Proyecto: {{ course.project_name }}
                </p>
                <div class="flex gap-2 mt-1">
                  <Badge :value="`${course.module_count || 0} módulos`" severity="secondary" />
                  <Badge :value="`${course.lesson_count || 0} lecciones`" severity="info" />
                </div>
                <small class="text-color-secondary">
                  Creado: {{ formatDate(course.created_at) }}
                </small>
              </div>
              <div class="flex gap-2">
                <Button
                  icon="pi pi-eye"
                  label="Ver"
                  severity="info"
                  outlined
                  @click="viewCourse(course)"
                  size="small"
                />
                <Button
                  icon="pi pi-send"
                  label="Enviar a Revisión"
                  severity="success"
                  @click="submitForReview(course)"
                  size="small"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  outlined
                  @click="deleteCourse(course)"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Pending Courses Review Panel (for reviewers) -->
    <CourseReviewPanel
      v-if="canReviewCourses && workspaceId"
      :workspaceId="workspaceId"
      @course-actioned="onCourseActioned"
      class="mb-3"
    />

    <!-- Approved Courses Panel (ready to publish) -->
    <Card v-if="workspaceId && approvedCourses.length > 0" class="mb-3">
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-check-circle"></i>
          <span>Aprobados</span>
          <Badge :value="approvedCourses.length" severity="info" />
        </div>
      </template>
      <template #content>
        <div class="course-list">
          <div v-for="course in approvedCourses" :key="course.id" class="course-item p-3">
            <div class="flex justify-content-between align-items-start">
              <div class="flex-1">
                <div class="flex align-items-center gap-2">
                  <h4>{{ course.name }}</h4>
                  <Badge value="Aprobado" severity="info" />
                </div>
                <p class="text-color-secondary text-sm">
                  Proyecto: {{ course.project_name }}
                </p>
                <p class="text-sm mt-2">{{ course.description }}</p>
                <small class="text-color-secondary">
                  Aprobado: {{ formatDate(course.reviewed_at) }}
                </small>
              </div>
              <div class="flex gap-2">
                <Button
                  icon="pi pi-eye"
                  label="Ver"
                  severity="secondary"
                  outlined
                  @click="viewCourse(course)"
                  size="small"
                />
                <Button
                  icon="pi pi-upload"
                  label="Publicar"
                  severity="success"
                  @click="publishCourse(course)"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Published Courses Panel -->
    <Card v-if="workspaceId && publishedCourses.length > 0" class="mb-3">
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-bookmark"></i>
          <span>Publicados</span>
          <Badge :value="publishedCourses.length" severity="success" />
        </div>
      </template>
      <template #content>
        <div class="course-list">
          <div v-for="course in publishedCourses" :key="course.id" class="course-item p-3">
            <div class="flex justify-content-between align-items-start">
              <div class="flex-1">
                <div class="flex align-items-center gap-2">
                  <h4>{{ course.name }}</h4>
                  <Badge value="Publicado" severity="success" />
                </div>
                <p class="text-color-secondary text-sm">
                  Proyecto: {{ course.project_name }}
                </p>
                <div class="flex gap-2 mt-1">
                  <Badge :value="`${course.module_count || 0} módulos`" severity="secondary" />
                  <Badge :value="`${course.lesson_count || 0} lecciones`" severity="info" />
                </div>
                <small class="text-color-secondary">
                  Publicado: {{ formatDate(course.published_at) }}
                </small>
              </div>
              <div class="flex gap-2">
                <Button
                  icon="pi pi-eye"
                  label="Ver Contenido"
                  severity="secondary"
                  outlined
                  @click="viewCourse(course)"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Generate Dialog -->
    <CourseGenerateDialog
      ref="generateDialog"
      :projectId="projectId"
      @generated="onCourseGenerated"
    />

    <!-- Role Manager Dialog -->
    <CourseRoleManager
      ref="roleManagerDialog"
      :workspaceId="workspaceId"
      :users="workspaceUsers"
      @role-assigned="onRoleAssigned"
      @role-removed="onRoleRemoved"
    />

    <!-- Course Content Preview Dialog -->
    <Dialog
      v-model:visible="showContentDialog"
      modal
      header="Contenido del Curso"
      :style="{ maxWidth: '1200px' }"
      :contentStyle="{ maxHeight: '80vh', overflow: 'auto' }"
    >
      <div v-if="loadingContent" class="flex justify-content-center p-4">
        <ProgressSpinner />
      </div>
      <div v-else-if="courseContent" class="course-content">
        <div class="course-header mb-3">
          <div class="flex justify-content-between align-items-start">
            <div class="flex-1">
              <!-- Course Name with Inline Edit -->
              <div class="flex align-items-center gap-2">
                <h3 v-if="!editingCourseName" @click="startEditingCourseName" class="editable hover-highlight">
                  {{ courseContent.course.name }}
                </h3>
                <InputText
                  v-else
                  v-model="editedCourseName"
                  @blur="saveCourseName"
                  @keyup.enter="saveCourseName"
                  @keyup.esc="cancelCourseNameEdit"
                  ref="courseNameInput"
                  class="course-name-input"
                />
                <Button
                  v-if="!editingCourseName && canEditCourse"
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  @click="startEditingCourseName"
                  title="Editar nombre"
                />
              </div>

              <!-- Course Description with Inline Edit -->
              <div class="flex align-items-start gap-2 mt-2">
                <p v-if="!editingCourseDesc" @click="startEditingCourseDesc" class="text-color-secondary editable hover-highlight m-0">
                  {{ courseContent.course.description || 'Sin descripción' }}
                </p>
                <Textarea
                  v-else
                  v-model="editedCourseDesc"
                  @blur="saveCourseDesc"
                  rows="2"
                  cols="60"
                  class="course-desc-input"
                  ref="courseDescInput"
                />
                <Button
                  v-if="!editingCourseDesc && canEditCourse"
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  @click="startEditingCourseDesc"
                  title="Editar descripción"
                />
              </div>
            </div>
          </div>

          <div class="flex gap-2 mt-3">
            <Badge :value="courseContent.course.status" :severity="getStatusSeverity(courseContent.course.status)" />
            <Badge :value="courseContent.course.scope" severity="secondary" />
            <Badge :value="`${courseContent.modules.length} módulos`" severity="info" />
            <Badge :value="`${courseContent.lessons.length} lecciones`" severity="info" />
          </div>
        </div>

        <!-- Modules with Lessons in Accordion -->
        <div v-if="courseContent.modules.length > 0" class="modules-section">
          <h4>Módulos del Curso</h4>
          <Accordion v-model:activeIndex="activeModuleIndex" multiple>
            <AccordionTab v-for="module in courseContent.modules" :key="module.id">
              <template #header>
                <div class="flex justify-content-between align-items-center w-full">
                  <div>
                    <span class="module-order">M{{ module.module_order }}</span>
                    <span class="module-title">{{ module.title }}</span>
                  </div>
                  <Chip :label="`${getModuleLessonCount(module.id)} lecciones`" size="small" />
                </div>
              </template>
              <div class="module-lessons">
                <div v-if="getModuleLessons(module.id).length === 0" class="text-center p-3 text-color-secondary">
                  <i class="pi pi-info-circle"></i> Este módulo no tiene lecciones aún.
                </div>
                <DataTable v-else :value="getModuleLessons(module.id)" stripedRows size="small">
                  <Column field="lesson_order" header="#" style="width: 50px" />
                  <Column field="title" header="Lección" />
                  <Column header="Tipo" style="width: 120px">
                    <template #body="slotProps">
                      <Chip v-if="slotProps.data.is_dynamic" label="Dinámica" size="small" severity="warning" />
                      <Chip v-else label="Estática" size="small" severity="secondary" />
                    </template>
                  </Column>
                  <Column header="Ejercicio" style="width: 80px">
                    <template #body="slotProps">
                      <i v-if="slotProps.data.exercise_data" class="pi pi-check text-green-500" title="Tiene ejercicio" />
                      <i v-else class="pi pi-times text-color-secondary" title="Sin ejercicio" />
                    </template>
                  </Column>
                  <Column header="Contenido" style="width: 150px">
                    <template #body="slotProps">
                      <div class="flex gap-1">
                        <Button
                          icon="pi pi-eye"
                          size="small"
                          outlined
                          @click="previewLesson(slotProps.data)"
                          title="Ver contenido"
                        />
                        <Button
                          icon="pi pi-pencil"
                          size="small"
                          outlined
                          severity="primary"
                          @click="editLesson(slotProps.data)"
                          title="Editar lección"
                        />
                      </div>
                    </template>
                  </Column>
                </DataTable>
              </div>
            </AccordionTab>
          </Accordion>
        </div>
        <div v-else class="text-center p-4 text-color-secondary">
          <i class="pi pi-info-circle"></i> Este curso no tiene módulos aún.
        </div>
      </div>
    </Dialog>

    <!-- Lesson Content Preview Dialog -->
    <Dialog
      v-model:visible="showLessonDialog"
      modal
      :header="currentLesson?.title"
      :style="{ maxWidth: '900px' }"
      :contentStyle="{ maxHeight: '70vh', overflow: 'auto' }"
    >
      <div v-if="currentLesson" class="lesson-content">
        <div class="flex justify-content-between align-items-center mb-3">
          <div class="lesson-metadata">
            <Chip :label="`Orden: ${currentLesson.lesson_order}`" size="small" class="mr-2" />
            <Chip v-if="currentLesson.is_dynamic" label="Dinámica" size="small" severity="warning" />
            <Chip v-else label="Estática" size="small" severity="secondary" />
          </div>
          <Button
            icon="pi pi-pencil"
            label="Editar lección"
            size="small"
            severity="primary"
            @click="editLesson(currentLesson)"
            outlined
          />
        </div>
        <div class="lesson-body" v-html="renderMarkdown(currentLesson.content)"></div>
        <div v-if="currentLesson.exercise_data" class="exercise-info mt-3 p-3">
          <h5><i class="pi pi-pencil"></i> Ejercicio</h5>
          <pre class="text-sm">{{ JSON.stringify(currentLesson.exercise_data, null, 2) }}</pre>
        </div>
      </div>
    </Dialog>

    <!-- Lesson Edit Dialog -->
    <LessonEditDialog
      v-model:visible="showLessonEditDialog"
      :lessonId="editingLessonId"
      @saved="onLessonEditSaved"
      @closed="editingLessonId = undefined"
    />

    <!-- Toast for notifications -->
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import Button from 'primevue/button'
import Toast from 'primevue/toast'
import Card from 'primevue/card'
import Badge from 'primevue/badge'
import Dialog from 'primevue/dialog'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'

import { useCourseStore } from '@/stores/courseStore'
import CourseGenerateDialog from './CourseGenerateDialog.vue'
import CourseReviewPanel from './CourseReviewPanel.vue'
import CourseRoleManager from './CourseRoleManager.vue'
import LessonEditDialog from './LessonEditDialog.vue'
import { useToast } from 'primevue/usetoast'
import { courseGenerationService, type CourseContent } from '@/services/courseGenerationService'
import DOMPurify from 'dompurify'

interface Props {
  projectId?: string
  workspaceId?: string
  workspaceUsers?: Array<{ id: string; email: string; first_name?: string; last_name?: string }>
}

interface DraftCourse {
  id: string
  name: string  // Changed from 'title' to match backend v2
  description: string
  status: string
  created_at: string
  project_name: string
  module_count?: number
  lesson_count?: number
  version_number?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  courseGenerated: []
}>()

const courseStore = useCourseStore()
const toast = useToast()

const generateDialog = ref()
const roleManagerDialog = ref()
const loading = ref(false)
const draftCourses = ref<DraftCourse[]>([])
const approvedCourses = ref<DraftCourse[]>([])
const publishedCourses = ref<DraftCourse[]>([])

// Course preview dialog
const showContentDialog = ref(false)
const loadingContent = ref(false)
const courseContent = ref<CourseContent | null>(null)
const activeModuleIndex = ref<number[]>([])

// Lesson preview dialog
const showLessonDialog = ref(false)
const currentLesson = ref<CourseContent['lessons'][0] | null>(null)

// Lesson edit dialog
const showLessonEditDialog = ref(false)
const editingLessonId = ref<string | undefined>(undefined)

// Course inline editing state
const editingCourseName = ref(false)
const editingCourseDesc = ref(false)
const editedCourseName = ref('')
const editedCourseDesc = ref('')
const courseNameInput = ref()
const courseDescInput = ref()

const canGenerateCourse = computed(() => courseStore.canGenerateCourse)
const canEditCourse = computed(() => courseStore.canGenerateCourse || courseStore.canReviewCourses)
const canReviewCourses = computed(() => courseStore.canReviewCourses)

const loadDraftCourses = async () => {
  if (!props.workspaceId) return

  try {
    const response = await courseGenerationService.getDraftCourses(props.workspaceId)
    draftCourses.value = response.courses
  } catch (e: any) {
    console.error('Error loading draft courses:', e)
  }
}

const loadApprovedCourses = async () => {
  if (!props.workspaceId) return

  try {
    const response = await courseGenerationService.getApprovedCourses(props.workspaceId)
    approvedCourses.value = response.courses
  } catch (e: any) {
    console.error('Error loading approved courses:', e)
  }
}

const loadPublishedCourses = async () => {
  if (!props.workspaceId) return

  try {
    const response = await courseGenerationService.getPublishedCourses(props.workspaceId)
    publishedCourses.value = response.courses
  } catch (e: any) {
    console.error('Error loading published courses:', e)
  }
}

const publishCourse = async (course: DraftCourse) => {
  try {
    await courseGenerationService.publishCourse(course.id, true) // archive existing
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Curso publicado', life: 3000 })
    await loadApprovedCourses()
    await loadPublishedCourses()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message || 'Error al publicar curso', life: 3000 })
  }
}

const viewCourse = async (course: DraftCourse) => {
  showContentDialog.value = true
  loadingContent.value = true
  courseContent.value = null

  try {
    const content = await courseGenerationService.getCourseContent(course.id)
    console.log('Course content loaded:', content)
    console.log('Modules count:', content?.modules?.length)
    console.log('Lessons count:', content?.lessons?.length)
    courseContent.value = content
  } catch (e: any) {
    console.error('Error loading course content:', e)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al cargar contenido del curso', life: 3000 })
    showContentDialog.value = false
  } finally {
    loadingContent.value = false
  }
}

const previewLesson = (lesson: CourseContent['lessons'][0]) => {
  currentLesson.value = lesson
  showLessonDialog.value = true
}

const editLesson = (lesson: CourseContent['lessons'][0]) => {
  editingLessonId.value = lesson.id
  showLessonEditDialog.value = true
}

const onLessonEditSaved = () => {
  // Reload course content to show updated lesson
  if (courseContent.value) {
    viewCourse({ id: courseContent.value.course.id } as any)
  }
}

const getModuleLessonCount = (moduleId: string) => {
  if (!courseContent.value) return 0
  const count = courseContent.value.lessons.filter(l => l.module_id === moduleId).length
  console.log(`Module ${moduleId} has ${count} lessons`)
  return count
}

const getModuleLessons = (moduleId: string) => {
  if (!courseContent.value) return []
  const lessons = courseContent.value.lessons.filter(l => l.module_id === moduleId)
  console.log(`Getting lessons for module ${moduleId}:`, lessons)
  return lessons
}

const renderMarkdown = (content: string) => {
  if (!content) return ''
  // Simple markdown-like replacements
  const rawHtml = content
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'br'],
    ALLOWED_ATTR: [],
    ALLOW_DATA_ATTR: false
  })
}

const getStatusSeverity = (status: string) => {
  switch (status) {
    case 'draft': return 'secondary'
    case 'pending': return 'warning'
    case 'approved': return 'info'
    case 'published': return 'success'
    case 'archived': return 'danger'
    default: return 'secondary'
  }
}

const submitForReview = async (course: DraftCourse) => {
  try {
    await courseGenerationService.submitForReview(course.id)
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Curso enviado a revisión', life: 3000 })
    await loadDraftCourses()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message || 'Error al enviar a revisión', life: 3000 })
  }
}

const deleteCourse = async (course: DraftCourse) => {
  if (!confirm(`¿Estás seguro de eliminar el curso "${course.name}"?`)) return

  try {
    await courseGenerationService.deleteCourse(course.id)
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Curso eliminado', life: 3000 })
    await loadDraftCourses()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: e.message || 'Error al eliminar curso', life: 3000 })
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const openGenerateDialog = () => {
  generateDialog.value?.open()
}

const openRoleManager = () => {
  roleManagerDialog.value?.open()
}

const onCourseGenerated = async () => {
  toast.add({ severity: 'success', summary: 'Éxito', detail: 'Curso generado exitosamente', life: 3000 })
  await loadDraftCourses()
  emit('courseGenerated')  // Notify parent to reload course progress
}

const onCourseActioned = () => {
  // Course was approved/rejected/published
  toast.add({ severity: 'success', summary: 'Éxito', detail: 'Acción completada', life: 3000 })
  // Reload all course lists
  loadDraftCourses()
  loadApprovedCourses()
  loadPublishedCourses()
}

const onRoleAssigned = () => {
  toast.add({ severity: 'success', summary: 'Éxito', detail: 'Rol asignado', life: 3000 })
}

const onRoleRemoved = () => {
  toast.add({ severity: 'success', summary: 'Éxito', detail: 'Rol removido', life: 3000 })
}

// Course inline editing methods
const startEditingCourseName = async () => {
  if (!courseContent.value) return
  editedCourseName.value = courseContent.value.course.name
  editingCourseName.value = true
  await nextTick()
  courseNameInput.value?.$el?.focus()
}

const saveCourseName = async () => {
  if (!courseContent.value || !editedCourseName.value.trim()) {
    cancelCourseNameEdit()
    return
  }

  try {
    await courseGenerationService.updateCourse(courseContent.value.course.id, {
      name: editedCourseName.value.trim()
    })
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Nombre actualizado', life: 3000 })
    await reloadCourseContent()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al actualizar nombre', life: 3000 })
  }
  editingCourseName.value = false
}

const cancelCourseNameEdit = () => {
  editingCourseName.value = false
  editedCourseName.value = ''
}

const startEditingCourseDesc = async () => {
  if (!courseContent.value) return
  editedCourseDesc.value = courseContent.value.course.description || ''
  editingCourseDesc.value = true
  await nextTick()
  courseDescInput.value?.$el?.focus()
}

const saveCourseDesc = async () => {
  if (!courseContent.value) return

  try {
    await courseGenerationService.updateCourse(courseContent.value.course.id, {
      description: editedCourseDesc.value.trim()
    })
    toast.add({ severity: 'success', summary: 'Éxito', detail: 'Descripción actualizada', life: 3000 })
    await reloadCourseContent()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al actualizar descripción', life: 3000 })
  }
  editingCourseDesc.value = false
}

const reloadCourseContent = async () => {
  if (!courseContent.value) return
  try {
    const content = await courseGenerationService.getCourseContent(courseContent.value.course.id)
    courseContent.value = content
  } catch (e: any) {
    console.error('Error reloading course content:', e)
  }
}

// Load draft courses when workspace changes or on mount
watch(() => props.workspaceId, () => {
  if (props.workspaceId) {
    loadDraftCourses()
    loadApprovedCourses()
    loadPublishedCourses()
  }
}, { immediate: true })

onMounted(() => {
  if (props.workspaceId) {
    loadDraftCourses()
    loadApprovedCourses()
    loadPublishedCourses()
  }
})

// Expose methods for parent components
defineExpose({
  openGenerateDialog,
  openRoleManager,
  loadDraftCourses
})
</script>

<style scoped>
.course-management-widget {
  margin-bottom: 1rem;
}

.mb-3 {
  margin-bottom: 1rem;
}

.course-list {
  max-height: 400px;
  overflow-y: auto;
}

.course-item {
  border-bottom: 1px solid var(--surface-200);
}

.course-item:last-child {
  border-bottom: none;
}

.text-color-secondary {
  color: var(--text-color-secondary);
}

.text-sm {
  font-size: 0.875rem;
}

.course-content {
  padding: 0.5rem;
}

.course-header h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary-color);
}

.course-header p {
  margin: 0;
}

.modules-section h4 {
  margin-top: 0;
  color: var(--text-color-secondary);
}

.module-order {
  font-weight: bold;
  color: var(--primary-color);
  margin-right: 0.5rem;
}

.module-title {
  font-weight: 500;
}

.module-lessons {
  padding: 0.5rem 0;
}

.lessons-section h4 {
  margin-top: 0;
  color: var(--text-color-secondary);
}

.lesson-content .lesson-metadata {
  display: flex;
  gap: 0.5rem;
}

.lesson-body {
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}

.lesson-body h4 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.lesson-body h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
}

.lesson-body h2 {
  margin-top: 2rem;
  margin-bottom: 0.75rem;
}

.exercise-info {
  background: var(--surface-100);
  border-radius: 8px;
  border-left: 4px solid var(--primary-color);
}

.exercise-info pre {
  background: var(--surface-200);
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}

.mr-2 {
  margin-right: 0.5rem;
}

.mt-3 {
  margin-top: 1rem;
}

.text-green-500 {
  color: var(--green-500);
}

/* Inline editing styles */
.editable {
  cursor: pointer;
  transition: background-color 0.2s;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  display: inline-block;
}

.editable:hover,
.hover-highlight:hover {
  background-color: var(--surface-100);
}

.course-header h3.editable {
  margin: 0;
  display: inline-block;
}

.course-name-input {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
  padding: 0.25rem 0.5rem;
}

.course-desc-input {
  resize: both;
  min-height: 60px;
}

.flex-1 {
  flex: 1;
}

.hover-highlight {
  border-radius: 4px;
}

.mt-2 {
  margin-top: 0.5rem;
}
</style>
