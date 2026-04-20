<template>
  <div class="llm-model-selection">
    <!-- Header -->
    <div class="selection-header">
      <h2>
        <i class="pi pi-cog"></i>
        Configuración de Modelos LLM
      </h2>
      <p class="subtitle">
        Configura el modelo principal, modelos de respaldo y evaluadores
      </p>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
      <p>Cargando configuración...</p>
    </div>

    <!-- Selection content -->
    <div v-else class="selection-content">
      <!-- Modelo Principal -->
      <div class="selection-section">
        <div class="section-header">
          <h3>
            <i class="pi pi-star"></i>
            Modelo Principal
          </h3>
          <p class="section-description">
            Este es el modelo principal que se usará para generar explicaciones de anomalías
          </p>
        </div>

        <div class="model-config">
          <div class="form-row">
            <div class="form-group">
              <label>Proveedor</label>
              <Dropdown
                v-model="defaultModel.provider"
                :options="providers"
                optionLabel="name"
                optionValue="id"
                placeholder="Selecciona proveedor"
                @change="onDefaultProviderChange"
              />
            </div>

            <div class="form-group">
              <label>Modelo</label>
              <Dropdown
                v-model="defaultModel.model"
                :options="getModelsForProvider(defaultModel.provider)"
                optionLabel="name"
                optionValue="id"
                placeholder="Selecciona modelo"
                :loading="loadingModels"
                :disabled="!defaultModel.provider"
              />
            </div>

            <div class="form-group">
              <label>Credenciales</label>
              <div class="credentials-status" :class="{ configured: hasDefaultCredentials }">
                <i :class="hasDefaultCredentials ? 'pi pi-check' : 'pi pi-times'"></i>
                <span>{{ hasDefaultCredentials ? 'Configurado' : 'No configurado' }}</span>
              </div>
            </div>
          </div>

          <div v-if="defaultModel.model" class="model-status">
            <small>
              <i class="pi pi-info-circle"></i>
              Modelo: <strong>{{ defaultModel.provider }}/{{ defaultModel.model }}</strong>
            </small>
          </div>
        </div>
      </div>

      <!-- Modelos Fallback -->
      <div class="selection-section">
        <div class="section-header">
          <h3>
            <i class="pi pi-refresh"></i>
            Modelos Fallback
          </h3>
          <p class="section-description">
            Modelos alternativos que se usarán si el principal falla (ordenados por prioridad)
          </p>
        </div>

        <!-- Lista de fallbacks -->
        <div v-if="fallbackModels.length > 0" class="fallback-list">
          <div
            v-for="(fallback, index) in fallbackModels"
            :key="`${fallback.provider}-${index}`"
            class="fallback-item"
          >
            <div class="fallback-priority">
              <Tag :value="index + 1" severity="info" />
            </div>
            <div class="fallback-info">
              <span class="fallback-model">{{ fallback.provider }}/{{ fallback.model }}</span>
              <span v-if="fallback.isAvailable" class="status-badge available">
                <i class="pi pi-check"></i> Disponible
              </span>
              <span v-else class="status-badge unavailable">
                <i class="pi pi-times"></i> No disponible
              </span>
            </div>
            <div class="fallback-actions">
              <Button
                v-if="index > 0"
                icon="pi pi-arrow-up"
                rounded
                text
                size="small"
                @click="moveFallbackUp(index)"
                v-tooltip="'Subir prioridad'"
              />
              <Button
                v-if="index < fallbackModels.length - 1"
                icon="pi pi-arrow-down"
                rounded
                text
                size="small"
                @click="moveFallbackDown(index)"
                v-tooltip="'Bajar prioridad'"
              />
              <Button
                icon="pi pi-trash"
                rounded
                text
                size="small"
                severity="danger"
                @click="removeFallback(index)"
                v-tooltip="'Eliminar'"
              />
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <i class="pi pi-inbox"></i>
          <p>No hay modelos fallback configurados</p>
        </div>

        <!-- Agregar nuevo fallback -->
        <div class="add-fallback">
          <h4>Agregar modelo fallback</h4>
          <div class="form-row">
            <div class="form-group">
              <Dropdown
                v-model="newFallback.provider"
                :options="providers"
                optionLabel="name"
                optionValue="id"
                placeholder="Proveedor"
                @change="onFallbackProviderChange"
              />
            </div>
            <div class="form-group">
              <Dropdown
                v-model="newFallback.model"
                :options="getModelsForProvider(newFallback.provider)"
                optionLabel="name"
                optionValue="id"
                placeholder="Modelo"
                :disabled="!newFallback.provider"
              />
            </div>
            <div class="form-group">
              <Button
                icon="pi pi-plus"
                label="Agregar"
                @click="addFallback"
                :disabled="!newFallback.provider || !newFallback.model"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Modelos Evaluadores -->
      <div class="selection-section">
        <div class="section-header">
          <h3>
            <i class="pi pi-chart-bar"></i>
            Modelos Evaluadores
          </h3>
          <p class="section-description">
            Modelos especializados para tareas de evaluación y comparación
          </p>
        </div>

        <!-- Lista de evaluadores -->
        <div v-if="evaluatorModels.length > 0" class="evaluator-list">
          <div
            v-for="(evaluator, index) in evaluatorModels"
            :key="`${evaluator.provider}-${index}`"
            class="evaluator-item"
          >
            <div class="evaluator-info">
              <span class="evaluator-model">{{ evaluator.provider }}/{{ evaluator.model }}</span>
              <span v-if="evaluator.isAvailable" class="status-badge available">
                <i class="pi pi-check"></i> Disponible
              </span>
              <span v-else class="status-badge unavailable">
                <i class="pi pi-times"></i> No disponible
              </span>
            </div>
            <Button
              icon="pi pi-trash"
              rounded
              text
              size="small"
              severity="danger"
              @click="removeEvaluator(index)"
              v-tooltip="'Eliminar'"
            />
          </div>
        </div>

        <div v-else class="empty-state">
          <i class="pi pi-inbox"></i>
          <p>No hay modelos evaluadores configurados</p>
        </div>

        <!-- Agregar nuevo evaluador -->
        <div class="add-evaluator">
          <h4>Agregar modelo evaluador</h4>
          <div class="form-row">
            <div class="form-group">
              <Dropdown
                v-model="newEvaluator.provider"
                :options="providers"
                optionLabel="name"
                optionValue="id"
                placeholder="Proveedor"
                @change="onEvaluatorProviderChange"
              />
            </div>
            <div class="form-group">
              <Dropdown
                v-model="newEvaluator.model"
                :options="getModelsForProvider(newEvaluator.provider)"
                optionLabel="name"
                optionValue="id"
                placeholder="Modelo"
                :disabled="!newEvaluator.provider"
              />
            </div>
            <div class="form-group">
              <Button
                icon="pi pi-plus"
                label="Agregar"
                @click="addEvaluator"
                :disabled="!newEvaluator.provider || !newEvaluator.model"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="selection-actions">
        <Button
          label="Guardar Configuración"
          icon="pi pi-save"
          @click="saveConfiguration"
          :loading="saving"
          :disabled="!hasChanges"
        />
        <Button
          label="Cancelar"
          icon="pi pi-times"
          outlined
          @click="cancelChanges"
          :disabled="!hasChanges || saving"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import llmService from '../services/llmService'

