<template>
  <div class="analysis-history" :class="{ compact }">
    <!-- Vista compacta (tabla) -->
    <template v-if="compact">
      <DataTable
        :value="analysisHistory"
        :loading="isLoading"
        paginator
        :rows="10"
        :rowsPerPageOptions="[5, 10, 20]"
        sortField="timestamp"
        :sortOrder="-1"
        stripedRows
        class="history-table"
      >
        <Column field="timestamp" header="Fecha" sortable>
          <template #body="{ data }">
            {{ formatDateTime(data.timestamp) }}
          </template>
        </Column>
        <Column field="fileName" header="Archivo" sortable>
          <template #body="{ data }">
            <span class="filename">{{ data.fileName || 'Sin nombre' }}</span>
          </template>
        </Column>
        <Column field="total_logs" header="Logs" sortable>
          <template #body="{ data }">
            {{ formatNumber(data.total_logs) }}
          </template>
        </Column>
        <Column field="anomalies_detected" header="Anomalías" sortable>
          <template #body="{ data }">
            <span :class="getAnomalyClass(data)">
              {{ formatNumber(data.anomalies_detected) }}
            </span>
          </template>
        </Column>
        <Column field="percentage" header="%" sortable>
          <template #body="{ data }">
            {{ getPercentage(data) }}%
          </template>
        </Column>
        <Column header="Acciones" :exportable="false">
          <template #body="{ data }">
            <div class="actions">
              <Button
                icon="pi pi-eye"
                text
                rounded
                v-tooltip="'Ver detalles'"
                @click="viewDetails(data)"
              />
              <Button
                icon="pi pi-refresh"
                text
                rounded
                severity="info"
                v-tooltip="'Re-analizar'"
                @click="confirmReanalyze(data)"
                :loading="reanalyzingId === data.id"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                v-tooltip="'Eliminar'"
                @click="confirmDelete(data)"
                :loading="deletingId === data.id"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </template>

    <!-- Vista original (sidebar) -->
    <template v-else>
      <div class="history-header">
        <h3>Historial</h3>
        <div class="header-actions">
          <Button
            icon="pi pi-refresh"
            severity="secondary"
            text
            :loading="isLoading"
            @click="loadReportsFromDirectory"
          />
        </div>
      </div>

      <div v-if="isLoading" class="loading-state">
        <ProgressSpinner style="width: 30px; height: 30px" />
      </div>

      <div v-else-if="analysisHistory.length === 0" class="empty-state">
        <i class="pi pi-folder-open"></i>
        <small>Sin análisis previos</small>
      </div>

      <div v-else class="history-list">
        <div
          v-for="analysis in analysisHistory.slice(0, 5)"
          :key="analysis.id"
          class="history-item"
          :class="{ active: currentAnalysis?.id === analysis.id }"
          @click="selectAnalysis(analysis)"
        >
          <div class="item-main">
            <span class="filename">{{ truncate(analysis.fileName || 'Sin nombre', 25) }}</span>
            <span class="anomalies" :class="getAnomalyClass(analysis)">
              {{ analysis.anomalies_detected }} anomalías
            </span>
          </div>
          <div class="item-meta">
            <span class="date">{{ formatDate(analysis.timestamp) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useAnalysisStore } from '../stores/analysisStore'
import { useAuthStore } from '../stores/authStore'
import { storeToRefs } from 'pinia'
import { computed, watch, ref } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import { useConfirm } from 'primevue/useconfirm'
import { useRouter } from 'vue-router'
import { jobService } from '../services/jobService'

const props = defineProps<{
  compact?: boolean
}>()

const emit = defineEmits<{
  viewDetails: [analysis: any]
}>()

const store = useAnalysisStore()
const authStore = useAuthStore()
const { analysisHistory, currentAnalysis, isLoading } = storeToRefs(store)
const { setCurrentAnalysis, loadReportsFromDirectory } = store
const confirm = useConfirm()
const router = useRouter()

const deletingId = ref<string | null>(null)
const reanalyzingId = ref<string | null>(null)

// Cargar reportes cuando cambia el proyecto seleccionado
watch(() => authStore.selectedProjectId, async (newProjectId) => {
  if (newProjectId) {
    await loadReportsFromDirectory(newProjectId)
  }
}, { immediate: true })

async function viewDetails(analysis: any) {
  // Emitir evento al componente padre
  emit('viewDetails', analysis)

  // También actualizar en el store
  setCurrentAnalysis(analysis)

  // Navegar a la vista de análisis
  router.push({ name: 'analysis' })
}

async function deleteAnalysis(analysis: any) {
  deletingId.value = analysis.id

  try {
    const result = await jobService.deleteJob(analysis.id)

    // Recargar la lista de análisis
    if (authStore.selectedProjectId) {
      await loadReportsFromDirectory(authStore.selectedProjectId)
    }

    // Limpiar currentAnalysis si es el que se eliminó
    if (currentAnalysis.value?.id === analysis.id) {
      setCurrentAnalysis(null)
    }
  } catch (error: any) {
    console.error('Error eliminando análisis:', error)
    alert('Error al eliminar el análisis. Intenta nuevamente.')
  } finally {
    deletingId.value = null
  }
}

function selectAnalysis(analysis: any) {
  setCurrentAnalysis(analysis)
}

function confirmDelete(analysis: any) {
  confirm.require({
    message: `¿Eliminar el análisis de "${analysis.fileName || 'Sin nombre'}"?`,
    header: 'Confirmar eliminación',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Eliminar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await deleteAnalysis(analysis)
    }
  })
}

