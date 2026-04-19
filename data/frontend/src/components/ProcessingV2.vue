<template>
  <div class="processing-v2">
    <div v-if="currentJob" class="job-status">
      <h3>Procesando: {{ currentJob.job_id }}</h3>
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: `${currentJob.progress * 100}%` }"
        ></div>
      </div>
      <p>Progreso: {{ currentJob.chunks_processed }}/{{ currentJob.total_chunks }} chunks</p>
      <p>Anomalías encontradas: {{ currentJob.anomalies_found }}</p>
      <p>Estado: {{ currentJob.status }}</p>
      
      <button 
        v-if="currentJob.status === 'processing'" 
        @click="cancelProcessing"
        class="cancel-btn"
      >
        Cancelar
      </button>
    </div>
    
    <div v-if="streamingResults.length > 0" class="streaming-results">
      <h4>Resultados en tiempo real:</h4>
      <div class="streaming-summary">
        <p>Total de anomalías detectadas hasta ahora: <strong>{{ accumulatedAnomalies.length }}</strong></p>
      </div>

      <!-- Mensaje de completado -->
      <div v-if="allComplete" class="completion-message">
        <h5>✅ Procesamiento completado</h5>
        <p>Total de anomalías detectadas: <strong>{{ accumulatedAnomalies.length }}</strong></p>
        <Button label="Ver detalles" severity="success" text @click="goToHistory" />
      </div>
      <div 
        v-for="result in streamingResults" 
        :key="result.chunk_number"
        class="chunk-result"
      >
        <h5>Chunk {{ result.chunk_number }}</h5>
        <p>Anomalías: {{ result.anomalies.length }}</p>
        <p>Progreso: {{ Number(result.progress).toFixed(1) }}%</p>
        <div v-if="result.is_complete" class="complete-indicator">
          ✅ Completado
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysisStore'
import { useAuthStore } from '../stores/authStore'
import type { StreamResult } from '../stores/analysisStore'
import Button from 'primevue/button'

const router = useRouter()
const analysisStore = useAnalysisStore()
const authStore = useAuthStore()
const streamingResults = ref<StreamResult[]>([])
const statusInterval = ref<NodeJS.Timeout | null>(null)
const accumulatedAnomalies = ref<any[]>([])

const currentJob = computed(() => analysisStore.currentJob)

// Verificar si todos los resultados están completos
const allComplete = computed(() => {
  return streamingResults.value.length > 0 &&
         streamingResults.value.every(r => r.is_complete)
})

// Funciones de polling y streaming (definidas antes del watch)
async function startStatusPolling(jobId: string) {
  // Limpiar intervalo anterior si existe
  if (statusInterval.value) {
    clearInterval(statusInterval.value)
  }

  statusInterval.value = setInterval(async () => {
    try {
      const status = await analysisStore.getJobStatus(jobId)
      
      // Actualizar job en el store
      if (analysisStore.currentJob) {
        analysisStore.updateCurrentJob({
          ...analysisStore.currentJob,
          ...status
        })
      } else {
        analysisStore.updateCurrentJob(status)
      }
      
      if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
        if (statusInterval.value) {
          clearInterval(statusInterval.value)
          statusInterval.value = null
        }
        
        // Recargar reportes cuando se complete el job
        if (status.status === 'completed' && authStore.selectedProjectId) {
          await analysisStore.loadReportsFromDirectory(authStore.selectedProjectId)
        }
      }
    } catch (error: any) {
      console.error('Error obteniendo estado:', error)
      if (error.response?.status === 403) {
        // Sin permisos, detener polling
        if (statusInterval.value) {
          clearInterval(statusInterval.value)
          statusInterval.value = null
        }
      }
    }
  }, 2000)
}

