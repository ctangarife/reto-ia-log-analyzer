<template>
  <Dialog
    v-model:visible="visible"
    modal
    :header="editing ? 'Editar Lección' : lesson?.title"
    :style="{ maxWidth: '1400px', width: '95vw', height: '90vh' }"
    :contentStyle="{ height: 'calc(90vh - 80px)', overflow: 'auto', padding: '1.5rem' }"
    :maximizable="true"
    @update:visible="onClose"
  >
    <div v-if="loading" class="flex justify-content-center p-4">
      <ProgressSpinner />
    </div>

    <div v-else-if="lesson" class="lesson-editor">
      <!-- Edit Mode Toggle -->
      <div class="flex justify-content-between align-items-center mb-3">
        <div class="flex gap-2">
          <Button
            :label="editing ? 'Cancelar Edición' : 'Editar Lección'"
            :icon="editing ? 'pi pi-times' : 'pi pi-pencil'"
            :severity="editing ? 'secondary' : 'primary'"
            @click="toggleEditMode"
            outlined
          />
          <Button
            v-if="editing"
            label="Vista Previa"
            icon="pi pi-eye"
            severity="info"
            @click="showPreview = !showPreview"
            outlined
          />
          <Button
            label="Ver Historial"
            icon="pi pi-history"
            severity="secondary"
            @click="showHistory = !showHistory"
            outlined
          />
        </div>
        <div v-if="editing" class="flex gap-2 align-items-center">
          <label class="flex align-items-center gap-2 text-sm">
            <Checkbox v-model="isMinorEdit" binary inputId="minorEdit" />
            <span>Edición menor (no requiere aprobación)</span>
          </label>
        </div>
      </div>

      <!-- Main Content Area -->
      <div class="editor-container">
        <!-- Edit Mode -->
        <div v-if="editing" class="edit-mode">
          <div class="form-grid">
            <div class="form-field">
              <label for="edit-title">Título de la Lección</label>
              <InputText
                id="edit-title"
                v-model="editForm.title"
                class="w-full"
                placeholder="Título de la lección..."
              />
            </div>

            <div class="form-field content-editor">
              <label for="edit-content">Contenido (Markdown)</label>
              <Textarea
                id="edit-content"
                v-model="editForm.content"
                class="w-full markdown-editor"
                placeholder="Escribe el contenido en formato Markdown..."
                @input="updatePreview"
              />
              <small class="text-color-secondary mt-2">
                Puedes usar Markdown para dar formato. Soporta: **negrita**, *cursiva*, # encabezados, - listas, etc.
              </small>
            </div>

            <div v-if="!showPreview" class="form-field full-width">
              <label for="change-description">Descripción del Cambio</label>
              <InputText
                id="change-description"
                v-model="editForm.changeDescription"
                class="w-full"
                placeholder="Describe qué cambiaste..."
              />
            </div>
          </div>

          <!-- Live Preview (side by side) -->
          <div v-if="showPreview" class="preview-panel">
            <h4>Vista Previa</h4>
            <div class="preview-content" v-html="renderMarkdown(editForm.content)"></div>
          </div>
        </div>

        <!-- View Mode -->
        <div v-else class="view-mode">
          <div class="lesson-header mb-3">
            <h3>{{ lesson.title }}</h3>
            <div class="flex gap-2 mt-2">
              <Chip :label="`Orden: ${lesson.lesson_order}`" size="small" />
              <Chip v-if="lesson.is_dynamic" label="Dinámica" size="small" severity="warning" />
              <Chip v-else label="Estática" size="small" severity="secondary" />
            </div>
          </div>
          <div class="lesson-body" v-html="renderMarkdown(lesson.content)"></div>
        </div>
      </div>

      <!-- History Panel -->
      <div v-if="showHistory" class="history-panel mt-4">
        <Divider />
        <h4>Historial de Cambios</h4>
        <div v-if="loadingHistory" class="flex justify-content-center p-4">
          <ProgressSpinner />
        </div>
        <Timeline v-else-if="changes.length > 0" :value="changes" class="w-full">
          <template #marker="item">
            <i
              class="pi"
              :class="{
                'pi-pencil': item.change_type === 'content' || item.change_type === 'title',
                'pi-code': item.change_type === 'exercise',
                'pi-check': item.is_minor_edit
              }"
            />
          </template>
          <template #content="item">
            <Card class="mb-3 change-card">
              <template #title>
                <div class="flex justify-content-between align-items-center">
                  <span>{{ getChangeTypeLabel(item.change_type) }}</span>
                  <small class="text-color-secondary">{{ formatDate(item.changed_at) }}</small>
                </div>
              </template>
              <template #subtitle>
                <div class="flex justify-content-between align-items-center">
                  <span>
                    Por {{ item.first_name || item.last_name ? `${item.first_name || ''} ${item.last_name || ''}` : 'Usuario' }}
                    <Chip v-if="item.is_minor_edit" label="Menor" size="small" severity="info" class="ml-2" />
                  </span>
                  <div class="flex gap-2">
                    <Button
                      label="Ver Diff"
                      icon="pi pi-eye"
                      size="small"
                      outlined
                      @click="viewDiff(item.id)"
                    />
                    <Button
                      label="Restaurar"
                      icon="pi pi-undo"
                      size="small"
                      severity="warning"
                      outlined
                      @click="restoreVersion(item.id)"
                    />
                  </div>
                </div>
              </template>
              <template #content>
                <p v-if="item.change_description">{{ item.change_description }}</p>
                <small v-else class="text-color-secondary">Sin descripción</small>
              </template>
            </Card>
          </template>
        </Timeline>
        <div v-else class="text-center p-4 text-color-secondary">
          <i class="pi pi-info-circle"></i> No hay cambios registrados para esta lección.
        </div>
      </div>

      <!-- Diff View Dialog -->
      <Dialog v-model:visible="showDiffDialog" modal header="Cambios" :style="{ width: '70vw' }">
        <div v-if="currentDiff" class="diff-view">
          <div v-for="(line, idx) in currentDiff" :key="idx" class="diff-line">
            <span
              :class="{
                'diff-add': line.startsWith('+'),
                'diff-remove': line.startsWith('-'),
                'diff-header': line.startsWith('@@')
              }"
            >{{ line }}</span>
          </div>
        </div>
      </Dialog>

      <!-- Action Buttons -->
      <div class="flex justify-content-between mt-4 pt-3 border-top">
        <Button
          v-if="editing"
          label="Cancelar"
          icon="pi pi-times"
          severity="secondary"
          @click="cancelEdit"
          outlined
        />
        <div v-else></div>

        <div class="flex gap-2">
          <Button
            v-if="editing"
            label="Guardar Cambios"
            icon="pi pi-save"
            severity="success"
            @click="saveChanges"
            :loading="saving"
            :disabled="!hasChanges"
          />
          <Button
            label="Cerrar"
            icon="pi pi-times"
            severity="secondary"
            @click="visible = false"
            outlined
          />
        </div>
      </div>
    </div>
  </Dialog>
