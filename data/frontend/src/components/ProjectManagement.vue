<template>
  <div class="project-management">
    <div class="management-header">
      <h2>Gestión de Proyectos</h2>
      <Button
        v-if="canCreateProjects"
        icon="pi pi-plus"
        label="Crear Proyecto"
        @click="openCreateDialog"
        severity="success"
        :disabled="!selectedWorkspace"
      />
    </div>

    <!-- Selector de workspace -->
    <div class="workspace-selector-section">
      <label>Workspace:</label>
      <Dropdown
        v-model="selectedWorkspace"
        :options="workspaces"
        optionLabel="name"
        optionValue="workspace_id"
        placeholder="Selecciona un workspace"
        @change="onWorkspaceChange"
        class="workspace-dropdown"
      />
    </div>

    <div v-if="!selectedWorkspace" class="empty-state">
      <i class="pi pi-building" style="font-size: 3rem; color: #ccc;"></i>
      <p>Selecciona un workspace para ver sus proyectos</p>
    </div>

    <div v-else-if="isLoading && projects.length === 0" class="loading-state">
      <ProgressSpinner />
      <p>Cargando proyectos...</p>
    </div>

    <div v-else-if="projects.length === 0" class="empty-state">
      <i class="pi pi-folder-open" style="font-size: 3rem; color: #ccc;"></i>
      <p>No hay proyectos en este workspace</p>
      <p v-if="canCreateProjects" class="empty-hint">
        Crea tu primer proyecto para comenzar
      </p>
    </div>

    <div v-else class="projects-list">
      <DataTable
        :value="projects"
        :paginator="true"
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        paginatorTemplate="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        currentPageReportTemplate="{first} a {last} de {totalRecords}"
        responsiveLayout="scroll"
        class="projects-table"
      >
        <Column field="name" header="Nombre" sortable>
          <template #body="{ data }">
            <div class="project-name">
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

    <!-- Dialog para crear/editar proyecto -->
    <Dialog
      v-model:visible="showForm"
      :header="isEditing ? 'Editar Proyecto' : 'Crear Proyecto'"
      :modal="true"
      :style="{ width: '500px' }"
      @hide="closeForm"
    >
      <div class="form-container">
        <div class="form-field">
          <label for="projectName">Nombre *</label>
          <InputText
            id="projectName"
            v-model="formData.name"
            placeholder="Ej: Análisis de Logs API"
            :class="{ 'p-invalid': errors.name }"
          />
          <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
        </div>

        <div class="form-field">
          <label for="projectSlug">Slug</label>
          <InputText
            id="projectSlug"
            v-model="formData.slug"
            placeholder="Ej: analisis-logs-api"
            :class="{ 'p-invalid': errors.slug }"
          />
          <small class="form-hint">Se generará automáticamente si se deja vacío</small>
          <small v-if="errors.slug" class="p-error">{{ errors.slug }}</small>
        </div>

        <div class="form-field">
          <label for="projectDescription">Descripción</label>
          <Textarea
            id="projectDescription"
            v-model="formData.description"
            placeholder="Descripción del proyecto..."
            rows="3"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          @click="closeForm"
        />
        <Button
          label="Guardar"
          @click="saveProject"
          :loading="isSaving"
          :disabled="!formData.name"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { getWorkspaceProjects, createProject, updateProject, deactivateProject, type Project, type ProjectCreate } from '../services/projectService'
import { formatDate } from '../utils/formatters'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Dropdown from 'primevue/dropdown'
import { useConfirm } from 'primevue/useconfirm'

const authStore = useAuthStore()
const confirm = useConfirm()

const workspaces = computed(() => authStore.workspaces)
const selectedWorkspace = ref<string | null>(null)
const projects = ref<Project[]>([])
const isLoading = ref(false)
const showForm = ref(false)
const selectedProject = ref<Project | null>(null)
const isSaving = ref(false)

const formData = ref<{
  name: string
  slug: string
  description: string
}>({
  name: '',
  slug: '',
  description: ''
})

const errors = ref<Record<string, string>>({})

const isEditing = computed(() => selectedProject.value !== null)

