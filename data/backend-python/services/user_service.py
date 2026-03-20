"""
Servicio de gestión de usuarios
Maneja operaciones CRUD de usuarios
"""
import logging
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

from passlib.context import CryptContext
from config.database import db_manager

logger = logging.getLogger(__name__)

# Contexto para hash de contraseñas
# Configurado para usar bcrypt con truncamiento silencioso
# (aunque truncamos manualmente antes de pasar a passlib)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False  # No lanzar error si passlib intenta truncar
)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña usando bcrypt.
    
    IMPORTANTE: Bcrypt tiene una limitación estricta de 72 bytes.
    Las versiones nuevas de bcrypt rechazan contraseñas > 72 bytes.
    Truncamos explícitamente ANTES de pasar a passlib para evitar errores.
    """
    # Convertir a bytes UTF-8 y truncar a máximo 72 bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        # Decodificar ignorando errores si cortamos en medio de un carácter UTF-8
        password = password_bytes.decode('utf-8', errors='ignore')
    
    # Passlib manejará el hash, pero ya tenemos la contraseña truncada
    return pwd_context.hash(password)


async def create_user(
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None,
    is_super_admin: bool = False,
    created_by: Optional[UUID] = None
) -> Optional[UUID]:
    """
    Crea un nuevo usuario.
    
    Args:
        email: Email del usuario
        username: Nombre de usuario
        password: Contraseña en texto plano
        full_name: Nombre completo (opcional)
        is_super_admin: Si es super administrador
        created_by: ID del usuario que crea este usuario
    
    Returns:
        ID del usuario creado o None si hay error
    """
    try:
        password_hash = get_password_hash(password)
        
        async with db_manager.postgres_pool.acquire() as conn:
            user_id = await conn.fetchval(
                """
                INSERT INTO auth.users (
                    email, username, password_hash, full_name,
                    is_active, is_super_admin
                )
                VALUES ($1, $2, $3, $4, true, $5)
                RETURNING id
                """,
                email, username, password_hash, full_name, is_super_admin
            )
            
            logger.info(f"Usuario creado: {username} ({user_id})")
            return user_id
            
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        return None


async def get_user_by_id(user_id: UUID) -> Optional[Dict]:
    """
    Obtiene un usuario por su ID.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Diccionario con datos del usuario o None si no existe
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, username, full_name, is_active, 
                       is_super_admin, last_login, created_at, updated_at
                FROM auth.users
                WHERE id = $1
                """,
                user_id
            )
            
            if not user:
                return None
            
            return {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "is_active": user["is_active"],
                "is_super_admin": user["is_super_admin"],
                "last_login": user["last_login"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"]
            }
            
    except Exception as e:
        logger.error(f"Error obteniendo usuario por ID: {e}")
        return None


async def get_user_by_username(username: str) -> Optional[Dict]:
    """
    Obtiene un usuario por su username.
    
    Args:
        username: Nombre de usuario
    
    Returns:
        Diccionario con datos del usuario o None si no existe
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT id, email, username, full_name, is_active, 
                       is_super_admin, last_login, created_at, updated_at
                FROM auth.users
                WHERE username = $1
                """,
                username
            )
            
            if not user:
                return None
            
            return {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "is_active": user["is_active"],
                "is_super_admin": user["is_super_admin"],
                "last_login": user["last_login"],
                "created_at": user["created_at"],
                "updated_at": user["updated_at"]
            }
            
    except Exception as e:
        logger.error(f"Error obteniendo usuario por username: {e}")
        return None


async def list_users(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Dict]:
    """
    Lista usuarios con paginación y filtros.
    
    Args:
        skip: Número de registros a saltar
        limit: Número máximo de registros a retornar
        is_active: Filtrar por estado activo/inactivo
        search: Buscar por username o email
    
    Returns:
        Lista de usuarios
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            query = """
                SELECT id, email, username, full_name, is_active, 
                       is_super_admin, last_login, created_at, updated_at
                FROM auth.users
                WHERE 1=1
            """
            params = []
            param_count = 0
            
            if is_active is not None:
                param_count += 1
                query += f" AND is_active = ${param_count}"
                params.append(is_active)
            
            if search:
                param_count += 1
                query += f" AND (username ILIKE ${param_count} OR email ILIKE ${param_count})"
                params.append(f"%{search}%")

            # Agregar LIMIT y OFFSET con parámetros correctamente numerados
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)

            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(skip)
            
            users = await conn.fetch(query, *params)
            
            return [
                {
                    "id": user["id"],
                    "email": user["email"],
                    "username": user["username"],
                    "full_name": user["full_name"],
                    "is_active": user["is_active"],
                    "is_super_admin": user["is_super_admin"],
                    "last_login": user["last_login"],
                    "created_at": user["created_at"],
                    "updated_at": user["updated_at"]
                }
                for user in users
            ]
            
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        return []


