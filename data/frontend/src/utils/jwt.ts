/**
 * Utilidades para manejo de JWT
 */

export interface JWTPayload {
  user_id: string
  username: string
  is_super_admin?: boolean
  exp?: number
  [key: string]: any
}

/**
 * Decodifica un token JWT sin verificar la firma
 * (La verificación de firma la hace el backend)
 */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }

    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded) as JWTPayload
  } catch (error) {
    console.error('Error decodificando JWT:', error)
    return null
  }
}

/**
 * Extrae el user_id del token JWT
 */
export function getUserIdFromToken(token: string): string | null {
  const payload = decodeJWT(token)
  return payload?.user_id || null
}

/**
 * Verifica si el usuario es super administrador
 */
export function isSuperAdmin(token: string): boolean {
  const payload = decodeJWT(token)
  return payload?.is_super_admin === true
}

/**
 * Verifica si el token ha expirado
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token)
  if (!payload?.exp) {
    return false // Si no tiene exp, asumimos que no expira
  }

  const expirationTime = payload.exp * 1000 // Convertir a milisegundos
  return Date.now() >= expirationTime
}

/**
 * Obtiene información completa del usuario desde el token
 */
export function getUserFromToken(token: string): JWTPayload | null {
  return decodeJWT(token)
}