</template>

<style>
/* Estilos globales para sobreescribir PrimeVue Dialog */
.p-dialog {
  max-width: 95vw !important;
  width: 95vw !important;
  max-height: 95vh !important;
}

@media (min-width: 1400px) {
  .p-dialog {
    max-width: 1400px !important;
    width: 1400px !important;
  }
}

.p-dialog-content {
  width: 100% !important;
  overflow: auto !important;
  max-height: calc(95vh - 80px) !important;
}

.p-dialog-header {
  flex-shrink: 0 !important;
}
</style>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Card from 'primevue/card'
import Chip from 'primevue/chip'
import Timeline from 'primevue/timeline'
import Divider from 'primevue/divider'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import DOMPurify from 'dompurify'
import { lessonEditService, type LessonUpdateRequest, type LessonChange } from '@/services/lessonEditService'

interface Props {
  lessonId?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  saved: []
  closed: []
}>()

const toast = useToast()

const visible = defineModel<boolean>({ required: true })
const loading = ref(false)
const saving = ref(false)
const lesson = ref<any>(null)

// Edit mode state
const editing = ref(false)
const showPreview = ref(false)
const showHistory = ref(false)
const isMinorEdit = ref(false)

// Form state
const editForm = ref({
  title: '',
  content: '',
  changeDescription: ''
})

