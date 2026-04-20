"""
Servicio de gestión de workspaces.
CRUD de workspaces y listado según permisos del usuario.
"""
import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import db_manager
from models.orm.entities import Workspace, UserWorkspaceRole, Role
from services.permission_service import (
    get_user_workspaces,
    validate_workspace_access,
    check_workspace_permission,
    is_super_admin,
)

logger = logging.getLogger(__name__)

# Constantes para nombres de roles
ROLE_WORKSPACE_ADMIN = "workspace_admin"
ROLE_PROJECT_ADMIN = "project_admin"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"
ROLE_SUPER_ADMIN = "super_admin"


def _slugify(name: str) -> str:
    """
    Genera un slug URL-friendly a partir del nombre.
    Minúsculas, espacios a guiones, solo alfanuméricos y guiones.
    """
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "workspace"


async def create_workspace(
    name: str,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    created_by: Optional[UUID] = None,
) -> Optional[UUID]:
    """
    Crea un nuevo workspace usando el ORM.

    Args:
        name: Nombre del workspace
        description: Descripción opcional
        slug: Slug opcional; si no se proporciona se genera desde name
        created_by: ID del usuario creador

    Returns:
        UUID del workspace creado o None si hay error
    """
    try:
        async with await db_manager.get_async_session() as session:
            # Generar slug único
            base_slug = (slug.strip() if slug else _slugify(name)) or _slugify(name)

            # Verificar si el slug ya existe
            existing = await session.execute(
                select(Workspace).filter(Workspace.slug == base_slug)
            )
            if existing.scalar_one_or_none():
                # Slug existe, agregar sufijo numérico
                n = 1
                while True:
                    candidate = f"{base_slug}-{n}"
                    existing = await session.execute(
                        select(Workspace).filter(Workspace.slug == candidate)
                    )
                    if not existing.scalar_one_or_none():
                        unique_slug = candidate
                        break
                    n += 1
            else:
                unique_slug = base_slug

            # Crear el workspace
            workspace = Workspace(
                name=name.strip(),
                slug=unique_slug,
                description=description,
                is_active=True,
                created_by=created_by
            )
            session.add(workspace)
            await session.flush()  # Para obtener el ID

            # Si hay un creador, asignarlo automáticamente como administrador del workspace
            if created_by:
                # Obtener el rol workspace_admin
                role_result = await session.execute(
                    select(Role).filter(Role.name == ROLE_WORKSPACE_ADMIN)
                )
                role = role_result.scalar_one_or_none()

                if role:
                    # Crear relación usuario-workspace-rol
                    user_workspace_role = UserWorkspaceRole(
                        user_id=created_by,
                        workspace_id=workspace.id,
                        role_id=role.id,
                        assigned_by=created_by
                    )
                    session.add(user_workspace_role)
                    logger.info(f"Usuario {created_by} asignado como administrador del workspace {workspace.id}")

            await session.commit()
            logger.info(f"Workspace creado: {workspace.id} ({name})")
            return workspace.id

    except Exception as e:
        logger.error(f"Error creando workspace: {e}", exc_info=True)
        return None


