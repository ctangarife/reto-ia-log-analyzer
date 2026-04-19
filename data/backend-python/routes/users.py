"""
Rutas de gestión de usuarios
Endpoints CRUD para usuarios
"""
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends, Query

from pydantic import BaseModel, Field
from models.rbac_models import (
    UserCreate, UserUpdate, UserResponse
)
from services.user_service import (
    create_user, get_user_by_id, list_users, update_user,
    update_user_password, delete_user, count_users
)
from middleware.auth_middleware import get_current_user, get_current_user_optional, CurrentUser
from config.database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def require_super_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """
    Dependency que verifica que el usuario sea super administrador.
    
    Raises:
        HTTPException: Si el usuario no es super administrador
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de super administrador"
        )
    return current_user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: UserCreate,
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional)
):
    """
    Crea un nuevo usuario.
    
    Comportamiento:
    - Si no hay token: permite registro público (usuarios normales)
    - Si hay token y el usuario es super admin: permite crear usuarios
    - Si hay token pero NO es super admin: retorna 403
    
    Args:
        user_data: Datos del usuario a crear
        current_user: Usuario actual (opcional, solo si hay token)
    
    Returns:
        UserResponse con los datos del usuario creado
    
    Raises:
        HTTPException: Si el usuario ya existe, no tiene permisos o hay un error
    """
    # Si hay usuario autenticado, debe ser super admin
    if current_user is not None and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de super administrador para crear usuarios"
        )
    
    try:
        # Verificar si el usuario o email ya existe
        async with db_manager.postgres_pool.acquire() as conn:
            existing = await conn.fetchrow(
                """
                SELECT id FROM auth.users
                WHERE username = $1 OR email = $2
                """,
                user_data.username, user_data.email
            )
            
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El usuario o email ya existe"
                )
        
        # Crear usuario
        created_by = current_user.user_id if current_user else None
        user_id = await create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
            is_super_admin=False,  # Por defecto no es super admin
            created_by=created_by
        )
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el usuario"
            )
        
        # Obtener usuario creado
        user = await get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Usuario creado pero no se pudo obtener"
            )
        
        if current_user:
            logger.info(f"Usuario creado por {current_user.username}: {user_data.username}")
        else:
            logger.info(f"Usuario registrado públicamente: {user_data.username}")
        
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando usuario: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear usuario: {str(e)}"
        )


@router.get("", response_model=List[UserResponse])
async def list_users_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_super_admin)
):
    """
    Lista usuarios con paginación y filtros.
    
    Solo super administradores pueden listar usuarios.
    
    Args:
        skip: Número de registros a saltar
        limit: Número máximo de registros a retornar
        is_active: Filtrar por estado activo/inactivo
        search: Buscar por username o email
        current_user: Usuario actual (debe ser super admin)
    
    Returns:
        Lista de usuarios
    """
    try:
        users = await list_users(
            skip=skip,
            limit=limit,
            is_active=is_active,
            search=search
        )
        
        return [UserResponse(**user) for user in users]
        
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar usuarios: {str(e)}"
        )


@router.get("/count")
async def count_users_endpoint(
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(require_super_admin)
):
    """
    Cuenta el número total de usuarios.
    
    Solo super administradores pueden contar usuarios.
    
    Args:
        is_active: Filtrar por estado activo/inactivo
        current_user: Usuario actual (debe ser super admin)
    
    Returns:
        Número total de usuarios
    """
    try:
        total = await count_users(is_active=is_active)
        return {"total": total}
        
    except Exception as e:
        logger.error(f"Error contando usuarios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al contar usuarios: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(
    user_id: UUID,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Obtiene un usuario por su ID.
    
    Los usuarios pueden ver su propia información.
    Los super administradores pueden ver cualquier usuario.
    
    Args:
        user_id: ID del usuario
        current_user: Usuario actual
    
    Returns:
        UserResponse con los datos del usuario
    
    Raises:
        HTTPException: Si el usuario no existe o no tiene permisos
    """
    # Verificar permisos: solo puede ver su propio perfil o ser super admin
    if user_id != current_user.user_id and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver este usuario"
        )
    
    user = await get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return UserResponse(**user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Actualiza un usuario.
    
    Los usuarios pueden actualizar su propia información básica.
    Los super administradores pueden actualizar cualquier usuario.
    
    Args:
        user_id: ID del usuario a actualizar
        user_data: Datos a actualizar
        current_user: Usuario actual
    
    Returns:
        UserResponse con los datos actualizados del usuario
    
    Raises:
        HTTPException: Si el usuario no existe o no tiene permisos
    """
    # Verificar permisos
    is_own_profile = user_id == current_user.user_id
    is_super_admin = current_user.is_super_admin
    
    if not is_own_profile and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para actualizar este usuario"
        )
    
    # Si es su propio perfil, no puede cambiar is_active ni is_super_admin
    if is_own_profile and not is_super_admin:
        if user_data.is_active is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes cambiar tu propio estado activo"
            )
    
    # Verificar si el usuario existe
    existing_user = await get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar si el nuevo username o email ya existe (si se está cambiando)
    if user_data.username or user_data.email:
        async with db_manager.postgres_pool.acquire() as conn:
            if user_data.username and user_data.username != existing_user["username"]:
                existing = await conn.fetchrow(
                    "SELECT id FROM auth.users WHERE username = $1 AND id != $2",
                    user_data.username, user_id
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="El username ya está en uso"
                    )
            
            if user_data.email and user_data.email != existing_user["email"]:
                existing = await conn.fetchrow(
                    "SELECT id FROM auth.users WHERE email = $1 AND id != $2",
                    user_data.email, user_id
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="El email ya está en uso"
                    )
    
    # Actualizar usuario
    success = await update_user(
        user_id=user_id,
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        is_active=user_data.is_active if is_super_admin else None,
        is_super_admin=None  # Solo se puede cambiar mediante endpoint específico
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el usuario"
        )
    
    # Obtener usuario actualizado
    updated_user = await get_user_by_id(user_id)
    
    logger.info(f"Usuario actualizado por {current_user.username}: {user_id}")
    
    return UserResponse(**updated_user)


class PasswordUpdate(BaseModel):
    new_password: str = Field(..., min_length=8)


@router.patch("/{user_id}/password")
async def update_user_password_endpoint(
    user_id: UUID,
    password_data: PasswordUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """
    Actualiza la contraseña de un usuario.
    
    Los usuarios pueden cambiar su propia contraseña.
    Los super administradores pueden cambiar cualquier contraseña.
    
    Args:
        user_id: ID del usuario
        new_password: Nueva contraseña
        current_user: Usuario actual
    
    Returns:
        Mensaje de éxito
    
    Raises:
        HTTPException: Si no tiene permisos o hay un error
    """
    # Verificar permisos
    if user_id != current_user.user_id and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cambiar esta contraseña"
        )
    
    # Verificar si el usuario existe
    existing_user = await get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Actualizar contraseña
    success = await update_user_password(user_id, password_data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar la contraseña"
        )
    
    logger.info(f"Contraseña actualizada por {current_user.username} para usuario: {user_id}")
    
    return {"message": "Contraseña actualizada exitosamente"}


@router.patch("/{user_id}/toggle-active")
async def toggle_user_active_endpoint(
    user_id: UUID,
    current_user: CurrentUser = Depends(require_super_admin)
):
    """
    Activa o desactiva un usuario (toggle).
    
    Solo super administradores pueden activar/desactivar usuarios.
    
    Args:
        user_id: ID del usuario
        current_user: Usuario actual (debe ser super admin)
    
    Returns:
        UserResponse con los datos actualizados del usuario
    
    Raises:
        HTTPException: Si el usuario no existe o no tiene permisos
    """
    # Verificar si el usuario existe
    existing_user = await get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir desactivarse a sí mismo
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta"
        )
    
    # Toggle estado
    new_status = not existing_user["is_active"]
    
    success = await update_user(
        user_id=user_id,
        is_active=new_status
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el estado del usuario"
        )
    
    # Obtener usuario actualizado
    updated_user = await get_user_by_id(user_id)
    
    logger.info(f"Usuario {'activado' if new_status else 'desactivado'} por {current_user.username}: {user_id}")
    
    return UserResponse(**updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: UUID,
    current_user: CurrentUser = Depends(require_super_admin)
):
    """
    Elimina un usuario (soft delete).
    
    Solo super administradores pueden eliminar usuarios.
    
    Args:
        user_id: ID del usuario a eliminar
        current_user: Usuario actual (debe ser super admin)
    
    Returns:
        Sin contenido (204)
    
    Raises:
        HTTPException: Si el usuario no existe o no tiene permisos
    """
    # Verificar si el usuario existe
    existing_user = await get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir eliminarse a sí mismo
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta"
        )
    
    # Eliminar usuario (soft delete)
    success = await delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el usuario"
        )
    
    logger.info(f"Usuario eliminado por {current_user.username}: {user_id}")
    
    return None
