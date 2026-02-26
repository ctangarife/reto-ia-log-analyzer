"""
Servicio de verificación de permisos RBAC
"""
import logging
from typing import Optional
from uuid import UUID
from config.database import db_manager

logger = logging.getLogger(__name__)


async def check_permission(
    user_id: UUID,
    project_id: UUID,
    module: str,
    action: str
) -> bool:
    """
    Verifica si un usuario tiene un permiso específico en un proyecto.
    
    Args:
        user_id: ID del usuario
        project_id: ID del proyecto
        module: Nombre del módulo ('logs', 'projects', 'anomalies', etc.)
        action: Acción ('read', 'write', 'delete', 'admin')
    
    Returns:
        True si el usuario tiene el permiso, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT user_has_project_permission($1, $2, $3, $4)
                """,
                user_id, project_id, module, action
            )
            return bool(result) if result is not None else False
    except Exception as e:
        logger.error(f"Error verificando permiso: {e}")
        return False


async def check_workspace_permission(
    user_id: UUID,
    workspace_id: UUID,
    module: str,
    action: str
) -> bool:
    """
    Verifica si un usuario tiene un permiso específico en un workspace.
    
    Args:
        user_id: ID del usuario
        workspace_id: ID del workspace
        module: Nombre del módulo
        action: Acción
    
    Returns:
        True si el usuario tiene el permiso, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT user_has_workspace_permission($1, $2, $3, $4)
                """,
                user_id, workspace_id, module, action
            )
            return bool(result) if result is not None else False
    except Exception as e:
        logger.error(f"Error verificando permiso de workspace: {e}")
        return False


async def is_super_admin(user_id: UUID) -> bool:
    """
    Verifica si un usuario es super administrador.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        True si es super admin, False en caso contrario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT is_super_admin FROM auth.users WHERE id = $1
                """,
                user_id
            )
            return bool(result) if result is not None else False
    except Exception as e:
        logger.error(f"Error verificando super admin: {e}")
        return False


async def get_user_workspaces(user_id: UUID) -> list:
    """
    Obtiene todos los workspaces a los que un usuario tiene acceso.
    
    Args:
        user_id: ID del usuario
    
    Returns:
        Lista de workspaces con información del rol del usuario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM user_accessible_workspaces($1)
                """,
                user_id
            )
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obteniendo workspaces del usuario: {e}")
        return []


async def get_user_projects(
    user_id: UUID,
    workspace_id: Optional[UUID] = None
) -> list:
    """
    Obtiene todos los proyectos a los que un usuario tiene acceso.
    
    Args:
        user_id: ID del usuario
        workspace_id: ID del workspace (opcional, para filtrar)
    
    Returns:
        Lista de proyectos con información del rol del usuario
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            if workspace_id:
                rows = await conn.fetch(
                    """
                    SELECT * FROM user_accessible_projects($1, $2)
                    """,
                    user_id, workspace_id
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM user_accessible_projects($1)
                    """,
                    user_id
                )
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obteniendo proyectos del usuario: {e}")
        return []


async def validate_project_access(user_id: UUID, project_id: UUID) -> bool:
    """
    Valida que un usuario tiene acceso a un proyecto.
    
    Args:
        user_id: ID del usuario
        project_id: ID del proyecto
    
    Returns:
        True si tiene acceso, False en caso contrario
    """
    projects = await get_user_projects(user_id)
    project_ids = [p['project_id'] for p in projects]
    return project_id in project_ids


async def validate_workspace_access(user_id: UUID, workspace_id: UUID) -> bool:
    """
    Valida que un usuario tiene acceso a un workspace.
    
    Args:
        user_id: ID del usuario
        workspace_id: ID del workspace
    
    Returns:
        True si tiene acceso, False en caso contrario
    """
    workspaces = await get_user_workspaces(user_id)
    workspace_ids = [w['workspace_id'] for w in workspaces]
    return workspace_id in workspace_ids


async def get_project_workspace(project_id: UUID) -> Optional[UUID]:
    """
    Obtiene el workspace_id de un proyecto.
    
    Args:
        project_id: ID del proyecto
    
    Returns:
        workspace_id o None si no existe
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT workspace_id FROM auth.projects WHERE id = $1
                """,
                project_id
            )
            return result
    except Exception as e:
        logger.error(f"Error obteniendo workspace del proyecto: {e}")
        return None

