<template>
  <div class="draft-courses-panel">
    <!-- Generate Course Button -->
    <div class="generate-section">
      <Button
        icon="pi pi-plus"
        label="Generar Nuevo Curso"
        @click="openGenerateDialog"
        :loading="generating"
        size="large"
      />
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando borradores...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="courses.length === 0" class="empty-state">
      <i class="pi pi-file-edit" style="font-size: 3rem; color: #cbd5e1;"></i>
      <h3>No hay borradores</h3>
      <p>No tienes cursos en estado de borrador.</p>
      <p class="hint">Usa el botón de arriba para generar un nuevo curso.</p>
    </div>

    <!-- Courses list -->
    <div v-else class="courses-list">
      <Card
        v-for="course in courses"
        :key="course.id"
        class="course-card"
      >
        <template #title>
          <div class="course-title">
            <h3>{{ course.name }}</h3>
            <Tag value="Borrador" severity="secondary" />
          </div>
        </template>
        <template #subtitle>
          <p class="project-name">Proyecto: {{ course.project_name }}</p>
        </template>
        <template #content>
          <p class="course-description">{{ course.description || 'Sin descripción' }}</p>
          <div class="course-meta">
            <Chip :label="`${course.module_count || 0} módulos`" size="small" class="mr-2" />
            <Chip :label="`${course.lesson_count || 0} lecciones`" size="small" />
          </div>
          <small class="created-date">
            <i class="pi pi-calendar"></i>
            Creado: {{ formatDate(course.created_at) }}
          </small>
        </template>
        <template #footer>
          <div class="course-actions">
            <Button
              icon="pi pi-eye"
              label="Ver Contenido"
              severity="secondary"
              outlined
              @click="viewCourse(course)"
              size="small"
            />
            <Button
              icon="pi pi-pencil"
              label="Editar"
              severity="info"
              outlined
              @click="editCourse(course)"
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
        </template>
      </Card>
    </div>

    <!-- Course Content Dialog -->
    <Dialog v-model:visible="showContentDialog" modal header="Contenido del Curso" :style="{ width: '90vw' }" :contentStyle="{ maxHeight: '70vh', overflow: 'auto' }">
      <div v-if="loadingContent" class="flex justify-content-center p-4">
        <ProgressSpinner />
      </div>
      <div v-else-if="courseContent" class="course-content">
        <div class="course-header mb-3">
          <h3>{{ courseContent.course.name }}</h3>
          <p class="text-color-secondary">{{ courseContent.course.description }}</p>
          <div class="flex gap-2 mt-2 flex-wrap">
            <Tag :value="courseContent.course.status" severity="secondary" />
            <Tag :value="courseContent.course.scope" severity="info" />
            <Chip :label="`${courseContent.modules.length} módulos`" size="small" />
            <Chip :label="`${courseContent.lessons.length} lecciones`" size="small" />
          </div>
        </div>

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
            <DataTable
              :value="getModuleLessons(module.id)"
              stripedRows
              size="small"
              v-model:selection="selectedLesson"
              selectionMode="single"
              @row-select="viewLessonContent"
              @row-unselect="clearLessonContent"
            >
              <Column selectionMode="single" headerStyle="width: 3rem"></Column>
              <Column field="lesson_order" header="#" style="width: 50px" />
              <Column field="title" header="Lección" />
              <Column header="Tipo" style="width: 120px">
                <template #body="slotProps">
                  <Chip v-if="slotProps.data.is_dynamic" label="Dinámica" size="small" severity="warning" />
                  <Chip v-else label="Estática" size="small" severity="secondary" />
                </template>
              </Column>
            </DataTable>
          </AccordionTab>
        </Accordion>

        <!-- Lesson Content Preview -->
        <div v-if="selectedLessonContent" class="lesson-content-preview mt-4 p-3 surface-ground border-round">
          <div class="flex justify-content-between align-items-center mb-3">
            <h4 class="m-0">{{ selectedLessonContent.title }}</h4>
            <Button
              icon="pi pi-pencil"
              label="Editar Lección"
              size="small"
              text
              @click="openLessonEdit(selectedLessonContent)"
            />
          </div>
          <Divider />
          <div class="lesson-content-text" v-html="renderMarkdown(selectedLessonContent.content)"></div>
        </div>
      </div>
    </Dialog>

    <!-- Lesson Edit Dialog -->
    <Dialog
      v-model:visible="showLessonEditDialog"
      modal
      header="Editar Lección"
      :style="{ maxWidth: '1400px', width: '95vw', height: '90vh' }"
      :contentStyle="{ height: 'calc(90vh - 100px)', overflow: 'auto' }"
    >
      <div v-if="editingLesson" class="lesson-edit-form">
        <div class="field">
          <label for="lesson-title">Título</label>
          <InputText id="lesson-title" v-model="editingLesson.title" class="w-full" />
        </div>

        <div class="field content-field">
          <label for="lesson-content">Contenido (Markdown)</label>
          <Textarea
            id="lesson-content"
            v-model="editingLesson.content"
            class="w-full markdown-textarea"
            autoResize
          />
          <small class="text-color-secondary mt-2">
            Puedes usar Markdown para dar formato. Soporta: **negrita**, *cursiva*, # encabezados, - listas, etc.
          </small>
        </div>

        <div class="field">
          <label>Opciones de edición</label>
          <div class="flex align-items-center gap-3">
            <Checkbox v-model="isMinorEdit" inputId="minor-edit" binary />
            <label for="minor-edit">Edición menor (no requiere reaprobación)</label>
          </div>
          <small class="text-color-secondary block mt-1">
            Las ediciones menores se limitan a cambios de menos del 10% del contenido o máximo 500 caracteres.
          </small>
        </div>

        <div class="field">
          <label for="change-description">Descripción del cambio</label>
          <InputText
            id="change-description"
            v-model="changeDescription"
            placeholder="Describe qué modificaste en esta lección"
            class="w-full"
          />
        </div>

        <!-- Preview -->
        <div class="field">
          <label>Vista Previa</label>
          <div class="preview-box p-3 surface-ground border-round" v-html="renderMarkdown(editingLesson?.content || '')"></div>
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" text @click="showLessonEditDialog = false" />
        <Button
          label="Guardar Cambios"
          @click="saveLessonEdit"
          :loading="savingLesson"
          :disabled="!changeDescription?.trim()"
        />
      </template>
    </Dialog>

    <!-- Course Generate Dialog -->
    <CourseGenerateDialog
      ref="generateDialog"
      :projectId="authStore.selectedProjectId"
      @generated="onCourseGenerated"
    />

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { courseGenerationService, type CourseContent, type CourseModule, type Lesson } from '../services/courseGenerationService'
import { lessonService } from '../services/lessonService'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Dialog from 'primevue/dialog'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Divider from 'primevue/divider'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '../stores/authStore'
import CourseGenerateDialog from './CourseGenerateDialog.vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'

