"""
Middleware de autenticación para FastAPI
Soporta httpOnly cookies (prioridad) y Authorization header (fallback)
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import decode_token, get_user_by_id

logger = logging.getLogger(__name__)

# Esquema de seguridad HTTP Bearer (fallback para compatibilidad)
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Clase para almacenar información del usuario actual"""
    def __init__(self, user_id: UUID, username: str, is_super_admin: bool):
        self.user_id = user_id
        self.username = username
        self.is_super_admin = is_super_admin


async def _get_token_from_request(request: Request) -> Optional[str]:
    """Extrae token de cookie httpOnly o Authorization header (fallback)"""
    # 1. Prioridad: cookie httpOnly
    token = request.cookies.get("auth_token")
    if token:
        return token

    # 2. Fallback: header Authorization (compatibilidad)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]

    return None


async def _validate_token(token: str) -> CurrentUser:
    """Valida token JWT y retorna información del usuario"""
    payload = decode_token(token)
    if payload is None:
        logger.warning("Token inválido o expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta user_id",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: user_id no válido",
        )

    user = await get_user_by_id(user_id)
    if not user or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return CurrentUser(
        user_id=user_id,
        username=payload.get("username", user["username"]),
        is_super_admin=bool(payload.get("is_super_admin", user["is_super_admin"]))
    )


# Dependency functions para FastAPI
async def get_current_user(request: Request) -> CurrentUser:
    """
    Dependency que extrae y valida token JWT de cookie o header.

    Uso: Depends(get_current_user)
    """
    token = await _get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
        )
    return await _validate_token(token)


async def get_current_user_optional(request: Request) -> Optional[CurrentUser]:
    """
    Dependency opcional que retorna None si no hay token.

    Uso: Depends(get_current_user_optional)
    """
    token = await _get_token_from_request(request)
    if not token:
        return None
    try:
        return await _validate_token(token)
    except HTTPException:
        return None
