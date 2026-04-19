/**
 * Cliente HTTP con manejo de cookies httpOnly y errores
 * SEGURIDAD: Token JWT manejado vía httpOnly cookies (enviadas automáticamente por el navegador)
 */
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  },
  // IMPORTANTE: Habilitar envío de cookies para autenticación
  withCredentials: true
})

// Interceptor para manejar errores de autenticación
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status

      // 401 Unauthorized - Sesión inválida o expirada
      if (status === 401) {
        // Limpiar datos locales (el token cookie será manejado por el navegador)
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
