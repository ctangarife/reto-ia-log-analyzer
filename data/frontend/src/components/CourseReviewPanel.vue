<template>
  <div class="course-review-panel">
    <Card>
      <template #title>
        <div class="flex align-items-center gap-2">
          <i class="pi pi-file-edit"></i>
          <span>Cursos Pendientes de Revisión</span>
          <Badge v-if="pendingCourses.length > 0" :value="pendingCourses.length" severity="warning" />
        </div>
      </template>

      <template #content>
        <div v-if="loading" class="text-center p-4">
          <ProgressSpinner />
        </div>

        <div v-else-if="error" class="p-3">
          <InlineMessage severity="error">{{ error }}</InlineMessage>
        </div>

        <div v-else-if="pendingCourses.length === 0" class="text-center p-4">
          <i class="pi pi-check-circle text-green-500" style="font-size: 2rem;"></i>
          <p class="mt-2 text-color-secondary">No hay cursos pendientes de revisión</p>
        </div>

        <div v-else class="course-list">
          <div v-for="course in pendingCourses" :key="course.id" class="course-item p-3">
            <div class="flex justify-content-between align-items-start">
              <div class="flex-1">
                <h4>{{ course.name }}</h4>
                <p class="text-color-secondary text-sm">
                  Proyecto: {{ course.project_name }}
                </p>
                <p class="text-sm mt-2">{{ course.description }}</p>
                <small class="text-color-secondary">
                  Creado: {{ formatDate(course.created_at) }}
                  por {{ course.creator_email }}
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
                  icon="pi pi-check"
                  label="Aprobar"
                  severity="success"
                  @click="approveCourse(course)"
                  size="small"
                />
                <Button
                  icon="pi pi-times"
                  label="Rechazar"
                  severity="danger"
                  @click="rejectCourse(course)"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Course Content Preview Dialog -->
    <Dialog v-model:visible="showContentDialog" modal header="Contenido del Curso" :style="{ width: '80vw' }">
      <div v-if="loadingContent" class="flex justify-content-center p-4">
        <ProgressSpinner />
      </div>
      <div v-else-if="courseContent" class="course-content">
        <div class="course-header mb-3">
          <h3>{{ courseContent.course.name }}</h3>
          <p class="text-color-secondary">{{ courseContent.course.description }}</p>
          <div class="flex gap-2 mt-2">
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
                  <Column header="Contenido" style="width: 100px">
                    <template #body="slotProps">
                      <Button
                        icon="pi pi-eye"
                        size="small"
                        outlined
                        @click="previewLesson(slotProps.data)"
                        title="Ver contenido"
                      />
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
    <Dialog v-model:visible="showLessonDialog" modal :header="currentLesson?.title" :style="{ width: '60vw' }">
      <div v-if="currentLesson" class="lesson-content">
        <div class="lesson-metadata mb-3">
          <Chip :label="`Orden: ${currentLesson.lesson_order}`" size="small" class="mr-2" />
          <Chip v-if="currentLesson.is_dynamic" label="Dinámica" size="small" severity="warning" />
          <Chip v-else label="Estática" size="small" severity="secondary" />
        </div>
        <div class="lesson-body" v-html="renderMarkdown(currentLesson.content)"></div>
        <div v-if="currentLesson.exercise_data" class="exercise-info mt-3 p-3">
          <h5><i class="pi pi-pencil"></i> Ejercicio</h5>
          <pre class="text-sm">{{ JSON.stringify(currentLesson.exercise_data, null, 2) }}</pre>
        </div>
      </div>
    </Dialog>

    <!-- Approve Dialog -->
    <Dialog v-model:visible="showApproveDialog" header="Aprobar Curso" modal :style="{ width: '500px' }">
      <div class="formgroup">
        <label>Comentarios (opcional)</label>
        <Textarea
          v-model="approveComments"
          rows="3"
          placeholder="Añade comentarios sobre la aprobación..."
          class="w-full"
        />
      </div>

      <template #footer>
        <Button label="Cancelar" severity="secondary" @click="showApproveDialog = false" />
        <Button label="Aprobar" severity="success" @click="confirmApprove" />
      </template>
    </Dialog>

    <!-- Reject Dialog -->
    <Dialog v-model:visible="showRejectDialog" header="Rechazar Curso" modal :style="{ width: '500px' }">
      <div class="formgroup">
        <label>Motivo del rechazo *</label>
        <Textarea
          v-model="rejectReason"
          rows="3"
          placeholder="Explica por qué se rechaza el curso..."
          class="w-full"
        />
        <small v-if="!rejectReason" class="p-error">El motivo es obligatorio</small>
      </div>

      <template #footer>
        <Button label="Cancelar" severity="secondary" @click="showRejectDialog = false" />
        <Button label="Rechazar" severity="danger" @click="confirmReject" :disabled="!rejectReason" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import ProgressSpinner from 'primevue/progressspinner'