const originalContent = ref({
  title: '',
  content: ''
})

// History state
const loadingHistory = ref(false)
const changes = ref<LessonChange[]>([])
const showDiffDialog = ref(false)
const currentDiff = ref<string[] | null>(null)

const hasChanges = computed(() => {
  return editForm.value.title !== originalContent.value.title ||
         editForm.value.content !== originalContent.value.content
})

const loadLesson = async () => {
  if (!props.lessonId) return

  loading.value = true
  try {
    lesson.value = await lessonEditService.getLesson(props.lessonId)
    editForm.value = {
      title: lesson.value.title,
      content: lesson.value.content,
      changeDescription: ''
    }
    originalContent.value = {
      title: lesson.value.title,
      content: lesson.value.content
    }
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al cargar la lección',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const loadHistory = async () => {
  if (!props.lessonId || !showHistory.value) return

  loadingHistory.value = true
  try {
    const response = await lessonEditService.getHistory(props.lessonId)
    changes.value = response.changes
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al cargar el historial',
      life: 3000
    })
  } finally {
    loadingHistory.value = false
  }
}

const toggleEditMode = () => {
  editing.value = !editing.value
  if (!editing.value) {
    // Reset form to original
    editForm.value = {
      title: originalContent.value.title,
      content: originalContent.value.content,
      changeDescription: ''
    }
  }
  showPreview.value = false
}

const updatePreview = () => {
  // Trigger re-render of preview
}

const saveChanges = async () => {
  if (!props.lessonId) return

  saving.value = true
  try {
    const data: LessonUpdateRequest = {
      title: editForm.value.title !== originalContent.value.title ? editForm.value.title : undefined,
      content: editForm.value.content !== originalContent.value.content ? editForm.value.content : undefined,
      is_minor_edit: isMinorEdit.value,
      change_description: editForm.value.changeDescription || undefined
    }

    const response = await lessonEditService.updateLesson(props.lessonId, data)

    toast.add({
      severity: 'success',
      summary: 'Éxito',
      detail: response.message,
      life: 3000
    })

    // Reload lesson data
    await loadLesson()
    editing.value = false
    showPreview.value = false
    emit('saved')
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: e.response?.data?.detail || 'Error al guardar cambios',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

const cancelEdit = () => {
  editForm.value = {
    title: originalContent.value.title,
    content: originalContent.value.content,
    changeDescription: ''
  }
  editing.value = false
  showPreview.value = false
}

const viewDiff = async (changeId: string) => {
  if (!props.lessonId) return

  try {
    const response = await lessonEditService.getDiff(props.lessonId, changeId)
    currentDiff.value = response.diff
    showDiffDialog.value = true
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al cargar el diff',
      life: 3000
    })
  }
}

const restoreVersion = async (changeId: string) => {
  if (!props.lessonId) return
  if (!confirm('¿Estás seguro de restaurar esta versión?')) return

  try {
    await lessonEditService.restoreVersion(props.lessonId, changeId)
    toast.add({
      severity: 'success',
      summary: 'Éxito',
      detail: 'Versión restaurada exitosamente',
      life: 3000
    })
    await loadLesson()
    emit('saved')
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al restaurar versión',
      life: 3000
    })
  }
}

const renderMarkdown = (content: string) => {
  if (!content) return ''
  const rawHtml = content
    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'br', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote'],
    ALLOWED_ATTR: ['href', 'title', 'class'],
    ALLOW_DATA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false
  })
}

const getChangeTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    content: 'Cambio de Contenido',
    title: 'Cambio de Título',
    exercise: 'Cambio de Ejercicio',
    minor_edit: 'Edición Menor'
  }
  return labels[type] || type
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

const onClose = () => {
  editing.value = false
  showPreview.value = false
  showHistory.value = false
  emit('closed')
}

// Watch for lessonId changes
watch(() => props.lessonId, () => {
  if (props.lessonId) {
    loadLesson()
  }
}, { immediate: true })

// Load history when history panel is opened
watch(showHistory, () => {
  if (showHistory.value) {
    loadHistory()
  }
})
</script>

<style scoped>
.lesson-editor {
  padding: 0.5rem;
  width: 100%;
  overflow: visible;
}

.editor-container {
  min-height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.edit-mode,
.view-mode {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
  flex: 1;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.form-field.full-width {
  width: 100%;
}

.markdown-editor {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 0.95rem;
  line-height: 1.6;
  width: 100%;
  min-height: 400px;
}

.markdown-editor :deep(.p-inputtextarea) {
  width: 100% !important;
  max-width: 100% !important;
  min-height: 400px !important;
  height: auto !important;
  resize: vertical !important;
  overflow-y: auto !important;
  padding: 1rem !important;
  border: 1px solid var(--surface-border) !important;
  border-radius: 8px !important;
  background: var(--surface-ground) !important;
  color: var(--text-color) !important;
}

.content-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Forzar InputText y Textarea a ancho completo */
:deep(.p-inputtext) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}

:deep(.p-inputtextarea) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}

.preview-panel {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background: var(--surface-ground);
  border-radius: 8px;
  border: 1px solid var(--surface-border);
  width: 100%;
  overflow: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.preview-content {
  max-height: 600px;
  overflow-y: auto;
  width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
  line-height: 1.7;
  padding: 0.5rem;
}

.preview-content h4 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.preview-content h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  color: var(--text-color);
}

.preview-content strong {
  font-weight: 600;
}

.view-mode {
  padding: 1rem;
  max-width: 100%;
}

/* Asegurar que los inputs PrimeVue respeten el ancho */
.w-full {
  width: 100% !important;
  max-width: 100%;
}

/* Textarea específico */
.markdown-editor :deep(.p-inputtextarea-resizable),
.preview-panel :deep(.p-inputtextarea-resizable) {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

.view-mode {
  padding: 1rem;
  width: 100%;
}

.lesson-header h3 {
  margin: 0 0 0.5rem 0;
  color: var(--primary-color);
}

.lesson-body {
  line-height: 1.7;
  max-height: 500px;
  overflow-y: auto;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.history-panel {
  margin-top: 1rem;
}

.change-card {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.diff-view {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 8px;
  font-family: monospace;
  font-size: 0.85rem;
  max-height: 500px;
  overflow-y: auto;
}

.diff-line {
  padding: 0.25rem 0;
  white-space: pre-wrap;
}

.diff-add {
  color: #16a34a;
  background: #dcfce7;
}

.diff-remove {
  color: #dc2626;
  background: #fee2e2;
}

.diff-header {
  color: #64748b;
  font-weight: 500;
}

.border-top {
  border-top: 1px solid var(--surface-200);
}

.text-color-secondary {
  color: var(--text-color-secondary);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .lesson-editor {
    padding: 0.25rem;
  }

  .form-grid {
    gap: 0.75rem;
  }

  .markdown-editor {
    font-size: 0.85rem;
  }

  .preview-panel {
    padding: 0.75rem;
  }

  .history-panel {
    margin-top: 0.75rem;
  }
}

@media (max-width: 480px) {
  .flex.gap-2 {
    flex-wrap: wrap;
  }

  .flex.gap-2 button {
    font-size: 0.85rem;
    padding: 0.5rem 0.75rem;
  }
}
</style>
