<template>
  <div class="user-management">
    <div class="management-header">
      <h2>Gestión de Usuarios</h2>
      <Button
        v-if="authStore.isSuperAdmin"
        icon="pi pi-plus"
        label="Crear Usuario"
        @click="openCreateDialog"
        severity="success"
      />
    </div>

    <div v-if="isLoading && users.length === 0" class="loading-state">
      <ProgressSpinner />
      <p>Cargando usuarios...</p>
    </div>

    <div v-else-if="users.length === 0" class="empty-state">
      <i class="pi pi-users" style="font-size: 3rem; color: #ccc;"></i>
      <p>No hay usuarios registrados</p>
    </div>

    <div v-else class="users-list">
      <DataTable
        :value="users"
        :paginator="true"
        :rows="10"
        :rowsPerPageOptions="[10, 25, 50]"
        paginatorTemplate="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        currentPageReportTemplate="{first} a {last} de {totalRecords}"
        responsiveLayout="scroll"
        class="users-table"
      >
        <Column field="username" header="Usuario" sortable>
          <template #body="{ data }">
            <div class="user-info">
              <strong>{{ data.username }}</strong>
              <Tag v-if="data.is_super_admin" value="Super Admin" severity="warning" />
            </div>
          </template>
        </Column>

        <Column field="email" header="Email" sortable>
          <template #body="{ data }">
            {{ data.email }}
          </template>
        </Column>

        <Column field="full_name" header="Nombre Completo">
          <template #body="{ data }">
            {{ data.full_name || '-' }}
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
                icon="pi pi-key"
                severity="secondary"
                text
                rounded
                @click="openAssignRoleDialog(data)"
                title="Asignar Rol"
              />
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text
                rounded
                @click="openEditDialog(data)"
                title="Editar"
              />
              <Button
                icon="pi pi-power-off"
                severity="warning"
                text
                rounded
                @click="confirmToggleActive(data)"
                :disabled="data.id === currentUserId"
                :title="data.is_active ? 'Desactivar' : 'Activar'"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Dialog de confirmación -->
    <ConfirmDialog />

    <!-- Dialog para crear usuario -->
    <Dialog
      v-model:visible="showCreateForm"
      header="Crear Usuario"
      :modal="true"
      :style="{ width: '500px' }"
      @hide="closeCreateForm"
    >
      <div class="form-container">
        <div class="form-field">
          <label for="userName">Usuario *</label>
          <InputText
            id="userName"
            v-model="createFormData.username"
            placeholder="nombre_de_usuario"
            :class="{ 'p-invalid': createErrors.username }"
          />
          <small v-if="createErrors.username" class="p-error">{{ createErrors.username }}</small>
        </div>

        <div class="form-field">
          <label for="userEmail">Email *</label>
          <InputText
            id="userEmail"
            v-model="createFormData.email"
            type="email"
            placeholder="usuario@ejemplo.com"
            :class="{ 'p-invalid': createErrors.email }"
          />
          <small v-if="createErrors.email" class="p-error">{{ createErrors.email }}</small>
        </div>

        <div class="form-field">
          <label for="userFullName">Nombre Completo *</label>
          <InputText
            id="userFullName"
            v-model="createFormData.full_name"
            placeholder="Juan Pérez"
            :class="{ 'p-invalid': createErrors.full_name }"
          />
          <small v-if="createErrors.full_name" class="p-error">{{ createErrors.full_name }}</small>
        </div>

        <div class="form-field">
          <label for="userPassword">Contraseña *</label>
          <Password
            id="userPassword"
            v-model="createFormData.password"
            placeholder="Contraseña"
            toggleMask
            :class="{ 'p-invalid': createErrors.password }"
          />
          <small class="form-hint">Mínimo 8 caracteres</small>
          <small v-if="createErrors.password" class="p-error">{{ createErrors.password }}</small>
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          @click="closeCreateForm"
        />
        <Button
          label="Crear"
          @click="createUser"
          :loading="isSaving"
        />
      </template>
    </Dialog>

    <!-- Dialog para editar usuario -->
    <Dialog
      v-model:visible="showEditForm"
      header="Editar Usuario"
      :modal="true"
      :style="{ width: '500px' }"
      @hide="closeEditForm"
    >
      <div class="form-container">
        <div class="form-field">
          <label for="editUserName">Usuario</label>
          <InputText
            id="editUserName"
            v-model="editFormData.username"
            :class="{ 'p-invalid': editErrors.username }"
          />
          <small v-if="editErrors.username" class="p-error">{{ editErrors.username }}</small>
        </div>

        <div class="form-field">
          <label for="editUserEmail">Email</label>
          <InputText
            id="editUserEmail"
            v-model="editFormData.email"
            type="email"
            :class="{ 'p-invalid': editErrors.email }"
          />
          <small v-if="editErrors.email" class="p-error">{{ editErrors.email }}</small>
        </div>

        <div class="form-field">
          <label for="editUserFullName">Nombre Completo</label>
          <InputText
            id="editUserFullName"
            v-model="editFormData.full_name"
          />
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          @click="closeEditForm"
        />
        <Button
          label="Guardar"
          @click="updateUser"
          :loading="isSaving"
        />
      </template>
    </Dialog>

    <!-- Dialog para asignar rol -->
    <Dialog
      v-model:visible="showRoleForm"
      header="Asignar Rol a Usuario"
      :modal="true"
      :style="{ width: '600px' }"
      @hide="closeRoleForm"
    >
      <div v-if="selectedUser" class="role-assignment-container">
        <Message severity="info" :closable="false">
          Asignando rol para: <strong>{{ selectedUser.username }}</strong>
        </Message>

        <div class="form-container">
          <div class="form-field">
            <label for="roleScope">Ámbito del Rol *</label>
            <Dropdown
              id="roleScope"
              v-model="roleFormData.scope"
              :options="scopeOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Selecciona el ámbito"
              @change="onScopeChange"
              class="full-width"
            />
          </div>

          <div class="form-field" v-if="roleFormData.scope === 'workspace'">
            <label for="roleWorkspace">Workspace *</label>
            <Dropdown
              id="roleWorkspace"
              v-model="roleFormData.workspace_id"
              :options="workspaces"
              optionLabel="name"
              optionValue="workspace_id"
              placeholder="Selecciona un workspace"
              class="full-width"
            />
          </div>

          <div class="form-field" v-if="roleFormData.scope === 'project'">
            <label for="roleWorkspace">Workspace *</label>
            <Dropdown
              id="roleWorkspaceForProject"
              v-model="roleFormData.workspace_id"
              :options="workspaces"
              optionLabel="name"
              optionValue="workspace_id"
              placeholder="Selecciona un workspace"
              @change="loadProjectsForRole"
              class="full-width"
            />
          </div>

          <div class="form-field" v-if="roleFormData.scope === 'project' && roleFormData.workspace_id">
            <label for="roleProject">Proyecto *</label>
            <Dropdown
              id="roleProject"
              v-model="roleFormData.project_id"
              :options="availableProjectsForRole"
              optionLabel="name"
              optionValue="project_id"
              placeholder="Selecciona un proyecto"
              class="full-width"
            />
          </div>

          <div class="form-field" v-if="roleFormData.scope">
            <label for="roleName">Rol *</label>
            <Dropdown
              id="roleName"
              v-model="roleFormData.role"
              :options="availableRoles"
              optionLabel="label"
              optionValue="value"
              placeholder="Selecciona un rol"
              class="full-width"
            />
          </div>
        </div>

        <Message severity="warn" :closable="false" class="role-info">
          <i class="pi pi-info-circle"></i>
          <strong>Información:</strong>
          <ul>
            <li>Usuarios con rol de <strong>workspace</strong> pueden ver TODOS los proyectos del workspace.</li>
            <li>Usuarios con rol de <strong>proyecto</strong> SOLO pueden ver el proyecto asignado.</li>
          </ul>
        </Message>
      </div>

      <template #footer>
        <Button
          label="Cancelar"
          severity="secondary"
          @click="closeRoleForm"
        />
        <Button
          label="Asignar Rol"
          @click="assignRole"
          :loading="isSaving"
          :disabled="!canAssignRole"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { registerUser } from '../services/authService'
