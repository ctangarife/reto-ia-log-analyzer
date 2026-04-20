<template>
  <div class="llm-config">
    <!-- Header -->
    <div class="llm-config-header">
      <h2>
        <i class="pi pi-cog"></i>
        Configuración LLM
      </h2>
      <p class="subtitle">
        Configura las credenciales de los proveedores LLM. Selecciona los modelos en la vista de "Modelos LLM".
      </p>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
      <p>Cargando configuración...</p>
    </div>

    <!-- Config content -->
    <div v-else class="config-content">
      <!-- Provider selection -->
      <div class="config-section">
        <h3>
          <i class="pi pi-server"></i>
          Proveedor
        </h3>
        <div class="provider-cards">
          <div
            v-for="provider in providers"
            :key="provider.id"
            class="provider-card"
            :class="{ active: selectedProvider === provider.id, available: isProviderAvailable(provider.id) }"
            @click="selectProvider(provider.id)"
          >
            <div class="provider-icon">
              <i :class="getProviderIcon(provider.id)"></i>
            </div>
            <div class="provider-info">
              <h4>{{ provider.name }}</h4>
              <p>{{ provider.description }}</p>
              <div class="provider-status">
                <span
                  class="status-badge"
                  :class="{ available: isProviderAvailable(provider.id) }"
                >
                  <i class="pi" :class="isProviderAvailable(provider.id) ? 'pi-check' : 'pi-times'"></i>
                  {{ isProviderAvailable(provider.id) ? 'Configurado' : 'No configurado' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Credentials configuration -->
      <div v-if="selectedProvider" class="config-section">
        <div class="section-header">
          <h3>
            <i class="pi pi-key"></i>
            Credenciales
          </h3>
          <Tag
            v-if="currentProviderHasSavedCredentials"
            icon="pi pi-check"
            severity="success"
          >
            Configuradas
          </Tag>
        </div>

        <div class="credentials-form">
          <div v-if="currentProviderHasSavedCredentials" class="credentials-status">
            <i class="pi pi-lock"></i>
            <span>Tienes credenciales guardadas para {{ getProviderName(selectedProvider) }}</span>
          </div>

          <div class="form-group">
            <label>API Key</label>
            <Password
              v-model="credentials.apiKey"
              :feedback="false"
              toggleMask
              :placeholder="apiKeyPlaceholder"
              class="credential-input"
            />
            <small class="help-text">
              <i class="pi pi-info-circle"></i>
              <span v-if="currentProviderHasSavedCredentials">
                Deja este campo vacío para usar las credenciales guardadas, o ingresa una nueva para reemplazarlas.
              </span>
              <span v-else>
                Tu API key se guardará de forma segura en tu workspace.
              </span>
            </small>
          </div>

          <div class="form-group">
            <label>API Endpoint (opcional)</label>
            <InputText
              v-model="credentials.apiEndpoint"
              :placeholder="apiEndpointPlaceholder"
              class="credential-input"
            />
            <small class="help-text">
              Deja vacío para usar el endpoint default de {{ getProviderName(selectedProvider) }}
            </small>
          </div>

          <div class="form-actions">
            <Button
              label="Probar conexión"
              icon="pi pi-plug"
              @click="testConnection"
              :loading="testingConnection"
              class="test-button"
            />
            <Button
              label="Guardar Credenciales"
              icon="pi pi-save"
              @click="saveCredentials"
              :disabled="!credentials.apiKey && !currentProviderHasSavedCredentials"
              :loading="saving"
              severity="success"
            />
          </div>
        </div>
      </div>

      <!-- Status message -->
      <Message
        v-if="statusMessage"
        :severity="statusMessage.type"
        :life="5000"
        :closable="false"
      >
        {{ statusMessage.text }}
      </Message>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Password from 'primevue/password'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import llmService from '../services/llmService'
import type { LLMProvider } from '../services/llmService'

// State
const loading = ref(true)
const saving = ref(false)
const testingConnection = ref(false)

const providers = ref<LLMProvider[]>([])
const selectedProvider = ref<string>('')
const credentials = ref<{ apiKey: string; apiEndpoint: string }>({
  apiKey: '',
  apiEndpoint: ''
})

const hasSavedCredentials = ref<Record<string, boolean>>({})
const savedEndpoints = ref<Record<string, string>>({})

const statusMessage = ref<{ type: 'success' | 'error' | 'info'; text: string } | null>(null)

// Computed
const currentProviderHasSavedCredentials = computed(() => {
  return selectedProvider.value ? (hasSavedCredentials.value[selectedProvider.value] || false) : false
})

const currentSavedEndpoint = computed(() => {
  return selectedProvider.value ? (savedEndpoints.value[selectedProvider.value] || '') : ''
})

const apiKeyPlaceholder = computed(() => {
  return currentProviderHasSavedCredentials.value
    ? '•••••••••••• (Deja vacío para mantener)'
    : 'Ingresa tu API key'
})

const apiEndpointPlaceholder = computed(() => {
  return currentSavedEndpoint.value && currentProviderHasSavedCredentials.value
    ? currentSavedEndpoint.value
    : 'URL del endpoint (opcional)'
})

// Methods
const loadProviders = async () => {
  try {
    const data = await llmService.getProviders()
    providers.value = data.providers
  } catch (error) {
    console.error('Error loading providers:', error)
    showStatus('error', 'Error cargando proveedores')
  }
}

const loadSavedCredentials = async (providerId: string) => {
  try {
    const saved = await llmService.getSavedCredentials(providerId)

    // Actualizar flag de credenciales guardadas
    hasSavedCredentials.value[providerId] = saved.hasCredentials

    if (saved.hasCredentials) {
      // Guardar endpoint para mostrar en placeholder
      if (saved.apiEndpoint) {
        savedEndpoints.value[providerId] = saved.apiEndpoint
      }
    } else {
      // Limpiar endpoint si no hay guardadas
      delete savedEndpoints.value[providerId]
    }
  } catch (error) {
    console.error('Error loading saved credentials:', error)
    // En caso de error, limpiar
    delete savedEndpoints.value[providerId]
    hasSavedCredentials.value[providerId] = false
  }
}

const selectProvider = async (providerId: string) => {
  selectedProvider.value = providerId

  // Cargar credenciales guardadas del workspace
  await loadSavedCredentials(providerId)

  // Limpiar formulario de credenciales
  credentials.value = { apiKey: '', apiEndpoint: '' }
}

const getProviderName = (providerId: string): string => {
  const provider = providers.value.find(p => p.id === providerId)
  return provider?.name || providerId
}

const getProviderIcon = (providerId: string): string => {
  const icons: Record<string, string> = {
    'ollama': 'pi-cloud',
    'zai': 'pi-compass',
    'minimax': 'pi-bolt'
  }
  return icons[providerId] || 'pi-server'
}

const isProviderAvailable = (providerId: string): boolean => {
  return hasSavedCredentials.value[providerId] || false
}

const testConnection = async () => {
  if (!selectedProvider.value) return

  testingConnection.value = true
  try {
    const providerCreds: Record<string, { apiKey?: string; apiEndpoint?: string }> = {}

    if (credentials.value.apiKey || credentials.value.apiEndpoint) {
      providerCreds[selectedProvider.value] = {
        ...(credentials.value.apiKey && { apiKey: credentials.value.apiKey }),
        ...(credentials.value.apiEndpoint && { apiEndpoint: credentials.value.apiEndpoint })
      }
    }

    // Si hay credenciales guardadas y no se ingresaron nuevas, usar las guardadas
    if (Object.keys(providerCreds).length === 0 && currentProviderHasSavedCredentials.value) {
      // Cargar credenciales completas guardadas
      const saved = await llmService.getSavedCredentials(selectedProvider.value)
      if (saved.apiKey) {
        providerCreds[selectedProvider.value] = {
          apiKey: saved.apiKey,
          ...(saved.apiEndpoint && { apiEndpoint: saved.apiEndpoint })
        }
      }
    }

    const isAvailable = await llmService.testConnection(selectedProvider.value, providerCreds)

    if (isAvailable) {
      showStatus('success', `Conexión exitosa con ${getProviderName(selectedProvider.value)}`)
    } else {
      showStatus('error', 'No se pudo establecer conexión. Verifica tus credenciales.')
    }
  } catch (error: any) {
    console.error('Error testing connection:', error)
    showStatus('error', error.response?.data?.detail || 'Error probando conexión')
  } finally {
    testingConnection.value = false
  }
}

const saveCredentials = async () => {
  if (!selectedProvider.value) return

  saving.value = true
  try {
    const providerCreds: Record<string, { apiKey?: string; apiEndpoint?: string }> = {}

    // Solo incluir credenciales si se ingresaron nuevas
    if (credentials.value.apiKey || credentials.value.apiEndpoint) {
      providerCreds[selectedProvider.value] = {
        ...(credentials.value.apiKey && { apiKey: credentials.value.apiKey }),
        ...(credentials.value.apiEndpoint && { apiEndpoint: credentials.value.apiEndpoint })
      }
    }

    // Guardar credenciales (sin modelo, sin setAsDefault)
    // Usamos un modelo dummy ya que este endpoint lo requiere, pero no se usará
    await llmService.configureLLM({
      provider: selectedProvider.value,
      model: 'dummy', // No se usa, es requerido por el endpoint
      credentials: Object.keys(providerCreds).length > 0 ? providerCreds : undefined,
      setAsDefault: false // No marcar como default
    })

    // Actualizar estado
    hasSavedCredentials.value[selectedProvider.value] = true
    if (credentials.value.apiEndpoint) {
      savedEndpoints.value[selectedProvider.value] = credentials.value.apiEndpoint
    }

    // Limpiar formulario después de guardar
    credentials.value = { apiKey: '', apiEndpoint: '' }

    showStatus('success', 'Credenciales guardadas correctamente')
  } catch (error: any) {
    console.error('Error saving credentials:', error)
    showStatus('error', error.response?.data?.detail || 'Error guardando credenciales')
  } finally {
    saving.value = false
  }
}

const showStatus = (type: 'success' | 'error' | 'info', text: string) => {
  statusMessage.value = { type, text }
  setTimeout(() => {
    statusMessage.value = null
  }, 5000)
}

// Lifecycle
onMounted(async () => {
  await loadProviders()

  // Cargar estado de credenciales para todos los proveedores
  try {
    const saved = await llmService.getSavedConfigs()
    for (const config of saved.configs) {
      if (config.hasCredentials) {
        hasSavedCredentials.value[config.provider] = true
      }
    }
  } catch (error) {
    console.error('Error loading saved configs:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.llm-config {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.llm-config-header h2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.5rem;
  color: #1e293b;
}

.subtitle {
  margin: 0.5rem 0 0;
  color: #64748b;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-section h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-size: 1.1rem;
  color: #334155;
}

.provider-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.provider-card {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.provider-card:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.provider-card.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.provider-card.available {
  border-color: #10b981;
}

.provider-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 0.375rem;
  background: #f1f5f9;
  font-size: 1.5rem;
  color: #64748b;
}

.provider-card.available .provider-icon {
  background: #d1fae5;
  color: #10b981;
}

.provider-info {
  flex: 1;
}

.provider-info h4 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  color: #1e293b;
}

.provider-info p {
  margin: 0 0 0.5rem;
  font-size: 0.875rem;
  color: #64748b;
}

.provider-status {
  display: flex;
  gap: 0.5rem;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 500;
  background: #f1f5f9;
  color: #64748b;
}

.status-badge.available {
  background: #d1fae5;
  color: #10b981;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.credentials-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.credentials-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 0.375rem;
  color: #166534;
  font-size: 0.875rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #334155;
  font-size: 0.875rem;
}

.credential-input {
  width: 100%;
}

.help-text {
  display: flex;
  align-items: flex-start;
  gap: 0.25rem;
  color: #64748b;
  font-size: 0.75rem;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.test-button {
  flex: 1;
}
</style>
