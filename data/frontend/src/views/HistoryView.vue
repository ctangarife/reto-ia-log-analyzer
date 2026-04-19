<template>
  <div class="history-view">
    <!-- Header -->
    <div class="history-header">
      <div class="header-main">
        <h2>Historial de Análisis</h2>
        <div v-if="authStore.selectedProjectId" class="project-badge">
          <i class="pi pi-folder"></i>
          {{ getProjectName(authStore.selectedProjectId) }}
        </div>
      </div>
      <div class="header-actions">
        <Button
          icon="pi pi-refresh"
          :loading="isLoading"
          @click="loadHistory"
          v-tooltip="'Recargar historial'"
        />
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!authStore.selectedProjectId" class="empty-selection">
      <i class="pi pi-folder-open text-4xl"></i>
      <p>Selecciona un proyecto para ver su historial</p>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Loading -->
      <div v-if="isLoading && analysisHistory.length === 0" class="loading-state">
        <ProgressSpinner />
        <p>Cargando historial...</p>
      </div>

      <!-- Empty history -->
      <div v-else-if="analysisHistory.length === 0" class="empty-history">
        <i class="pi pi-inbox text-4xl"></i>
        <h3>Sin análisis previos</h3>
        <p>No hay análisis registrados para este proyecto.</p>
        <Button label="Ir a Análisis" @click="goToAnalysis" />
      </div>

      <!-- History table -->
      <div v-else class="history-content">
        <DataTable
          :value="analysisHistory"
          :loading="isLoading"
          paginator
          :rows="15"
          :rowsPerPageOptions="[10, 15, 25, 50]"
          sortField="timestamp"
          :sortOrder="-1"
          stripedRows
          class="history-table"
        >
          <Column field="timestamp" header="Fecha" sortable>
            <template #body="{ data }">
              <span class="date-cell">
                <i class="pi pi-calendar"></i>
                {{ formatDateTime(data.timestamp) }}
              </span>
            </template>
          </Column>
          <Column field="fileName" header="Archivo" sortable>
            <template #body="{ data }">
              <span class="filename-cell">{{ data.fileName || 'Sin nombre' }}</span>
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
          <Column header="Acciones" :exportable="false" style="width: 140px;">
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
      </div>
    </template>

    <!-- Confirm dialogs -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysisStore'
import { useAuthStore } from '../stores/authStore'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { jobService } from '../services/jobService'
import { storeToRefs } from 'pinia'

const router = useRouter()
const store = useAnalysisStore()
const authStore = useAuthStore()
const confirm = useConfirm()
const toast = useToast()

const { analysisHistory, isLoading } = storeToRefs(store)

const deletingId = ref<string | null>(null)
const reanalyzingId = ref<string | null>(null)

// Load history on mount and project change
onMounted(async () => {
  if (authStore.selectedProjectId) {
    await loadHistory()
  }
})

watch(() => authStore.selectedProjectId, async (newProjectId) => {
  if (newProjectId) {
    await loadHistory()
  }
})

async function loadHistory() {
  if (!authStore.selectedProjectId) return
  await store.loadReportsFromDirectory(authStore.selectedProjectId)
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

function getAnomalyClass(analysis: any): string {
  const pct = parseFloat(getPercentage(analysis))
  if (pct > 10) return 'high'
  if (pct > 5) return 'medium'
  return 'low'
}

function getProjectName(projectId: string): string {
  for (const wsId in authStore.projects) {
    const project = authStore.projects[wsId]?.find((p: any) => p.project_id === projectId)
    if (project) return project.name
  }
  return 'Proyecto desconocido'
}

function viewDetails(analysis: any) {
  store.setCurrentAnalysis(analysis)
  router.push({ name: 'analysis-detail', params: { id: analysis.id } })
}

function goToAnalysis() {
  router.push({ name: 'analysis' })
}

async function deleteAnalysis(analysis: any) {
  deletingId.value = analysis.id

  try {
    await jobService.deleteJob(analysis.id)

    if (authStore.selectedProjectId) {
      await store.loadReportsFromDirectory(authStore.selectedProjectId)
    }

    if (store.currentAnalysis?.id === analysis.id) {
      store.setCurrentAnalysis(null)
    }

    toast.add({
      severity: 'success',
      summary: 'Análisis eliminado',
      life: 3000
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error al eliminar',
      detail: error.response?.data?.detail || 'Intenta nuevamente',
      life: 5000
    })
  } finally {
    deletingId.value = null
  }
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

    await new Promise(resolve => setTimeout(resolve, 1000))

    store.updateCurrentJob({
      job_id: result.job_id,
      status: result.status as any,
      progress: 0,
      chunks_processed: 0,
      total_chunks: result.total_chunks,
      anomalies_found: 0
    })

    if (authStore.selectedProjectId) {
      await store.loadReportsFromDirectory(authStore.selectedProjectId)
    }

    toast.add({
      severity: 'success',
      summary: 'Re-análisis iniciado',
      life: 3000
    })

    router.push({ name: 'analysis' })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Error al iniciar re-análisis',
      detail: error.response?.data?.detail || 'Intenta nuevamente',
      life: 5000
    })
  } finally {
    reanalyzingId.value = null
  }
}

function confirmReanalyze(analysis: any) {
  confirm.require({
    message: `¿Re-analizar el archivo "${analysis.fileName || 'Sin nombre'}"?`,
    header: 'Confirmar re-análisis',
    icon: 'pi pi-refresh',
    acceptLabel: 'Re-analizar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await reanalyzeJob(analysis)
    }
  })
}
</script>

<style scoped>
.history-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Header */
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  border-radius: 12px;
  padding: 1rem 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header-main {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.history-header h2 {
  margin: 0;
  color: #1e293b;
}

.project-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 1rem;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 20px;
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

/* Empty states */
.empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 1rem;
  color: #94a3b8;
}

.empty-selection i {
  color: #cbd5e1;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 1rem;
  color: #94a3b8;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 1rem;
  text-align: center;
  color: #94a3b8;
}

.empty-history h3 {
  margin: 0;
  color: #1e293b;
}

.empty-history p {
  margin: 0;
  color: #64748b;
}

/* History table */
.history-content {
  background: white;
  border-radius: 12px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.date-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #64748b;
}

.filename-cell {
  font-family: monospace;
  font-size: 0.85rem;
  color: #1e293b;
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
</style>
