"""
Servicio de autenticación JWT
Maneja login, creación de tokens y verificación de credenciales
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from config.database import db_manager

logger = logging.getLogger(__name__)

# Configuración de JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Contexto para hash de contraseñas
# Configurado para usar bcrypt con truncamiento silencioso
# (aunque truncamos manualmente antes de pasar a passlib)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False  # No lanzar error si passlib intenta truncar
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash almacenado.
    
    Nota: Bcrypt tiene una limitación de 72 bytes. Truncamos explícitamente
    de la misma manera que en get_password_hash para asegurar consistencia.
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña almacenado
    
    Returns:
        True si coinciden, False en caso contrario
    """
    # Truncar de la misma manera que en get_password_hash para consistencia
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña usando bcrypt.
    
    IMPORTANTE: Bcrypt tiene una limitación estricta de 72 bytes.
    Las versiones nuevas de bcrypt rechazan contraseñas > 72 bytes.
    Truncamos explícitamente ANTES de pasar a passlib para evitar errores.
    
    Args:
        password: Contraseña en texto plano
    
    Returns:
        Hash de la contraseña
    """
    # Convertir a bytes UTF-8 y truncar a máximo 72 bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        # Decodificar ignorando errores si cortamos en medio de un carácter UTF-8
        password = password_bytes.decode('utf-8', errors='ignore')
    
    # Passlib manejará el hash, pero ya tenemos la contraseña truncada
    return pwd_context.hash(password)


def create_access_token(user_id: UUID, username: str, is_super_admin: bool) -> str:
    """
    Crea un token JWT con los datos del usuario.
    
    Args:
        user_id: ID del usuario
        username: Nombre de usuario
        is_super_admin: Si el usuario es super administrador
    
    Returns:
        Token JWT codificado
    """
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "sub": str(user_id),  # Subject (usuario)
        "username": username,
        "is_super_admin": is_super_admin,
        "exp": expire,  # Expiración
        "iat": datetime.utcnow()  # Issued at
    }
    
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    """
    Decodifica y valida un token JWT.
    
    Args:
        token: Token JWT codificado
    
    Returns:
        Diccionario con los datos del token si es válido, None en caso contrario
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Error decodificando token: {e}")
        return None


async def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """
    Autentica un usuario con username y password.
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
    
    Returns:
        Diccionario con datos del usuario si las credenciales son válidas, None en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Buscar usuario por username
            user = await conn.fetchrow(
                """
                SELECT id, username, email, password_hash, is_active, is_super_admin
                FROM auth.users
                WHERE username = $1
                """,
                username
            )
            
            if not user:
                logger.warning(f"Usuario no encontrado: {username}")
                return None
            
            # Verificar si el usuario está activo
            if not user["is_active"]:
                logger.warning(f"Usuario inactivo: {username}")
                return None
            
            # Verificar contraseña
            if not verify_password(password, user["password_hash"]):
                logger.warning(f"Contraseña incorrecta para usuario: {username}")
                return None
            
            # Actualizar último login
            await conn.execute(
                """
                UPDATE auth.users
                SET last_login = $1
                WHERE id = $2
                """,
                datetime.utcnow(),
                user["id"]
            )
            
            logger.info(f"Usuario autenticado exitosamente: {username}")
            
            return {
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_super_admin": user["is_super_admin"]
            }
            
    except Exception as e:
        logger.error(f"Error autenticando usuario: {e}")
        return None


async def get_user_by_id(user_id: UUID) -> Optional[Dict]:
    """
    Obtiene información de un usuario por su ID.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Diccionario con datos del usuario si existe, None en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, username, email, is_active, is_super_admin, full_name
                FROM auth.users
                WHERE id = $1
                """,
                user_id
            )
            
            if not user:
                return None
            
            return {
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "is_super_admin": user["is_super_admin"],
                "full_name": user["full_name"],
                "is_active": user["is_active"]
            }
            
    except Exception as e:
        logger.error(f"Error obteniendo usuario por ID: {e}")
        return None