import { getWorkspaces, type Workspace } from '../services/workspaceService'
import { getWorkspaceProjects, type Project } from '../services/projectService'
import { formatDate } from '../utils/formatters'
import api from '../services/api'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Dropdown from 'primevue/dropdown'
import Message from 'primevue/message'
import { useConfirm } from 'primevue/useconfirm'

interface User {
  id: string
  username: string
  email: string
  full_name: string
  is_active: boolean
  is_super_admin: boolean
  created_at: string
}

const authStore = useAuthStore()
const confirm = useConfirm()

const users = ref<User[]>([])
const workspaces = ref<Workspace[]>([])
const availableProjectsForRole = ref<Project[]>([])
const isLoading = ref(false)
const isSaving = ref(false)

// Forms
const showCreateForm = ref(false)
const showEditForm = ref(false)
const showRoleForm = ref(false)

const selectedUser = ref<User | null>(null)
const currentUserId = computed(() => authStore.user?.user_id || '')

const createFormData = ref({
  username: '',
  email: '',
  full_name: '',
  password: ''
})

const editFormData = ref({
  username: '',
  email: '',
  full_name: ''
})

const roleFormData = ref({
  scope: '',
  workspace_id: '',
  project_id: '',
  role: ''
})

const createErrors = ref<Record<string, string>>({})
const editErrors = ref<Record<string, string>>({})