async def update_user(
    user_id: UUID,
    email: Optional[str] = None,
    username: Optional[str] = None,
    full_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_super_admin: Optional[bool] = None
) -> bool:
    """
    Actualiza un usuario.
    
    Args:
        user_id: ID del usuario a actualizar
        email: Nuevo email (opcional)
        username: Nuevo username (opcional)
        full_name: Nuevo nombre completo (opcional)
        is_active: Nuevo estado activo (opcional)
        is_super_admin: Nuevo estado super admin (opcional)
    
    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Construir query dinámicamente
            updates = []
            params = []
            param_count = 0
            
            if email is not None:
                param_count += 1
                updates.append(f"email = ${param_count}")
                params.append(email)
            
            if username is not None:
                param_count += 1
                updates.append(f"username = ${param_count}")
                params.append(username)
            
            if full_name is not None:
                param_count += 1
                updates.append(f"full_name = ${param_count}")
                params.append(full_name)
            
            if is_active is not None:
                param_count += 1
                updates.append(f"is_active = ${param_count}")
                params.append(is_active)
            
            if is_super_admin is not None:
                param_count += 1
                updates.append(f"is_super_admin = ${param_count}")
                params.append(is_super_admin)
            
            if not updates:
                return False
            
            # Agregar updated_at
            param_count += 1
            updates.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            
            # Agregar user_id al final
            param_count += 1
            params.append(user_id)
            
            query = f"""
                UPDATE auth.users
                SET {', '.join(updates)}
                WHERE id = ${param_count}
            """
            
            result = await conn.execute(query, *params)
            
            logger.info(f"Usuario actualizado: {user_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error actualizando usuario: {e}")
        return False


async def update_user_password(user_id: UUID, new_password: str) -> bool:
    """
    Actualiza la contraseña de un usuario.
    
    Args:
        user_id: ID del usuario
        new_password: Nueva contraseña en texto plano
    
    Returns:
        True si se actualizó correctamente, False en caso contrario
    """
    try:
        password_hash = get_password_hash(new_password)
        
        async with db_manager.postgres_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE auth.users
                SET password_hash = $1, updated_at = $2
                WHERE id = $3
                """,
                password_hash, datetime.utcnow(), user_id
            )
            
            logger.info(f"Contraseña actualizada para usuario: {user_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error actualizando contraseña: {e}")
        return False


async def delete_user(user_id: UUID) -> bool:
    """
    Elimina un usuario (soft delete marcándolo como inactivo).
    
    Args:
        user_id: ID del usuario a eliminar
    
    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Soft delete: marcar como inactivo
            await conn.execute(
                """
                UPDATE auth.users
                SET is_active = false, updated_at = $1
                WHERE id = $2
                """,
                datetime.utcnow(), user_id
            )
            
            logger.info(f"Usuario eliminado (soft delete): {user_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}")
        return False


async def count_users(is_active: Optional[bool] = None) -> int:
    """
    Cuenta el número total de usuarios.
    
    Args:
        is_active: Filtrar por estado activo/inactivo
    
    Returns:
        Número total de usuarios
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            if is_active is not None:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM auth.users WHERE is_active = $1",
                    is_active
                )
            else:
                count = await conn.fetchval("SELECT COUNT(*) FROM auth.users")
            
            return count or 0
            
    except Exception as e:
        logger.error(f"Error contando usuarios: {e}")
        return 0
