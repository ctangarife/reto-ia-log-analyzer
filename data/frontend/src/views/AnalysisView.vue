<template>
  <div class="analysis-view">
    <!-- Mensaje si no hay proyectos -->
    <div v-if="!authStore.selectedProjectId" class="empty-selection">
      <i class="pi pi-folder-open text-4xl"></i>
      <p>Selecciona un workspace y proyecto para comenzar</p>
    </div>

    <!-- Contenido de análisis -->
    <template v-else>
      <!-- Zona de upload -->
      <div class="upload-zone">
        <div v-if="!store.currentJob" class="upload-area">
          <h2>Subir archivo de logs</h2>

          <!-- Sin archivo seleccionado -->
          <div v-if="!selectedFile" class="file-input-container">
            <input
              ref="fileInput"
              type="file"
              accept=".txt,.log,.json,.csv"
              @change="onFileSelect"
              :disabled="!canProcessLogs"
              class="file-input"
            />
            <div
              class="upload-placeholder"
              @click="triggerFileInput"
              :class="{ 'disabled': !canProcessLogs }"
            >
              <i class="pi pi-file-import text-4xl"></i>
              <p>Arrastra un archivo aquí o haz clic para seleccionar</p>
              <small>Soporta: .txt, .log, .json, .csv (máx 30MB)</small>
            </div>
          </div>

          <!-- Archivo seleccionado -->
          <div v-else class="selected-file-container">
            <div class="selected-file">
              <div class="file-icon">
                <i class="pi pi-file-text"></i>
              </div>
              <div class="file-details">
                <span class="file-name">{{ selectedFile.name }}</span>
                <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
              </div>
            </div>
            <div class="file-actions">
              <Button
                label="Cancelar"
                severity="secondary"
                text
                @click="clearSelectedFile"
              />
              <Button
                label="Analizar"
                @click="processSelectedFile"
              />
            </div>
          </div>

          <Message v-if="!canProcessLogs" severity="warn" :closable="false">
            No tienes permiso para procesar logs en este proyecto
          </Message>
        </div>

        <!-- Job en procesamiento -->
        <div v-else class="processing-area">
          <ProcessingV2 />
        </div>
      </div>

      <!-- Resultados del análisis actual -->
      <div v-if="currentAnalysis" class="results-area">
        <div class="results-header">
          <h3>Resultados del análisis</h3>
          <div class="results-stats">
            <div class="stat-badge">
              <span class="label">Total</span>
              <span class="value">{{ currentAnalysis.total_logs }}</span>
            </div>
            <div class="stat-badge danger">
              <span class="label">Anomalías</span>
              <span class="value">{{ currentAnalysis.anomalies_detected }}</span>
            </div>
            <div class="stat-badge">
              <span class="label">%</span>
              <span class="value">{{ ((currentAnalysis.anomalies_detected / currentAnalysis.total_logs) * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <!-- Detalle de anomalías -->
        <div v-if="currentAnalysis.anomalies && currentAnalysis.anomalies.length > 0" class="anomalies-detail">
          <Divider />
          <h4>Detalle de anomalías detectadas</h4>
          <Accordion :multiple="true">
            <AccordionTab v-for="(anomaly, index) in displayedAnomalies" :key="index">
              <template #header>
                <span class="anomaly-title">
                  <i class="pi pi-exclamation-triangle" style="color: #f59e0b;"></i>
                  Anomalía #{{ index + 1 }}
                  <Tag :value="getAnomalySeverity(anomaly)" :severity="getSeverityClass(anomaly)" class="ml-2" />
                </span>
              </template>
              <div class="anomaly-content">
                <div class="anomaly-log">
                  <h5>Log detectado:</h5>
                  <pre>{{ anomaly.log_entry || anomaly.log_line || anomaly.line || 'Sin información del log' }}</pre>
                </div>
                <div v-if="anomaly.explanation" class="anomaly-explanation">
                  <h5>Explicación:</h5>
                  <p>{{ anomaly.explanation }}</p>
                </div>
                <div v-if="anomaly.score !== undefined" class="anomaly-score">
                  <h5>Score de anomalía:</h5>
                  <ProgressBar :value="(anomaly.score * 100).toFixed(1)" :showValue="true" />
                </div>
              </div>
            </AccordionTab>
          </Accordion>

          <!-- Paginación si hay muchas anomalías -->
          <Paginator
            v-if="currentAnalysis.anomalies.length > itemsPerPage"
            :rows="itemsPerPage"
            :totalRecords="currentAnalysis.anomalies.length"
            @page="onPageChange"
            class="mt-4"
          />
        </div>

        <!-- Sin anomalías -->
        <div v-else class="no-anomalies">
          <i class="pi pi-check-circle" style="color: #10b981; font-size: 3rem;"></i>
          <p>No se detectaron anomalías en este análisis.</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAnalysisStore } from '../stores/analysisStore'
import { useAuthStore } from '../stores/authStore'
import ProcessingV2 from '../components/ProcessingV2.vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import Divider from 'primevue/divider'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import Paginator from 'primevue/paginator'

const store = useAnalysisStore()
const authStore = useAuthStore()

// Estado de upload
const selectedFile = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

const currentAnalysis = computed(() => store.currentAnalysis)

// Permisos
const canProcessLogs = computed(() => {
  if (!authStore.selectedProjectId) return false
  return authStore.canProcessLogsInProject()
})

function onFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedFile.value = file
  }
}

