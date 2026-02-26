/**
 * Servicio de autenticación
 */
import api from './api'
import axios from 'axios'
import { decodeJWT, getUserFromToken } from '../utils/jwt'

export interface LoginCredentials {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: {
    user_id: string
    username: string
    is_super_admin: boolean
  }
}

export interface UserInfo {
  user_id: string
  username: string
  is_super_admin: boolean
}

/**
 * Realiza login y almacena el token
 */
export async function login(credentials: LoginCredentials): Promise<UserInfo> {
  try {
    const response = await api.post<LoginResponse>('/auth/login', credentials)
    const { access_token, user } = response.data

    // Almacenar token
    localStorage.setItem('auth_token', access_token)
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
 * Obtiene información del usuario actual
 */
export async function getCurrentUser(): Promise<UserInfo | null> {
  try {
    const response = await api.get<UserInfo>('/auth/me')
    return response.data
  } catch (error) {
    // Si falla, intentar obtener del token almacenado
    const token = localStorage.getItem('auth_token')
    if (token) {
      const user = getUserFromToken(token)
      if (user) {
        return {
          user_id: user.user_id,
          username: user.username || '',
          is_super_admin: user.is_super_admin || false
        }
      }
    }
    return null
  }
}

/**
 * Cierra sesión
 */
export function logout(): void {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user_info')
  window.location.href = '/login'
}

/**
 * Verifica si hay un token válido almacenado
 */
export function isAuthenticated(): boolean {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    return false
  }

  // Verificar expiración (si el token tiene exp)
  const user = getUserFromToken(token)
  if (user?.exp) {
    const expirationTime = user.exp * 1000
    if (Date.now() >= expirationTime) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')
      return false
    }
  }

  return true
}

/**
 * Obtiene el token almacenado
 */
export function getToken(): string | null {
  return localStorage.getItem('auth_token')
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
 * Nota: Según la API, esto requiere permisos de super administrador
 * Si el backend permite registro público, funcionará. Si no, retornará 403.
 */
export async function registerUser(data: RegisterData): Promise<RegisterResponse> {
  try {
    // Crear instancia de axios sin interceptores para permitir registro público
    // Esto permite registro sin token si el backend lo soporta
    const token = getToken()
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    
    // Solo agregar token si existe (para super admins que crean usuarios)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Usar axios directamente sin interceptores para permitir registro público
    // Usar solo '/users' porque baseURL ya incluye '/api'
    const response = await axios.post<RegisterResponse>('/users', data, { 
      headers,
      baseURL: '/api'
    })
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
