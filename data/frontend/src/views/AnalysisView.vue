<template>
  <div class="analysis-view">
    <!-- Mensaje si no hay proyectos -->
    <div v-if="!authStore.selectedProjectId" class="empty-selection">
      <i class="pi pi-folder-open text-4xl"></i>
      <p>Selecciona un workspace y proyecto para comenzar</p>
    </div>

    <!-- Contenido de análisis -->
    <template v-else>
      <!-- Jobs Activos -->
      <ActiveJobsList />

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

          <!-- Toggle para cambiar entre vista agrupada e individual -->
          <div class="view-toggle mb-3">
            <Button
              :label="showGroupedView ? 'Ver Individual' : 'Ver Agrupado'"
              :icon="showGroupedView ? 'pi pi-list' : 'pi pi-th-large'"
              @click="showGroupedView = !showGroupedView"
              size="small"
              text
            />
            <Tag v-if="showGroupedView && anomalyGroups.length > 0" class="ml-2">
              {{ anomalyGroups.length }} grupos únicos
            </Tag>
            <Tag v-else class="ml-2">
              {{ currentAnalysis.anomalies.length }} anomalías totales
            </Tag>
          </div>

          <!-- Vista agrupada (default cuando hay repeticiones) -->
          <div v-if="showGroupedView">
            <h4>Detalle de anomalías (Agrupado por similitud)</h4>
            <Message severity="info" :closable="false" class="mb-3">
              Las anomalías se han agrupado por patrones similares para evitar repeticiones.
              Cada grupo representa un tipo de anomalía que puede repetirse múltiples veces.
            </Message>

            <div v-if="anomalyGroups.length > 0" class="anomaly-groups">
              <div
                v-for="group in anomalyGroups"
                :key="group.id"
                class="anomaly-group-card"
                :class="{ 'high-severity': group.severity === 'critical' || group.severity === 'high' }"
              >
                <div class="group-header">
                  <div class="group-title">
                    <i class="pi pi-folder-open" style="color: #f59e0b;"></i>
                    <span>Grupo #{{ group.id }} - {{ group.pattern.substring(0, 80) }}{{ group.pattern.length > 80 ? '...' : '' }}</span>
                  </div>
                  <div class="group-tags">
                    <Tag :value="`${group.count} ${group.count === 1 ? 'vez' : 'veces'}`" severity="info" />
                    <Tag :value="getAnomalySeverity(group)" :severity="getSeverityClass(group)" />
                  </div>
                </div>

                <Accordion>
                  <AccordionTab>
                    <template #header>
                      <span class="group-content-toggle">
                        <i class="pi pi-eye"></i>
                        Ver detalles
                      </span>
                    </template>

                    <div class="group-content">
                      <div class="group-stats">
                        <div class="stat-item">
                          <span class="stat-label">Total ocurrencias:</span>
                          <span class="stat-value">{{ group.count }}</span>
                        </div>
                        <div class="stat-item">
                          <span class="stat-label">Severidad:</span>
                          <span class="stat-value">{{ getAnomalySeverity(group) }}</span>
                        </div>
                        <div class="stat-item" v-if="group.score !== undefined">
                          <span class="stat-label">Score promedio:</span>
                          <span class="stat-value">{{ (group.score * 100).toFixed(1) }}%</span>
                        </div>
                      </div>

                      <div class="group-explanation">
                        <h5>Explicación:</h5>
                        <p>{{ group.explanation }}</p>
                      </div>

                      <div class="group-logs">
                        <h5>Logs del grupo ({{ group.count }} ocurrencias):</h5>
                        <small class="text-muted">Mostrando primera ocurrencia:</small>
                        <pre>{{ group.representative }}</pre>

                        <div v-if="group.count > 1" class="mt-3">
                          <Button
                            label="Ver todas las ocurrencias"
                            size="small"
                            text
                            @click="toggleGroupOccurrences(group)"
                          />
                          <div v-if="group.showOccurrences" class="all-occurrences mt-3">
                            <Divider />
                            <div v-for="(occ, idx) in group.occurrences" :key="idx" class="occurrence-item">
                              <small class="text-muted">Ocurrencia #{{ idx + 1 }}:</small>
                              <pre>{{ occ.log_entry || occ.log_line || occ.line }}</pre>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </AccordionTab>
                </Accordion>
              </div>
            </div>
          </div>

          <!-- Vista individual (original) -->
          <div v-else>
            <h4>Detalle de anomalías detectadas (Individual)</h4>
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
import ActiveJobsList from '../components/ActiveJobsList.vue'
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