interface Provider {
  id: string
  name: string
  description: string
}

interface ModelInfo {
  id: string
  name: string
  provider: string
}

interface ModelConfig {
  provider: string
  model: string
  isAvailable?: boolean
}

// Estado
const loading = ref(true)
const saving = ref(false)
const loadingModels = ref(false)

const providers = ref<Provider[]>([])
const allModels = ref<ModelInfo[]>([])

const defaultModel = ref<ModelConfig>({ provider: '', model: '' })
const fallbackModels = ref<ModelConfig[]>([])
const evaluatorModels = ref<ModelConfig[]>([])

const newFallback = ref<ModelConfig>({ provider: '', model: '' })
const newEvaluator = ref<ModelConfig>({ provider: '', model: '' })

const originalConfig = ref<string>('')

// Computed
const hasDefaultCredentials = computed(() => {
  return providers.value.find(p => p.id === defaultModel.value.provider)?.hasCredentials || false
})

const hasChanges = computed(() => {
  const current = JSON.stringify({
    default: defaultModel.value,
    fallback: fallbackModels.value,
    evaluators: evaluatorModels.value
  })
  return current !== originalConfig.value
})

// Métodos
const loadConfiguration = async () => {
  loading.value = true
  try {
    // Cargar proveedores
    const providersResponse = await llmService.getProviders()
    providers.value = providersResponse.providers

    // Cargar configuración de selección
    const selectionResponse = await llmService.getModelSelectionConfig()

    if (selectionResponse.default) {
      defaultModel.value = {
        provider: selectionResponse.default.provider,
        model: selectionResponse.default.model,
        isAvailable: selectionResponse.default.isAvailable
      }
    }

    fallbackModels.value = selectionResponse.fallback || []
    evaluatorModels.value = selectionResponse.evaluators || []

    // Guardar estado original
    originalConfig.value = JSON.stringify({
      default: defaultModel.value,
      fallback: fallbackModels.value,
      evaluators: evaluatorModels.value
    })

    // Cargar modelos disponibles para todos los proveedores
    await loadModels()
  } catch (error) {
    console.error('Error cargando configuración:', error)
  } finally {
    loading.value = false
  }
}

