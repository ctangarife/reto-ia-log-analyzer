/**
 * Cliente HTTP con interceptores para JWT y manejo de errores
 */
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor para agregar token JWT a todas las peticiones
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor para manejar errores de autenticación
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status

      // 401 Unauthorized - Token inválido o expirado
      if (status === 401) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_info')
        // Redirigir al login si no estamos ya ahí
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }

      // 403 Forbidden - Sin permisos
      // El componente manejará este error específicamente
    }

    return Promise.reject(error)
  }
)

export default api