const scopeOptions = [
  { label: 'Workspace', value: 'workspace' },
  { label: 'Proyecto', value: 'project' }
]

const workspaceRoles = [
  { label: 'Viewer (Solo lectura)', value: 'viewer' },
  { label: 'Analyst (Análisis)', value: 'analyst' },
  { label: 'Workspace Admin (Admin)', value: 'workspace_admin' }
]

const projectRoles = [
  { label: 'Viewer (Solo lectura)', value: 'viewer' },
  { label: 'Analyst (Análisis)', value: 'analyst' },
  { label: 'Project Admin (Admin)', value: 'project_admin' }
]

const availableRoles = computed(() => {
  if (roleFormData.value.scope === 'workspace') {
    return workspaceRoles
  }
  return projectRoles
})

const canAssignRole = computed(() => {
  if (!roleFormData.value.scope) return false
  if (roleFormData.value.scope === 'workspace') {
    return roleFormData.value.workspace_id && roleFormData.value.role
  }
  if (roleFormData.value.scope === 'project') {
    return roleFormData.value.workspace_id && roleFormData.value.project_id && roleFormData.value.role
  }
  return false
})

async function loadUsers() {
  try {
    isLoading.value = true
    const response = await api.get<User[]>('/users')
    users.value = response.data
  } catch (error: any) {
    console.error('Error cargando usuarios:', error)
    users.value = []
  } finally {
    isLoading.value = false
  }
}

async function loadWorkspaces() {
  try {
    workspaces.value = await getWorkspaces()
  } catch (error: any) {
    console.error('Error cargando workspaces:', error)
    workspaces.value = []
  }
}

function onScopeChange() {
  // Reset project selection when scope changes
  roleFormData.value.workspace_id = ''
  roleFormData.value.project_id = ''
  roleFormData.value.role = ''
}

async function loadProjectsForRole() {
  if (roleFormData.value.workspace_id) {
    try {
      availableProjectsForRole.value = await getWorkspaceProjects(roleFormData.value.workspace_id)
    } catch (error: any) {
      console.error('Error cargando proyectos:', error)
      availableProjectsForRole.value = []
    }
  } else {
    availableProjectsForRole.value = []
  }
  roleFormData.value.project_id = ''
}

function openCreateDialog() {
  createFormData.value = { username: '', email: '', full_name: '', password: '' }
  createErrors.value = {}
  showCreateForm.value = true
}

function closeCreateForm() {
  showCreateForm.value = false
  createFormData.value = { username: '', email: '', full_name: '', password: '' }
  createErrors.value = {}
}

