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
      <div 
        v-for="result in streamingResults" 
        :key="result.chunk_number"
        class="chunk-result"
      >
        <h5>Chunk {{ result.chunk_number }}</h5>
        <p>Anomalías: {{ result.anomalies.length }}</p>
        <div v-if="result.is_complete" class="complete-indicator">
          ✅ Completado
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAnalysisStore } from '../stores/analysisStore'
import type { StreamResult } from '../stores/analysisStore'

const analysisStore = useAnalysisStore()
const streamingResults = ref<StreamResult[]>([])
const statusInterval = ref<NodeJS.Timeout | null>(null)

const currentJob = computed(() => analysisStore.currentJob)

async function cancelProcessing() {
  if (currentJob.value) {
    try {
      await analysisStore.cancelJob(currentJob.value.job_id)
      console.log('Procesamiento cancelado')
    } catch (error) {
      console.error('Error cancelando:', error)
    }
  }
}

async function startStatusPolling(jobId: string) {
  statusInterval.value = setInterval(async () => {
    try {
      const status = await analysisStore.getJobStatus(jobId)
      analysisStore.currentJob = status
      
      if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
        if (statusInterval.value) {
          clearInterval(statusInterval.value)
          statusInterval.value = null
        }
        
        // Recargar reportes cuando se complete el job
        if (status.status === 'completed') {
          await analysisStore.loadReportsFromDirectory()
        }
      }
    } catch (error) {
      console.error('Error obteniendo estado:', error)
    }
  }, 2000)
}

async function startStreaming(jobId: string) {
  await analysisStore.streamResults(jobId, (result: StreamResult) => {
    streamingResults.value.push(result)
    console.log('Nuevo resultado:', result)
  })
}

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

.chunk-result {
  border: 1px solid #ddd;
  padding: 10px;
  margin: 10px 0;
  border-radius: 5px;
}

.complete-indicator {
  color: #4CAF50;
  font-weight: bold;
}
</style>
