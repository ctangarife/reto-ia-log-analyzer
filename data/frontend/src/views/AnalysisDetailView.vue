<template>
  <div class="analysis-detail-view">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Cargando análisis...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle text-4xl" style="color: #ef4444;"></i>
      <h3>Análisis no encontrado</h3>
      <p>{{ error }}</p>
      <Button label="Volver al historial" @click="goToHistory" />
    </div>

    <!-- Content -->
    <template v-else-if="analysis">
      <!-- Header del análisis -->
      <div class="analysis-header">
        <div class="header-main">
          <Button
            icon="pi pi-arrow-left"
            text
            @click="goBack"
            v-tooltip="'Volver'"
          />
          <div class="header-info">
            <h2>{{ analysis.fileName || 'Análisis sin nombre' }}</h2>
            <div class="meta">
              <span class="date">
                <i class="pi pi-calendar"></i>
                {{ formatDateTime(analysis.timestamp) }}
              </span>
              <span class="project">
                <i class="pi pi-folder"></i>
                {{ getProjectName() }}
              </span>
            </div>
          </div>
        </div>

        <div class="header-actions">
          <Button
            icon="pi pi-refresh"
            label="Re-analizar"
            severity="info"
            outlined
            @click="confirmReanalyze"
            :loading="reanalyzing"
          />
          <Button
            icon="pi pi-trash"
            label="Eliminar"
            severity="danger"
            outlined
            @click="confirmDelete"
            :loading="deleting"
          />
        </div>
      </div>

      <!-- Stats badges -->
      <div class="stats-bar">
        <div class="stat-badge">
          <span class="label">Total de Logs</span>
          <span class="value">{{ formatNumber(analysis.total_logs) }}</span>
        </div>
        <div class="stat-badge danger">
          <span class="label">Anomalías Detectadas</span>
          <span class="value">{{ formatNumber(analysis.anomalies_detected) }}</span>
        </div>
        <div class="stat-badge">
          <span class="label">Porcentaje</span>
          <span class="value">{{ getPercentage(analysis) }}%</span>
        </div>
        <div v-if="analysis.fileHash" class="stat-badge">
          <span class="label">Hash</span>
          <span class="value mono">{{ truncateHash(analysis.fileHash || analysis.file_id) }}</span>
        </div>
      </div>

      <!-- Anomalías -->
      <div class="anomalies-section">
        <!-- Sin anomalías -->
        <div v-if="!analysis.anomalies || analysis.anomalies.length === 0" class="no-anomalies">
          <i class="pi pi-check-circle" style="color: #10b981; font-size: 4rem;"></i>
          <h3>No se detectaron anomalías</h3>
          <p>Este análisis no encontró patrones anómalos en el archivo de logs.</p>
        </div>

        <!-- Con anomalías -->
        <template v-else>
          <div class="anomalies-header">
            <h3>Anomalías Detectadas</h3>
            <div class="filters">
              <Dropdown
                v-model="severityFilter"
                :options="severityOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Filtrar por severidad"
                class="filter-dropdown"
                showClear
              />
            </div>
          </div>

          <div class="anomalies-list">
            <div
              v-for="(anomaly, index) in filteredAnomalies"
              :key="index"
              class="anomaly-card"
              :class="getAnomalyClass(anomaly)"
            >
              <div class="anomaly-header">
                <span class="anomaly-number">Anomalía #{{ index + 1 }}</span>
                <Tag :value="getAnomalySeverity(anomaly)" :severity="getSeverityClass(anomaly)" />
                <span class="anomaly-score">{{ getAnomalyScore(anomaly) }}%</span>
              </div>

              <Divider />

              <div class="anomaly-body">
                <div class="anomaly-log">
                  <h5>Log detectado:</h5>
                  <pre>{{ anomaly.log_entry || anomaly.log_line || anomaly.line || 'Sin información del log' }}</pre>
                </div>

                <div v-if="anomaly.explanation" class="anomaly-explanation">
                  <h5>Explicación:</h5>
                  <p>{{ anomaly.explanation }}</p>
                </div>

                <div v-if="anomaly.chunk_info" class="anomaly-chunk">
                  <small>
                    <i class="pi pi-info-circle"></i>
                    Chunk {{ anomaly.chunk_info.chunk_index }} de {{ anomaly.chunk_info.total_chunks }}
                  </small>
                </div>
              </div>
            </div>
          </div>

          <!-- Paginación -->
          <Paginator
            v-if="filteredAnomalies.length > itemsPerPage"
            :rows="itemsPerPage"
            :totalRecords="filteredAnomalies.length"
            @page="onPageChange"
            class="mt-4"
          />
        </template>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysisStore'
