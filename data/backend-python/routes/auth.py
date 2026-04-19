"""
Rutas de autenticación
Endpoints para login y obtención de información del usuario actual
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.responses import JSONResponse
from models.rbac_models import LoginRequest, TokenResponse, UserResponse
from services.auth_service import authenticate_user, create_access_token
from middleware.auth_middleware import get_current_user, CurrentUser
from config.database import db_manager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login")
async def login(login_data: LoginRequest):
    """
    Endpoint de autenticación de usuarios.

    Valida credenciales (username/password) y retorna un token JWT via httpOnly cookie.

    Args:
        login_data: Datos de login (username y password)

    Returns:
        UserResponse con información del usuario (token via cookie)

    Raises:
        HTTPException: Si las credenciales son inválidas
    """
    from datetime import timezone
    from fastapi.responses import JSONResponse

    # Autenticar usuario
    user_data = await authenticate_user(login_data.username, login_data.password)

    if not user_data:
        logger.warning(f"Intento de login fallido para usuario: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    # Crear token JWT
    access_token = create_access_token(
        user_id=user_data["user_id"],
        username=user_data["username"],
        is_super_admin=user_data["is_super_admin"]
    )

    # Obtener expiración en segundos
    from services.auth_service import JWT_EXPIRATION_HOURS
    expires_in_seconds = JWT_EXPIRATION_HOURS * 3600

    # Crear fecha UTC con timezone aware
    now_utc = datetime.now(timezone.utc)
    expire_date = now_utc + timedelta(seconds=expires_in_seconds)

    # Crear respuesta del usuario
    user_response = UserResponse(
        id=user_data["user_id"],
        username=user_data["username"],
        email=user_data["email"],
        is_active=True,
        is_super_admin=user_data["is_super_admin"],
        last_login=now_utc,
        created_at=now_utc,
        updated_at=now_utc
    )

    # Crear respuesta JSON y setear cookie
    response = JSONResponse(content=user_response.model_dump(mode='json'))

    # Setear httpOnly cookie con el token
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=False,  # Cambiar a True en producción con HTTPS
        samesite="lax",
        max_age=expires_in_seconds,
        expires=expire_date,
        path="/"
    )

    logger.info(f"Login exitoso para usuario: {user_data['username']}")

    return response


@router.post("/logout")
async def logout():
    """
    Endpoint para cerrar sesión.

    Elimina la cookie del token.

    Returns:
        Mensaje de confirmación
    """
    from fastapi.responses import JSONResponse

    response = JSONResponse(content={"message": "Sesión cerrada exitosamente"})
    response.delete_cookie(
        key="auth_token",
        path="/"
    )

    logger.info("Logout ejecutado")

    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser = Depends(get_current_user)):
    """
    Obtiene información del usuario actual desde el token JWT.
    
    Args:
        current_user: Usuario actual extraído del token (dependency)
    
    Returns:
        UserResponse con información del usuario
    
    Raises:
        HTTPException: Si el token es inválido o expirado (manejado por get_current_user)
    """
    # Obtener información completa del usuario desde la BD
    from services.auth_service import get_user_by_id
    
    user_data = await get_user_by_id(current_user.user_id)
    
    if not user_data:
        logger.error(f"Usuario no encontrado en BD: {current_user.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Obtener fecha de creación y actualización desde la BD
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            user_db = await conn.fetchrow(
                """
                SELECT created_at, updated_at
                FROM auth.users
                WHERE id = $1
                """,
                current_user.user_id
            )
            
            created_at = user_db["created_at"] if user_db else datetime.utcnow()
            updated_at = user_db["updated_at"] if user_db else datetime.utcnow()
    except Exception as e:
        logger.warning(f"Error obteniendo fechas del usuario: {e}")
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()
    
    return UserResponse(
        id=user_data["user_id"],
        username=user_data["username"],
        email=user_data["email"],
        full_name=user_data.get("full_name"),
        is_active=user_data.get("is_active", True),
        is_super_admin=user_data["is_super_admin"],
        last_login=None,  # Se puede obtener de la BD si es necesario
        created_at=created_at,
        updated_at=updated_at
    )
