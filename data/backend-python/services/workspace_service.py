"""
Servicio de gestión de workspaces.
CRUD de workspaces y listado según permisos del usuario.
"""
import logging
import re
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from config.database import db_manager
from services.permission_service import (
    get_user_workspaces,
    validate_workspace_access,
    check_workspace_permission,
    is_super_admin,
)

logger = logging.getLogger(__name__)


def _slugify(name: str) -> str:
    """
    Genera un slug URL-friendly a partir del nombre.
    Minúsculas, espacios a guiones, solo alfanuméricos y guiones.
    """
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "workspace"


async def _ensure_unique_slug(conn, slug: str, exclude_workspace_id: Optional[UUID] = None) -> str:
    """
    Asegura que el slug sea único. Si existe, agrega sufijo numérico.
    """
    base = slug
    candidate = base
    n = 0
    while True:
        if exclude_workspace_id:
            row = await conn.fetchval(
                """
                SELECT id FROM auth.workspaces
                WHERE slug = $1 AND id != $2
                """,
                candidate,
                exclude_workspace_id,
            )
        else:
            row = await conn.fetchval(
                "SELECT id FROM auth.workspaces WHERE slug = $1",
                candidate,
            )
        if not row:
            return candidate
        n += 1
        candidate = f"{base}-{n}"


async def create_workspace(
    name: str,
    description: Optional[str] = None,
    slug: Optional[str] = None,
    created_by: Optional[UUID] = None,
) -> Optional[UUID]:
    """
    Crea un nuevo workspace.

    Args:
        name: Nombre del workspace
        description: Descripción opcional
        slug: Slug opcional; si no se proporciona se genera desde name
        created_by: ID del usuario creador

    Returns:
        UUID del workspace creado o None si hay error
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            base_slug = (slug.strip() if slug else _slugify(name)) or _slugify(name)
            unique_slug = await _ensure_unique_slug(conn, base_slug, exclude_workspace_id=None)

            workspace_id = await conn.fetchval(
                """
                INSERT INTO auth.workspaces (name, slug, description, is_active, created_by)
                VALUES ($1, $2, $3, true, $4)
                RETURNING id
                """,
                name.strip(),
                unique_slug,
                description,
                created_by,
            )
            logger.info(f"Workspace creado: {workspace_id} ({name})")
            return workspace_id
    except Exception as e:
        logger.error(f"Error creando workspace: {e}", exc_info=True)
        return None


async def get_workspace_by_id(workspace_id: UUID) -> Optional[Dict[str, Any]]:
    """
    Obtiene un workspace por ID.

    Args:
        workspace_id: ID del workspace

    Returns:
        Diccionario con los datos del workspace o None si no existe
    """
    try:
        async with db_manager.postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, slug, description, is_active, created_by, created_at, updated_at
                FROM auth.workspaces
                WHERE id = $1
                """,
                workspace_id,
            )
            return dict(row) if row else None
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

        workspace_ids = [a["workspace_id"] for a in accessible]
        role_by_id = {a["workspace_id"]: a["role_name"] for a in accessible}

        async with db_manager.postgres_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, slug, description, is_active, created_by, created_at, updated_at
                FROM auth.workspaces
                WHERE id = ANY($1::uuid[]) AND is_active = true
                ORDER BY name
                """,
                workspace_ids,
            )

        result = []
        for row in rows:
            d = dict(row)
            d["role"] = role_by_id.get(row["id"], "")
            result.append(d)
        return result
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
    Actualiza un workspace.

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
        async with db_manager.postgres_pool.acquire() as conn:
            current = await conn.fetchrow(
                "SELECT name, slug FROM auth.workspaces WHERE id = $1",
                workspace_id,
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
                unique_slug = await _ensure_unique_slug(conn, base_slug, exclude_workspace_id=workspace_id)
                n += 1
                updates.append(f"slug = ${n}")
                params.append(unique_slug)

            if not updates:
                return True

            n += 1
            updates.append(f"updated_at = CURRENT_TIMESTAMP")
            params.append(workspace_id)

            await conn.execute(
                f"""
                UPDATE auth.workspaces
                SET {", ".join(updates)}
                WHERE id = ${n}
                """,
                *params,
            )
            logger.info(f"Workspace actualizado: {workspace_id}")
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
