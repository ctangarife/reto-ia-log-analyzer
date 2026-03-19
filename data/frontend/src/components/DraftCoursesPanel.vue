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
              label="Ver"
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
    <Dialog v-model:visible="showContentDialog" modal header="Contenido del Curso" :style="{ width: '80vw' }">
      <div v-if="loadingContent" class="flex justify-content-center p-4">
        <ProgressSpinner />
      </div>
      <div v-else-if="courseContent" class="course-content">
        <div class="course-header mb-3">
          <h3>{{ courseContent.course.name }}</h3>
          <p class="text-color-secondary">{{ courseContent.course.description }}</p>
          <div class="flex gap-2 mt-2">
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
            <DataTable :value="getModuleLessons(module.id)" stripedRows size="small">
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
      </div>
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
import { courseGenerationService, type CourseContent } from '../services/courseGenerationService'
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
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '../stores/authStore'
import CourseGenerateDialog from './CourseGenerateDialog.vue'

interface Props {
  workspaceId?: string
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

async function loadCourses() {
  if (!props.workspaceId) return

  loading.value = true
  try {
    const response = await courseGenerationService.getDraftCourses(props.workspaceId)
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

  courseGenerationService.getCourseContent(course.id)
    .then(content => {
      courseContent.value = content
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

function editCourse(course: Course) {
  emit('courseSelected', course)
  // TODO: Open edit dialog
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
  return courseContent.value.lessons.filter(l => l.module_id === moduleId)
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

watch(() => props.workspaceId, () => {
  if (props.workspaceId) {
    loadCourses()
  }
}, { immediate: true })

onMounted(() => {
  if (props.workspaceId) {
    loadCourses()
  }
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
</style>
