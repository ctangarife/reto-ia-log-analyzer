<template>
  <!-- Toast para notificaciones -->
  <Toast />
  <ConfirmDialog />

  <!-- Mostrar login o registro si no está autenticado -->
  <Login v-if="!authStore.isLoggedIn && !authStore.isLoading && !showRegister" @go-to-register="showRegister = true" />
  <Register v-if="!authStore.isLoggedIn && !authStore.isLoading && showRegister" @go-to-login="showRegister = false" />

  <!-- Mostrar aplicación principal si está autenticado -->
  <div v-else-if="authStore.isLoggedIn" class="app-container">
    <!-- Header simplificado -->
    <header class="app-header">
      <div class="header-left">
        <h1 class="app-title">
          <i class="pi pi-shield"></i>
          LogAnomaly
        </h1>
      </div>

      <div class="header-center">
        <div class="selectors">
          <Dropdown
            v-model="authStore.selectedWorkspaceId"
            :options="authStore.workspaces"
            optionLabel="name"
            optionValue="workspace_id"
            placeholder="Workspace"
            @change="onWorkspaceChange"
            :disabled="authStore.isLoading"
            class="compact-selector"
          />
          <Dropdown
            v-model="authStore.selectedProjectId"
            :options="availableProjects"
            optionLabel="name"
            optionValue="project_id"
            placeholder="Proyecto"
            @change="onProjectChange"
            :disabled="authStore.isLoading || !authStore.selectedWorkspaceId"
            class="compact-selector"
          />
        </div>
      </div>

      <div class="header-right">
        <span class="username">{{ authStore.user?.username }}</span>
        <Button
          icon="pi pi-sign-out"
          severity="secondary"
          text
          @click="handleLogout"
          v-tooltip.right="'Cerrar sesión'"
        />
      </div>
    </header>

    <!-- Navegación principal -->
    <nav class="main-nav">
      <button
        class="nav-item"
        :class="{ active: mainView === 'analysis' }"
        @click="mainView = 'analysis'"
      >
        <i class="pi pi-play"></i>
        Análisis
      </button>
      <button
        class="nav-item"
        :class="{ active: mainView === 'history' }"
        @click="mainView = 'history'"
      >
        <i class="pi pi-history"></i>
        Historia
      </button>
      <button
        v-if="authStore.isSuperAdmin"
        class="nav-item"
        :class="{ active: mainView === 'admin' }"
        @click="mainView = 'admin'"
      >
        <i class="pi pi-cog"></i>
        Administración
      </button>
    </nav>

    <!-- Contenido principal según vista seleccionada -->
    <main class="main-content">
      <!-- Vista: ANÁLISIS -->
      <div v-if="mainView === 'analysis'" class="view-container analysis-view">
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
              <FileUpload
                v-if="!selectedFile"
                :maxFileSize="30000000"
                :multiple="false"
                accept=".txt,.log,.json,.csv"
                :auto="false"
                @select="onFileSelect"
                :customUpload="true"
                :showCancelButton="false"
                :showUploadButton="false"
                chooseLabel="Seleccionar archivo"
                :disabled="!canProcessLogs"
              >
                <template #empty>
                  <div class="upload-placeholder">
                    <i class="pi pi-file-import text-4xl"></i>
                    <p>Arrastra un archivo aquí o haz clic para seleccionar</p>
                    <small>Soporta: .txt, .log, .json, .csv (máx 30MB)</small>
                  </div>
                </template>
              </FileUpload>

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

      <!-- Vista: HISTORIA -->
      <div v-if="mainView === 'history'" class="view-container history-view">
        <div class="history-header">
          <h2>Historial de análisis</h2>
          <div v-if="authStore.selectedProjectId" class="project-badge">
            <i class="pi pi-folder"></i>
            {{ getProjectName(authStore.selectedProjectId) }}
          </div>
        </div>

        <div v-if="!authStore.selectedProjectId" class="empty-selection">
          <i class="pi pi-folder-open text-4xl"></i>
          <p>Selecciona un proyecto para ver su historial</p>
        </div>

        <AnalysisHistory v-else compact @view-details="handleViewDetails" />
      </div>

      <!-- Vista: ADMINISTRACIÓN -->
      <div v-if="mainView === 'admin' && authStore.isSuperAdmin" class="view-container admin-view">
        <div class="admin-tabs">
          <button
            class="admin-tab"
            :class="{ active: adminTab === 'workspaces' }"
            @click="adminTab = 'workspaces'"
          >
            <i class="pi pi-building"></i>
            Workspaces
          </button>
          <button
            class="admin-tab"
            :class="{ active: adminTab === 'projects' }"
            @click="adminTab = 'projects'"
          >
            <i class="pi pi-folder"></i>
            Proyectos
          </button>
          <button
            class="admin-tab"
            :class="{ active: adminTab === 'users' }"
            @click="adminTab = 'users'"
          >
            <i class="pi pi-users"></i>
            Usuarios
          </button>
        </div>

        <div class="admin-content">
          <WorkspaceManagement v-if="adminTab === 'workspaces'" />
          <ProjectManagement v-else-if="adminTab === 'projects'" />
          <UserManagement v-else-if="adminTab === 'users'" />
        </div>
      </div>
    </main>
  </div>

  <!-- Loading inicial -->
  <div v-if="authStore.isLoading" class="loading-overlay">
    <ProgressSpinner />
    <p>Cargando...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAnalysisStore } from './stores/analysisStore'
