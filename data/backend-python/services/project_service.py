"""
Servicio de gestión de proyectos.
CRUD de proyectos y listado por workspace según permisos del usuario.
"""
import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID

from config.database import db_manager
from services.permission_service import (
    get_user_projects,
    validate_workspace_access,
    validate_project_access,
    check_workspace_permission,
    check_permission,
)

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """Genera un slug URL-friendly a partir del nombre."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "project"


async def _ensure_unique_slug(conn, slug: str, exclude_project_id: Optional[UUID] = None) -> str:
    """Asegura que el slug sea único en auth.projects. Si existe, agrega sufijo numérico."""
    base = slug
    candidate = base
    n = 0
    while True:
        if exclude_project_id:
            row = await conn.fetchval(
                "SELECT id FROM auth.projects WHERE slug = $1 AND id != $2",
                candidate,
                exclude_project_id,
            )
        else:
            row = await conn.fetchval(
                "SELECT id FROM auth.projects WHERE slug = $1",
                candidate,
            )
        if not row:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


async def list_projects_for_user_in_workspace(
    user_id: UUID,
    workspace_id: UUID,
) -> List[Dict[str, Any]]:
    """
    Lista los proyectos a los que el usuario tiene acceso dentro de un workspace.

    Super admin ve todos los proyectos activos del workspace. El resto solo los que tienen
    rol asignado (directo o heredado del workspace).

    Args:
        user_id: ID del usuario
        workspace_id: ID del workspace

    Returns:
        Lista de proyectos con id, name, slug, description, is_active, workspace_id, role, etc.
    """
    try:
        accessible = await get_user_projects(user_id, workspace_id)
        if not accessible:
            return []

        project_ids = [a["project_id"] for a in accessible]
        role_by_id = {a["project_id"]: a["role_name"] for a in accessible}

        async with db_manager.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, workspace_id, name, slug, description, is_active, created_by, created_at, updated_at
                FROM auth.projects
                WHERE id = ANY($1::uuid[]) AND workspace_id = $2 AND is_active = true
                ORDER BY name
                """,
                project_ids,
                workspace_id,
            )

        result = []
        for row in rows:
            d = dict(row)
            d["role"] = role_by_id.get(row["id"], "")
            result.append(d)
        return result
    except Exception as e:
        logger.error(f"Error listando proyectos para workspace {workspace_id}: {e}", exc_info=True)
        return []


async def create_project(
    workspace_id: UUID,
    name: str,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    created_by: Optional[UUID] = None,
) -> Optional[UUID]:
    """
    Crea un nuevo proyecto en un workspace.

    Args:
        workspace_id: ID del workspace
        name: Nombre del proyecto
        description: Descripción opcional
        slug: Slug opcional; si no se proporciona se genera desde name (único globalmente)
        created_by: ID del usuario creador

    Returns:
        UUID del proyecto creado o None si hay error
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            # Verificar que el workspace existe
            ws = await conn.fetchval(
                "SELECT id FROM auth.workspaces WHERE id = $1 AND is_active = true",
                workspace_id,
            )
            if not ws:
                return None

            base_slug = (slug.strip() if slug else _slugify(name)) or _slugify(name)
            unique_slug = await _ensure_unique_slug(conn, base_slug, exclude_project_id=None)

            project_id = await conn.fetchval(
                """
                INSERT INTO auth.projects (workspace_id, name, slug, description, is_active, created_by)
                VALUES ($1, $2, $3, $4, true, $5)
                RETURNING id
                """,
                workspace_id,
                name.strip(),
                unique_slug,
                description,
                created_by,
            )
            logger.info(f"Proyecto creado: {project_id} ({name}) en workspace {workspace_id}")
            return project_id
    except Exception as e:
        logger.error(f"Error creando proyecto: {e}", exc_info=True)
        return None


async def get_project_by_id(project_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un proyecto por ID.

    Args:
        project_id: ID del proyecto

    Returns:
        Diccionario con los datos del proyecto o None si no existe
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, workspace_id, name, slug, description, is_active, created_by, created_at, updated_at
                FROM auth.projects
                WHERE id = $1
                """,
                project_id,
            )
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error obteniendo proyecto {project_id}: {e}")
        return None


async def update_project(
    project_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    slug: Optional[str] = None,
) -> bool:
    """
    Actualiza un proyecto.

    Args:
        project_id: ID del proyecto
        name: Nuevo nombre (opcional)
        description: Nueva descripción (opcional)
        is_active: Nuevo estado activo (opcional)
        slug: Nuevo slug (opcional); se valida unicidad global

    Returns:
        True si se actualizó, False si no existe o error
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            current = await conn.fetchrow(
                "SELECT name, slug FROM auth.projects WHERE id = $1",
                project_id,
            )
            if not current:
                return False

            updates = []
            params = []
            n = 0

            if name is not None:
                n += 1
                updates.append(f"name = ${n}")
                params.append(name.strip())
            if description is not None:
                n += 1
                updates.append(f"description = ${n}")
                params.append(description)
            if is_active is not None:
                n += 1
                updates.append(f"is_active = ${n}")
                params.append(is_active)
            if slug is not None:
                base_slug = (slug.strip() or _slugify(current["name"])).strip() or _slugify(current["name"])
                unique_slug = await _ensure_unique_slug(conn, base_slug, exclude_project_id=project_id)
                n += 1
                updates.append(f"slug = ${n}")
                params.append(unique_slug)

            if not updates:
                return True

            n += 1
            params.append(project_id)
            await conn.execute(
                f"""
                UPDATE auth.projects
                SET {", ".join(updates)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ${n}
                """,
                *params,
            )
            logger.info(f"Proyecto actualizado: {project_id}")
            return True
    except Exception as e:
        logger.error(f"Error actualizando proyecto {project_id}: {e}", exc_info=True)
        return False


async def deactivate_project(project_id: UUID) -> bool:
    """
    Desactiva un proyecto (soft delete: is_active = false).

    Args:
        project_id: ID del proyecto

    Returns:
        True si se desactivó, False si no existe o error
    """
    return await update_project(project_id, is_active=False)
