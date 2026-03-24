<template>
  <div class="archived-courses-panel">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando cursos archivados...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="courses.length === 0" class="empty-state">
      <i class="pi pi-archive" style="font-size: 3rem; color: #cbd5e1;"></i>
      <h3>No hay archivados</h3>
      <p>No hay cursos archivados.</p>
    </div>

    <!-- Courses list -->
    <div v-else class="courses-list">
      <Card
        v-for="course in courses"
        :key="course.id"
        class="course-card archived-card"
      >
        <template #title>
          <div class="course-title">
            <h3>{{ course.name }}</h3>
            <Tag value="Archivado" severity="secondary" />
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
          <small class="archived-date">
            <i class="pi pi-calendar"></i>
            Archivado: {{ formatDate(course.reviewed_at || course.created_at) }}
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
              icon="pi pi-refresh"
              label="Republicar"
              severity="success"
              @click="republishCourseAction(course)"
              size="small"
            />
          </div>
        </template>
      </Card>
    </div>

    <!-- Course Content Dialog -->
    <Dialog v-model:visible="showContentDialog" modal header="Contenido del Curso (Archivado)" :style="{ width: '80vw' }">
      <div v-if="loadingContent" class="flex justify-content-center p-4">
        <ProgressSpinner />
      </div>
      <div v-else-if="courseContent" class="course-content archived-content">
        <div class="course-header mb-3">
          <h3>{{ courseContent.course.name }}</h3>
          <p class="text-color-secondary">{{ courseContent.course.description }}</p>
          <div class="flex gap-2 mt-2">
            <Tag value="Archivado" severity="secondary" />
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

    <!-- Confirm Republish Dialog -->
    <ConfirmDialog />
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
import ConfirmDialog from 'primevue/confirmdialog'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'

interface Props {
  projectId?: string
  workspaceId?: string
}

interface Course {
  id: string
  name: string
  description: string
  status: string
  created_at: string
  reviewed_at?: string
  project_name: string
  project_id: string
  module_count?: number
  lesson_count?: number
  version_number?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  courseRepublished: []
}>()

const toast = useToast()
const confirm = useConfirm()
const loading = ref(false)
const courses = ref<Course[]>([])
const showContentDialog = ref(false)
const loadingContent = ref(false)
const courseContent = ref<CourseContent | null>(null)
const activeModuleIndex = ref<number[]>([])

async function loadCourses() {
  if (!props.projectId && !props.workspaceId) return

  loading.value = true
  try {
    const response = await courseGenerationService.getArchivedCourses(props.projectId, props.workspaceId)
    courses.value = response.courses
  } catch (e: any) {
    console.error('Error loading archived courses:', e)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al cargar cursos archivados',
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

function republishCourseAction(course: Course) {
  confirm.require({
    message: `¿Estás seguro de que quieres republicar el curso "${course.name}"? Se archivará cualquier curso publicado actualmente en este proyecto.`,
    header: 'Confirmar Republicación',
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      doRepublish(course)
    }
  })
}

function doRepublish(course: Course) {
  courseGenerationService.republishCourse(course.id)
    .then(() => {
      toast.add({
        severity: 'success',
        summary: 'Éxito',
        detail: 'Curso republicado exitosamente',
        life: 3000
      })
      emit('courseRepublished')
      loadCourses()
    })
    .catch((e: any) => {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: e.response?.data?.detail || e.message || 'Error al republicar curso',
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

// Cargar cuando workspaceId o projectId cambien
watch(() => [props.workspaceId, props.projectId], () => {
  if (props.workspaceId) {
    loadCourses()
  }
}, { immediate: true })

defineExpose({
  loadCourses
})
</script>

<style scoped>
.archived-courses-panel {
  padding: 1rem;
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

.courses-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.course-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.archived-card {
  border-left: 4px solid #94a3b8;
  opacity: 0.9;
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

.archived-date {
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

.archived-content {
  opacity: 0.95;
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
