<template>
  <div class="app">
    <header class="header">
      <h1>Detector de Anomalías en Logs</h1>
      <p class="subtitle">Sube un archivo de logs para detectar anomalías usando IA</p>
    </header>

    <main class="main">
      <div class="content-layout">
        <!-- Panel izquierdo: Historial -->
        <aside class="history-panel">
          <AnalysisHistory />
        </aside>

        <!-- Panel derecho: Carga y resultados -->
        <div class="main-panel">
          <div class="upload-container">
            <FileUpload
              mode="advanced"
              :multiple="false"
              accept=".txt,.json,.log"
              :maxFileSize="100000000"
              @select="onFileSelect"
              :auto="true"
              chooseLabel="Seleccionar archivo"
              uploadLabel="Analizar"
              cancelLabel="Cancelar"
              :showUploadButton="false"
              :showCancelButton="false"
              :customUpload="true"
            >
              <template #empty>
                <div class="upload-placeholder">
                  <i class="pi pi-file text-5xl"></i>
                  <span>Arrastra y suelta tu archivo aquí o haz clic para seleccionar</span>
                  <small>Máximo 100MB (se procesará en chunks de 500KB) - Formatos: .txt, .json, .log</small>
                </div>
              </template>
            </FileUpload>
          </div>

          <div v-if="loading" class="analysis-status">
            <div class="progress-info">
              <ProgressSpinner />
              <p class="progress-text">{{ typeof loading === 'string' ? loading : 'Analizando logs con IA...' }}</p>
              <div v-if="chunkInfo" class="chunk-info">
                <p>Procesando chunk {{ chunkInfo.current }} de {{ chunkInfo.total }}</p>
                <p>Tamaño del chunk: {{ formatBytes(chunkInfo.size) }}</p>
                <p>Líneas: {{ chunkInfo.startLine }} - {{ chunkInfo.endLine }} de {{ chunkInfo.totalLines }}</p>
              </div>
            </div>
          </div>

          <div v-if="currentAnalysis" class="analysis-results">
            <div class="results-header">
              <h2>Resultados del Análisis</h2>
              <div class="results-meta">
                <span class="total-logs">Total logs: {{ currentAnalysis.total_logs }}</span>
                <span class="anomalies">Anomalías: {{ currentAnalysis.anomalies.length }}</span>
                <span class="percentage">{{ ((currentAnalysis.anomalies.length / currentAnalysis.total_logs) * 100).toFixed(1) }}%</span>
              </div>
            </div>

            <div class="anomalies-list">
              <TransitionGroup name="list">
                <div v-for="anomaly in currentAnalysis.anomalies" :key="anomaly.log_entry" class="anomaly-card">
                  <div class="anomaly-header">
                    <span :class="getScoreClass(anomaly.anomaly_score)" class="score-badge">
                      {{ (anomaly.anomaly_score).toFixed(3) }}
                    </span>
                  </div>
                  <div class="anomaly-content">
                    <pre class="log-entry">{{ anomaly.log_entry }}</pre>
                    <p class="explanation">{{ anomaly.explanation }}</p>
                  </div>
                </div>
              </TransitionGroup>
            </div>
          </div>

          <div v-if="!loading && !currentAnalysis" class="empty-results">
            <i class="pi pi-folder-open" style="font-size: 3rem; color: #ccc;"></i>
            <p>Selecciona un análisis del historial o sube un nuevo archivo para comenzar</p>
          </div>

          <div v-if="error" class="error-message">
            <Message severity="error" :closable="false">{{ error }}</Message>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAnalysisStore } from './stores/analysisStore'
import AnalysisHistory from './components/AnalysisHistory.vue'
import { splitLogFile, createChunkFile } from './utils/fileChunker'

interface Results {
  total_logs: number;
  anomalies_detected: number;
  anomalies: any[];
  report_file: string;
  chunk_info: any;
}

const loading = ref<boolean | string>(false)
const error = ref('')
const chunkInfo = ref<any>(null)

// Store para el historial de análisis
const analysisStore = useAnalysisStore()
const { currentAnalysis } = storeToRefs(analysisStore)