import InlineMessage from 'primevue/inlinemessage'
import Badge from 'primevue/badge'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Chip from 'primevue/chip'

import { courseGenerationService, type CourseContent } from '@/services/courseGenerationService'

interface Props {
  workspaceId: string
}

interface PendingCourse {
  id: string
  name: string  // Changed from 'title' to match backend v2
  description: string
  status: string
  created_at: string
  created_by: string
  creator_email: string
  project_name: string
  project_id: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  courseActioned: [action: 'approved' | 'rejected', courseId: string]
}>()

const loading = ref(false)
const error = ref('')
const pendingCourses = ref<PendingCourse[]>([])

const showApproveDialog = ref(false)
const showRejectDialog = ref(false)
const approveComments = ref('')
const rejectReason = ref('')
const selectedCourse = ref<PendingCourse | null>(null)

// Course preview dialog
const showContentDialog = ref(false)
const loadingContent = ref(false)
const courseContent = ref<CourseContent | null>(null)
const activeModuleIndex = ref<number[]>([])

// Lesson preview dialog
const showLessonDialog = ref(false)
const currentLesson = ref<CourseContent['lessons'][0] | null>(null)

const loadPendingCourses = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await courseGenerationService.getPendingCourses(props.workspaceId)
    pendingCourses.value = response.courses
  } catch (e: any) {
    error.value = e.message || 'Error al cargar cursos pendientes'
  } finally {
    loading.value = false
  }
}

const viewCourse = async (course: PendingCourse) => {
  showContentDialog.value = true
  loadingContent.value = true
  courseContent.value = null

  try {
    courseContent.value = await courseGenerationService.getCourseContent(course.id)
  } catch (e: any) {
    error.value = e.message || 'Error al cargar contenido del curso'
    showContentDialog.value = false
  } finally {
    loadingContent.value = false
  }
}

const previewLesson = (lesson: CourseContent['lessons'][0]) => {
  currentLesson.value = lesson
  showLessonDialog.value = true
}

const getModuleLessonCount = (moduleId: string) => {
  if (!courseContent.value) return 0
  return courseContent.value.lessons.filter(l => l.module_id === moduleId).length
}

const getModuleLessons = (moduleId: string) => {
  if (!courseContent.value) return []
  return courseContent.value.lessons.filter(l => l.module_id === moduleId)
}

const renderMarkdown = (content: string) => {
  if (!content) return ''
  return content
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
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

const approveCourse = (course: PendingCourse) => {
  selectedCourse.value = course
  approveComments.value = ''
  showApproveDialog.value = true
}

const confirmApprove = async () => {
  if (!selectedCourse.value) return

  try {
    await courseGenerationService.approveCourse(selectedCourse.value.id, {
      comments: approveComments.value || undefined
    })

    emit('courseActioned', 'approved', selectedCourse.value.id)
    await loadPendingCourses()
    showApproveDialog.value = false
  } catch (e: any) {
    error.value = e.message || 'Error al aprobar curso'
  }
}

const rejectCourse = (course: PendingCourse) => {
  selectedCourse.value = course
  rejectReason.value = ''
  showRejectDialog.value = true
}

const confirmReject = async () => {
  if (!selectedCourse.value) return

  try {
    await courseGenerationService.rejectCourse(selectedCourse.value.id, {
      comments: rejectReason.value
    })

    emit('courseActioned', 'rejected', selectedCourse.value.id)
    await loadPendingCourses()
    showRejectDialog.value = false
  } catch (e: any) {
    error.value = e.message || 'Error al rechazar curso'
  }
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadPendingCourses()
})

defineExpose({
  loadPendingCourses
})
</script>

<style scoped>
.course-review-panel {
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

.formgroup {
  margin-bottom: 1rem;
}

.formgroup label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.text-color-secondary {
  color: var(--text-color-secondary);
}

.text-sm {
  font-size: 0.875rem;
}

.mt-2 {
  margin-top: 0.5rem;
}

.mt-3 {
  margin-top: 1rem;
}

.mb-3 {
  margin-bottom: 1rem;
}

.p-error {
  color: var(--red-500);
}

.text-green-500 {
  color: var(--green-500);
}

.mr-2 {
  margin-right: 0.5rem;
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
</style>