const loadModels = async () => {
  loadingModels.value = true
  try {
    const response = await llmService.getSavedModels()
    allModels.value = response.models
  } catch (error) {
    console.error('Error cargando modelos:', error)
  } finally {
    loadingModels.value = false
  }
}

const getModelsForProvider = (providerId: string) => {
  if (!providerId) return []
  return allModels.value.filter(m => m.provider === providerId)
}

const onDefaultProviderChange = () => {
  defaultModel.value.model = ''
}

const onFallbackProviderChange = () => {
  newFallback.value.model = ''
}

const onEvaluatorProviderChange = () => {
  newEvaluator.value.model = ''
}

const addFallback = () => {
  if (!newFallback.value.provider || !newFallback.value.model) return

  fallbackModels.value.push({
    provider: newFallback.value.provider,
    model: newFallback.value.model
  })

  newFallback.value = { provider: '', model: '' }
}

const removeFallback = (index: number) => {
  fallbackModels.value.splice(index, 1)
}

const moveFallbackUp = (index: number) => {
  if (index > 0) {
    const temp = fallbackModels.value[index]
    fallbackModels.value[index] = fallbackModels.value[index - 1]
    fallbackModels.value[index - 1] = temp
  }
}

const moveFallbackDown = (index: number) => {
  if (index < fallbackModels.value.length - 1) {
    const temp = fallbackModels.value[index]
    fallbackModels.value[index] = fallbackModels.value[index + 1]
    fallbackModels.value[index + 1] = temp
  }
}

const addEvaluator = () => {
  if (!newEvaluator.value.provider || !newEvaluator.value.model) return

  evaluatorModels.value.push({
    provider: newEvaluator.value.provider,
    model: newEvaluator.value.model
  })

  newEvaluator.value = { provider: '', model: '' }
}

const removeEvaluator = (index: number) => {
  evaluatorModels.value.splice(index, 1)
}

const saveConfiguration = async () => {
  saving.value = true
  try {
    // Preparar configuración batch
    const batchConfig: any = {}

    // Default model
    if (defaultModel.value.provider && defaultModel.value.model) {
      batchConfig.default = {
        provider: defaultModel.value.provider,
        model: defaultModel.value.model
      }
    }

    // Fallback models (con prioridad automática)
    if (fallbackModels.value.length > 0) {
      batchConfig.fallback = fallbackModels.value.map(fb => ({
        provider: fb.provider,
        model: fb.model
      }))
    }

    // Evaluator models
    if (evaluatorModels.value.length > 0) {
      batchConfig.evaluators = evaluatorModels.value.map(ev => ({
        provider: ev.provider,
        model: ev.model
      }))
    }

    // Guardar todo en una sola llamada
    await llmService.saveBatchConfig(batchConfig)

    // Actualizar estado original
    originalConfig.value = JSON.stringify({
      default: defaultModel.value,
      fallback: fallbackModels.value,
      evaluators: evaluatorModels.value
    })

    // Recargar configuración desde el servidor
    await loadModelSelectionConfig()

    console.log('Configuración guardada exitosamente')
  } catch (error) {
    console.error('Error guardando configuración:', error)
    throw error
  } finally {
    saving.value = false
  }
}

const cancelChanges = () => {
  const config = JSON.parse(originalConfig.value)
  defaultModel.value = config.default
  fallbackModels.value = config.fallback
  evaluatorModels.value = config.evaluators
  newFallback.value = { provider: '', model: '' }
  newEvaluator.value = { provider: '', model: '' }
}

onMounted(() => {
  loadConfiguration()
})
</script>

<style scoped>
.llm-model-selection {
  padding: 1rem;
}

.selection-header {
  margin-bottom: 2rem;
}

.selection-header h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
}

.subtitle {
  margin: 0;
  color: #6c757d;
}

.selection-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.selection-section {
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
}

.section-description {
  margin: 0;
  color: #6c757d;
  font-size: 0.875rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group {
  flex: 1;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.credentials-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.25rem;
  background: #f8f9fa;
}

.credentials-status.configured {
  background: #d4edda;
  color: #155724;
}

.model-status {
  margin-top: 0.5rem;
  color: #6c757d;
}

.fallback-list,
.evaluator-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.fallback-item,
.evaluator-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 0.25rem;
}

.fallback-priority {
  flex-shrink: 0;
}

.fallback-info,
.evaluator-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fallback-model,
.evaluator-model {
  font-weight: 500;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
}

.status-badge.available {
  background: #d4edda;
  color: #155724;
}

.status-badge.unavailable {
  background: #f8d7da;
  color: #721c24;
}

.fallback-actions {
  display: flex;
  gap: 0.25rem;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #6c757d;
}

.empty-state i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.add-fallback,
.add-evaluator {
  padding-top: 1rem;
  border-top: 1px solid #dee2e6;
}

.add-fallback h4,
.add-evaluator h4 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
}

.selection-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
}
</style>