// Variables reactivas para acumular resultados
const accumulator = ref({
  allResults: [] as any[],
  totalLogs: 0,
  totalAnomalies: 0,
  fileName: ''
})

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getScoreClass = (score) => {
  if (score < -0.3) return 'high-risk'
  if (score < -0.2) return 'medium-risk'
  return 'low-risk'
}

const onFileSelect = async (event) => {
    try {
      const file = event.files[0]
      // Reiniciar estado
      loading.value = true
      error.value = ''
      accumulator.value = {
        allResults: [],
        totalLogs: 0,
        totalAnomalies: 0,
        fileName: file.name
      }
    console.log('Archivo seleccionado:', {
      name: file.name,
      size: file.size,
      type: file.type
    })

    loading.value = 'Dividiendo archivo en chunks...'
    const chunks = await splitLogFile(file)
    console.log('Chunks generados:', chunks.map(chunk => ({
      startLine: chunk.startLine,
      endLine: chunk.endLine,
      totalLines: chunk.totalLines,
      size: new Blob([chunk.content]).size,
      contentPreview: chunk.content.slice(0, 100) + '...'
    })))
    
    const allResults = []
    let totalLogs = 0
    let totalAnomalies = 0
    
    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i]
      const chunkFile = createChunkFile(chunk)
      
      // Actualizar información del chunk actual
      chunkInfo.value = {
        current: i + 1,
        total: chunks.length,
        size: new Blob([chunk.content]).size,
        startLine: chunk.startLine + 1,
        endLine: chunk.endLine + 1,
        totalLines: chunk.totalLines
      }
      
      // Actualizar estado de progreso
      loading.value = `Analizando chunk ${i + 1} de ${chunks.length}...`
      
      try {
        const formData = new FormData()
        formData.append('file', chunkFile)
        
        console.log('Enviando chunk:', {
          fileName: chunkFile.name,
          fileSize: chunkFile.size,
          fileType: chunkFile.type,
          content: chunkFile.size > 1000 ? 
            chunkFile.text().then(text => text.substring(0, 100) + '...') : 
            chunkFile.text()
        })
        
        // Configurar para recibir streaming de datos
        const response = await fetch('/api/detect', {
          method: 'POST',
          body: formData
        })

        // Crear un reader para procesar el stream
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        
        if (!reader) {
          throw new Error('No se pudo iniciar el streaming')
        }

        // Procesar el stream
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          // Decodificar y procesar cada línea
          const text = decoder.decode(value)
          const lines = text.split('\n').filter(line => line.trim())
          
          for (const line of lines) {
            try {
              const partialResult = JSON.parse(line)
              console.log('Resultado parcial recibido:', partialResult)
              
              // Actualizar progreso
              if (partialResult.processed_percentage) {
                loading.value = `Procesando anomalías: ${Math.round(partialResult.processed_percentage)}%`
              }
              
              // Actualizar resultados
              // Asegurarnos de que partialResult tiene la estructura esperada
              if (partialResult && typeof partialResult === 'object') {
                // Agregar nuevas anomalías si existen
                if (Array.isArray(partialResult.anomalies)) {
                  accumulator.value.allResults.push(...partialResult.anomalies);
                }

                // Actualizar contadores
                accumulator.value.totalLogs = partialResult.total_logs || 0;
                accumulator.value.totalAnomalies = partialResult.anomalies_detected || 0;
                
                // Crear o actualizar el análisis en el store
                const analysisResult = {
                  id: `${accumulator.value.fileName}_${Date.now()}`,
                  timestamp: new Date().toISOString(),
                  fileName: accumulator.value.fileName,
                  total_logs: accumulator.value.totalLogs,
                  anomalies_detected: accumulator.value.totalAnomalies,
                  anomalies: accumulator.value.allResults,
                  report_file: partialResult.report_file || ''
                }
                
                analysisStore.addAnalysis(analysisResult)

                // Log para debugging
                console.log('Estado actual:', {
                  totalLogs: accumulator.value.totalLogs,
                  totalAnomalies: accumulator.value.totalAnomalies,
                  anomaliesCount: accumulator.value.allResults.length,
                  lastResult: partialResult
                });
              }
            } catch (e) {
              console.warn('Error procesando línea:', e)
            }
          }
        }
      } catch (err) {
        error.value = `Error en chunk ${i + 1}/${chunks.length} (líneas ${chunkInfo.value.startLine}-${chunkInfo.value.endLine}): ${err.response?.data?.detail || err.message}`
        throw err // Detener el procesamiento
      }
    }
    
    // Finalizar el análisis actual
    const finalAnalysis = {
      id: `${accumulator.value.fileName}_${Date.now()}`,
      timestamp: new Date().toISOString(),
      fileName: accumulator.value.fileName,
      total_logs: accumulator.value.totalLogs,
      anomalies_detected: accumulator.value.totalAnomalies,
      anomalies: accumulator.value.allResults.sort((a, b) => b.anomaly_score - a.anomaly_score),
      report_file: accumulator.value.reportFile || ''
    }
    
    // Actualizar el store con el análisis completo
    analysisStore.addAnalysis(finalAnalysis)
    
  } catch (err) {
    error.value = 'Error al procesar el archivo: ' + (err.response?.data?.detail || err.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.app {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.content-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 2rem;
  align-items: start;
  margin-top: 2rem;
}

.history-panel {
  position: sticky;
  top: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  max-height: calc(100vh - 4rem);
  overflow-y: auto;
}

.main-panel {
  min-width: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  padding: 1.5rem;
}

.header {
  text-align: center;
  margin-bottom: 3rem;
}

.header h1 {
  margin: 0;
  color: #2c3e50;
}

.subtitle {
  color: #666;
  margin-top: 0.5rem;
}

.upload-container {
  max-width: 600px;
  margin: 0 auto 2rem;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
  text-align: center;
  color: #666;
}

.upload-placeholder small {
  color: #999;
}

.analysis-status {
  text-align: center;
  margin: 2rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.progress-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.progress-text {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0;
}

.chunk-info {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 0.5rem;
  text-align: left;
}

.chunk-info p {
  margin: 0.25rem 0;
  color: #666;
  font-family: monospace;
}

.analysis-results {
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.results-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

.results-header h2 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.results-meta {
  display: flex;
  gap: 2rem;
  font-size: 1.1rem;
}

.total-logs {
  color: #2196f3;
}

.anomalies {
  color: #f44336;
}

.percentage {
  color: #4caf50;
  font-weight: 500;
}

.empty-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 4rem;
  text-align: center;
  color: #666;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.anomalies-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.anomaly-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  transition: all 0.3s ease;
}

.anomaly-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
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
  font-family: monospace;
  font-size: 0.9rem;
}

.high-risk {
  background: #ffebee;
  color: #d32f2f;
}

.medium-risk {
  background: #fff3e0;
  color: #f57c00;
}

.low-risk {
  background: #e8f5e9;
  color: #388e3c;
}

.log-entry {
  background: #f5f5f5;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
  margin: 0.5rem 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.explanation {
  color: #666;
  font-size: 0.95rem;
  margin: 0.5rem 0 0 0;
}

/* Animaciones */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

.list-move {
  transition: transform 0.5s ease;
}

.error-message {
  max-width: 600px;
  margin: 1rem auto;
}

.summary-card {
  max-width: 800px;
  margin: 0 auto 2rem;
}

.summary-stats {
  display: flex;
  justify-content: space-around;
  padding: 1rem 0;
}

.stat {
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #2c3e50;
}

.stat-label {
  color: #666;
  margin-top: 0.5rem;
}

.anomalies-section {
  margin-top: 3rem;
}

.anomalies-section h2 {
  text-align: center;
  color: #2c3e50;
  margin-bottom: 2rem;
}

.anomaly-card {
  margin-bottom: 1.5rem;
}

.anomaly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.anomaly-index {
  font-weight: bold;
  color: #666;
}

.anomaly-score {
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  font-weight: bold;
}

.high-risk {
  background-color: #ffebee;
  color: #d32f2f;
}

.medium-risk {
  background-color: #fff3e0;
  color: #f57c00;
}

.low-risk {
  background-color: #e8f5e9;
  color: #388e3c;
}

.log-content {
  margin-top: 1rem;
}

.log-content h3 {
  color: #2c3e50;
  font-size: 1rem;
  margin: 1rem 0 0.5rem;
}

.log-content pre {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
}

.explanation {
  color: #2c3e50;
  line-height: 1.6;
  margin: 0.5rem 0;
  font-style: italic;
}
</style>