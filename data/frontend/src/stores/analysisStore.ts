import { ref, onMounted } from 'vue'
import { defineStore } from 'pinia'
import api from '../services/api'

export interface AnalysisResult {
  id: string;
  timestamp: string;
  fileName: string;
  total_logs: number;
  anomalies_detected: number;
  anomalies: any[];
  report_file: string;
  file_id?: string;
  status?: string;
  total_chunks?: number;
  chunks_processed?: number;
}

// Nuevas interfaces para V2
export interface ProcessingJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  chunks_processed: number;
  total_chunks: number;
  anomalies_found: number;
  estimated_remaining_time?: number;
  error_message?: string;
}

export interface StreamResult {
  chunk_number: number;
  anomalies: any[];
  progress: number;
  is_complete: boolean;
}

export const useAnalysisStore = defineStore('analysis', () => {
  const analysisHistory = ref<AnalysisResult[]>([])
  const currentAnalysis = ref<AnalysisResult | null>(null)
  const isLoading = ref(false)
  
  // Nuevas variables para V2
  const currentJob = ref<ProcessingJob | null>(null)
  const isStreaming = ref(false)
  
  // Función para actualizar el job actual
  function updateCurrentJob(job: ProcessingJob | null) {
    currentJob.value = job
  }

  async function loadReportsFromDirectory(projectId?: string) {
    try {
      isLoading.value = true
      console.log('Cargando reportes desde la base de datos...')
      const params: any = {}
      if (projectId) {
        params.project_id = projectId
      }
      const response = await api.get('/reports', { params })
      const reports = response.data
      console.log('Reportes recibidos desde BD:', reports)
      
      // Procesar y ordenar los reportes por timestamp
      const processedReports = reports
        .map(report => {
          try {
            // Asegurarnos de que las anomalías estén presentes
            const anomalies = Array.isArray(report.anomalies) ? report.anomalies : []
            
            return {
              id: report.id || report.file_id,
              timestamp: report.timestamp || new Date().toISOString(),
              fileName: report.fileName || report.filename || 'Unknown',
              total_logs: report.total_logs || 0,
              anomalies_detected: report.anomalies_detected || anomalies.length,
              anomalies: anomalies,
              report_file: report.report_file,
              file_id: report.file_id || report.id,
              status: report.status,
              total_chunks: report.total_chunks,
              chunks_processed: report.chunks_processed
            }
          } catch (e) {
            console.warn('Error procesando reporte:', e)
            return null
          }
        })
        .filter(r => r !== null)
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

      console.log('Reportes procesados:', processedReports)
      analysisHistory.value = processedReports
      
      // Si hay reportes, establecer el más reciente como actual
      if (processedReports.length > 0) {
        console.log('Estableciendo análisis actual:', processedReports[0])
        setCurrentAnalysis(processedReports[0])
      }
    } catch (error) {
      console.error('Error cargando reportes:', error)
    } finally {
      isLoading.value = false
    }
  }

  function addAnalysis(result: AnalysisResult) {
    console.log('Agregando análisis:', result)
    // Verificar si ya existe un análisis con el mismo ID
    const existingIndex = analysisHistory.value.findIndex(a => a.id === result.id)
    if (existingIndex !== -1) {
      // Actualizar el existente
      analysisHistory.value[existingIndex] = result
    } else {
      // Agregar nuevo al inicio
      analysisHistory.value.unshift(result)
    }
    setCurrentAnalysis(result)
  }

  function setCurrentAnalysis(analysis: AnalysisResult) {
    console.log('Estableciendo análisis actual:', analysis)
    // Crear una nueva referencia del objeto para asegurar la reactividad
    currentAnalysis.value = {
      id: analysis.id,
      timestamp: analysis.timestamp,
      fileName: analysis.fileName,
      total_logs: analysis.total_logs,
      anomalies_detected: analysis.anomalies_detected,
      anomalies: Array.isArray(analysis.anomalies) ? [...analysis.anomalies] : [],
      report_file: analysis.report_file,
      file_id: analysis.file_id,
      status: analysis.status,
      total_chunks: analysis.total_chunks,
      chunks_processed: analysis.chunks_processed
    }
    console.log('Análisis actual establecido:', currentAnalysis.value)
  }

  function clearHistory() {
    analysisHistory.value = []
    currentAnalysis.value = null
  }

  // Nuevas funciones para V2
  async function processFileV2(file: File, projectId?: string): Promise<string> {
    try {
      isLoading.value = true
      const formData = new FormData()
      formData.append('file', file)
      if (projectId) {
        formData.append('project_id', projectId)
      }
      
      const response = await api.post('/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      const result = response.data
      currentJob.value = {
        job_id: result.job_id,
        status: result.status,
        progress: 0,
        chunks_processed: 0,
        total_chunks: result.total_chunks,
        anomalies_found: 0
      }
      
      return result.job_id
    } catch (error) {
      console.error('Error procesando archivo:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }
  
  // Función para obtener estado
  async function getJobStatus(jobId: string): Promise<ProcessingJob> {
    const response = await api.get(`/status/${jobId}`)
    return response.data
  }
  
  // Función para streaming de resultados
  async function streamResults(jobId: string, onChunk: (result: StreamResult) => void) {
    try {
      isStreaming.value = true
      const token = localStorage.getItem('auth_token')
      
      const response = await fetch(`/api/results/${jobId}/stream`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      if (!reader) return
      
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onChunk(data)
            } catch (e) {
              console.warn('Error parseando chunk:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error en streaming:', error)
    } finally {
      isStreaming.value = false
    }
  }
  
  // Función para cancelar job
  async function cancelJob(jobId: string) {
    try {
      const response = await api.post(`/cancel/${jobId}`)
      return response.data
    } catch (error) {
      console.error('Error cancelando job:', error)
      throw error
    }
  }

  // No cargar automáticamente - se cargará después de autenticación

  return {
    analysisHistory,
    currentAnalysis,
    isLoading,
    addAnalysis,
    setCurrentAnalysis,
    clearHistory,
    loadReportsFromDirectory,
    // Nuevas exportaciones para V2
    currentJob,
    isStreaming,
    processFileV2,
    getJobStatus,
    streamResults,
    cancelJob,
    updateCurrentJob
  }
})