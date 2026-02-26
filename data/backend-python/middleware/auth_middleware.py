"""
Middleware de autenticación para FastAPI
Extrae y valida tokens JWT de las peticiones
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import decode_token, get_user_by_id

logger = logging.getLogger(__name__)

# Esquema de seguridad HTTP Bearer
security = HTTPBearer()


class CurrentUser:
    """Clase para almacenar información del usuario actual"""
    def __init__(self, user_id: UUID, username: str, is_super_admin: bool):
        self.user_id = user_id
        self.username = username
        self.is_super_admin = is_super_admin


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Dependency de FastAPI que extrae y valida el token JWT del header Authorization.
    
    Args:
        credentials: Credenciales HTTP Bearer del header Authorization
    
    Returns:
        CurrentUser con información del usuario autenticado
    
    Raises:
        HTTPException: Si el token es inválido, expirado o no está presente
    """
    token = credentials.credentials
    
    # Decodificar token
    payload = decode_token(token)
    
    if payload is None:
        logger.warning("Token inválido o expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extraer user_id del payload
    user_id_str = payload.get("sub")
    if not user_id_str:
        logger.warning("Token sin subject (user_id)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta user_id",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        logger.warning(f"user_id inválido en token: {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: user_id no válido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario existe y está activo
    user = await get_user_by_id(user_id)
    if not user:
        logger.warning(f"Usuario no encontrado: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", False):
        logger.warning(f"Usuario inactivo: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extraer información del token (puede diferir de la BD si se actualizó)
    username = payload.get("username", user["username"])
    is_super_admin = payload.get("is_super_admin", user["is_super_admin"])
    
    return CurrentUser(
        user_id=user_id,
        username=username,
        is_super_admin=bool(is_super_admin)
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[CurrentUser]:
    """
    Dependency opcional que permite endpoints públicos o protegidos.
    Retorna None si no hay token, en lugar de lanzar excepción.
    
    Args:
        credentials: Credenciales HTTP Bearer (opcional)
    
    Returns:
        CurrentUser si hay token válido, None en caso contrario
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