function triggerFileInput() {
  if (!canProcessLogs.value) return
  fileInput.value?.click()
}

function clearSelectedFile() {
  selectedFile.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function processSelectedFile() {
  if (!selectedFile.value) return

  if (!authStore.selectedProjectId) {
    alert('Por favor selecciona un proyecto antes de procesar archivos')
    return
  }

  if (!canProcessLogs.value) {
    alert('No tienes permiso para procesar logs en este proyecto')
    return
  }

  try {
    await store.processFileV2(selectedFile.value, authStore.selectedProjectId)
    selectedFile.value = null
  } catch (error: any) {
    if (error.response?.status === 409) {
      alert('Este archivo ya fue procesado anteriormente.')
    } else if (error.response?.status === 403) {
      alert('No tienes permiso para procesar logs en este proyecto')
    } else {
      alert('Error al procesar el archivo. Intenta nuevamente.')
    }
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// Paginación de anomalías
const currentPage = ref(0)
const itemsPerPage = 20

const displayedAnomalies = computed(() => {
  if (!currentAnalysis.value?.anomalies) return []
  const start = currentPage.value * itemsPerPage
  const end = start + itemsPerPage
  return currentAnalysis.value.anomalies.slice(start, end)
})

function onPageChange(event: any) {
  currentPage.value = event.page
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
</script>

<style scoped>
.analysis-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: #94a3b8;
}

.empty-selection i {
  color: #cbd5e1;
}

.upload-zone {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.upload-area h2 {
  margin: 0 0 1rem 0;
  font-size: 1.1rem;
  color: #1e293b;
}

.file-input-container {
  position: relative;
}

.file-input {
  position: absolute;
  width: 0.1px;
  height: 0.1px;
  opacity: 0;
  overflow: hidden;
  z-index: -1;
}

.upload-placeholder {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-placeholder:hover:not(.disabled) {
  border-color: #3b82f6;
  background-color: #f0f9ff;
  color: #3b82f6;
}

.upload-placeholder.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-placeholder i {
  color: #cbd5e1;
  margin-bottom: 0.5rem;
}

.selected-file-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 2px dashed #cbd5e1;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: #eff6ff;
  border-radius: 8px;
  color: #3b82f6;
  font-size: 1.5rem;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #1e293b;
  word-break: break-all;
}

.file-size {
  font-size: 0.875rem;
  color: #64748b;
}

.file-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.processing-area {
  min-height: 200px;
}

.results-area {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.results-header h3 {
  margin: 0;
  color: #1e293b;
}

.results-stats {
  display: flex;
  gap: 0.75rem;
}

.stat-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #f1f5f9;
  border-radius: 8px;
  min-width: 70px;
}

.stat-badge.danger {
  background: #fef2f2;
}

.stat-badge .label {
  font-size: 0.7rem;
  color: #64748b;
  text-transform: uppercase;
}

.stat-badge .value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.stat-badge.danger .value {
  color: #dc2626;
}

.anomalies-detail {
  margin-top: 1.5rem;
}

.anomalies-detail h4 {
  margin: 0 0 1rem 0;
  color: #1e293b;
  font-size: 1rem;
}

.anomaly-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.anomaly-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.anomaly-log h5,
.anomaly-explanation h5,
.anomaly-score h5 {
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

.no-anomalies {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  color: #10b981;
}

.no-anomalies p {
  margin: 0;
  color: #64748b;
}
</style>

<style>
.p-fileupload {
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  padding: 2rem;
  transition: border-color 0.2s;
}

.p-fileupload:hover {
  border-color: #3b82f6;
}
</style>
