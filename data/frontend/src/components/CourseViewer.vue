<template>
  <div class="course-viewer">
    <div v-if="loading" class="flex justify-content-center p-4">
      <ProgressSpinner />
    </div>

    <div v-else-if="error" class="p-3">
      <InlineMessage severity="error">{{ error }}</InlineMessage>
    </div>

    <div v-else-if="!progressData" class="text-center p-4">
      <i class="pi pi-book text-500" style="font-size: 3rem;"></i>
      <p class="mt-2">No hay un curso disponible para este proyecto.</p>
    </div>

    <div v-else>
      <!-- Course Header -->
      <Card class="course-header mb-3">
        <template #title>
          <div class="flex justify-content-between align-items-center">
            <div>
              <h2>Curso de Análisis de Logs</h2>
              <p class="text-color-secondary">{{ progressData.project_id }}</p>
            </div>
            <div class="flex gap-2 align-items-center">
              <Badge v-if="progressData.is_completed" value="Completado" severity="success" />
              <Badge v-else :value="`${progressData.progress_percentage}%`" severity="info" />
            </div>
          </div>
        </template>

        <template #content>
          <ProgressBar :value="progressData.progress_percentage" class="mt-3" />

          <div class="grid mt-4">
            <div class="col-3 text-center">
              <span class="stat-value">{{ progressData.completed_modules }}/{{ progressData.total_modules }}</span>
              <span class="stat-label">Módulos</span>
            </div>
            <div class="col-3 text-center">
              <span class="stat-value">{{ progressData.completed_lessons }}/{{ progressData.total_lessons }}</span>
              <span class="stat-label">Lecciones</span>
            </div>
            <div class="col-3 text-center">
              <span class="stat-value">{{ progressData.progress_percentage }}%</span>
              <span class="stat-label">Progreso</span>
            </div>
            <div class="col-3 text-center">
              <span v-if="progressData.is_completed" class="text-green-500">
                <i class="pi pi-check-circle"></i> Completado
              </span>
              <span v-else class="text-color-secondary">En progreso</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Modules and Lessons -->
      <Accordion v-model:activeIndex="activeModule" multiple>
        <AccordionTab v-for="module in progressData.modules" :key="module.id">
          <template #header>
            <div class="flex justify-content-between align-items-center w-full">
              <div>
                <span class="module-order">M{{ module.module_order }}</span>
                <span class="module-title">{{ module.title }}</span>
              </div>
              <Chip :label="`${module.completed_lessons}/${module.total_lessons}`" size="small" />
            </div>
          </template>

          <div class="module-content">
            <p v-if="module.description" class="text-color-secondary mb-3">{{ module.description }}</p>

            <DataTable :value="module.lessons" stripedRows class="p-0">
              <Column field="lesson_order" header="#" style="width: 50px" />
              <Column field="title" header="Lección" />
              <Column header="Estado" style="width: 120px">
                <template #body="slotProps">
                  <Chip v-if="slotProps.data.is_completed" label="Completado" severity="success" size="small" />
                  <Chip v-else label="Pendiente" severity="warning" size="small" />
                </template>
              </Column>
              <Column header="Acción" style="width: 100px">
                <template #body="slotProps">
                  <Button
                    v-if="!slotProps.data.is_completed"
                    icon="pi pi-play"
                    rounded
                    outlined
                    size="small"
                    @click="openLesson(slotProps.data)"
                  />
                  <Button
                    v-else
                    icon="pi pi-eye"
                    rounded
                    outlined
                    size="small"
                    @click="openLesson(slotProps.data)"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
        </AccordionTab>
      </Accordion>

      <!-- Certificate Section (if completed) -->
      <Card v-if="progressData.is_completed" class="mt-3">
        <template #title>
          <div class="flex align-items-center gap-2">
            <i class="pi pi-award text-yellow-500"></i>
            <span>Certificado de Completitud</span>
          </div>
        </template>

        <template #content>
          <div class="flex justify-content-between align-items-center">
            <div>
              <p>¡Felicidades! Has completado el curso.</p>
              <small class="text-color-secondary">
                Completado: {{ formatDate(progressData.completed_at) }}
              </small>
            </div>
            <div class="flex gap-2">
              <Button label="Ver Insignia" @click="viewBadge" outlined />
              <Button label="Descargar Certificado" @click="downloadCertificate" />
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Lesson Viewer Dialog -->
    <Dialog v-model:visible="showLessonDialog" :header="currentLesson?.title" modal :style="{ width: '800px' }">
      <div v-if="currentLesson" class="lesson-content">
        <div v-html="renderMarkdown(currentLesson.content)"></div>

        <div v-if="currentLesson.exercise_data" class="exercise-section mt-4">
          <h4>Ejercicio</h4>
          <p>Este módulo incluye un ejercicio práctico.</p>
          <Button label="Comenzar Ejercicio" @click="startExercise" />
        </div>

        <div class="flex justify-content-between mt-4">
          <Button label="Lección Anterior" :disabled="!hasPreviousLesson" outlined />
          <Button
            :label="currentLesson.is_completed ? 'Completada' : 'Marcar como Completada'"
            :disabled="currentLesson.is_completed"
            @click="completeLesson"
            severity="success"
          />
          <Button label="Siguiente Lección" :disabled="!hasNextLesson" outlined />
        </div>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from 'primevue/card'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Chip from 'primevue/chip'