import { useAuthStore } from './stores/authStore'
import AnalysisHistory from './components/AnalysisHistory.vue'
import ProcessingV2 from './components/ProcessingV2.vue'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import WorkspaceManagement from './components/WorkspaceManagement.vue'
import ProjectManagement from './components/ProjectManagement.vue'
import UserManagement from './components/UserManagement.vue'
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import Divider from 'primevue/divider'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import Paginator from 'primevue/paginator'

const store = useAnalysisStore()
const authStore = useAuthStore()

// Estado de navegación
const mainView = ref<'analysis' | 'history' | 'admin'>('analysis')
const adminTab = ref<'workspaces' | 'projects' | 'users'>('workspaces')
const showRegister = ref(false)

// Estado de upload
const selectedFile = ref<File | null>(null)

const currentAnalysis = computed(() => store.currentAnalysis)

// Permisos
const canProcessLogs = computed(() => {
  if (!authStore.selectedProjectId) return false
  return authStore.canProcessLogsInProject()
})

const availableProjects = computed(() => {
  if (!authStore.selectedWorkspaceId) return []
  return authStore.projects[authStore.selectedWorkspaceId] || []
})

// Handlers
async function onWorkspaceChange() {
  if (authStore.selectedWorkspaceId) {
    await authStore.loadProjects(authStore.selectedWorkspaceId)
    const projects = authStore.projects[authStore.selectedWorkspaceId] || []
    if (projects.length > 0) {
      authStore.selectProject(projects[0].project_id)
    }
  }
}

function onProjectChange() {
  if (authStore.selectedProjectId) {
    store.loadReportsFromDirectory(authStore.selectedProjectId)
  }
}

function onFileSelect(event: any) {
  // Solo guardar el archivo seleccionado, no procesar todavía
  const file = event.files[0]
  if (file) {
    selectedFile.value = file
  }
}

function clearSelectedFile() {
  selectedFile.value = null
}

async function processSelectedFile() {
  if (!selectedFile.value) return

  if (!canProcessLogs.value) {
    alert('No tienes permiso para procesar logs en este proyecto')
    return
  }

  try {
    await store.processFileV2(selectedFile.value, authStore.selectedProjectId)
    selectedFile.value = null  // Limpiar después de procesar
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

function handleLogout() {
  authStore.logoutUser()
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function getProjectName(projectId: string): string {
  for (const wsId in authStore.projects) {
    const project = authStore.projects[wsId]?.find((p: any) => p.project_id === projectId)
    if (project) return project.name
  }
  return 'Proyecto desconocido'
}

async function handleViewDetails(analysis: any) {
  // Establecer el análisis actual en el store
  store.setCurrentAnalysis(analysis)

  // Cambiar a la vista de análisis
  mainView.value = 'analysis'

  // Resetear paginación
  currentPage.value = 0
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

// Inicialización
onMounted(async () => {
  authStore.initialize()
  if (authStore.isLoggedIn) {
    await authStore.loadUserData()
  }
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f8fafc;
}

/* Header */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: white;
  border-bottom: 1px solid #e2e8f0;
  gap: 2rem;
}

.header-left .app-title {
  margin: 0;
  font-size: 1.25rem;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.selectors {
  display: flex;
  gap: 0.75rem;
}

.compact-selector {
  min-width: 180px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.username {
  font-weight: 500;
  color: #475569;
}

/* Navegación principal */
.main-nav {
  display: flex;
  background: white;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 1.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border: none;
  background: transparent;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.nav-item:hover {
  color: #3b82f6;
  background: #f8fafc;
}

.nav-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

/* Contenido principal */
.main-content {
  flex: 1;
  overflow: hidden;
}

.view-container {
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem;
}

/* Vista Análisis */
.analysis-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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

.upload-placeholder {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
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

.upload-placeholder p {
  margin: 0.5rem 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f1f5f9;
  border-radius: 8px;
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

/* Vista Historia */
.history-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-header h2 {
  margin: 0;
  color: #1e293b;
}

.project-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #eff6ff;
  color: #3b82f6;
  border-radius: 20px;
  font-size: 0.9rem;
}

/* Vista Admin */
.admin-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.admin-tabs {
  display: flex;
  gap: 0.5rem;
  background: white;
  padding: 0.5rem;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.admin-tab {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  color: #64748b;
  font-weight: 500;
  transition: all 0.2s;
}

.admin-tab:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.admin-tab.active {
  background: #3b82f6;
  color: white;
}

.admin-content {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  flex: 1;
}

/* Estados vacíos */
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

/* Loading */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  z-index: 9999;
}

/* Detalle de anomalías */
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
/* Global PrimeVue overrides */
.p-fileupload {
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  padding: 2rem;
  transition: border-color 0.2s;
}

.p-fileupload:hover {
  border-color: #3b82f6;
}

.p-dropdown {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.p-dropdown:not(.p-disabled):hover {
  border-color: #cbd5e1;
}

.p-dropdown:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}
</style>
