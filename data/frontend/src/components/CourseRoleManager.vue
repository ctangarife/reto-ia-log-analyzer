<template>
  <Dialog v-model:visible="showDialog" header="Gestionar Roles de Curso" :style="{ width: '700px' }" modal>
    <div class="role-management">
      <!-- Tabs -->
      <TabView v-model:activeIndex="activeTab">
        <!-- Tab 1: Asignar Roles -->
        <TabPanel header="Asignar Roles">
          <div class="p-3">
            <h4>Asignar Rol a Usuario</h4>

            <div class="formgroup mt-4">
              <label for="userSelect">Usuario</label>
              <Dropdown
                id="userSelect"
                v-model="selectedUserId"
                :options="availableUsers"
                optionLabel="email"
                optionValue="id"
                placeholder="Selecciona un usuario"
                class="w-full"
                filter
              />
            </div>

            <div class="formgroup mt-4">
              <label for="roleSelect">Rol</label>
              <Dropdown
                id="roleSelect"
                v-model="selectedRole"
                :options="roleOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Selecciona un rol"
                class="w-full"
              />
              <small class="text-color-secondary block mt-2">
                {{ roleDescription }}
              </small>
            </div>

            <div class="flex justify-content-end mt-4">
              <Button
                label="Asignar Rol"
                @click="assignRole"
                :disabled="!selectedUserId || !selectedRole || assigning"
              />
            </div>
          </div>
        </TabPanel>

        <!-- Tab 2: Miembros con Roles -->
        <TabPanel header="Miembros">
          <div class="p-3">
            <h4>Usuarios con Roles de Curso</h4>

            <Dropdown
              v-model="roleFilter"
              :options="roleFilterOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Todos los roles"
              class="mb-3"
            />

            <DataTable
              :value="filteredMembers"
              stripedRows
              :paginator="true"
              :rows="10"
            >
              <Column field="email" header="Usuario" />
              <Column field="role_name" header="Rol">
                <template #body="slotProps">
                  <Chip :label="slotProps.data.role_name" severity="secondary" />
                </template>
              </Column>
              <Column header="Acciones" style="width: 100px">
                <template #body="slotProps">
                  <Button
                    icon="pi pi-times"
                    rounded
                    outlined
                    severity="danger"
                    size="small"
                    @click="removeRole(slotProps.data)"
                    v-tooltip="'Remover rol'"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>

        <!-- Tab 3: Mis Permisos -->
        <TabPanel header="Mis Permisos">
          <div class="p-3">
            <h4>Mis Permisos de Curso</h4>

            <div v-if="loadingPermissions" class="text-center p-4">
              <ProgressSpinner />
            </div>

            <div v-else>
              <div class="mb-4">
                <h5>Mis Roles</h5>
                <div v-if="myPermissions.roles.length > 0">
                  <Chip
                    v-for="role in myPermissions.roles"
                    :key="role.name"
                    :label="role.name"
                    class="mr-2 mb-2"
                  />
                </div>
                <p v-else class="text-color-secondary">No tienes roles de curso asignados.</p>
              </div>

              <div>
                <h5>Mis Permisos</h5>
                <div v-if="myPermissions.permissions.length > 0">
                  <div class="permission-grid">
                    <Chip
                      v-for="perm in myPermissions.permissions"
                      :key="perm"
                      :label="perm"
                      class="mr-2 mb-2"
                      severity="info"
                    />
                  </div>
                </div>
                <p v-else class="text-color-secondary">No tienes permisos de curso.</p>
              </div>
            </div>
          </div>
        </TabPanel>
      </TabView>
    </div>

    <template #footer>
      <Button label="Cerrar" @click="close" severity="secondary" />
    </template>

    <!-- Toast for notifications -->
    <Toast />
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'

import { courseRBACService } from '@/services/courseRBACService'

interface Props {
  workspaceId: string
  users: Array<{ id: string; email: string; first_name?: string; last_name?: string }>
}

const props = defineProps<Props>()
const emit = defineEmits<{
  roleAssigned: []
  roleRemoved: []
}>()

const showDialog = ref(false)
const activeTab = ref(0)
const assigning = ref(false)
const loadingPermissions = ref(false)

const selectedUserId = ref('')
const selectedRole = ref('')
const roleFilter = ref('')

const availableUsers = ref(props.users)
const members = ref<any[]>([])
const myPermissions = ref<{
  roles: any[]
  permissions: string[]
}>({ roles: [], permissions: [] })

const roleOptions = [
  { label: 'Creador de Curso', value: 'course_creator' },
  { label: 'Revisor de Curso', value: 'course_reviewer' },
  { label: 'Administrador de Curso', value: 'course_admin' }
]

const roleFilterOptions = [
  { label: 'Todos los Roles', value: '' },
  { label: 'Creador de Curso', value: 'course_creator' },
  { label: 'Revisor de Curso', value: 'course_reviewer' },
  { label: 'Administrador de Curso', value: 'course_admin' }
]

const roleDescription = computed(() => {
  const descriptions: Record<string, string> = {
    course_creator: 'Puede crear y editar sus propios cursos',
    course_reviewer: 'Puede revisar cursos y aprobarlos/rechazarlos',
    course_admin: 'Control total sobre cursos (crear, editar, revisar, publicar)'
  }
  return descriptions[selectedRole.value] || ''
})

const filteredMembers = computed(() => {
  if (!roleFilter.value) return members.value
  return members.value.filter(m => m.role_name === roleFilter.value)
})

const open = async () => {
  showDialog.value = true
  await loadMembers()
  await loadMyPermissions()
}

const close = () => {
  showDialog.value = false
}

const loadMembers = async () => {
  try {
    const response = await courseRBACService.getWorkspaceMembers(props.workspaceId)
    members.value = response.members
  } catch (e: any) {
    console.error('Error loading members:', e)
  }
}

const loadMyPermissions = async () => {
  loadingPermissions.value = true

  try {
    myPermissions.value = await courseRBACService.getMyPermissions(props.workspaceId)
  } catch (e: any) {
    console.error('Error loading permissions:', e)
  } finally {
    loadingPermissions.value = false
  }
}

const assignRole = async () => {
  if (!selectedUserId.value || !selectedRole.value) return

  assigning.value = true

  try {
    await courseRBACService.assignRole(props.workspaceId, {
      user_id: selectedUserId.value,
      role_name: selectedRole.value as any
    })

    // Reset form
    selectedUserId.value = ''
    selectedRole.value = ''

    // Reload members
    await loadMembers()
    emit('roleAssigned')
  } catch (e: any) {
    console.error('Error assigning role:', e)
  } finally {
    assigning.value = false
  }
}

const removeRole = async (member: any) => {
  if (!confirm(`¿Remover rol ${member.role_name} de ${member.email}?`)) return

  try {
    await courseRBACService.removeRole(props.workspaceId, {
      user_id: member.id,
      role_name: member.role_name
    })

    await loadMembers()
    emit('roleRemoved')
  } catch (e: any) {
    console.error('Error removing role:', e)
  }
}

defineExpose({
  open
})
</script>

<style scoped>
.role-management {
  padding: 1rem;
}

.formgroup {
  margin-bottom: 1rem;
}

.formgroup label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.permission-grid {
  display: flex;
  flex-wrap: wrap;
}

.text-color-secondary {
  color: var(--text-color-secondary);
}
</style>