async function reanalyzeJob(analysis: any) {
  reanalyzingId.value = analysis.id

  try {
    const result = await jobService.reanalyzeJob(analysis.id)

    // Esperar un momento para que el job se inicie
    await new Promise(resolve => setTimeout(resolve, 1000))

    // Actualizar el store con el nuevo job
    store.updateCurrentJob({
      job_id: result.job_id,
      status: result.status as any,
      progress: 0,
      chunks_processed: 0,
      total_chunks: result.total_chunks,
      anomalies_found: 0
    })

    // Recargar la lista de análisis
    if (authStore.selectedProjectId) {
      await loadReportsFromDirectory(authStore.selectedProjectId)
    }
  } catch (error: any) {
    console.error('Error re-analizando:', error)
    const errorMsg = error.response?.data?.detail || 'Error al iniciar el re-análisis. Intenta nuevamente.'
    alert(errorMsg)
  } finally {
    reanalyzingId.value = null
  }
}

function confirmReanalyze(analysis: any) {
  confirm.require({
    message: `¿Re-analizar el archivo "${analysis.fileName || 'Sin nombre'}"? Se creará un nuevo análisis con el mismo contenido.`,
    header: 'Confirmar re-análisis',
    icon: 'pi pi-refresh',
    acceptLabel: 'Re-analizar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await reanalyzeJob(analysis)
    }
  })
}

function formatDateTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString()
}

function formatDate(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    return 'Hoy'
  } else if (diffDays === 1) {
    return 'Ayer'
  } else if (diffDays < 7) {
    return `Hace ${diffDays} días`
  } else {
    return date.toLocaleDateString()
  }
}

function formatNumber(num: number): string {
  return num.toLocaleString()
}

function getPercentage(analysis: any): string {
  if (!analysis.total_logs || analysis.total_logs === 0) return '0'
  return ((analysis.anomalies_detected / analysis.total_logs) * 100).toFixed(1)
}

function getAnomalyClass(analysis: any): string {
  const pct = parseFloat(getPercentage(analysis))
  if (pct > 10) return 'high'
  if (pct > 5) return 'medium'
  return 'low'
}

function truncate(str: string, max: number): string {
  return str.length > max ? str.substring(0, max) + '...' : str
}
</script>

<style scoped>
.analysis-history {
  height: 100%;
}

/* Vista compacta */
.analysis-history.compact {
  background: transparent;
}

.history-table {
  font-size: 0.9rem;
}

.filename {
  font-family: monospace;
  font-size: 0.85rem;
}

.actions {
  display: flex;
  gap: 0.25rem;
}

.high {
  color: #dc2626;
  font-weight: 600;
}

.medium {
  color: #f59e0b;
  font-weight: 500;
}

.low {
  color: #10b981;
}

/* Vista original (sidebar) */
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 1rem 1rem;
  border-bottom: 1px solid #f1f5f9;
}

.history-header h3 {
  margin: 0;
  font-size: 0.9rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.header-actions {
  display: flex;
  gap: 0.25rem;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  color: #94a3b8;
  gap: 0.5rem;
}

.empty-state i {
  font-size: 1.5rem;
}

.history-list {
  padding: 0.5rem;
}

.history-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.history-item.active {
  background: #eff6ff;
  border-color: #3b82f6;
}

.item-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.item-main .filename {
  font-weight: 500;
  color: #1e293b;
  font-size: 0.9rem;
}

.anomalies {
  font-size: 0.8rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  background: #f1f5f9;
}

.anomalies.high {
  background: #fef2f2;
  color: #dc2626;
}

.anomalies.medium {
  background: #fffbeb;
  color: #f59e0b;
}

.anomalies.low {
  background: #f0fdf4;
  color: #10b981;
}

.item-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94a3b8;
}
</style>