interface Props {
  workspaceId?: string
  projectId?: string
}

interface Course {
  id: string
  name: string
  description: string
  status: string
  created_at: string
  project_name: string
  project_id: string
  module_count?: number
  lesson_count?: number
  version_number?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  courseSelected: [course: Course]
  courseActioned: []
  courseGenerated: []
}>()

const authStore = useAuthStore()
const toast = useToast()
const loading = ref(false)
const generating = ref(false)
const courses = ref<Course[]>([])
const showContentDialog = ref(false)
const loadingContent = ref(false)
const courseContent = ref<CourseContent | null>(null)
const activeModuleIndex = ref<number[]>([])
const generateDialog = ref()

// Lesson selection and editing
const selectedLesson = ref<Lesson | null>(null)
const selectedLessonContent = ref<Lesson | null>(null)
const showLessonEditDialog = ref(false)
const editingLesson = ref<Lesson | null>(null)
const isMinorEdit = ref(false)
const changeDescription = ref('')
const savingLesson = ref(false)

// Markdown rendering with DOMPurify
function renderMarkdown(content: string): string {
  if (!content) return '<p class="text-color-secondary">Sin contenido</p>'
  const rawHtml = marked(content)
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'br', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote', 'a', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
    ALLOWED_ATTR: ['href', 'title', 'class', 'target'],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false
  })
}

async function loadCourses() {
  if (!props.workspaceId) return

  loading.value = true
  try {
    const response = await courseGenerationService.getDraftCourses(props.workspaceId, props.projectId)
    courses.value = response.courses
  } catch (e: any) {
    console.error('Error loading draft courses:', e)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al cargar borradores',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function viewCourse(course: Course) {
  showContentDialog.value = true
  loadingContent.value = true
  courseContent.value = null
  selectedLessonContent.value = null
  selectedLesson.value = null

  courseGenerationService.getCourseContent(course.id)
    .then(content => {
      courseContent.value = content
      // Open first module by default
      if (content.modules.length > 0) {
        activeModuleIndex.value = [0]
      }
    })
    .catch(e => {
      console.error('Error loading course content:', e)
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'Error al cargar contenido del curso',
        life: 3000
      })
      showContentDialog.value = false
    })
    .finally(() => {
      loadingContent.value = false
    })
}

function viewLessonContent() {
  if (selectedLesson.value) {
    selectedLessonContent.value = selectedLesson.value
  }
}

function clearLessonContent() {
  selectedLessonContent.value = null
}

function editCourse(course: Course) {
  // Open the content dialog for editing
  viewCourse(course)
}

function openLessonEdit(lesson: Lesson) {
  editingLesson.value = { ...lesson }
  isMinorEdit.value = false
  changeDescription.value = ''
  showLessonEditDialog.value = true
}