async function createUser() {
  // Validación
  createErrors.value = {}
  if (!createFormData.value.username) {
    createErrors.value.username = 'El usuario es requerido'
    return
  }
  if (!createFormData.value.email) {
    createErrors.value.email = 'El email es requerido'
    return
  }
  if (!createFormData.value.full_name) {
    createErrors.value.full_name = 'El nombre completo es requerido'
    return
  }
  if (!createFormData.value.password || createFormData.value.password.length < 8) {
    createErrors.value.password = 'La contraseña debe tener al menos 8 caracteres'
    return
  }

  try {
    isSaving.value = true
    await registerUser(createFormData.value)
    closeCreateForm()
    await loadUsers()
  } catch (error: any) {
    console.error('Error creando usuario:', error)
    alert(error.message || 'Error al crear el usuario')
  } finally {
    isSaving.value = false
  }
}

function openEditDialog(user: User) {
  selectedUser.value = user
  editFormData.value = {
    username: user.username,
    email: user.email,
    full_name: user.full_name
  }
  editErrors.value = {}
  showEditForm.value = true
}

function closeEditForm() {
  showEditForm.value = false
  selectedUser.value = null
  editFormData.value = { username: '', email: '', full_name: '' }
  editErrors.value = {}
}

async function updateUser() {
  if (!selectedUser.value) return

  try {
    isSaving.value = true
    await api.put(`/users/${selectedUser.value.id}`, editFormData.value)
    closeEditForm()
    await loadUsers()
  } catch (error: any) {
    console.error('Error actualizando usuario:', error)
    alert(error.response?.data?.detail || 'Error al actualizar el usuario')
  } finally {
    isSaving.value = false
  }
}

function confirmToggleActive(user: User) {
  const action = user.is_active ? 'desactivar' : 'activar'
  confirm.require({
    message: `¿Estás seguro de que deseas ${action} el usuario "${user.username}"?`,
    header: `Confirmar ${action}`,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: user.is_active ? 'p-button-warning' : 'p-button-success',
    acceptLabel: user.is_active ? 'Desactivar' : 'Activar',
    rejectLabel: 'Cancelar',
    accept: async () => {
      await handleToggleActive(user)
    }
  })
}

async function handleToggleActive(user: User) {
  try {
    await api.patch(`/users/${user.id}/toggle-active`)
    await loadUsers()
  } catch (error: any) {
    console.error('Error cambiando estado de usuario:', error)
    alert(error.response?.data?.detail || 'Error al cambiar el estado del usuario')
  }
}

function openAssignRoleDialog(user: User) {
  selectedUser.value = user
  roleFormData.value = {
    scope: '',
    workspace_id: '',
    project_id: '',
    role: ''
  }
  availableProjectsForRole.value = []
  showRoleForm.value = true
}

function closeRoleForm() {
  showRoleForm.value = false
  selectedUser.value = null
  roleFormData.value = {
    scope: '',
    workspace_id: '',
    project_id: '',
    role: ''
  }
  availableProjectsForRole.value = []
}

async function assignRole() {
  if (!selectedUser.value) return

  try {
    isSaving.value = true

    if (roleFormData.value.scope === 'workspace') {
      // Asignar rol a workspace
      await api.post(`/workspaces/${roleFormData.value.workspace_id}/members`, {
        user_id: selectedUser.value.id,
        role: roleFormData.value.role
      })
    } else if (roleFormData.value.scope === 'project') {
      // Asignar rol a proyecto
      await api.post(`/projects/${roleFormData.value.project_id}/members`, {
        user_id: selectedUser.value.id,
        role: roleFormData.value.role
      })
    }

    closeRoleForm()
    alert('Rol asignado exitosamente')
  } catch (error: any) {
    console.error('Error asignando rol:', error)
    alert(error.response?.data?.detail || 'Error al asignar el rol')
  } finally {
    isSaving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadWorkspaces()])
})
</script>

<style scoped>
.user-management {
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

.users-table {
  margin-top: 1rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
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

.full-width {
  width: 100%;
}

.role-assignment-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.role-info {
  margin-top: 1rem;
}

.role-info ul {
  margin: 0.5rem 0 0 1.5rem;
  padding: 0;
}

.role-info li {
  margin-bottom: 0.25rem;
}

:deep(.p-datatable) {
  font-size: 0.9rem;
}

:deep(.p-datatable-thead > tr > th) {
  background-color: #f8f9fa;
  font-weight: 600;
  color: #2c3e50;
}
</style>
