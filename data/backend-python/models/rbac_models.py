"""
Modelos Pydantic para RBAC: Workspaces, Proyectos y Permisos
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ============================================================================
# MODELOS DE USUARIOS
# ============================================================================

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)  # Para cambio de contraseña separado


class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_super_admin: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELOS DE WORKSPACES
# ============================================================================

class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceCreate(WorkspaceBase):
    slug: Optional[str] = None  # Si no se proporciona, se genera del name


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class WorkspaceResponse(WorkspaceBase):
    id: UUID
    slug: str
    is_active: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceWithRole(WorkspaceResponse):
    role: str  # Rol del usuario en este workspace


# ============================================================================
# MODELOS DE PROYECTOS
# ============================================================================

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    workspace_id: Optional[UUID] = None  # Se toma de la URL en el endpoint /workspaces/{workspace_id}/projects
    slug: Optional[str] = None  # Si no se proporciona, se genera del name


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(ProjectBase):
    id: UUID
    workspace_id: UUID
    slug: str
    is_active: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectWithRole(ProjectResponse):
    role: str  # Rol del usuario en este proyecto


# ============================================================================
# MODELOS DE ROLES Y PERMISOS
# ============================================================================

class PermissionResponse(BaseModel):
    id: UUID
    module: str
    action: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# MODELOS DE ASIGNACIÓN DE ROLES
# ============================================================================

class UserWorkspaceRoleCreate(BaseModel):
    user_id: UUID
    workspace_id: UUID
    role_id: UUID


class UserWorkspaceRoleResponse(BaseModel):
    id: UUID
    user_id: UUID
    workspace_id: UUID
    role_id: UUID
    role_name: str
    assigned_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserProjectRoleCreate(BaseModel):
    user_id: UUID
    project_id: UUID
    role_id: UUID


class UserProjectRoleResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: UUID
    role_id: UUID
    role_name: str
    assigned_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODELOS DE AUTENTICACIÓN
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None

