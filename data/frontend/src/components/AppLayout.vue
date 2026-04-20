<template>
  <div class="app-container">
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
            :modelValue="authStore.selectedProjectId"
            @update:modelValue="onProjectSelect"
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
          v-tooltip="{ value: 'Cerrar sesión', showDelay: 300 }"
        />
      </div>
    </header>

    <!-- Navegación principal -->
    <nav class="main-nav">
      <RouterLink
        to="/analysis"
        class="nav-item"
        :class="{ active: route.name === 'analysis' || route.name === 'analysis-detail' }"
      >
        <i class="pi pi-play"></i>
        Análisis
      </RouterLink>
      <RouterLink to="/history" class="nav-item" :class="{ active: route.name === 'history' }">
        <i class="pi pi-history"></i>
        Historia
      </RouterLink>
      <RouterLink
        to="/learning"
        class="nav-item"
        :class="{ active: route.name === 'learning', disabled: !authStore.selectedProjectId }"
      >
        <i class="pi pi-book"></i>
        Aprender
      </RouterLink>
      <RouterLink
        to="/llm-models"
        class="nav-item"
        :class="{ active: route.name === 'llm-models', disabled: !authStore.selectedWorkspaceId }"
      >
        <i class="pi pi-microchip"></i>
        Modelos LLM
      </RouterLink>
      <RouterLink
        v-if="authStore.isSuperAdmin"
        to="/admin"
        class="nav-item"
        :class="{ active: route.name === 'admin' }"
      >
        <i class="pi pi-cog"></i>
        Administración
      </RouterLink>
    </nav>

    <!-- Contenido principal -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/authStore'
import { useAnalysisStore } from '../stores/analysisStore'
import { useCourseStore } from '../stores/courseStore'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const store = useAnalysisStore()
const courseStore = useCourseStore()

const availableProjects = computed(() => {
  if (!authStore.selectedWorkspaceId) return []
  return authStore.projects[authStore.selectedWorkspaceId] || []
})

async function onWorkspaceChange() {
  if (authStore.selectedWorkspaceId) {
    await authStore.loadProjects(authStore.selectedWorkspaceId)
    const projects = authStore.projects[authStore.selectedWorkspaceId] || []
    if (projects.length > 0) {
      authStore.selectProject(projects[0].project_id)
    }
    // Limpiar datos al cambiar de workspace
    courseStore.clearAll()
    store.clearHistory()
  }
}

function onProjectSelect(projectId: string) {
  authStore.selectProject(projectId)
  onProjectChange()
}

async function onProjectChange() {
  if (authStore.selectedProjectId) {
    // Limpiar datos antiguos antes de cargar nuevos
    courseStore.clearAll()
    store.clearHistory()
    await store.loadReportsFromDirectory(authStore.selectedProjectId)
  }
}

function handleLogout() {
  authStore.logoutUser()
  router.push({ name: 'login' })
}
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
  text-decoration: none;
}

.nav-item:hover {
  color: #3b82f6;
  background: #f8fafc;
}

.nav-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

.nav-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* Contenido principal */
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}
</style>