async function startStreaming(jobId: string) {
  try {
    await analysisStore.streamResults(jobId, (data: any) => {
      if (data.type === 'batch_progress') {
        // Acumular anomalías
        if (data.anomalies && Array.isArray(data.anomalies)) {
          accumulatedAnomalies.value.push(...data.anomalies)
        }
        
        // Actualizar resultados de streaming
        const existingResult = streamingResults.value.find(r => r.chunk_number === data.chunk_number)
        if (existingResult) {
          existingResult.anomalies = data.anomalies || []
          existingResult.progress = data.progress
        } else {
          streamingResults.value.push({
            chunk_number: data.chunk_number,
            anomalies: data.anomalies || [],
            progress: data.progress,
            is_complete: false
          })
        }
      } else if (data.type === 'job_completed') {
        // Marcar todos como completados con progreso al 100%
        streamingResults.value.forEach(r => {
          r.is_complete = true
          r.progress = 100
        })
        // Mostrar resumen final
        const totalAnomalies = data.total_anomalies ?? accumulatedAnomalies.value.length
        console.log('Job completado, total anomalías:', totalAnomalies)
      } else if (data.type === 'chunk_progress') {
        // Actualizar progreso general del procesamiento
        const progress = Math.round((data.current_chunk / data.total_chunks) * 100)
        console.log(`Progreso chunk: ${data.current_chunk}/${data.total_chunks} (${progress}%)`)
        // Crear un resultado temporal para mostrar progreso
        const existingResult = streamingResults.value.find(r => r.chunk_number === data.current_chunk)
        if (!existingResult) {
          streamingResults.value.push({
            chunk_number: data.current_chunk,
            anomalies: [],
            progress: progress,
            is_complete: false
          })
        }
      } else if (data.type === 'stream_started') {
        console.log('Stream iniciado para job:', data.job_id)
      }
    })
  } catch (error: any) {
    console.error('Error en streaming:', error)
    if (error.response?.status === 403) {
      alert('No tienes permiso para ver los resultados de este procesamiento')
    }
  }
}

// Watch para iniciar polling cuando se crea un nuevo job
watch(() => analysisStore.currentJob?.job_id, (newJobId, oldJobId) => {
  if (newJobId && newJobId !== oldJobId) {
    startStatusPolling(newJobId)
    startStreaming(newJobId)
  }
}, { immediate: true })

async function cancelProcessing() {
  if (currentJob.value) {
    try {
      await analysisStore.cancelJob(currentJob.value.job_id)
      console.log('Procesamiento cancelado')
      if (statusInterval.value) {
        clearInterval(statusInterval.value)
        statusInterval.value = null
      }
    } catch (error: any) {
      console.error('Error cancelando:', error)
      if (error.response?.status === 403) {
        alert('No tienes permiso para cancelar este procesamiento')
      } else {
        alert('Error al cancelar el procesamiento')
      }
    }
  }
}

function goToHistory() {
  router.push({ name: 'history' })
}

onMounted(() => {
  // Si ya hay un job activo, iniciar polling y streaming
  if (analysisStore.currentJob?.job_id) {
    startStatusPolling(analysisStore.currentJob.job_id)
    startStreaming(analysisStore.currentJob.job_id)
  }
})

onUnmounted(() => {
  if (statusInterval.value) {
    clearInterval(statusInterval.value)
  }
})
</script>

<style scoped>
.processing-v2 {
  padding: 20px;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  height: 100%;
  background-color: #4CAF50;
  transition: width 0.3s ease;
}

.cancel-btn {
  background-color: #f44336;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  margin-top: 10px;
}

.streaming-results {
  margin-top: 20px;
}

.streaming-summary {
  background-color: #e3f2fd;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 15px;
}

.chunk-result {
  border: 1px solid #ddd;
  padding: 10px;
  margin: 10px 0;
  border-radius: 5px;
  background-color: #f8f9fa;
}

.complete-indicator {
  color: #4CAF50;
  font-weight: bold;
}

.completion-message {
  background-color: #e8f5e9;
  border: 1px solid #4CAF50;
  border-radius: 8px;
  padding: 15px;
  margin: 15px 0;
  text-align: center;
}

.completion-message h5 {
  margin: 0 0 10px 0;
  color: #2e7d32;
  font-size: 1.1rem;
}

.completion-message p {
  margin: 5px 0 15px 0;
  color: #1b5e20;
}
</style>
