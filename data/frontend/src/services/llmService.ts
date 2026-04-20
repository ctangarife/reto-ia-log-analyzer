/**
 * Servicio para gestión de configuración LLM multi-proveedor
 */
import api from './api'

export interface LLMProvider {
  id: string
  name: string
  description: string
  env_vars: string[]
}

export interface LLMModelInfo {
  id: string
  provider: string
  name: string
  context_size?: number
  description?: string
}

export interface LLMModelList {
  models: LLMModelInfo[]
  default_provider: string
  default_model: string
}

export interface LLMConfigRequest {
  provider: string
  model: string
  credentials?: {
    ollama?: { apiKey?: string; apiEndpoint?: string }
    zai?: { apiKey?: string; apiEndpoint?: string }
    minimax?: { apiKey?: string; apiEndpoint?: string }
  }
}

export interface LLMConfigResponse {
  provider: string
  model: string
  is_available: boolean
  available_models: string[]
}

export interface LLMModelConfig {
  provider: string
  model: string
  role?: string
  priority?: number
  isAvailable?: boolean
}

export interface LLMProvidersResponse {
  providers: LLMProvider[]
  default: string
}

class LLMService {
  /**
   * Obtiene la lista de proveedores LLM disponibles
   */
  async getProviders(): Promise<LLMProvidersResponse> {
    const response = await api.get<LLMProvidersResponse>('/llm/providers')
    return response.data
  }

  /**
   * Obtiene la lista de modelos disponibles
   * @param provider Proveedor específico (opcional)
   */
  async getModels(provider?: string): Promise<LLMModelList> {
    const params = provider ? { provider } : {}
    const response = await api.get<LLMModelList>('/llm/models', { params })
    return response.data
  }

  /**
   * Obtiene modelos disponibles para un proveedor con credenciales específicas
   * Usa el endpoint /llm/config para probar conexión y obtener modelos
   */
  async getModelsWithCredentials(provider: string, credentials: LLMConfigRequest['credentials']): Promise<string[]> {
    const result = await this.configureLLM({
      provider,
      model: 'test', // Modelo dummy para obtener lista
      credentials
    })
    return result.available_models
  }

  /**
   * Obtiene la configuración default del sistema
   */
  async getDefaultConfig(): Promise<LLMConfigResponse> {
    const response = await api.get<LLMConfigResponse>('/llm/config/default')
    return response.data
  }

  /**
   * Obtiene todos los modelos de proveedores con credenciales guardadas
   */
  async getSavedModels(): Promise<LLMModelList> {
    const response = await api.get<LLMModelList>('/llm/models/saved')
    return response.data
  }

  /**
   * Configura el proveedor y modelo LLM
   * @param config Configuración a aplicar
   */
  async configureLLM(config: LLMConfigRequest & { setAsDefault?: boolean }): Promise<LLMConfigResponse> {
    const response = await api.post<LLMConfigResponse>('/llm/config', config)
    return response.data
  }

  /**
   * Verifica disponibilidad de un proveedor (útil para pruebas de conexión)
   */
  async testConnection(provider: string, credentials?: LLMConfigRequest['credentials']): Promise<boolean> {
    try {
      const result = await this.configureLLM({
        provider,
        model: 'test', // Modelo dummy para prueba
        credentials
      })
      return result.is_available
    } catch {
      return false
    }
  }

  /**
   * Obtiene las credenciales guardadas del usuario para un proveedor
   */
  async getSavedCredentials(provider: string): Promise<{
    hasCredentials: boolean
    apiKey?: string
    apiEndpoint?: string
    model?: string
    isDefault?: boolean
  }> {
    const response = await api.get<{
      hasCredentials: boolean
      apiKey?: string
      apiEndpoint?: string
      model?: string
      isDefault?: boolean
    }>(`/llm/credentials/${provider}`)
    return response.data
  }

  /**
   * Obtiene todas las configuraciones guardadas del usuario
   */
  async getSavedConfigs(): Promise<{
    configs: Array<{
      provider: string
      hasCredentials: boolean
      savedModel?: string
      isDefault?: boolean
    }>
  }> {
    const response = await api.get('/llm/config/saved')
    return response.data
  }

  /**
   * Obtiene la configuración completa de selección de modelos
   */
  async getModelSelectionConfig(): Promise<{
    default: LLMModelConfig | null
    fallback: LLMModelConfig[]
    evaluators: LLMModelConfig[]
  }> {
    const response = await api.get('/llm/config/selection')
    return response.data
  }

  /**
   * Configura un modelo con un rol específico
   */
  async configureModelWithRole(config: {
    provider: string
    model: string
    role: 'default' | 'fallback' | 'evaluator'
    priority?: number
  }): Promise<LLMConfigResponse> {
    const response = await api.post('/llm/config/model', config)
    return response.data
  }

  /**
   * Elimina una configuración de modelo específica
   */
  async removeModelConfig(provider: string, role: string): Promise<void> {
    await api.delete(`/llm/config/model/${provider}/${role}`)
  }

  /**
   * Guarda múltiples configuraciones LLM en una sola llamada (batch)
   */
  async saveBatchConfig(config: {
    default?: {
      provider: string
      model: string
      credentials?: LLMConfigRequest['credentials']
    }
    fallback?: Array<{
      provider: string
      model: string
      credentials?: LLMConfigRequest['credentials']
    }>
    evaluators?: Array<{
      provider: string
      model: string
      credentials?: LLMConfigRequest['credentials']
    }>
  }): Promise<{
    default: LLMModelConfig | null
    fallback: LLMModelConfig[]
    evaluators: LLMModelConfig[]
  }> {
    const response = await api.post('/llm/config/batch', config)
    return response.data
  }
}

export default new LLMService()
