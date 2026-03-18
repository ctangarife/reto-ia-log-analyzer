"""
Rutas de gestión de workspaces.
Endpoints CRUD para workspaces (prefijo /workspaces; /api lo añade nginx).
"""
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from models.rbac_models import WorkspaceCreate, WorkspaceUpdate, ProjectCreate
from services.workspace_service import (
    create_workspace,
    get_workspace_by_id,
    list_workspaces_for_user,
    update_workspace,
    deactivate_workspace,
)
from services.permission_service import (
    validate_workspace_access,
    check_workspace_permission,
)
from services.project_service import (
    list_projects_for_user_in_workspace,
    create_project,
    get_project_by_id,
)
from services.rbac_service import (
    assign_user_to_workspace,
    remove_user_from_workspace,
    get_user_roles_in_workspace,
)
from middleware.auth_middleware import get_current_user, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _require_super_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency: exige que el usuario sea super administrador."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de super administrador",
        )
    return current_user


@router.get("", response_model=list)
async def list_workspaces(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Lista los workspaces a los que el usuario tiene acceso.

    Super admin ve todos los workspaces activos. El resto solo los que tienen rol asignado.
    """
    try:
        items = await list_workspaces_for_user(current_user.user_id)
        return [
            {
                "id": str(w["id"]),
                "workspace_id": str(w["id"]),
                "name": w["name"],
                "slug": w["slug"],
                "description": w.get("description"),
                "is_active": w["is_active"],
                "role": w.get("role", ""),
                "created_at": w["created_at"].isoformat() if w.get("created_at") else None,
                "updated_at": w["updated_at"].isoformat() if w.get("updated_at") else None,
            }
            for w in items
        ]
    except Exception as e:
        logger.error(f"Error listando workspaces: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar workspaces",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    body: WorkspaceCreate,
    current_user: CurrentUser = Depends(_require_super_admin),
):
    """
    Crea un nuevo workspace. Solo super administrador.
    """
    try:
        workspace_id = await create_workspace(
            name=body.name,
            description=body.description,
            slug=body.slug,
            created_by=current_user.user_id,
        )
        if not workspace_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo crear el workspace",
            )
        workspace = await get_workspace_by_id(workspace_id)
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workspace creado pero no encontrado",
            )
        return {
            "id": str(workspace["id"]),
            "workspace_id": str(workspace["id"]),
            "name": workspace["name"],
            "slug": workspace["slug"],
            "description": workspace.get("description"),
            "is_active": workspace["is_active"],
            "created_by": str(workspace["created_by"]) if workspace.get("created_by") else None,
            "created_at": workspace["created_at"].isoformat() if workspace.get("created_at") else None,
            "updated_at": workspace["updated_at"].isoformat() if workspace.get("updated_at") else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando workspace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear workspace",
        )


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Obtiene un workspace por ID. El usuario debe tener acceso al workspace.
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    workspace = await get_workspace_by_id(workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado",
        )
    return {
        "id": str(workspace["id"]),
        "workspace_id": str(workspace["id"]),
        "name": workspace["name"],
        "slug": workspace["slug"],
        "description": workspace.get("description"),
        "is_active": workspace["is_active"],
        "created_by": str(workspace["created_by"]) if workspace.get("created_by") else None,
        "created_at": workspace["created_at"].isoformat() if workspace.get("created_at") else None,
        "updated_at": workspace["updated_at"].isoformat() if workspace.get("updated_at") else None,
    }


@router.get("/{workspace_id}/projects", response_model=list)
async def list_workspace_projects(
    workspace_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Lista los proyectos accesibles por el usuario en un workspace.

    El usuario debe tener acceso al workspace. Super admin ve todos los proyectos activos
    del workspace; el resto solo los que tienen rol (directo o heredado del workspace).
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    try:
        items = await list_projects_for_user_in_workspace(current_user.user_id, workspace_id)
        return [
            {
                "id": str(p["id"]),
                "project_id": str(p["id"]),
                "workspace_id": str(p["workspace_id"]),
                "name": p["name"],
                "slug": p["slug"],
                "description": p.get("description"),
                "is_active": p["is_active"],
                "role": p.get("role", ""),
                "created_at": p["created_at"].isoformat() if p.get("created_at") else None,
                "updated_at": p["updated_at"].isoformat() if p.get("updated_at") else None,
            }
            for p in items
        ]
    except Exception as e:
        logger.error(f"Error listando proyectos del workspace {workspace_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al listar proyectos",
        )


@router.post("/{workspace_id}/projects", status_code=status.HTTP_201_CREATED)
async def create_project_in_workspace(
    workspace_id: UUID,
    body: ProjectCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Crea un proyecto dentro del workspace. Requiere permiso projects:write o projects:admin
    en el workspace, o ser super administrador.
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_write = await check_workspace_permission(
            current_user.user_id, workspace_id, "projects", "write"
        )
        can_admin = await check_workspace_permission(
            current_user.user_id, workspace_id, "projects", "admin"
        )
        if not (can_write or can_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para crear proyectos en este workspace",
            )
    # Usar workspace_id de la URL para evitar que el body sobrescriba
    project_id = await create_project(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        slug=body.slug,
        created_by=current_user.user_id,
    )
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el proyecto",
        )
    project = await get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Proyecto creado pero no encontrado",
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


@router.put("/{workspace_id}")
async def update_workspace_endpoint(
    workspace_id: UUID,
    body: WorkspaceUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Actualiza un workspace. Requiere permiso workspaces:write o workspaces:admin en el workspace,
    o ser super administrador.
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_write = await check_workspace_permission(
            current_user.user_id, workspace_id, "workspaces", "write"
        )
        can_admin = await check_workspace_permission(
            current_user.user_id, workspace_id, "workspaces", "admin"
        )
        if not (can_write or can_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para editar este workspace",
            )
    ok = await update_workspace(
        workspace_id,
        name=body.name,
        description=body.description,
        is_active=body.is_active,
        slug=None,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado",
        )
    workspace = await get_workspace_by_id(workspace_id)
    return {
        "id": str(workspace["id"]),
        "workspace_id": str(workspace["id"]),
        "name": workspace["name"],
        "slug": workspace["slug"],
        "description": workspace.get("description"),
        "is_active": workspace["is_active"],
        "created_at": workspace["created_at"].isoformat() if workspace.get("created_at") else None,
        "updated_at": workspace["updated_at"].isoformat() if workspace.get("updated_at") else None,
    }


@router.delete("/{workspace_id}", status_code=status.HTTP_200_OK)
async def delete_workspace(
    workspace_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Desactiva un workspace (soft delete). Requiere permiso workspaces:delete o workspaces:admin
    en el workspace, o ser super administrador.
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_delete = await check_workspace_permission(
            current_user.user_id, workspace_id, "workspaces", "delete"
        )
        can_admin = await check_workspace_permission(
            current_user.user_id, workspace_id, "workspaces", "admin"
        )
        if not (can_delete or can_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para eliminar este workspace",
            )
    ok = await deactivate_workspace(workspace_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado",
        )
    return {"message": "Workspace desactivado", "workspace_id": str(workspace_id)}


class AssignMemberRequest(BaseModel):
    """Request body para asignar miembro a workspace."""
    user_id: str
    role: str


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def assign_workspace_member(
    workspace_id: UUID,
    body: AssignMemberRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Asigna un usuario a un workspace con un rol específico.

    Requiere permiso workspaces:admin en el workspace, o ser super administrador.

    Args:
        workspace_id: ID del workspace
        body: Contiene user_id y role (viewer, analyst, workspace_admin)
        current_user: Usuario actual

    Returns:
        Mensaje de confirmación
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_admin = await check_workspace_permission(
            current_user.user_id, workspace_id, "workspaces", "admin"
        )
        if not can_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para asignar miembros a este workspace",
            )

    try:
        user_uuid = UUID(body.user_id)
        success = await assign_user_to_workspace(
            user_id=user_uuid,
            workspace_id=workspace_id,
            role_name=body.role,
            assigned_by=current_user.user_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al asignar el usuario al workspace",
            )
        return {
            "message": f"Usuario asignado al workspace con rol {body.role}",
            "user_id": body.user_id,
            "workspace_id": str(workspace_id),
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
            detail="Error al asignar el usuario al workspace",
        )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Elimina la asignación de un usuario a un workspace.

    Requiere permiso workspaces:admin en el workspace, o ser super administrador.

    Args:
        workspace_id: ID del workspace
        user_id: ID del usuario a remover
        current_user: Usuario actual

    Returns:
        Mensaje de confirmación
    """
    has_access = await validate_workspace_access(current_user.user_id, workspace_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace no encontrado o sin acceso",
        )
    if not current_user.is_super_admin:
        can_admin = await check_workspace_permission(
            current_user.user_id, workspace_id, "workspaces", "admin"
        )
        if not can_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sin permiso para remover miembros de este workspace",
            )

    try:
        user_uuid = UUID(user_id)
        success = await remove_user_from_workspace(
            user_id=user_uuid,
            workspace_id=workspace_id
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al remover el usuario del workspace",
            )
        return {
            "message": "Usuario removido del workspace",
            "user_id": user_id,
            "workspace_id": str(workspace_id)
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
            detail="Error al remover el usuario del workspace",
        )


@router.get("/{workspace_id}/course-permissions")
async def get_course_permissions(
    workspace_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Obtiene los permisos de cursos del usuario actual en el workspace.

    Retorna los permisos del módulo de aprendizaje (learning:*) y los roles
    de curso asignados al usuario en este workspace.
    """
    try:
        from services.course_rbac_service import course_rbac_service

        # Verificar acceso al workspace
        has_access = await validate_workspace_access(current_user.user_id, workspace_id)
        if not has_access and not current_user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace no encontrado o sin acceso",
            )

        # Obtener roles y permisos de cursos
        roles = await course_rbac_service.get_user_course_roles(
            current_user.user_id, workspace_id
        )
        permissions_data = await course_rbac_service.get_user_course_permissions(
            current_user.user_id, workspace_id
        )

        return {
            "permissions": permissions_data.get("permissions", []),
            "roles": roles
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo permisos de cursos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener permisos de cursos",
        )
