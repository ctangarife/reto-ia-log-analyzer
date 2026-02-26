<template>
  <!-- Toast para notificaciones -->
  <Toast />
  
  <!-- Mostrar login o registro si no está autenticado -->
  <Login v-if="!authStore.isLoggedIn && !authStore.isLoading && !showRegister" @go-to-register="showRegister = true" />
  <Register v-if="!authStore.isLoggedIn && !authStore.isLoading && showRegister" @go-to-login="showRegister = false" />

  <!-- Mostrar aplicación principal si está autenticado -->
  <div v-else-if="authStore.isLoggedIn" class="app-container">
    <!-- Header con selectores y logout -->
    <header class="app-header">
      <div class="header-left">
        <h1 class="app-title">Log Anomaly Detector</h1>
      </div>
      <div class="header-center">
        <div class="selectors">
          <div class="selector-group">
            <label>Workspace:</label>
            <Dropdown
              v-model="authStore.selectedWorkspaceId"
              :options="authStore.workspaces"
              optionLabel="name"
              optionValue="workspace_id"
              placeholder="Selecciona un workspace"
              @change="onWorkspaceChange"
              :disabled="authStore.isLoading"
              class="workspace-selector"
            />
          </div>
          <div class="selector-group">
            <label>Proyecto:</label>
            <Dropdown
              v-model="authStore.selectedProjectId"
              :options="availableProjects"
              optionLabel="name"
              optionValue="project_id"
              placeholder="Selecciona un proyecto"
              @change="onProjectChange"
              :disabled="authStore.isLoading || !authStore.selectedWorkspaceId"
              class="project-selector"
            />
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="user-info">
          <span class="username">{{ authStore.user?.username }}</span>
          <span v-if="authStore.isSuperAdmin" class="super-admin-badge">Super Admin</span>
          <Button
            icon="pi pi-user"
            label="Perfil"
            severity="secondary"
            text
            @click="showProfile = true"
            v-if="authStore.isSuperAdmin"
          />
          <Button
            icon="pi pi-users"
            label="Usuarios"
            severity="secondary"
            text
            @click="showUsers = true"
            v-if="authStore.isSuperAdmin"
          />
          <Button
            icon="pi pi-sign-out"
            label="Salir"
            severity="secondary"
            text
            @click="handleLogout"
          />
        </div>
      </div>
    </header>

    <!-- Mensaje si no hay proyectos accesibles (solo para usuarios normales) -->
    <div v-if="!authStore.isLoading && authStore.workspaces.length === 0 && !authStore.isSuperAdmin" class="no-access-message">
      <Message severity="warn" :closable="false">
        No tienes acceso a ningún workspace. Contacta a un administrador.
      </Message>
    </div>

    <!-- Contenido principal -->
    <div v-if="authStore.isLoading || authStore.workspaces.length > 0 || authStore.isSuperAdmin" class="app-content">
      <aside class="side-panel">
        <!-- Mensaje para super admin sin workspaces -->
        <div v-if="authStore.isSuperAdmin && authStore.workspaces.length === 0" class="super-admin-info">
          <Message severity="info" :closable="false">
            <p><strong>Super Administrador</strong></p>
            <p>No hay workspaces creados aún. Puedes crear workspaces y proyectos desde el panel de administración.</p>
          </Message>
        </div>

        <!-- Selector de archivo solo si tiene permiso de escritura y hay workspaces -->
        <div v-if="canProcessLogs && authStore.workspaces.length > 0" class="upload-section">
          <h3>Procesar Logs</h3>
          <FileUpload
            :maxFileSize="30000000"
            :multiple="false"
            accept=".txt,.log,.json"
            :auto="false"
            @select="onFileSelect"
            :customUpload="true"
            uploadLabel="Analizar"
            chooseLabel="Seleccionar archivo"
            cancelLabel="Cancelar"
            :disabled="!canProcessLogs || !authStore.selectedProjectId"
          >
            <template #empty>
              <p>Arrastra y suelta un archivo aquí o haz clic para seleccionar</p>
            </template>
          </FileUpload>
          <Message
            v-if="!authStore.selectedProjectId"
            severity="info"
            :closable="false"
            class="info-message"
          >
            Selecciona un proyecto para procesar logs
          </Message>
          <Message
            v-else-if="!canProcessLogs"
            severity="warn"
            :closable="false"
            class="info-message"
          >
            No tienes permiso para procesar logs en este proyecto
          </Message>
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
              v-if="canAccessMonitoring"
              class="tab-button"
              :class="{ active: activeTab === 'monitoring' }"
              @click="activeTab = 'monitoring'"
            >
              <i class="pi pi-cog"></i>
              Monitoreo
            </button>
            <button
              v-if="authStore.isSuperAdmin"
              class="tab-button"
              :class="{ active: activeTab === 'admin' }"
              @click="activeTab = 'admin'"
            >
              <i class="pi pi-shield"></i>
              Administración
            </button>
          </div>

          <div class="tab-content">
            <!-- Tab de Administración para Super Admin -->
          <div v-if="activeTab === 'admin' && authStore.isSuperAdmin" class="tab-panel">
            <div class="admin-panel">
              <div class="admin-tabs">
                <div class="admin-tab-buttons">
                  <button
                    class="admin-tab-button"
                    :class="{ active: adminSubTab === 'workspaces' }"
                    @click="adminSubTab = 'workspaces'"
                  >
                    <i class="pi pi-building"></i>
                    Workspaces
                  </button>
                  <button
                    class="admin-tab-button"
                    :class="{ active: adminSubTab === 'users' }"
                    @click="adminSubTab = 'users'"
                  >
                    <i class="pi pi-users"></i>
                    Usuarios
                  </button>
                  <button
                    class="admin-tab-button"
                    :class="{ active: adminSubTab === 'projects' }"
                    @click="adminSubTab = 'projects'"
                  >
                    <i class="pi pi-folder"></i>
                    Proyectos
                  </button>
                </div>

                <div class="admin-tab-content">
                  <WorkspaceManagement v-if="adminSubTab === 'workspaces'" />
                  <div v-else-if="adminSubTab === 'users'" class="coming-soon">
                    <i class="pi pi-users" style="font-size: 3rem; color: #ccc;"></i>
                    <p>Gestión de Usuarios</p>
                    <p class="coming-soon-text">Próximamente</p>
                  </div>
                  <div v-else-if="adminSubTab === 'projects'" class="coming-soon">
                    <i class="pi pi-folder" style="font-size: 3rem; color: #ccc;"></i>
                    <p>Gestión de Proyectos</p>
                    <p class="coming-soon-text">Próximamente</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

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
                <p v-if="authStore.isSuperAdmin && authStore.workspaces.length === 0">
                  Como super administrador, puedes crear workspaces y proyectos desde el panel de administración.
                </p>
                <p v-else-if="!currentAnalysis">Selecciona un archivo para comenzar el análisis</p>
                <p v-else>No se encontraron anomalías en este análisis</p>
              </div>
            </div>

            <div v-if="activeTab === 'monitoring' && canAccessMonitoring" class="tab-panel">
              <MonitoringDashboard />
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- Loading inicial -->
    <div v-if="authStore.isLoading" class="loading-overlay">
      <ProgressSpinner />
      <p>Cargando...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAnalysisStore } from './stores/analysisStore'