const canCreateProjects = computed(() => {
  // Super admin puede crear en cualquier workspace
  if (authStore.isSuperAdmin) return true
  // Usuarios con rol workspace_admin pueden crear
  const workspace = workspaces.value.find(w => w.workspace_id === selectedWorkspace.value)
  return workspace?.role === 'workspace_admin'
})

const canEdit = computed(() => (project: Project) => {
  if (authStore.isSuperAdmin) return true
  return project.role === 'project_admin' || project.role === 'workspace_admin'
})

const canDelete = computed(() => (project: Project) => {
  if (authStore.isSuperAdmin) return true
  return project.role === 'project_admin' || project.role === 'workspace_admin'
})

async function loadProjects() {
  if (!selectedWorkspace.value) {
    projects.value = []
    return
  }

  try {
    isLoading.value = true
    projects.value = await getWorkspaceProjects(selectedWorkspace.value)
  } catch (error: any) {
    console.error('Error cargando proyectos:', error)
    projects.value = []
  } finally {
    isLoading.value = false
  }
}

function onWorkspaceChange() {
  loadProjects()
}

function openCreateDialog() {
  selectedProject.value = null
  formData.value = { name: '', slug: '', description: '' }
  errors.value = {}
  showForm.value = true
}

function openEditDialog(project: Project) {
  selectedProject.value = project
  formData.value = {
    name: project.name,
    slug: project.slug,
    description: project.description || ''
  }
  errors.value = {}
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  selectedProject.value = null
  formData.value = { name: '', slug: '', description: '' }
  errors.value = {}
}

async function saveProject() {
  // Validación
  errors.value = {}
  if (!formData.value.name) {
    errors.value.name = 'El nombre es requerido'
    return
  }

  try {
    isSaving.value = true

    if (isEditing.value && selectedProject.value) {
      // Editar proyecto existente
      await updateProject(selectedProject.value.project_id, {
        name: formData.value.name,
        description: formData.value.description || null
      })
    } else if (selectedWorkspace.value) {
      // Crear nuevo proyecto
      const data: ProjectCreate = {
        name: formData.value.name,
        description: formData.value.description || null,
        slug: formData.value.slug || null
      }
      await createProject(selectedWorkspace.value, data)
    }

    closeForm()
    await loadProjects()
    // Recargar proyectos en el store de auth
    await authStore.loadProjects(selectedWorkspace.value!)
  } catch (error: any) {
    console.error('Error guardando proyecto:', error)
    alert(error.message || 'Error al guardar el proyecto')
  } finally {
    isSaving.value = false
  }
}

function confirmDeactivate(project: Project) {
  confirm.require({
    message: `¿Estás seguro de que deseas desactivar el proyecto "${project.name}"? Los datos no se borrarán, pero el proyecto no será visible para los usuarios.`,
    header: 'Confirmar desactivación',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Desactivar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await handleDeactivate(project)
    }
  })
}

async function handleDeactivate(project: Project) {
  try {
    await deactivateProject(project.project_id)
    await loadProjects()
    // Recargar proyectos en el store de auth
    if (selectedWorkspace.value) {
      await authStore.loadProjects(selectedWorkspace.value)
    }

    // Si el proyecto desactivado era el seleccionado, limpiar selección
    if (authStore.selectedProjectId === project.project_id) {
      authStore.selectedProjectId = null
    }
  } catch (error: any) {
    console.error('Error desactivando proyecto:', error)
    alert(error.message || 'Error al desactivar el proyecto')
  }
}

onMounted(() => {
  // Seleccionar el primer workspace por defecto si hay alguno
  if (workspaces.value.length > 0) {
    selectedWorkspace.value = workspaces.value[0].workspace_id
    loadProjects()
  }
})
</script>

<style scoped>
.project-management {
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

.workspace-selector-section {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.workspace-selector-section label {
  font-weight: 500;
  color: #2c3e50;
}

.workspace-dropdown {
  min-width: 250px;
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

.projects-table {
  margin-top: 1rem;
}

.project-name {
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

.form-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.5rem 0;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 500;
  color: #2c3e50;
}

.form-hint {
  color: #999;
  font-size: 0.85rem;
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
