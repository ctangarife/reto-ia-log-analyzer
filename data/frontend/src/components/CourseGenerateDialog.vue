<template>
  <Dialog v-model:visible="showDialog" header="Generar Curso" :style="{ width: '600px' }" modal>
    <div v-if="loading" class="flex justify-content-center p-4">
      <ProgressSpinner />
    </div>

    <div v-else-if="error" class="p-3">
      <InlineMessage severity="error">{{ error }}</InlineMessage>
    </div>

    <div v-else>
      <!-- Step 1: Preview -->
      <div v-if="step === 'preview'">
        <div v-if="previewData" class="course-preview">
          <h3>Vista Previa del Curso</h3>

          <div class="grid">
            <div class="col-6">
              <div class="stat-box">
                <span class="stat-label">Logs Analizados</span>
                <span class="stat-value">{{ previewData.analysis.total_logs }}</span>
              </div>
            </div>
            <div class="col-6">
              <div class="stat-box">
                <span class="stat-label">Anomalías</span>
                <span class="stat-value">{{ previewData.analysis.total_anomalies }}</span>
              </div>
            </div>
          </div>

          <div class="mt-4">
            <h4>Categorías de Anomalías</h4>
            <Chip v-for="(count, category) in previewData.analysis.anomaly_categories"
                  :key="category"
                  :label="`${category}: ${count}`"
                  class="mr-2 mb-2" />
          </div>

          <div class="mt-4">
            <h4>Módulos Sugeridos</h4>
            <ul>
              <li v-for="module in previewData.suggested_modules" :key="module">
                {{ module }}
              </li>
            </ul>
          </div>

          <div class="mt-4">
            <InlineMessage v-if="!previewData.analysis.can_generate_course"
                          severity="warn">
              {{ previewData.analysis.min_anomalies_required }} anomalías requeridas.
              Actualmente: {{ previewData.analysis.total_anomalies }}
            </InlineMessage>
          </div>
        </div>

        <div class="flex justify-content-end gap-2 mt-4">
          <Button label="Cancelar" @click="close" severity="secondary" />
          <Button
            label="Generar Curso"
            @click="generateCourse"
            :disabled="!previewData?.analysis.can_generate_course"
          />
        </div>
      </div>

      <!-- Step 2: Configuration -->
      <div v-if="step === 'config'">
        <h3>Configuración del Curso</h3>

        <div class="formgroup mt-4">
          <label for="scope">Alcance del Curso</label>
          <Dropdown
            id="scope"
            v-model="config.scope"
            :options="scopeOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
          />
          <small class="text-color-secondary">
            {{ scopeDescription }}
          </small>
        </div>

        <div class="formgroup mt-4">
          <label for="name">Nombre del Curso (opcional)</label>
          <InputText
            id="name"
            v-model="config.name"
            placeholder="Curso de Análisis - Proyecto X"
            class="w-full"
          />
        </div>

        <div class="flex justify-content-end gap-2 mt-4">
          <Button label="Atrás" @click="step = 'preview'" severity="secondary" />
          <Button label="Generar" @click="generateCourse" />
        </div>
      </div>

      <!-- Step 3: Generating -->
      <div v-if="step === 'generating'">
        <div class="text-center">
          <ProgressSpinner />
          <p class="mt-3">Generando curso...</p>
        </div>
      </div>

      <!-- Step 4: Complete -->
      <div v-if="step === 'complete'">
        <div class="text-center">
          <i class="pi pi-check-circle text-green-500" style="font-size: 3rem;"></i>
          <h3 class="mt-3">¡Curso Generado!</h3>
          <p>{{ result?.message }}</p>
          <div class="flex gap-2 justify-content-center mt-4">
            <div class="stat-box inline-block">
              <span class="stat-label">Módulos</span>
              <span class="stat-value">{{ result?.modules_created }}</span>
            </div>
            <div class="stat-box inline-block">
              <span class="stat-label">Lecciones</span>
              <span class="stat-value">{{ result?.lessons_created }}</span>
            </div>
          </div>
        </div>
        <div class="flex justify-content-end mt-4">
          <Button label="Cerrar" @click="close" />
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import ProgressSpinner from 'primevue/progressspinner'
import InlineMessage from 'primevue/inlinemessage'
import Chip from 'primevue/chip'

import { courseGenerationService, type CourseGenerateRequest } from '@/services/courseGenerationService'

interface Props {
  projectId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  generated: []
}>()

const showDialog = ref(false)
const step = ref<'preview' | 'config' | 'generating' | 'complete'>('preview')
const loading = ref(false)
const error = ref('')

const previewData = ref()
const result = ref()

const config = ref<{
  scope: 'project' | 'workspace'
  name?: string
}>({
  scope: 'project'
})

const scopeOptions = [
  { label: 'Solo este Proyecto', value: 'project' },
  { label: 'Todo el Workspace', value: 'workspace' }
]

const scopeDescription = computed(() => {
  return config.value.scope === 'project'
    ? 'El curso estará disponible solo para este proyecto'
    : 'El curso estará disponible para todos los proyectos del workspace'
})

const open = async () => {
  showDialog.value = true
  step.value = 'preview'
  error.value = ''
  result.value = null
  previewData.value = null

  await loadPreview()
}

const loadPreview = async () => {
  loading.value = true
  error.value = ''

  try {
    previewData.value = await courseGenerationService.preview(props.projectId)
  } catch (e: any) {
    error.value = e.message || 'Error al cargar vista previa'
  } finally {
    loading.value = false
  }
}

const generateCourse = async () => {
  step.value = 'generating'
  error.value = ''

  try {
    const data: CourseGenerateRequest = {
      scope: config.value.scope,
      name: config.value.name || undefined
    }

    result.value = await courseGenerationService.generate(props.projectId, data)
    step.value = 'complete'
    emit('generated')
  } catch (e: any) {
    error.value = e.message || 'Error al generar curso'
    step.value = 'config'
  }
}

const close = () => {
  showDialog.value = false
}

defineExpose({
  open
})
</script>

<style scoped>
.course-preview {
  padding: 1rem;
}

.stat-box {
  text-align: center;
  padding: 1rem;
  background: var(--surface-100);
  border-radius: 8px;
}

.stat-box.inline-block {
  display: inline-block;
  min-width: 100px;
  margin: 0 1rem;
}

.stat-label {
  display: block;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--primary-color);
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
</style>
