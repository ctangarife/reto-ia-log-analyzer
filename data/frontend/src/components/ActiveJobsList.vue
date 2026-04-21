<template>
  <div v-if="activeJobs.length > 0" class="active-jobs-panel">
    <div class="panel-header">
      <h4>
        <i class="pi pi-spin pi-cog"></i>
        Procesos Activos
      </h4>
      <button
        class="refresh-btn"
        @click="refreshJobs"
        title="Actualizar lista"
      >
        <i class="pi pi-refresh"></i>
      </button>
    </div>

    <div class="jobs-list">
      <div
        v-for="job in activeJobs"
        :key="job.id"
        class="job-item"
        :class="{ 'job-current': isCurrentJob(job.id) }"
      >
        <div class="job-info">
          <div class="job-header">
            <i class="pi pi-file-pdf"></i>
            <span class="job-filename">{{ job.filename }}</span>
            <span
              v-if="isCurrentJob(job.id)"
              class="job-tag job-tag-current"
            >
              Actual
            </span>
          </div>

          <div class="job-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: job.progress + '%' }"></div>
            </div>
            <span class="job-stats">
              {{ job.chunks_processed }}/{{ job.total_chunks }} chunks • {{ job.progress }}%
            </span>
          </div>

          <div class="job-meta">
            <small class="job-time">
              <i class="pi pi-clock"></i>
              {{ formatElapsedTime(job.elapsed_seconds) }}
            </small>
            <small class="job-status">
              {{ getStatusText(job.status) }}
            </small>
          </div>
        </div>

        <div class="job-actions">
          <button
            v-if="!isCurrentJob(job.id)"
            class="connect-btn"
            @click="connectToJob(job.id)"
          >
            <i class="pi pi-eye"></i>
            Ver progreso
          </button>
          <button
            v-else
            class="connect-btn connect-btn-connected"
            disabled
          >
            <i class="pi pi-check"></i>
            Conectado
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="empty-state">
    <div class="spinner"></div>
    <small>Verificando procesos...</small>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useAnalysisStore } from '../stores/analysisStore'
import { jobService, type ActiveJob } from '../services/jobService'

const router = useRouter()
const authStore = useAuthStore()
const analysisStore = useAnalysisStore()

const activeJobs = ref<ActiveJob[]>([])
const loading = ref(false)
let refreshInterval: number | null = null

const currentJobId = computed(() => analysisStore.currentJob?.job_id)

const isCurrentJob = (jobId: string) => {
  return currentJobId.value === jobId
}

const refreshJobs = async () => {
  if (!authStore.selectedProjectId) return

  try {
    activeJobs.value = await jobService.getActiveJobs(authStore.selectedProjectId)
  } catch (error: any) {
    console.error('Error obteniendo jobs activos:', error)
  }
}

const connectToJob = (jobId: string) => {
  // Conectar al job existente
  analysisStore.updateCurrentJob({
    job_id: jobId,
    filename: activeJobs.value.find(j => j.id === jobId)?.filename || '',
    status: 'processing',
    total_chunks: 0,
    chunks_processed: 0,
    anomalies_found: 0,
    progress: 0
  })

  // Navegar a la vista de análisis
  router.push({ name: 'analysis' })
}

const formatElapsedTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

const getStatusText = (status: string): string => {
  const statusMap: Record<string, string> = {
    pending: 'En cola',
    processing: 'Procesando...'
  }
  return statusMap[status] || status
}

onMounted(() => {
  if (authStore.selectedProjectId) {
    refreshJobs()
  }
  // Actualizar cada 5 segundos
  refreshInterval = window.setInterval(refreshJobs, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.active-jobs-panel {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  margin-bottom: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.panel-header h4 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.panel-header h4 i {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.refresh-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  padding: 6px 10px;
  cursor: pointer;
  color: white;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.jobs-list {
  padding: 12px;
}

.job-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 8px;
  background: #fafafa;
  transition: all 0.2s;
}

.job-item:hover {
  background: #f0f0f0;
  border-color: #667eea;
}

.job-item.job-current {
  background: #e8f5e9;
  border-color: #4caf50;
}

.job-info {
  flex: 1;
}

.job-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.job-header i {
  color: #667eea;
}

.job-filename {
  font-weight: 500;
  color: #333;
  word-break: break-all;
  font-size: 13px;
}

.job-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.job-tag-current {
  background: #4caf50;
  color: white;
}

.job-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.progress-bar {
  flex: 1;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

.job-stats {
  font-size: 11px;
  color: #666;
  white-space: nowrap;
}

.job-meta {
  display: flex;
  gap: 12px;
}

.job-time,
.job-status {
  font-size: 11px;
  color: #888;
}

.job-time i {
  margin-right: 4px;
}

.job-actions {
  margin-left: 12px;
}

.connect-btn {
  padding: 6px 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.connect-btn:hover {
  background: #5568d3;
}

.connect-btn-connected {
  background: #4caf50;
  cursor: default;
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: #888;
}

.spinner {
  width: 30px;
  height: 30px;
  margin: 0 auto 10px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.empty-state small {
  display: block;
  margin-top: 8px;
}
</style>