import { useAuthStore } from '../stores/authStore'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { jobService } from '../services/jobService'

const props = defineProps<{
  id: string
}>()

const route = useRoute()
const router = useRouter()
const store = useAnalysisStore()
const authStore = useAuthStore()
const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const error = ref<string | null>(null)
const analysis = ref<any>(null)
const deleting = ref(false)
const reanalyzing = ref(false)

// Filtros
const severityFilter = ref<string | null>(null)
const severityOptions = [
  { label: 'Crítica', value: 'critical' },
  { label: 'Alta', value: 'high' },
  { label: 'Media', value: 'medium' },
  { label: 'Baja', value: 'low' }
]

// Paginación
const currentPage = ref(0)
const itemsPerPage = 10

const filteredAnomalies = computed(() => {
  if (!analysis.value?.anomalies) return []

  let anomalies = analysis.value.anomalies

  if (severityFilter.value) {
    anomalies = anomalies.filter((a: any) => {
      const severity = getSeverityValue(a)
      return severity === severityFilter.value
    })
  }

  const start = currentPage.value * itemsPerPage
  const end = start + itemsPerPage
  return anomalies.slice(start, end)
})

onMounted(async () => {
  await loadAnalysis()
})

async function loadAnalysis() {
  loading.value = true
  error.value = null

  try {
    // Buscar en el historial primero (más rápido)
    const history = store.analysisHistory
    const found = history.find(a => a.id === props.id)

    if (found) {
      analysis.value = found
      store.setCurrentAnalysis(found)
    } else {
      // No está en memoria, cargar desde el backend
      console.log('Análisis no encontrado en memoria, cargando desde backend...')
      try {
        const jobDetails = await jobService.getJobDetails(props.id)
        analysis.value = jobDetails
        store.setCurrentAnalysis(jobDetails)

        // Agregar al historial para no perderlo
        store.addAnalysis(jobDetails)
      } catch (backendError: any) {
        console.error('Error loading from backend:', backendError)
        if (backendError.response?.status === 404) {
          error.value = 'El análisis no existe o no está completado.'
        } else if (backendError.response?.status === 403) {
          error.value = 'No tienes permiso para ver este análisis.'
        } else {
          error.value = backendError.response?.data?.detail || 'Error al cargar el análisis desde el servidor.'
        }
      }
    }
  } catch (e: any) {
    console.error('Error en loadAnalysis:', e)
    error.value = e.message || 'Error al cargar el análisis'
  } finally {
    loading.value = false
  }
}

function formatDateTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString()
}

function formatNumber(num: number): string {
  return num.toLocaleString()
}

function getPercentage(analysis: any): string {
  if (!analysis.total_logs || analysis.total_logs === 0) return '0'
  return ((analysis.anomalies_detected / analysis.total_logs) * 100).toFixed(1)
}

function getProjectName(): string {
  for (const wsId in authStore.projects) {
    const project = authStore.projects[wsId]?.find((p: any) => p.project_id === analysis.value?.project_id)
    if (project) return project.name
  }
  return 'Proyecto desconocido'
}

function truncateHash(hash: string): string {
  return hash.length > 12 ? `${hash.substring(0, 6)}...${hash.substring(hash.length - 6)}` : hash
}

function getAnomalySeverity(anomaly: any): string {
  const score = anomaly.score || anomaly.anomaly_score || 0
  if (score > 0.8) return 'Crítica'
  if (score > 0.6) return 'Alta'
  if (score > 0.4) return 'Media'
  return 'Baja'
}

function getSeverityClass(anomaly: any): string {
  const score = anomaly.score || anomaly.anomaly_score || 0
  if (score > 0.8) return 'danger'
  if (score > 0.6) return 'warn'
  if (score > 0.4) return 'info'
  return 'success'
}

function getSeverityValue(anomaly: any): string {
  const score = anomaly.score || anomaly.anomaly_score || 0
  if (score > 0.8) return 'critical'
  if (score > 0.6) return 'high'
  if (score > 0.4) return 'medium'
  return 'low'
}

function getAnomalyScore(anomaly: any): number {
  const score = anomaly.score || anomaly.anomaly_score || 0
  return Math.round(score * 100)
}

function getAnomalyClass(anomaly: any): string {
  return getSeverityValue(anomaly)
}

