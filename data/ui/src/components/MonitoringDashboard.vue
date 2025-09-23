<template>
  <div class="monitoring-dashboard">
    <div class="dashboard-header">
      <h3>Dashboard de Monitoreo</h3>
      <div class="header-actions">
        <Button 
          icon="pi pi-refresh" 
          severity="secondary" 
          text 
          :loading="isLoading"
          @click="refreshData" 
        />
        <Button 
          icon="pi pi-chart-line" 
          severity="secondary" 
          text 
          @click="toggleAutoRefresh" 
          :class="{ active: autoRefresh }"
        />
      </div>
    </div>

    <div v-if="isLoading && !dashboardData" class="loading-state">
      <ProgressSpinner style="width: 50px; height: 50px" />
      <p>Cargando datos de monitoreo...</p>
    </div>

    <div v-else-if="dashboardData" class="dashboard-content">
      <!-- Resumen del Sistema -->
      <div class="summary-cards">
        <div class="summary-card memory">
          <div class="card-header">
            <i class="pi pi-memory"></i>
            <span>Memoria</span>
          </div>
          <div class="card-content">
            <div class="metric">
              <span class="value">{{ dashboardData.summary.memory.percent.toFixed(1) }}%</span>
              <span class="label">Uso del Sistema</span>
            </div>
            <div class="metric">
              <span class="value">{{ dashboardData.summary.memory.process_mb.toFixed(0) }}MB</span>
              <span class="label">Proceso</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: dashboardData.summary.memory.percent + '%' }"
                :class="getMemoryClass(dashboardData.summary.memory.percent)"
              ></div>
            </div>
          </div>
        </div>

        <div class="summary-card cpu">
          <div class="card-header">
            <i class="pi pi-cog"></i>
            <span>CPU</span>
          </div>
          <div class="card-content">
            <div class="metric">
              <span class="value">{{ dashboardData.summary.cpu.percent.toFixed(1) }}%</span>
              <span class="label">Uso</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: dashboardData.summary.cpu.percent + '%' }"
                :class="getCpuClass(dashboardData.summary.cpu.percent)"
              ></div>
            </div>
          </div>
        </div>

        <div class="summary-card connections">
          <div class="card-header">
            <i class="pi pi-link"></i>
            <span>Conexiones</span>
          </div>
          <div class="card-content">
            <div class="metric">
              <span class="value">{{ dashboardData.summary.connections.active }}</span>
              <span class="label">Activas</span>
            </div>
          </div>
        </div>

        <div class="summary-card processing">
          <div class="card-header">
            <i class="pi pi-box"></i>
            <span>Procesamiento</span>
          </div>
          <div class="card-content">
            <div class="metric">
              <span class="value">{{ dashboardData.summary.processing.chunks_in_memory }}</span>
              <span class="label">Chunks en Memoria</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Alertas -->
      <div v-if="dashboardData.alerts.length > 0" class="alerts-section">
        <h4>Alertas del Sistema</h4>
        <div class="alerts-list">
          <div 
            v-for="alert in dashboardData.alerts" 
            :key="alert.timestamp"
            class="alert-item"
            :class="alert.level"
          >
            <div class="alert-icon">
              <i :class="getAlertIcon(alert.level)"></i>
            </div>
            <div class="alert-content">
              <div class="alert-message">{{ alert.message }}</div>
              <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Gráfico de Memoria -->
      <div class="chart-section">
        <h4>Historial de Memoria</h4>
        <div class="chart-container">
          <canvas ref="memoryChart" width="400" height="200"></canvas>
        </div>
      </div>
    </div>

    <div v-else class="error-state">
      <i class="pi pi-exclamation-triangle" style="font-size: 2rem; color: #f44336;"></i>
      <p>Error cargando datos de monitoreo</p>
      <Button label="Reintentar" @click="refreshData" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'

// Estado reactivo
const isLoading = ref(false)
const dashboardData = ref<any>(null)
const autoRefresh = ref(false)
const refreshInterval = ref<number | null>(null)
const memoryChart = ref<HTMLCanvasElement | null>(null)

// Función para cargar datos del dashboard
async function loadDashboardData() {
  try {
    isLoading.value = true
    const response = await fetch('/api/v2/monitoring/dashboard')
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    dashboardData.value = await response.json()
    
    // Actualizar gráfico después de cargar datos
    await nextTick()
    updateMemoryChart()
    
  } catch (error) {
    console.error('Error cargando datos de monitoreo:', error)
    dashboardData.value = null
  } finally {
    isLoading.value = false
  }
}

// Función para refrescar datos
function refreshData() {
  loadDashboardData()
}

// Función para alternar auto-refresh
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  
  if (autoRefresh.value) {
    refreshInterval.value = setInterval(refreshData, 30000) // 30 segundos
  } else {
    if (refreshInterval.value) {
      clearInterval(refreshInterval.value)
      refreshInterval.value = null
    }
  }
}

