"""
Servicio de gestión de roles y asignaciones RBAC
Maneja la asignación de usuarios a workspaces y proyectos con roles
"""
import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from config.database import db_manager

logger = logging.getLogger(__name__)


async def get_role_id_by_name(role_name: str) -> Optional[UUID]:
    """
    Obtiene el ID de un rol por su nombre.

    Args:
        role_name: Nombre del rol (viewer, analyst, workspace_admin, project_admin)

    Returns:
        ID del rol o None si no existe
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            role_id = await conn.fetchval(
                "SELECT id FROM auth.roles WHERE name = $1",
                role_name
            )
            return role_id
    except Exception as e:
        logger.error(f"Error obteniendo rol por nombre: {e}")
        return None


async def assign_user_to_workspace(
    user_id: UUID,
    workspace_id: UUID,
    role_name: str,
    assigned_by: UUID
) -> bool:
    """
    Asigna un usuario a un workspace con un rol específico.

    Args:
        user_id: ID del usuario a asignar
        workspace_id: ID del workspace
        role_name: Nombre del rol (viewer, analyst, workspace_admin)
        assigned_by: ID del usuario que hace la asignación

    Returns:
        True si se asignó correctamente, False en caso contrario
    """
    try:
        # Obtener ID del rol
        role_id = await get_role_id_by_name(role_name)
        if not role_id:
            logger.error(f"Rol no encontrado: {role_name}")
            return False

        async with db_manager.postgres_pool.acquire() as conn:
            # Verificar si ya existe la asignación
            existing = await conn.fetchrow(
                """
                SELECT id FROM auth.user_workspace_roles
                WHERE user_id = $1 AND workspace_id = $2
                """,
                user_id, workspace_id
            )

            if existing:
                # Actualizar rol existente
                await conn.execute(
                    """
                    UPDATE auth.user_workspace_roles
                    SET role_id = $1, assigned_by = $2
                    WHERE user_id = $3 AND workspace_id = $4
                    """,
                    role_id, assigned_by, user_id, workspace_id
                )
                logger.info(f"Rol actualizado para usuario {user_id} en workspace {workspace_id}: {role_name}")
            else:
                # Crear nueva asignación
                await conn.execute(
                    """
                    INSERT INTO auth.user_workspace_roles (user_id, workspace_id, role_id, assigned_by)
                    VALUES ($1, $2, $3, $4)
                    """,
                    user_id, workspace_id, role_id, assigned_by
                )
                logger.info(f"Usuario {user_id} asignado a workspace {workspace_id} con rol: {role_name}")

            return True

    except Exception as e:
        logger.error(f"Error asignando usuario a workspace: {e}")
        return False


async def assign_user_to_project(
    user_id: UUID,
    project_id: UUID,
    role_name: str,
    assigned_by: UUID
) -> bool:
    """
    Asigna un usuario a un proyecto con un rol específico.

    Args:
        user_id: ID del usuario a asignar
        project_id: ID del proyecto
        role_name: Nombre del rol (viewer, analyst, project_admin)
        assigned_by: ID del usuario que hace la asignación

    Returns:
        True si se asignó correctamente, False en caso contrario
    """
    try:
        # Obtener ID del rol
        role_id = await get_role_id_by_name(role_name)
        if not role_id:
            logger.error(f"Rol no encontrado: {role_name}")
            return False

        async with db_manager.postgres_pool.acquire() as conn:
            # Verificar si ya existe la asignación
            existing = await conn.fetchrow(
                """
                SELECT id FROM auth.user_project_roles
                WHERE user_id = $1 AND project_id = $2
                """,
                user_id, project_id
            )

            if existing:
                # Actualizar rol existente
                await conn.execute(
                    """
                    UPDATE auth.user_project_roles
                    SET role_id = $1, assigned_by = $2
                    WHERE user_id = $3 AND project_id = $4
                    """,
                    role_id, assigned_by, user_id, project_id
                )
                logger.info(f"Rol actualizado para usuario {user_id} en proyecto {project_id}: {role_name}")
            else:
                # Crear nueva asignación
                await conn.execute(
                    """
                    INSERT INTO auth.user_project_roles (user_id, project_id, role_id, assigned_by)
                    VALUES ($1, $2, $3, $4)
                    """,
                    user_id, project_id, role_id, assigned_by
                )
                logger.info(f"Usuario {user_id} asignado a proyecto {project_id} con rol: {role_name}")

            return True

    except Exception as e:
        logger.error(f"Error asignando usuario a proyecto: {e}")
        return False


async def remove_user_from_workspace(
    user_id: UUID,
    workspace_id: UUID
) -> bool:
    """
    Elimina la asignación de un usuario a un workspace.

    Args:
        user_id: ID del usuario
        workspace_id: ID del workspace

    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM auth.user_workspace_roles
                WHERE user_id = $1 AND workspace_id = $2
                """,
                user_id, workspace_id
            )
            logger.info(f"Usuario {user_id} eliminado del workspace {workspace_id}")
            return True

    except Exception as e:
        logger.error(f"Error eliminando usuario del workspace: {e}")
        return False


async def remove_user_from_project(
    user_id: UUID,
    project_id: UUID
) -> bool:
    """
    Elimina la asignación de un usuario a un proyecto.

    Args:
        user_id: ID del usuario
        project_id: ID del proyecto

    Returns:
        True si se eliminó correctamente, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM auth.user_project_roles
                WHERE user_id = $1 AND project_id = $2
                """,
                user_id, project_id
            )
            logger.info(f"Usuario {user_id} eliminado del proyecto {project_id}")
            return True

    except Exception as e:
        logger.error(f"Error eliminando usuario del proyecto: {e}")
        return False


async def get_user_roles_in_workspace(
    user_id: UUID,
    workspace_id: UUID
) -> List[dict]:
    """
    Obtiene los roles de un usuario en un workspace.

    Args:
        user_id: ID del usuario
        workspace_id: ID del workspace

    Returns:
        Lista de roles del usuario en el workspace
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.name as role_name, uwr.created_at
                FROM auth.user_workspace_roles uwr
                JOIN auth.roles r ON uwr.role_id = r.id
                WHERE uwr.user_id = $1 AND uwr.workspace_id = $2
                """,
                user_id, workspace_id
            )
            return [{"role": row["role_name"], "assigned_at": row["created_at"]} for row in rows]
    except Exception as e:
        logger.error(f"Error obteniendo roles del usuario en workspace: {e}")
        return []


async def get_user_roles_in_project(
    user_id: UUID,
    project_id: UUID
) -> List[dict]:
    """
    Obtiene los roles de un usuario en un proyecto.

    Args:
        user_id: ID del usuario
        project_id: ID del proyecto

    Returns:
        Lista de roles del usuario en el proyecto
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.name as role_name, upr.created_at
                FROM auth.user_project_roles upr
                JOIN auth.roles r ON upr.role_id = r.id
                WHERE upr.user_id = $1 AND upr.project_id = $2
                """,
                user_id, project_id
            )
            return [{"role": row["role_name"], "assigned_at": row["created_at"]} for row in rows]
    except Exception as e:
        logger.error(f"Error obteniendo roles del usuario en proyecto: {e}")
        return []


async def list_available_roles() -> List[str]:
    """
    Lista todos los roles disponibles en el sistema.

    Returns:
        Lista de nombres de roles
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name FROM auth.roles ORDER BY name"
            )
            return [row["name"] for row in rows]
    except Exception as e:
        logger.error(f"Error listando roles disponibles: {e}")
        return []
