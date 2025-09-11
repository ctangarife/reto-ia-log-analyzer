import { ref, onMounted } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios'

export interface AnalysisResult {
  id: string;
  timestamp: string;
  fileName: string;
  total_logs: number;
  anomalies_detected: number;
  anomalies: any[];
  report_file: string;
  file_id?: string;
}

export interface CombinedAnalysis {
  total_logs: number;
  anomalies_detected: number;
  anomalies: any[];
  analyses: AnalysisResult[];
}

export const useAnalysisStore = defineStore('analysis', () => {
  const analysisHistory = ref<AnalysisResult[]>([])
  const currentAnalysis = ref<AnalysisResult | null>(null)
  const isLoading = ref(false)

  async function loadReportsFromDirectory() {
    try {
      isLoading.value = true
      console.log('Cargando reportes...')
      const response = await fetch('/api/reports')
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status} ${response.statusText}`)
      }
      const reports = await response.json()
      console.log('Reportes recibidos:', reports)
      
      // Procesar y ordenar los reportes por timestamp
      const processedReports = reports
        .map(report => {
          try {
            return {
              ...report,
              timestamp: report.timestamp || new Date(report.report_file.split('_')[2].replace('.json', '')).toISOString(),
              id: report.report_file.split('_report_')[0]
            }
          } catch (e) {
            console.warn('Error procesando reporte:', e)
            return null
          }
        })
        .filter(r => r !== null)
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

      analysisHistory.value = processedReports
      
      // Si hay reportes, establecer el más reciente como actual
      if (processedReports.length > 0) {
        currentAnalysis.value = processedReports[0]
      }
    } catch (error) {
      console.error('Error cargando reportes:', error)
    } finally {
      isLoading.value = false
    }
  }

  function addAnalysis(result: AnalysisResult) {
    // Verificar si ya existe un análisis con el mismo ID
    const existingIndex = analysisHistory.value.findIndex(a => a.id === result.id)
    if (existingIndex !== -1) {
      // Actualizar el existente
      analysisHistory.value[existingIndex] = result
    } else {
      // Agregar nuevo al inicio
      analysisHistory.value.unshift(result)
    }
    currentAnalysis.value = result
  }

  function setCurrentAnalysis(fileId: string) {
    // Encontrar todos los análisis del mismo archivo
    const fileAnalyses = analysisHistory.value.filter(a => a.file_id === fileId)
    if (fileAnalyses.length > 0) {
      // Combinar todos los análisis en uno solo
      const combined: CombinedAnalysis = {
        total_logs: fileAnalyses[0].total_logs,
        anomalies_detected: fileAnalyses[0].anomalies_detected,
        anomalies: fileAnalyses.reduce((acc, curr) => [...acc, ...curr.anomalies], [] as any[]),
        analyses: fileAnalyses
      }
      
      // Crear un AnalysisResult combinado
      currentAnalysis.value = {
        id: fileId,
        timestamp: fileAnalyses[0].timestamp,
        fileName: fileAnalyses[0].fileName,
        total_logs: combined.total_logs,
        anomalies_detected: combined.anomalies_detected,
        anomalies: combined.anomalies,
        report_file: fileAnalyses[0].report_file,
        file_id: fileId
      }
    }
  }

  function clearHistory() {
    analysisHistory.value = []
    currentAnalysis.value = null
  }

  // Cargar reportes al inicializar el store
  loadReportsFromDirectory()

  return {
    analysisHistory,
    currentAnalysis,
    isLoading,
    addAnalysis,
    setCurrentAnalysis,
    clearHistory,
    loadReportsFromDirectory
  }
})
