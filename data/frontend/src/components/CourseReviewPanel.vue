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
                <h4>{{ course.title }}</h4>
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

import { courseGenerationService } from '@/services/courseGenerationService'

interface Props {
  workspaceId: string
}

interface PendingCourse {
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

const viewCourse = (course: PendingCourse) => {
  // TODO: Open course viewer/edit dialog
  console.log('View course:', course)
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

.p-error {
  color: var(--red-500);
}
</style>
