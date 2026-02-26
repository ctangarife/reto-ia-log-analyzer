"""
Rutas de autenticación
Endpoints para login y obtención de información del usuario actual
"""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from models.rbac_models import LoginRequest, TokenResponse, UserResponse
from services.auth_service import authenticate_user, create_access_token
from middleware.auth_middleware import get_current_user, CurrentUser
from config.database import db_manager
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """
    Endpoint de autenticación de usuarios.
    
    Valida credenciales (username/password) y retorna un token JWT.
    
    Args:
        login_data: Datos de login (username y password)
    
    Returns:
        TokenResponse con el token JWT y información del usuario
    
    Raises:
        HTTPException: Si las credenciales son inválidas
    """
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
    expires_in = JWT_EXPIRATION_HOURS * 3600
    
    # Crear respuesta del usuario
    user_response = UserResponse(
        id=user_data["user_id"],
        username=user_data["username"],
        email=user_data["email"],
        is_active=True,
        is_super_admin=user_data["is_super_admin"],
        last_login=datetime.utcnow(),
        created_at=datetime.utcnow(),  # Estos campos deberían venir de la BD
        updated_at=datetime.utcnow()
    )
    
    logger.info(f"Login exitoso para usuario: {user_data['username']}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_response
    )


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
