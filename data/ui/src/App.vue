<template>
  <div class="app-container">
    <aside class="side-panel">
      <div class="upload-section">
        <FileUpload
          :maxFileSize="30000000"
          :multiple="false"
          accept=".txt,.log,.json"
          :auto="true"
          @select="onFileSelect"
          @upload="onFileUpload"
          :customUpload="true"
          uploadLabel="Analizar"
          chooseLabel="Seleccionar archivo"
          cancelLabel="Cancelar"
        >
          <template #empty>
            <p>Arrastra y suelta un archivo aquí o haz clic para seleccionar</p>
          </template>
        </FileUpload>
      </div>

      <div v-if="currentAnalysis" class="analysis-summary">
        <h3>Resumen del Análisis</h3>
        <div class="summary-stats">
          <div class="stat-item">
            <label>Total de Logs:</label>
            <span>{{ currentAnalysis.total_logs }}</span>
          </div>
          <div class="stat-item">
            <label>Anomalías:</label>
            <span>{{ currentAnalysis.anomalies_detected }}</span>
          </div>
          <div class="stat-item">
            <label>Porcentaje:</label>
            <span>{{ ((currentAnalysis.anomalies_detected / currentAnalysis.total_logs) * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <div class="filters-section" v-if="currentAnalysis && currentAnalysis.anomalies.length > 0">
        <h3>Filtros</h3>
        <div class="filter-group">
          <label>Nivel de Anomalía:</label>
          <InputNumber v-model="scoreFilter" :min="0" :max="1" :step="0.1" />
          <small>{{ scoreFilter.toFixed(1) }}</small>
        </div>
      </div>

      <AnalysisHistory />
    </aside>

    <main class="main-content">
      
      <div class="tabs-container">
        <div class="tabs-header">
          <button 
            class="tab-button" 
            :class="{ active: activeTab === 'analysis' }"
            @click="activeTab = 'analysis'"
          >
            <i class="pi pi-chart-bar"></i>
            Análisis
          </button>
          <button 
            class="tab-button" 
            :class="{ active: activeTab === 'monitoring' }"
            @click="activeTab = 'monitoring'"
          >
            <i class="pi pi-cog"></i>
            Monitoreo
          </button>
        </div>

        <div class="tab-content">
          
          <div v-if="activeTab === 'analysis'" class="tab-panel">
            
            <ProcessingV2 v-if="useV2Processing && store.currentJob" />
            
            <div v-else-if="loading" class="progress-overlay">
              <ProgressSpinner />
              <div class="progress-info">
                <p>{{ typeof loading === 'string' ? loading : 'Analizando logs...' }}</p>
                <div v-if="chunkInfo" class="chunk-details">
                  <small>Chunk {{ chunkInfo.current }}/{{ chunkInfo.total }}</small>
                  <div class="progress-bar">
                    <div 
                      class="progress-fill" 
                      :style="{ width: ((chunkInfo.current / chunkInfo.total) * 100) + '%' }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="currentAnalysis" class="anomalies-container">
        <div class="analysis-header">
          <h2>Resultados del Análisis</h2>
          <div class="analysis-stats">
            <div class="stat">
              <label>Total Logs</label>
              <span>{{ currentAnalysis.total_logs }}</span>
            </div>
            <div class="stat">
              <label>Anomalías</label>
              <span>{{ currentAnalysis.anomalies_detected }}</span>
            </div>
            <div class="stat">
              <label>Porcentaje</label>
              <span>{{ ((currentAnalysis.anomalies_detected / currentAnalysis.total_logs) * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <div class="anomalies-list">
          <div class="no-details-message">
            <h3>Anomalías Detectadas</h3>
            <p>Se detectaron {{ currentAnalysis.anomalies_detected }} anomalías de {{ currentAnalysis.total_logs }} logs totales.</p>
            <p>Porcentaje de anomalías: {{ ((currentAnalysis.anomalies_detected / currentAnalysis.total_logs) * 100).toFixed(1) }}%</p>
            <p v-if="currentAnalysis.total_chunks">Chunks procesados: {{ currentAnalysis.chunks_processed }}/{{ currentAnalysis.total_chunks }}</p>
            <p>Estado: {{ currentAnalysis.status || 'completed' }}</p>
            <p>Archivo: {{ currentAnalysis.fileName }}</p>
            <p>Análisis realizado el: {{ new Date(currentAnalysis.timestamp).toLocaleString() }}</p>
          </div>
          
          <div v-if="currentAnalysis.anomalies && currentAnalysis.anomalies.length > 0">
            <h4>Detalles de Anomalías ({{ currentAnalysis.anomalies.length }} encontradas):</h4>
            <div
              v-for="(anomaly, index) in currentAnalysis.anomalies"
              :key="index"
              class="anomaly-card"
            >
              <div class="anomaly-header">
                <span :class="getScoreClass(anomaly.score || anomaly.anomaly_score)" class="score-badge">
                  {{ (anomaly.score || anomaly.anomaly_score).toFixed(3) }}
                </span>
                <span class="timestamp">{{ formatTimestamp(anomaly.timestamp) }}</span>
              </div>
              <div class="anomaly-content">
                <pre class="log-entry">{{ anomaly.log_entry }}</pre>
                <p class="explanation">{{ anomaly.explanation }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
            <i class="pi pi-file-import text-6xl text-gray-300"></i>
            <p v-if="!currentAnalysis">Selecciona un archivo para comenzar el análisis</p>
            <p v-else>No se encontraron anomalías en este análisis</p>
          </div>
          </div>

          
          <div v-if="activeTab === 'monitoring'" class="tab-panel">
            <MonitoringDashboard />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAnalysisStore } from './stores/analysisStore'
import { formatTimestamp } from './utils/formatters'
import AnalysisHistory from './components/AnalysisHistory.vue'
import ProcessingV2 from './components/ProcessingV2.vue'
import MonitoringDashboard from './components/MonitoringDashboard.vue'
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import InputNumber from 'primevue/inputnumber'

const store = useAnalysisStore()
const loading = ref<boolean | string>(false)
const scoreFilter = ref(0.5)
const chunkInfo = ref<{current: number, total: number} | null>(null)
const activeTab = ref<'analysis' | 'monitoring'>('analysis')

// Variable para controlar qué versión usar
const useV2Processing = ref(true) // Cambiar a true para usar V2

const currentAnalysis = computed(() => store.currentAnalysis)

const filteredAnomalies = computed(() => {
  if (!currentAnalysis.value || !currentAnalysis.value.anomalies) return []
  return currentAnalysis.value.anomalies.filter(
    anomaly => (anomaly.score || anomaly.anomaly_score) >= scoreFilter.value
  ).sort((a, b) => (b.score || b.anomaly_score) - (a.score || a.anomaly_score))
})

function getScoreClass(score: number): string {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.5) return 'score-medium'
  return 'score-low'
}

async function onFileSelect(event: any) {
  const file = event.files[0]
  if (!file) return

  if (useV2Processing.value) {
    // Usar procesamiento V2
    try {
      loading.value = 'Iniciando procesamiento V2...'
      const jobId = await store.processFileV2(file)
      console.log('Job iniciado:', jobId)
      loading.value = false
    } catch (error) {
      console.error('Error durante el procesamiento V2:', error)
      loading.value = false
    }
  } else {
    // Usar procesamiento V1 (original)
    loading.value = 'Preparando archivo...'
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`)
      }

      const result = await response.json()
      store.addAnalysis(result)
    } catch (error) {
      console.error('Error durante el análisis:', error)
    } finally {
      loading.value = false
    }
  }
}

function onFileUpload(event: any) {
  // Handle file upload if needed
}
</script>

<style>
.app-container {
  display: flex;
  height: 100vh;
  background-color: #f5f5f5;
}

.side-panel {
  width: 300px;
  padding: 1rem;
  background-color: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
}

.main-content {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  position: relative;
}

.upload-section {
  margin-bottom: 1rem;
}

.analysis-summary {
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.summary-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters-section {
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.progress-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
}

.progress-info {
  text-align: center;
}

.chunk-details {
  width: 200px;
  text-align: center;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 0.5rem;
}

.progress-fill {
  height: 100%;
  background-color: #2196f3;
  transition: width 0.3s ease;
}

.anomalies-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.analysis-header {
  background-color: white;
  padding: 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.analysis-stats {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat label {
  font-size: 0.875rem;
  color: #666;
}

.stat span {
  font-size: 1.25rem;
  font-weight: 600;
}

.anomalies-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.anomaly-card {
  background-color: white;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.anomaly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.score-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
}

.score-high {
  background-color: #fecaca;
  color: #dc2626;
}

.score-medium {
  background-color: #fed7aa;
  color: #ea580c;
}

.score-low {
  background-color: #bfdbfe;
  color: #2563eb;
}

.timestamp {
  font-size: 0.875rem;
  color: #666;
}

.anomaly-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.log-entry {
  background-color: #f8f9fa;
  padding: 0.5rem;
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
}

.explanation {
  color: #4b5563;
  font-size: 0.875rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: #6b7280;
}

.no-details-message {
  padding: 2rem;
  text-align: center;
  color: #666;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-top: 1rem;
}

.no-details-message p {
  margin: 0.5rem 0;
}

/* Estilos para Tabs */
.tabs-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.tabs-header {
  display: flex;
  background: white;
  border-bottom: 1px solid #e0e0e0;
  padding: 0;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
  color: #666;
  font-weight: 500;
}

.tab-button:hover {
  background: #f8f9fa;
  color: #2c3e50;
}

.tab-button.active {
  background: #f8f9fa;
  color: #2196f3;
  border-bottom-color: #2196f3;
}

.tab-button i {
  font-size: 1.1rem;
}

.tab-content {
  flex: 1;
  overflow: hidden;
}

.tab-panel {
  height: 100%;
  overflow-y: auto;
}
</style>