import { useAuthStore } from './stores/authStore'
import { formatTimestamp } from './utils/formatters'
import AnalysisHistory from './components/AnalysisHistory.vue'
import ProcessingV2 from './components/ProcessingV2.vue'
import MonitoringDashboard from './components/MonitoringDashboard.vue'
import Login from './components/Login.vue'
import Register from './components/Register.vue'
import WorkspaceManagement from './components/WorkspaceManagement.vue'
import FileUpload from 'primevue/fileupload'
import ProgressSpinner from 'primevue/progressspinner'
import InputNumber from 'primevue/inputnumber'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { filterProjectsWithWriteAccess } from './utils/permissions'

const store = useAnalysisStore()
const authStore = useAuthStore()

const loading = ref<boolean | string>(false)
const scoreFilter = ref(0.5)
const chunkInfo = ref<{ current: number; total: number } | null>(null)
const activeTab = ref<'analysis' | 'monitoring' | 'admin'>('analysis')
const useV2Processing = ref(true)
const showRegister = ref(false)
const showProfile = ref(false)
const showUsers = ref(false)
const showWorkspaces = ref(false)
const showProjects = ref(false)
const adminSubTab = ref<'workspaces' | 'users' | 'projects'>('workspaces')

const currentAnalysis = computed(() => store.currentAnalysis)

// Computed para permisos
const canProcessLogs = computed(() => {
  if (!authStore.selectedProjectId) return false
  return authStore.canProcessLogsInProject()
})

const canAccessMonitoring = computed(() => {
  return authStore.canAccessMonitoringDashboard()
})

const availableProjects = computed(() => {
  if (!authStore.selectedWorkspaceId) return []
  return authStore.projects[authStore.selectedWorkspaceId] || []
})