async def get_workspace_by_id(workspace_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un workspace por ID usando el ORM.

    Args:
        workspace_id: ID del workspace

    Returns:
        Diccionario con los datos del workspace o None si no existe
    """
    try:
        async with await db_manager.get_async_session() as session:
            result = await session.execute(
                select(Workspace).filter(Workspace.id == workspace_id)
            )
            workspace = result.scalar_one_or_none()

            if workspace:
                return {
                    'id': str(workspace.id),
                    'name': workspace.name,
                    'slug': workspace.slug,
                    'description': workspace.description,
                    'is_active': workspace.is_active,
                    'created_by': str(workspace.created_by) if workspace.created_by else None,
                    'created_at': workspace.created_at.isoformat() if workspace.created_at else None,
                    'updated_at': workspace.updated_at.isoformat() if workspace.updated_at else None,
                }
            return None
    except Exception as e:
        logger.error(f"Error obteniendo workspace {workspace_id}: {e}")
        return None


async def list_workspaces_for_user(user_id: UUID) -> List[Dict[str, Any]]:
    """
    Lista los workspaces a los que el usuario tiene acceso, con datos completos.

    Super admin ve todos los workspaces activos. Resto ve solo donde tiene rol.

    Args:
        user_id: ID del usuario

    Returns:
        Lista de workspaces con id, name, slug, description, is_active, role (si aplica), etc.
    """
    try:
        # Obtener lista accesible (workspace_id, workspace_name, role_name)
        accessible = await get_user_workspaces(user_id)
        if not accessible:
            return []

        # asyncpg ya devuelve UUID, convertir a string para evitar errores
        workspace_ids = [UUID(str(a["workspace_id"])) for a in accessible]
        role_by_id = {UUID(str(a["workspace_id"])): a["role_name"] for a in accessible}

        async with await db_manager.get_async_session() as session:
            # Usar IN para filtrar por workspace_ids
            result = await session.execute(
                select(Workspace).filter(
                    Workspace.id.in_(workspace_ids),
                    Workspace.is_active == True
                ).order_by(Workspace.name)
            )
            workspaces = result.scalars().all()

            result_list = []
            for workspace in workspaces:
                result_list.append({
                    'id': str(workspace.id),
                    'name': workspace.name,
                    'slug': workspace.slug,
                    'description': workspace.description,
                    'is_active': workspace.is_active,
                    'created_by': str(workspace.created_by) if workspace.created_by else None,
                    'created_at': workspace.created_at.isoformat() if workspace.created_at else None,
                    'updated_at': workspace.updated_at.isoformat() if workspace.updated_at else None,
                    'role': role_by_id.get(workspace.id, "")
                })
            return result_list
    except Exception as e:
        logger.error(f"Error listando workspaces para usuario {user_id}: {e}", exc_info=True)
        return []


async def update_workspace(
    workspace_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    slug: Optional[str] = None,
) -> bool:
    """
    Actualiza un workspace usando el ORM.

    Args:
        workspace_id: ID del workspace
        name: Nuevo nombre (opcional)
        description: Nueva descripción (opcional)
        is_active: Nuevo estado activo (opcional)
        slug: Nuevo slug (opcional); se valida unicidad

    Returns:
        True si se actualizó, False si no existe o error
    """
    try:
        async with await db_manager.get_async_session() as session:
            # Obtener el workspace actual
            result = await session.execute(
                select(Workspace).filter(Workspace.id == workspace_id)
            )
            workspace = result.scalar_one_or_none()

            if not workspace:
                return False

            # Actualizar campos si se proporcionan
            if name is not None:
                workspace.name = name.strip()
            if description is not None:
                workspace.description = description
            if is_active is not None:
                workspace.is_active = is_active
            if slug is not None:
                base_slug = slug.strip() if slug.strip() else _slugify(workspace.name)
                # Verificar unicidad del slug
                existing = await session.execute(
                    select(Workspace).filter(
                        Workspace.slug == base_slug,
                        Workspace.id != workspace_id
                    )
                )
                if existing.scalar_one_or_none():
                    # Slug existe, agregar sufijo numérico
                    n = 1
                    while True:
                        candidate = f"{base_slug}-{n}"
                        existing = await session.execute(
                            select(Workspace).filter(
                                Workspace.slug == candidate,
                                Workspace.id != workspace_id
                            )
                        )
                        if not existing.scalar_one_or_none():
                            workspace.slug = candidate
                            break
                        n += 1
                else:
                    workspace.slug = base_slug

            await session.commit()
            logger.info(f"Workspace {workspace_id} actualizado")
            return True

    except Exception as e:
        logger.error(f"Error actualizando workspace {workspace_id}: {e}", exc_info=True)
        return False


async def deactivate_workspace(workspace_id: UUID) -> bool:
    """
    Desactiva un workspace (soft delete: is_active = false).

    Args:
        workspace_id: ID del workspace

    Returns:
        True si se desactivó, False si no existe o error
    """
    return await update_workspace(workspace_id, is_active=False)
