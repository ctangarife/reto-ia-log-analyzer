<template>
  <div class="analysis-history">
    <div class="history-header">
      <h3>Historial de Análisis</h3>
      <div class="header-actions">
        <Button 
          icon="pi pi-refresh" 
          severity="secondary" 
          text 
          :loading="isLoading"
          @click="loadReportsFromDirectory" 
        />
        <Button 
          icon="pi pi-trash" 
          severity="danger" 
          text 
          @click="clearHistory" 
        />
      </div>
    </div>

    <div v-if="isLoading" class="loading-state">
      <ProgressSpinner style="width: 50px; height: 50px" />
      <p>Cargando reportes...</p>
    </div>

    <div v-else-if="analysisHistory.length === 0" class="empty-state">
      <i class="pi pi-folder-open" style="font-size: 2rem; color: #666;"></i>
      <p>No hay análisis previos</p>
    </div>

    <div v-else class="history-list">
      <TransitionGroup name="list">
        <div v-for="(group, groupId) in groupedAnalysis" 
             :key="groupId" 
             class="history-group">
          <div class="group-header" 
               @click="toggleGroup(groupId)"
               :class="{ active: selectedGroupId === groupId }">
            <div class="group-title">
              <i :class="expandedGroups[groupId] ? 'pi pi-folder-open' : 'pi pi-folder'" />
              <span>{{ formatGroupName(groupId) }}</span>
              <span class="group-count">({{ group.length }})</span>
            </div>
            <div class="group-summary" v-if="group.length > 0">
              <span>Último: {{ formatDate(group[0].timestamp) }}</span>
            </div>
          </div>
          
          <TransitionGroup 
            name="expand" 
            tag="div" 
            class="group-items"
            v-show="expandedGroups[groupId]"
          >
            <div v-for="analysis in group" 
                 :key="analysis.id" 
                 class="history-item"
                 :class="{ active: currentAnalysis?.id === analysis.id }"
                 @click="selectAnalysis(analysis)">
              <div class="item-header">
                <span class="timestamp">{{ formatDate(analysis.timestamp) }}</span>
              </div>
              <div class="item-stats">
                <span>Total: {{ analysis.total_logs }}</span>
                <span>Anomalías: {{ analysis.anomalies_detected }}</span>
                <span>{{ ((analysis.anomalies_detected / analysis.total_logs) * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAnalysisStore } from '../stores/analysisStore'
import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'

const store = useAnalysisStore()
const { analysisHistory, currentAnalysis, isLoading } = storeToRefs(store)
const { setCurrentAnalysis, clearHistory, loadReportsFromDirectory } = store

// Estado para grupos
const selectedGroupId = ref<string | null>(null)
const expandedGroups = ref<Record<string, boolean>>({})

// Función para seleccionar un análisis específico
function selectAnalysis(analysis: any) {
  // Usar directamente los datos que ya tenemos disponibles
  setCurrentAnalysis(analysis)
  selectedGroupId.value = analysis.file_id || 'sin_grupo'
}

// Formatear nombre del grupo para mostrar
function formatGroupName(groupId: string) {
  return groupId.replace(/_/g, ' ')
}

// Agrupar análisis por carpeta
const groupedAnalysis = computed(() => {
  const groups: Record<string, any[]> = {}
  
  analysisHistory.value.forEach(analysis => {
    const groupId = analysis.file_id || 'sin_grupo'
    if (!groups[groupId]) {
      groups[groupId] = []
    }
    groups[groupId].push(analysis)
  })
  
  // Ordenar análisis dentro de cada grupo por timestamp
  Object.values(groups).forEach(group => {
    group.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  })
  
  return groups
})

// Función para expandir/colapsar grupos
function toggleGroup(groupId: string) {
  expandedGroups.value[groupId] = !expandedGroups.value[groupId]
  selectedGroupId.value = groupId
}

function formatDate(timestamp: string) {
  return new Date(timestamp).toLocaleString()
}
</script>

<style scoped>
.analysis-history {
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.history-header h3 {
  margin: 0;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
  color: #666;
  gap: 1rem;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.history-group {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  padding: 0.75rem 1rem;
  background: #f8f9fa;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 3px solid transparent;
}

.group-header:hover {
  background: #e9ecef;
}

.group-header.active {
  background: #e3f2fd;
  border-left-color: #2196f3;
}

.group-header.active .group-title {
  color: #1976d2;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #2c3e50;
  font-weight: 500;
}

.group-count {
  color: #666;
  font-size: 0.9rem;
  font-weight: normal;
}

.group-summary {
  font-size: 0.9rem;
  color: #666;
}

.group-items {
  background: white;
}

.history-item {
  padding: 0.75rem 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  border-top: 1px solid #f0f0f0;
}

.history-item:hover {
  background: #f8f9fa;
}

.history-item.active {
  background: #E8F5E9;
  border-left: 3px solid #4CAF50;
}

.item-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.timestamp {
  color: #666;
  font-size: 0.9rem;
}

.item-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.9rem;
  color: #666;
}

/* Animaciones */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  max-height: 1000px;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

/* Animaciones */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.list-move {
  transition: transform 0.5s ease;
}
</style>