// Watchers
watch(() => authStore.selectedProjectId, async (newProjectId) => {
  if (newProjectId) {
    // Cargar reportes del proyecto seleccionado
    await store.loadReportsFromDirectory(newProjectId)
  }
})

// Handlers
async function onWorkspaceChange() {
  if (authStore.selectedWorkspaceId) {
    await authStore.loadProjects(authStore.selectedWorkspaceId)
    // Seleccionar primer proyecto si hay disponibles
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

async function onFileSelect(event: any) {
  const file = event.files[0]
  if (!file) return

  // Verificar permisos antes de procesar
  if (!canProcessLogs.value) {
    alert('No tienes permiso para procesar logs en este proyecto')
    return
  }

  if (!authStore.selectedProjectId) {
    alert('Por favor selecciona un proyecto primero')
    return
  }

  if (useV2Processing.value) {
    try {
      loading.value = 'Iniciando procesamiento...'
      const jobId = await store.processFileV2(file, authStore.selectedProjectId)
      console.log('Job iniciado:', jobId)
      loading.value = false
    } catch (error: any) {
      console.error('Error durante el procesamiento:', error)
      if (error.response?.status === 409) {
        alert('Ya hay un archivo procesándose. Espera a que termine.')
      } else if (error.response?.status === 403) {
        alert('No tienes permiso para procesar logs en este proyecto')
      } else {
        alert('Error al procesar el archivo. Intenta nuevamente.')
      }
      loading.value = false
    }
  }
}

function handleLogout() {
  authStore.logoutUser()
}

function getScoreClass(score: number): string {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.5) return 'score-medium'
  return 'score-low'
}

// Inicialización
onMounted(async () => {
  // Inicializar store de autenticación
  authStore.initialize()

  // Si está autenticado, cargar datos
  if (authStore.isLoggedIn) {
    await authStore.loadUserData()
    if (authStore.selectedProjectId) {
      await store.loadReportsFromDirectory(authStore.selectedProjectId)
    }
  }
})
</script>

<style>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background-color: white;
  border-bottom: 1px solid #e0e0e0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  flex: 0 0 auto;
}

.app-title {
  margin: 0;
  font-size: 1.5rem;
  color: #2c3e50;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 2rem;
}

.selectors {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.selector-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.selector-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #666;
}

.workspace-selector,
.project-selector {
  min-width: 200px;
}

.header-right {
  flex: 0 0 auto;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.username {
  font-weight: 500;
  color: #2c3e50;
}

.super-admin-badge {
  background-color: #f59e0b;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-right: 0.5rem;
}

.super-admin-info {
  margin-bottom: 1rem;
}

.super-admin-info :deep(.p-message) {
  padding: 1rem;
}

.super-admin-info p {
  margin: 0.5rem 0;
}

.admin-panel {
  padding: 2rem;
}

.admin-panel h2 {
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

.admin-actions {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}

.admin-button {
  width: 100%;
  max-width: 300px;
  padding: 1rem;
  font-size: 1rem;
}

.admin-info {
  margin-top: 2rem;
}

.admin-info :deep(.p-message) {
  padding: 1rem;
}

.admin-info p {
  margin: 0.5rem 0;
}

.no-access-message {
  padding: 2rem;
  display: flex;
  justify-content: center;
}

.app-content {
  display: flex;
  flex: 1;
  overflow: hidden;
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

.upload-section {
  margin-bottom: 1rem;
}

.upload-section h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  color: #2c3e50;
}

.info-message {
  margin-top: 0.5rem;
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

.main-content {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  position: relative;
}

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

.tab-content {
  flex: 1;
  overflow: hidden;
}

.tab-panel {
  height: 100%;
  overflow-y: auto;
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

.loading-overlay {
  position: fixed;
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
  z-index: 9999;
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
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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

.log-entry {
  background-color: #f8f9fa;
  padding: 0.5rem;
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
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

.admin-tabs {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.admin-tab-buttons {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #e0e0e0;
}

.admin-tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
  color: #666;
  font-weight: 500;
  font-size: 0.95rem;
}

.admin-tab-button:hover {
  background: #f8f9fa;
  color: #2c3e50;
}

.admin-tab-button.active {
  color: #2196f3;
  border-bottom-color: #2196f3;
}

.admin-tab-content {
  padding: 1rem 0;
}

.coming-soon {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: #666;
  gap: 1rem;
}

.coming-soon-text {
  font-size: 0.9rem;
  color: #999;
  font-style: italic;
}
</style>
