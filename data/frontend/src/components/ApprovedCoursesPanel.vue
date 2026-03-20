<template>
  <div class="approved-courses-panel">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando cursos aprobados...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="courses.length === 0" class="empty-state">
      <i class="pi pi-check-circle" style="font-size: 3rem; color: #cbd5e1;"></i>
      <h3>No hay aprobados</h3>
      <p>No hay cursos aprobados esperando publicación.</p>
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
            <Tag value="Aprobado" severity="success" />
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
            Aprobado: {{ formatDate(course.created_at) }}
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
              icon="pi pi-upload"
              label="Publicar"
              severity="success"
              @click="publishCourse(course)"
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
            <Tag :value="courseContent.course.status" severity="success" />
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

interface Props {
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
  courseSelected: [course: Course]
  courseActioned: []
}>()

const toast = useToast()
const loading = ref(false)
const courses = ref<Course[]>([])
const showContentDialog = ref(false)
const loadingContent = ref(false)
const courseContent = ref<CourseContent | null>(null)
const activeModuleIndex = ref<number[]>([])

async function loadCourses() {
  if (!props.workspaceId) return

  loading.value = true
  try {
    const response = await courseGenerationService.getApprovedCourses(props.workspaceId)
    courses.value = response.courses
  } catch (e: any) {
    console.error('Error loading approved courses:', e)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al cargar cursos aprobados',
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

function publishCourse(course: Course) {
  courseGenerationService.publishCourse(course.id, true) // archive existing
    .then(() => {
      toast.add({
        severity: 'success',
        summary: 'Éxito',
        detail: 'Curso publicado exitosamente',
        life: 3000
      })
      emit('courseActioned')
      loadCourses()
    })
    .catch(e => {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: e.message || 'Error al publicar curso',
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

// Expose loadCourses for parent component to call
defineExpose({
  loadCourses
})
</script>

<style scoped>
.approved-courses-panel {
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