function onPageChange(event: any) {
  currentPage.value = event.page
}

function goBack() {
  router.push({ name: 'history' })
}

function goToHistory() {
  router.push({ name: 'history' })
}

function confirmDelete() {
  confirm.require({
    message: `¿Eliminar el análisis de "${analysis.value?.fileName || 'Sin nombre'}"?`,
    header: 'Confirmar eliminación',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Eliminar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await deleteAnalysis()
    }
  })
}

async function deleteAnalysis() {
  deleting.value = true

  try {
    await jobService.deleteJob(props.id)

    // Recargar historial
    if (authStore.selectedProjectId) {
      await store.loadReportsFromDirectory(authStore.selectedProjectId)
    }

    toast.add({
      severity: 'success',
      summary: 'Análisis eliminado',
      life: 3000
    })

    router.push({ name: 'history' })
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error al eliminar',
      detail: e.response?.data?.detail || 'Intenta nuevamente',
      life: 5000
    })
  } finally {
    deleting.value = false
  }
}

function confirmReanalyze() {
  confirm.require({
    message: `¿Re-analizar el archivo "${analysis.value?.fileName || 'Sin nombre'}"?`,
    header: 'Confirmar re-análisis',
    icon: 'pi pi-refresh',
    acceptLabel: 'Re-analizar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await reanalyzeJob()
    }
  })
}

async function reanalyzeJob() {
  reanalyzing.value = true

  try {
    const result = await jobService.reanalyzeJob(props.id)

    toast.add({
      severity: 'success',
      summary: 'Re-análisis iniciado',
      detail: 'El nuevo análisis está en proceso',
      life: 3000
    })

    // Ir a la vista de análisis en tiempo real
    router.push({ name: 'analysis' })

    // Esperar y actualizar el store
    await new Promise(resolve => setTimeout(resolve, 1000))
    store.updateCurrentJob({
      job_id: result.job_id,
      status: result.status as any,
      progress: 0,
      chunks_processed: 0,
      total_chunks: result.total_chunks,
      anomalies_found: 0
    })
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Error al iniciar re-análisis',
      detail: e.response?.data?.detail || 'Intenta nuevamente',
      life: 5000
    })
  } finally {
    reanalyzing.value = false
  }
}
</script>

<style scoped>
.analysis-detail-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  gap: 1rem;
  text-align: center;
}

.error-state h3 {
  margin: 0;
  color: #1e293b;
}

.error-state p {
  margin: 0;
  color: #64748b;
}

/* Header */
.analysis-header {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header-main {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.header-info h2 {
  margin: 0 0 0.5rem 0;
  color: #1e293b;
  font-size: 1.25rem;
}

.meta {
  display: flex;
  gap: 1.5rem;
  color: #64748b;
  font-size: 0.9rem;
}

.meta span {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.stat-badge {
  flex: 1;
  min-width: 140px;
  background: white;
  border-radius: 12px;
  padding: 1rem 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-badge.danger {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.stat-badge .label {
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-badge .value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1e293b;
}

.stat-badge.danger .value {
  color: #dc2626;
}

.stat-badge .value.mono {
  font-family: monospace;
  font-size: 1rem;
}

/* Anomalías Section */
.anomalies-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.no-anomalies {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  gap: 1rem;
  text-align: center;
}

.no-anomalies h3 {
  margin: 0;
  color: #1e293b;
}

.no-anomalies p {
  margin: 0;
  color: #64748b;
  max-width: 400px;
}

.anomalies-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.anomalies-header h3 {
  margin: 0;
  color: #1e293b;
}

.filters {
  display: flex;
  gap: 0.75rem;
}

.filter-dropdown {
  min-width: 180px;
}

/* Anomalías List */
.anomalies-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.anomaly-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.anomaly-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.anomaly-card.critical {
  border-left: 4px solid #dc2626;
}

.anomaly-card.high {
  border-left: 4px solid #f59e0b;
}

.anomaly-card.medium {
  border-left: 4px solid #3b82f6;
}

.anomaly-card.low {
  border-left: 4px solid #10b981;
}

.anomaly-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: #f8fafc;
}

.anomaly-number {
  font-weight: 600;
  color: #1e293b;
}

.anomaly-score {
  font-size: 0.9rem;
  font-weight: 600;
  color: #64748b;
}

.anomaly-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.anomaly-log h5,
.anomaly-explanation h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.anomaly-log pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.anomaly-explanation p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.anomaly-chunk {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: #94a3b8;
  font-size: 0.8rem;
}
</style>