// Agrupar anomalías similares
const anomalyGroups = computed(() => {
  if (!currentAnalysis.value?.anomalies) return []

  const groups: Record<string, any> = {}

  currentAnalysis.value.anomalies.forEach(anomaly => {
    const logEntry = anomaly.log_entry || anomaly.log_line || anomaly.line || ''

    // Extraer patrón (remover timestamps, IDs, etc.)
    const pattern = extractPattern(logEntry)

    if (!groups[pattern]) {
      groups[pattern] = {
        pattern: pattern,
        count: 0,
        representative: logEntry,
        explanation: anomaly.explanation,
        score: anomaly.score,
        severity: anomaly.severity,
        occurrences: []
      }
    }

    groups[pattern].count++
    groups[pattern].occurrences.push(anomaly)
  })

  // Convertir a array y ordenar por frecuencia
  return Object.values(groups)
    .sort((a, b) => b.count - a.count)
    .map((group, index) => ({
      ...group,
      id: index + 1,
      first_occurrence: group.occurrences[0]
    }))
})

// Extraer patrón de un log (versión simplificada)
function extractPattern(logLine: string): string {
  if (!logLine) return ''

  let pattern = logLine

  // Remover timestamps
  pattern = pattern.replace(/\[\w{3} \w{3} \s+\d+ \d{2}:\d{2}:\d{2} \d{4}\]/g, '[TIMESTAMP]')
  pattern = pattern.replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/g, '[TIMESTAMP]')
  pattern = pattern.replace(/\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2}/g, '[TIMESTAMP]')

  // Remover IDs numéricos
  pattern = pattern.replace(/\bchild \d+\b/g, 'child [ID]')
  pattern = pattern.replace(/\bslot \d+\b/g, 'slot [ID]')
  pattern = pattern.replace(/\bstate \d+\b/g, 'state [ID]')

  // Remover números de puerto
  pattern = pattern.replace(/:\d{4,5}/g, ':[PORT]')

  return pattern.trim()
}

// Determinar si mostrar grupos o anomalías individuales
const showGroupedView = computed(() => {
  // Mostrar grupos si hay más de 10 anomalías o si hay repeticiones
  if (!currentAnalysis.value?.anomalies) return false
  const anomalyCount = currentAnalysis.value.anomalies.length
  const hasRepetitions = anomalyGroups.value.some(g => g.count > 1)
  return anomalyCount > 10 || hasRepetitions
})

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

// Funciones para vista agrupada
function toggleGroupOccurrences(group: any) {
  group.showOccurrences = !group.showOccurrences
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

/* Estilos para vista agrupada */
.view-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.anomaly-groups {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.anomaly-group-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.anomaly-group-card:hover {
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.anomaly-group-card.high-severity {
  border-left: 4px solid #dc2626;
  background: #fef2f2;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: #1e293b;
}

.group-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.group-content-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #64748b;
}

.group-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.group-stats {
  display: flex;
  gap: 2rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.group-explanation {
  background: white;
  border-radius: 8px;
  padding: 1rem;
}

.group-explanation h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.group-explanation p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.group-logs {
  background: white;
  border-radius: 8px;
  padding: 1rem;
}

.group-logs h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.group-logs pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.all-occurrences {
  background: #f8fafc;
  border-radius: 8px;
  padding: 1rem;
}

.occurrence-item {
  padding: 0.75rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.occurrence-item:last-child {
  border-bottom: none;
}

.text-muted {
  color: #94a3b8;
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
