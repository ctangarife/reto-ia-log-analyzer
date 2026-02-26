"""
Rutas de gestión de proyectos (por ID).
Endpoints GET/PUT/DELETE para proyectos (prefijo /projects; /api lo añade nginx).
Listado y creación están en /workspaces/{workspace_id}/projects.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends

from models.rbac_models import ProjectUpdate
from services.project_service import (
    get_project_by_id,
    update_project,
    deactivate_project,
)
from services.permission_service import (
    validate_project_access,
    check_permission,
)
from middleware.auth_middleware import get_current_user, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{project_id}")
async def get_project(
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Obtiene un proyecto por ID. El usuario debe tener acceso al proyecto.
    """
    has_access = await validate_project_access(current_user.user_id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )
    project = await get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )
    return {
        "id": str(project["id"]),
        "project_id": str(project["id"]),
        "workspace_id": str(project["workspace_id"]),
        "name": project["name"],
        "slug": project["slug"],
        "description": project.get("description"),
        "is_active": project["is_active"],
        "created_by": str(project["created_by"]) if project.get("created_by") else None,
        "created_at": project["created_at"].isoformat() if project.get("created_at") else None,
        "updated_at": project["updated_at"].isoformat() if project.get("updated_at") else None,
    }


@router.put("/{project_id}")
async def update_project_endpoint(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Actualiza un proyecto. Requiere permiso projects:write o projects:admin en el proyecto,
    o ser super administrador.
    """
    has_access = await validate_project_access(current_user.user_id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_write = await check_permission(
            current_user.user_id, project_id, "projects", "write"
        )
        can_admin = await check_permission(
            current_user.user_id, project_id, "projects", "admin"
        )
        if not (can_write or can_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para editar este proyecto",
            )
    ok = await update_project(
        project_id,
        name=body.name,
        description=body.description,
        is_active=body.is_active,
        slug=None,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )
    project = await get_project_by_id(project_id)
    return {
        "id": str(project["id"]),
        "project_id": str(project["id"]),
        "workspace_id": str(project["workspace_id"]),
        "name": project["name"],
        "slug": project["slug"],
        "description": project.get("description"),
        "is_active": project["is_active"],
        "created_at": project["created_at"].isoformat() if project.get("created_at") else None,
        "updated_at": project["updated_at"].isoformat() if project.get("updated_at") else None,
    }


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Desactiva un proyecto (soft delete). Requiere permiso projects:delete o projects:admin
    en el proyecto, o ser super administrador.
    """
    has_access = await validate_project_access(current_user.user_id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_delete = await check_permission(
            current_user.user_id, project_id, "projects", "delete"
        )
        can_admin = await check_permission(
            current_user.user_id, project_id, "projects", "admin"
        )
        if not (can_delete or can_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para eliminar este proyecto",
            )
    ok = await deactivate_project(project_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado",
        )
    return {"message": "Proyecto desactivado", "project_id": str(project_id)}
