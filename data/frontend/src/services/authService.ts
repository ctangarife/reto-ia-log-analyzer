/**
 * Servicio de autenticación
 * SEGURIDAD: El token JWT ahora se maneja vía httpOnly cookies (no en localStorage)
 */
import api from './api'
import axios from 'axios'

export interface LoginCredentials {
  username: string
  password: string
}

export interface UserInfo {
  id: string
  username: string
  email: string
  is_super_admin: boolean
  full_name?: string
  is_active: boolean
}

/**
 * Realiza login.
 * NOTA: El token se maneja vía httpOnly cookie, no se almacena en localStorage.
 */
export async function login(credentials: LoginCredentials): Promise<UserInfo> {
  try {
    const response = await api.post('/auth/login', credentials)
    // Backend ahora retorna directamente UserInfo (no { access_token, user })
    const user = response.data as UserInfo

    // Almacenar user_info para display (no incluye token)
    localStorage.setItem('user_info', JSON.stringify(user))

    return user
  } catch (error: any) {
    if (error.response?.status === 401) {
      throw new Error('Credenciales inválidas')
    }
    throw new Error('Error al iniciar sesión')
  }
}

/**
 * Obtiene información del usuario actual desde el backend
 */
export async function getCurrentUser(): Promise<UserInfo | null> {
  try {
    const response = await api.get<UserInfo>('/auth/me')
    return response.data
  } catch (error) {
    return null
  }
}

/**
 * Cierra sesión llamando al backend para eliminar la cookie
 */
export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } catch (error) {
    // Continuar aunque falle el llamado al backend
    console.warn('Error al llamar logout en backend:', error)
  } finally {
    // Limpiar datos locales
    localStorage.removeItem('user_info')
    window.location.href = '/login'
  }
}

/**
 * Obtiene la información del usuario desde localStorage (solo para display)
 * NOTA: Esto no incluye el token, que está en una httpOnly cookie
 */
export function getStoredUserInfo(): UserInfo | null {
  const stored = localStorage.getItem('user_info')
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      return null
    }
  }
  return null
}

/**
 * Interfaz para registro de usuario
 */
export interface RegisterData {
  email: string
  username: string
  password: string
  full_name: string
}

/**
 * Interfaz de respuesta de registro
 */
export interface RegisterResponse {
  id: string
  email: string
  username: string
  full_name: string
  is_active: boolean
  is_super_admin: boolean
  last_login: string | null
  created_at: string
  updated_at: string
}

/**
 * Registra un nuevo usuario
 * NOTA: La cookie httpOnly se maneja automáticamente por el navegador
 */
export async function registerUser(data: RegisterData): Promise<RegisterResponse> {
  try {
    const response = await api.post<RegisterResponse>('/users', data)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 409) {
      const detail = error.response.data?.detail || ''
      if (detail.includes('email') || detail.includes('Email')) {
        throw new Error('Este email ya está registrado')
      } else if (detail.includes('username') || detail.includes('Username')) {
        throw new Error('Este usuario ya está registrado')
      }
      throw new Error('El usuario o email ya existe')
    } else if (error.response?.status === 403) {
      throw new Error('No tienes permisos para crear usuarios. Contacta a un administrador.')
    } else if (error.response?.status === 400) {
      const detail = error.response.data?.detail || 'Datos inválidos'
      throw new Error(detail)
    }
    throw new Error('Error al crear la cuenta')
  }
}