async function saveLessonEdit() {
  if (!editingLesson.value || !changeDescription.value.trim()) {
    toast.add({
      severity: 'warn',
      summary: 'Advertencia',
      detail: 'Por favor describe los cambios realizados',
      life: 3000
    })
    return
  }

  savingLesson.value = true
  try {
    await lessonService.updateLesson(
      editingLesson.value.id,
      {
        title: editingLesson.value.title,
        content: editingLesson.value.content,
        is_minor_edit: isMinorEdit.value,
        change_description: changeDescription.value
      }
    )

    toast.add({
      severity: 'success',
      summary: 'Éxito',
      detail: isMinorEdit.value ? 'Edición menor guardada' : 'Lección actualizada (pendiente aprobación)',
      life: 3000
    })

    // Refresh the course content
    if (courseContent.value?.course.id) {
      const courseId = courseContent.value.course.id
      courseGenerationService.getCourseContent(courseId)
        .then(content => {
          courseContent.value = content
        })
    }

    showLessonEditDialog.value = false
  } catch (e: any) {
    console.error('Error saving lesson:', e)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: e.message || 'Error al guardar la lección',
      life: 3000
    })
  } finally {
    savingLesson.value = false
  }
}

function submitForReview(course: Course) {
  courseGenerationService.submitForReview(course.id)
    .then(() => {
      toast.add({
        severity: 'success',
        summary: 'Éxito',
        detail: 'Curso enviado a revisión',
        life: 3000
      })
      emit('courseActioned')
      loadCourses()
      showContentDialog.value = false
    })
    .catch(e => {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: e.message || 'Error al enviar a revisión',
        life: 3000
      })
    })
}

function deleteCourse(course: Course) {
  if (!confirm(`¿Eliminar el borrador "${course.name}"?`)) return

  courseGenerationService.deleteCourse(course.id)
    .then(() => {
      toast.add({
        severity: 'success',
        summary: 'Éxito',
        detail: 'Borrador eliminado',
        life: 3000
      })
      loadCourses()
      showContentDialog.value = false
    })
    .catch(e => {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: e.message || 'Error al eliminar borrador',
        life: 3000
      })
    })
}

function getModuleLessonCount(moduleId: string) {
  if (!courseContent.value) return 0
  return courseContent.value.lessons.filter(l => l.module_id === moduleId).length
}

function getModuleLessons(moduleId: string) {
  if (!courseContent.value) return []
  return courseContent.value.lessons
    .filter(l => l.module_id === moduleId)
    .sort((a, b) => a.lesson_order - b.lesson_order)
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function openGenerateDialog() {
  generateDialog.value?.open()
}

function onCourseGenerated() {
  toast.add({
    severity: 'success',
    summary: 'Éxito',
    detail: 'Curso generado exitosamente',
    life: 3000
  })
  loadCourses()
  emit('courseGenerated')
}

// Solo cargar cuando ambos estén disponibles
watch(() => [props.workspaceId, props.projectId], () => {
  if (props.workspaceId) {
    loadCourses()
  }
}, { immediate: true })

// Expose loadCourses for parent component to call
defineExpose({
  loadCourses
})
</script>

<style scoped>
.draft-courses-panel {
  padding: 1rem;
}

.generate-section {
  display: flex;
  justify-content: center;
  padding: 1.5rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 1.5rem;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  text-align: center;
}

.empty-state h3 {
  margin: 0;
  color: #475569;
}

.empty-state p {
  margin: 0;
  color: #94a3b8;
}

.empty-state .hint {
  font-size: 0.9rem;
  color: #cbd5e1;
  font-style: italic;
}

.courses-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.course-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.course-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.course-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.course-title h3 {
  margin: 0;
  font-size: 1.1rem;
}

.project-name {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.course-description {
  margin: 0.5rem 0;
  color: #475569;
  line-height: 1.5;
}

.course-meta {
  display: flex;
  gap: 0.5rem;
  margin: 0.75rem 0;
}

.created-date {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #94a3b8;
  font-size: 0.85rem;
}

.course-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.mr-2 {
  margin-right: 0.5rem;
}

.course-content .course-header h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary-color);
}

.module-order {
  font-weight: bold;
  color: var(--primary-color);
  margin-right: 0.5rem;
}

.module-title {
  font-weight: 500;
}

.lesson-content-preview {
  border: 1px solid var(--surface-border);
}

.lesson-content-text :deep(h1),
.lesson-content-text :deep(h2),
.lesson-content-text :deep(h3),
.lesson-content-text :deep(h4) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.lesson-content-text :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.6;
}

.lesson-content-text :deep(code) {
  background: var(--surface-ground);
  padding: 0.125rem 0.25rem;
  border-radius: 4px;
  font-family: monospace;
}

.lesson-content-text :deep(pre) {
  background: var(--surface-ground);
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1rem 0;
}

.lesson-content-text :deep(ul),
.lesson-content-text :deep(ol) {
  margin-left: 1.5rem;
  margin-bottom: 1rem;
}

.lesson-edit-form .field {
  margin-bottom: 1rem;
}

.content-field {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 300px;
}

.markdown-textarea :deep(.p-inputtextarea) {
  min-height: 350px !important;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.95rem;
  line-height: 1.6;
  padding: 1rem !important;
  resize: vertical !important;
}

.lesson-edit-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.preview-box {
  min-height: 150px;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--surface-border);
}

.preview-box :deep(h1),
.preview-box :deep(h2),
.preview-box :deep(h3) {
  margin-top: 0.5rem;
  margin-bottom: 0.25rem;
}

.preview-box :deep(p) {
  margin-bottom: 0.5rem;
}
</style>
