<template>
  <div class="workspace-management">
    <div class="management-header">
      <h2>Gestión de Workspaces</h2>
      <Button
        v-if="authStore.isSuperAdmin"
        icon="pi pi-plus"
        label="Crear Workspace"
        @click="openCreateDialog"
        severity="success"
      />
    </div>

    <div v-if="isLoading && workspaces.length === 0" class="loading-state">
      <ProgressSpinner />
      <p>Cargando workspaces...</p>
    </div>

    <div v-else-if="workspaces.length === 0" class="empty-state">
      <i class="pi pi-folder-open" style="font-size: 3rem; color: #ccc;"></i>
      <p>No hay workspaces disponibles</p>
      <p v-if="authStore.isSuperAdmin" class="empty-hint">
        Crea tu primer workspace para comenzar
      </p>
    </div>

    <div v-else class="workspaces-list">
      <DataTable
        :value="workspaces"
        :paginator="true"
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        paginatorTemplate="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        currentPageReportTemplate="{first} a {last} de {totalRecords}"
        responsiveLayout="scroll"
        class="workspaces-table"
      >
        <Column field="name" header="Nombre" sortable>
          <template #body="{ data }">
            <div class="workspace-name">
              <strong>{{ data.name }}</strong>
              <span v-if="data.role" class="role-badge">{{ data.role }}</span>
            </div>
          </template>
        </Column>

        <Column field="description" header="Descripción">
          <template #body="{ data }">
            <span class="description-text">{{ data.description || '-' }}</span>
          </template>
        </Column>

        <Column field="slug" header="Slug">
          <template #body="{ data }">
            <code class="slug-text">{{ data.slug }}</code>
          </template>
        </Column>

        <Column field="is_active" header="Estado" sortable>
          <template #body="{ data }">
            <Tag
              :value="data.is_active ? 'Activo' : 'Inactivo'"
              :severity="data.is_active ? 'success' : 'danger'"
            />
          </template>
        </Column>

        <Column field="created_at" header="Creado" sortable>
          <template #body="{ data }">
            {{ formatDate(data.created_at) }}
          </template>
        </Column>

        <Column header="Acciones" :exportable="false">
          <template #body="{ data }">
            <div class="action-buttons">
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text
                rounded
                @click="openEditDialog(data)"
                :disabled="!canEdit(data)"
                title="Editar"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                @click="confirmDeactivate(data)"
                :disabled="!canDelete(data)"
                title="Desactivar"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Dialog de confirmación para desactivar -->
    <ConfirmDialog />

    <!-- Formulario de crear/editar -->
    <WorkspaceForm
      :visible="showForm"
      :workspace="selectedWorkspace"
      @close="closeForm"
      @saved="handleWorkspaceSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { getWorkspaces, deactivateWorkspace, type Workspace } from '../services/workspaceService'
import { formatDate } from '../utils/formatters'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import WorkspaceForm from './WorkspaceForm.vue'

const authStore = useAuthStore()
const confirm = useConfirm()

const workspaces = ref<Workspace[]>([])
const isLoading = ref(false)
const showForm = ref(false)
const selectedWorkspace = ref<Workspace | null>(null)

const canEdit = computed(() => (workspace: Workspace) => {
  // Super admin puede editar todos
  if (authStore.isSuperAdmin) return true
  // Usuarios con rol workspace_admin pueden editar
  return workspace.role === 'workspace_admin'
})

const canDelete = computed(() => (workspace: Workspace) => {
  // Super admin puede eliminar todos
  if (authStore.isSuperAdmin) return true
  // Usuarios con rol workspace_admin pueden eliminar
  return workspace.role === 'workspace_admin'
})

async function loadWorkspaces() {
  try {
    isLoading.value = true
    workspaces.value = await getWorkspaces()
  } catch (error: any) {
    console.error('Error cargando workspaces:', error)
    workspaces.value = []
  } finally {
    isLoading.value = false
  }
}

function openCreateDialog() {
  selectedWorkspace.value = null
  showForm.value = true
}

function openEditDialog(workspace: Workspace) {
  selectedWorkspace.value = workspace
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  selectedWorkspace.value = null
}

async function handleWorkspaceSaved(workspace: Workspace) {
  // Recargar lista de workspaces
  await loadWorkspaces()
  // Actualizar workspaces en el store de auth
  await authStore.refreshWorkspaces()
}

function confirmDeactivate(workspace: Workspace) {
  confirm.require({
    message: `¿Estás seguro de que deseas desactivar el workspace "${workspace.name}"? Los datos no se borrarán, pero el workspace no será visible para los usuarios.`,
    header: 'Confirmar desactivación',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Desactivar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await handleDeactivate(workspace)
    }
  })
}

async function handleDeactivate(workspace: Workspace) {
  try {
    await deactivateWorkspace(workspace.id || workspace.workspace_id)
    // Recargar lista
    await loadWorkspaces()
    // Actualizar workspaces en el store de auth
    await authStore.refreshWorkspaces()
    
    // Si el workspace desactivado era el seleccionado, limpiar selección
    if (authStore.selectedWorkspaceId === (workspace.id || workspace.workspace_id)) {
      authStore.selectedWorkspaceId = null
      authStore.selectedProjectId = null
    }
  } catch (error: any) {
    console.error('Error desactivando workspace:', error)
    // Mostrar mensaje de error (podrías usar un toast aquí)
    alert(error.message || 'Error al desactivar el workspace')
  }
}

onMounted(() => {
  loadWorkspaces()
})
</script>

<style scoped>
.workspace-management {
  padding: 1.5rem;
}

.management-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.management-header h2 {
  margin: 0;
  color: #2c3e50;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  color: #666;
  gap: 1rem;
}

.empty-hint {
  font-size: 0.9rem;
  color: #999;
}

.workspaces-table {
  margin-top: 1rem;
}

.workspace-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.role-badge {
  background-color: #e3f2fd;
  color: #1976d2;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.description-text {
  color: #666;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.slug-text {
  background-color: #f5f5f5;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85rem;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

:deep(.p-datatable) {
  font-size: 0.9rem;
}

:deep(.p-datatable-header) {
  background: transparent;
  border: none;
  padding: 0;
}

:deep(.p-datatable-thead > tr > th) {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #2c3e50;
}
</style>