import ProgressBar from 'primevue/progressbar'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import InlineMessage from 'primevue/inlinemessage'

import { courseProgressService, type CourseProgressResponse, type CourseLesson } from '@/services/courseProgressService'

interface Props {
  projectId: string
}

const props = defineProps<Props>()

const loading = ref(false)
const error = ref('')
const progressData = ref<CourseProgressResponse | null>(null)
const activeModule = ref<number[]>([])
const showLessonDialog = ref(false)
const currentLesson = ref<CourseLesson | null>(null)
const allLessons = ref<CourseLesson[]>([])

const loadProgress = async () => {
  loading.value = true
  error.value = ''

  try {
    progressData.value = await courseProgressService.getProgress(props.projectId)

    // Flatten all lessons for navigation
    allLessons.value = progressData.value.modules.flatMap(m => m.lessons)
  } catch (e: any) {
    error.value = e.message || 'Error al cargar progreso del curso'
  } finally {
    loading.value = false
  }
}

const openLesson = (lesson: CourseLesson) => {
  currentLesson.value = lesson
  showLessonDialog.value = true
}

const hasPreviousLesson = computed(() => {
  if (!currentLesson.value) return false
  const index = allLessons.value.findIndex(l => l.id === currentLesson.value.id)
  return index > 0
})

const hasNextLesson = computed(() => {
  if (!currentLesson.value) return false
  const index = allLessons.value.findIndex(l => l.id === currentLesson.value.id)
  return index < allLessons.value.length - 1
})

const completeLesson = async () => {
  if (!currentLesson.value) return

  try {
    await courseProgressService.completeLesson(props.projectId, currentLesson.value.id)
    await loadProgress()
    showLessonDialog.value = false
  } catch (e: any) {
    error.value = e.message || 'Error al completar lección'
  }
}

const startExercise = () => {
  // TODO: Implement exercise interface
  console.log('Start exercise:', currentLesson.value?.exercise_data)
}

const viewBadge = () => {
  // TODO: Show badge dialog
  console.log('View badge')
}

const downloadCertificate = async () => {
  try {
    const cert = await courseProgressService.getCertificate(props.projectId)
    window.open(cert.download_url, '_blank')
  } catch (e: any) {
    error.value = e.message || 'Error al descargar certificado'
  }
}

const renderMarkdown = (content: string) => {
  // Simple markdown rendering (in production, use a proper markdown library)
  if (!content) return ''

  return content
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Auto-load
loadProgress()
</script>

<style scoped>
.course-viewer {
  padding: 1rem;
}

.course-header {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-700) 100%);
  color: white;
}

.course-header :deep(.p-card-title) {
  color: white;
}

.course-header :deep(.p-card-content) {
  background: transparent;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
}

.stat-label {
  font-size: 0.875rem;
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

.module-content {
  padding: 1rem 0;
}

.lesson-content {
  line-height: 1.6;
}

.lesson-content h4 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.exercise-section {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 8px;
}

.text-color-secondary {
  color: var(--text-color-secondary);
}

.text-500 {
  color: var(--primary-500);
}

.text-green-500 {
  color: var(--green-500);
}
</style>
