<template>
  <Dialog
    :visible="visible"
    :modal="true"
    :closable="true"
    :draggable="false"
    :style="{ width: '500px' }"
    @hide="$emit('close')"
  >
    <template #header>
      <h3>{{ isEdit ? 'Editar Workspace' : 'Crear Workspace' }}</h3>
    </template>

    <form @submit.prevent="handleSubmit" class="workspace-form">
      <div class="form-group">
        <label for="name">Nombre <span class="required">*</span></label>
        <InputText
          id="name"
          v-model="formData.name"
          placeholder="Nombre del workspace"
          :disabled="isLoading"
          class="w-full"
          :class="{ 'p-invalid': errors.name }"
          required
        />
        <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
        <small v-else class="form-hint">Mínimo 1 carácter, máximo 255 caracteres</small>
      </div>

      <div class="form-group">
        <label for="description">Descripción</label>
        <Textarea
          id="description"
          v-model="formData.description"
          placeholder="Descripción del workspace (opcional)"
          :disabled="isLoading"
          class="w-full"
          rows="3"
          :autoResize="true"
        />
      </div>

      <div class="form-group">
        <label for="slug">Slug</label>
        <InputText
          id="slug"
          v-model="formData.slug"
          placeholder="mi-workspace (opcional, se genera automáticamente)"
          :disabled="isLoading"
          class="w-full"
          :class="{ 'p-invalid': errors.slug }"
        />
        <small v-if="errors.slug" class="p-error">{{ errors.slug }}</small>
        <small v-else class="form-hint">Identificador URL-friendly. Si se deja vacío, se genera automáticamente desde el nombre</small>
      </div>

      <div v-if="isEdit" class="form-group">
        <div class="checkbox-group">
          <Checkbox
            id="is_active"
            v-model="formData.is_active"
            :binary="true"
            :disabled="isLoading"
          />
          <label for="is_active">Workspace activo</label>
        </div>
        <small class="form-hint">Un workspace inactivo no será visible para los usuarios</small>
      </div>

      <Message
        v-if="errorMessage"
        severity="error"
        :closable="false"
        class="error-message"
      >
        {{ errorMessage }}
      </Message>
    </form>

    <template #footer>
      <Button
        label="Cancelar"
        severity="secondary"
        @click="$emit('close')"
        :disabled="isLoading"
      />
      <Button
        :label="isEdit ? 'Actualizar' : 'Crear'"
        @click="handleSubmit"
        :loading="isLoading"
        :disabled="!isFormValid"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { createWorkspace, updateWorkspace, type Workspace, type WorkspaceCreate, type WorkspaceUpdate } from '../services/workspaceService'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Message from 'primevue/message'

const props = defineProps<{
  visible: boolean
  workspace?: Workspace | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', workspace: Workspace): void
}>()

const isLoading = ref(false)
const errorMessage = ref('')
const errors = ref<Record<string, string>>({})

const isEdit = computed(() => !!props.workspace)

const formData = ref<WorkspaceCreate & { is_active?: boolean }>({
  name: '',
  description: null,
  slug: null,
  is_active: true
})

// Resetear formulario cuando cambia el workspace o se abre/cierra
watch([() => props.visible, () => props.workspace], ([visible, workspace]) => {
  if (visible) {
    if (workspace) {
      // Modo edición
      formData.value = {
        name: workspace.name,
        description: workspace.description || null,
        slug: workspace.slug,
        is_active: workspace.is_active
      }
    } else {
      // Modo creación
      formData.value = {
        name: '',
        description: null,
        slug: null,
        is_active: true
      }
    }
    errorMessage.value = ''
    errors.value = {}
  }
}, { immediate: true })

const isFormValid = computed(() => {
  return formData.value.name.trim().length > 0 && formData.value.name.length <= 255
})

function validateForm(): boolean {
  errors.value = {}

  if (!formData.value.name || formData.value.name.trim().length === 0) {
    errors.value.name = 'El nombre es requerido'
    return false
  }

  if (formData.value.name.length > 255) {
    errors.value.name = 'El nombre no puede exceder 255 caracteres'
    return false
  }

  if (formData.value.slug && formData.value.slug.length > 255) {
    errors.value.slug = 'El slug no puede exceder 255 caracteres'
    return false
  }

  return true
}

async function handleSubmit() {
  if (!validateForm()) {
    return
  }

  try {
    isLoading.value = true
    errorMessage.value = ''
    errors.value = {}

    let result: Workspace

    if (isEdit.value && props.workspace) {
      // Actualizar
      const updateData: WorkspaceUpdate = {
        name: formData.value.name,
        description: formData.value.description || null,
        is_active: formData.value.is_active
      }
      result = await updateWorkspace(props.workspace.id || props.workspace.workspace_id, updateData)
    } else {
      // Crear
      const createData: WorkspaceCreate = {
        name: formData.value.name,
        description: formData.value.description || null,
        slug: formData.value.slug || null
      }
      result = await createWorkspace(createData)
    }

    emit('saved', result)
    emit('close')
  } catch (error: any) {
    errorMessage.value = error.message || 'Error al guardar el workspace'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.workspace-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.required {
  color: #e24c4c;
}

.form-hint {
  color: #666;
  font-size: 0.85rem;
}

.checkbox-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-group label {
  margin: 0;
  font-weight: normal;
  cursor: pointer;
}

.error-message {
  margin: 0;
}

:deep(.p-inputtext),
:deep(.p-textarea) {
  width: 100%;
}

:deep(.p-dialog-header) {
  padding: 1.5rem;
}

:deep(.p-dialog-content) {
  padding: 1.5rem;
}

:deep(.p-dialog-footer) {
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