// Función para obtener clase CSS de memoria
function getMemoryClass(percent: number): string {
  if (percent >= 90) return 'critical'
  if (percent >= 80) return 'warning'
  return 'normal'
}

// Función para obtener clase CSS de CPU
function getCpuClass(percent: number): string {
  if (percent >= 95) return 'critical'
  if (percent >= 80) return 'warning'
  return 'normal'
}

// Función para obtener icono de alerta
function getAlertIcon(level: string): string {
  switch (level) {
    case 'critical': return 'pi pi-exclamation-triangle'
    case 'warning': return 'pi pi-exclamation-circle'
    default: return 'pi pi-info-circle'
  }
}

// Función para formatear tiempo
function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString()
}

// Función para actualizar gráfico de memoria
function updateMemoryChart() {
  if (!memoryChart.value || !dashboardData.value?.history) return
  
  const canvas = memoryChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const history = dashboardData.value.history
  if (history.length === 0) return
  
  // Limpiar canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // Configurar gráfico
  const padding = 40
  const chartWidth = canvas.width - (padding * 2)
  const chartHeight = canvas.height - (padding * 2)
  
  // Encontrar valores máximos y mínimos
  const memoryValues = history.map((h: any) => h.memory_percent)
  const maxMemory = Math.max(...memoryValues, 100)
  const minMemory = Math.min(...memoryValues, 0)
  
  // Dibujar ejes
  ctx.strokeStyle = '#ddd'
  ctx.lineWidth = 1
  
  // Eje Y
  ctx.beginPath()
  ctx.moveTo(padding, padding)
  ctx.lineTo(padding, canvas.height - padding)
  ctx.stroke()
  
  // Eje X
  ctx.beginPath()
  ctx.moveTo(padding, canvas.height - padding)
  ctx.lineTo(canvas.width - padding, canvas.height - padding)
  ctx.stroke()
  
  // Dibujar línea de memoria
  if (history.length > 1) {
    ctx.strokeStyle = '#2196f3'
    ctx.lineWidth = 2
    ctx.beginPath()
    
    history.forEach((point: any, index: number) => {
      const x = padding + (index / (history.length - 1)) * chartWidth
      const y = canvas.height - padding - ((point.memory_percent - minMemory) / (maxMemory - minMemory)) * chartHeight
      
      if (index === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    
    ctx.stroke()
  }
  
  // Dibujar puntos
  ctx.fillStyle = '#2196f3'
  history.forEach((point: any, index: number) => {
    const x = padding + (index / (history.length - 1)) * chartWidth
    const y = canvas.height - padding - ((point.memory_percent - minMemory) / (maxMemory - minMemory)) * chartHeight
    
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, 2 * Math.PI)
    ctx.fill()
  })
  
  // Etiquetas
  ctx.fillStyle = '#666'
  ctx.font = '12px Arial'
  ctx.textAlign = 'center'
  ctx.fillText('Memoria (%)', canvas.width / 2, canvas.height - 10)
  
  ctx.textAlign = 'right'
  ctx.save()
  ctx.translate(15, canvas.height / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('Tiempo', 0, 0)
  ctx.restore()
}

// Lifecycle hooks
onMounted(() => {
  loadDashboardData()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<style scoped>
.monitoring-dashboard {
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.dashboard-header h3 {
  margin: 0;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.header-actions .active {
  background-color: #e3f2fd !important;
  color: #1976d2 !important;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
  color: #666;
  gap: 1rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.summary-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  border-left: 4px solid #ddd;
}

.summary-card.memory {
  border-left-color: #2196f3;
}

.summary-card.cpu {
  border-left-color: #ff9800;
}

.summary-card.connections {
  border-left-color: #4caf50;
}

.summary-card.processing {
  border-left-color: #9c27b0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  font-weight: 500;
  color: #2c3e50;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #2c3e50;
}

.label {
  font-size: 0.9rem;
  color: #666;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 0.5rem;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
}

.progress-fill.normal {
  background: #4caf50;
}

.progress-fill.warning {
  background: #ff9800;
}

.progress-fill.critical {
  background: #f44336;
}

.alerts-section {
  margin-bottom: 2rem;
}

.alerts-section h4 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border-radius: 6px;
  border-left: 4px solid #ddd;
}

.alert-item.warning {
  background: #fff3cd;
  border-left-color: #ff9800;
}

.alert-item.critical {
  background: #f8d7da;
  border-left-color: #f44336;
}

.alert-icon {
  font-size: 1.2rem;
}

.alert-item.warning .alert-icon {
  color: #ff9800;
}

.alert-item.critical .alert-icon {
  color: #f44336;
}

.alert-content {
  flex: 1;
}

.alert-message {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.alert-time {
  font-size: 0.8rem;
  color: #666;
}

.chart-section {
  margin-bottom: 1rem;
}

.chart-section h4 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.chart-container {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
}

canvas {
  max-width: 100%;
  height: auto;
}
</style>
