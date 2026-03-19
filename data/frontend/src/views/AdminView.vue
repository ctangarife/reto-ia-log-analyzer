<template>
  <div class="admin-view">
    <!-- Admin tabs -->
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

    <!-- Admin content -->
    <div class="admin-content">
      <WorkspaceManagement v-if="adminTab === 'workspaces'" />
      <ProjectManagement v-else-if="adminTab === 'projects'" />
      <UserManagement v-else-if="adminTab === 'users'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import WorkspaceManagement from '../components/WorkspaceManagement.vue'
import ProjectManagement from '../components/ProjectManagement.vue'
import UserManagement from '../components/UserManagement.vue'

const adminTab = ref<'workspaces' | 'projects' | 'users'>('workspaces')
</script>

<style scoped>
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
</style>
