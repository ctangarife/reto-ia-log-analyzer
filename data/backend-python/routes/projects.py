"""
Rutas de gestión de proyectos (por ID).
Endpoints GET/PUT/DELETE para proyectos (prefijo /projects; /api lo añade nginx).
Listado y creación están en /workspaces/{workspace_id}/projects.
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from models.rbac_models import ProjectUpdate
from services.project_service import (
    get_project_by_id,
    update_project,
    deactivate_project,
)
from services.permission_service import (
    validate_project_access,
    check_permission,
    get_user_project_permissions,
)
from services.rbac_service import (
    assign_user_to_project,
    remove_user_from_project,
    get_user_roles_in_project,
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


class AssignMemberRequest(BaseModel):
    """Request body para asignar miembro a proyecto."""
    user_id: str
    role: str


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
async def assign_project_member(
    project_id: UUID,
    body: AssignMemberRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Asigna un usuario a un proyecto con un rol específico.

    Requiere permiso projects:admin en el proyecto, o ser super administrador.

    Args:
        project_id: ID del proyecto
        body: Contiene user_id y role (viewer, analyst, project_admin)
        current_user: Usuario actual

    Returns:
        Mensaje de confirmación
    """
    has_access = await validate_project_access(current_user.user_id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_admin = await check_permission(
            current_user.user_id, project_id, "projects", "admin"
        )
        if not can_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para asignar miembros a este proyecto",
            )

    try:
        user_uuid = UUID(body.user_id)
        success = await assign_user_to_project(
            user_id=user_uuid,
            project_id=project_id,
            role_name=body.role,
            assigned_by=current_user.user_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al asignar el usuario al proyecto",
            )
        return {
            "message": f"Usuario asignado al proyecto con rol {body.role}",
            "user_id": body.user_id,
            "project_id": str(project_id),
            "role": body.role
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id inválido",
        )
    except Exception as e:
        logger.error(f"Error asignando miembro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al asignar el usuario al proyecto",
        )


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_project_member(
    project_id: UUID,
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Elimina la asignación de un usuario a un proyecto.

    Requiere permiso projects:admin en el proyecto, o ser super administrador.

    Args:
        project_id: ID del proyecto
        user_id: ID del usuario a remover
        current_user: Usuario actual

    Returns:
        Mensaje de confirmación
    """
    has_access = await validate_project_access(current_user.user_id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_admin = await check_permission(
            current_user.user_id, project_id, "projects", "admin"
        )
        if not can_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para remover miembros de este proyecto",
            )

    try:
        user_uuid = UUID(user_id)
        success = await remove_user_from_project(
            user_id=user_uuid,
            project_id=project_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al remover el usuario del proyecto",
            )
        return {
            "message": "Usuario removido del proyecto",
            "user_id": user_id,
            "project_id": str(project_id)
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id inválido",
        )
    except Exception as e:
        logger.error(f"Error removiendo miembro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al remover el usuario del proyecto",
        )


@router.get("/{project_id}/permissions")
async def get_project_permissions(
    project_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Obtiene los permisos del usuario actual en un proyecto.

    Incluye lista de permisos (formato module:action) y roles con sus permisos.
    """
    has_access = await validate_project_access(current_user.user_id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado o sin acceso",
        )

    permissions_data = await get_user_project_permissions(current_user.user_id, project_id)
    return permissions_data
