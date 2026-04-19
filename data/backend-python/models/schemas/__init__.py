"""
Esquemas Pydantic para la API (request/response).

- rbac: usuarios, workspaces, proyectos, roles, permisos, auth.
- v2: procesamiento de logs, jobs, chunks, anomalías.
"""
from models.schemas.rbac import (
    UserBase, UserCreate, UserUpdate, UserResponse,
    WorkspaceBase, WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceWithRole,
    ProjectBase, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectWithRole,
    PermissionResponse, RoleResponse,
    UserWorkspaceRoleCreate, UserWorkspaceRoleResponse,
    UserProjectRoleCreate, UserProjectRoleResponse,
    LoginRequest, TokenResponse, TokenData,
)
from models.schemas.v2 import (
    ProcessingStatus, ChunkData, ProcessingJob, ProcessingStats,
    AnomalyResultV2, ChunkResult, ProcessResponseV2, StatusResponseV2, StreamResult,
)

__all__ = [
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "WorkspaceBase", "WorkspaceCreate", "WorkspaceUpdate", "WorkspaceResponse", "WorkspaceWithRole",
    "ProjectBase", "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectWithRole",
    "PermissionResponse", "RoleResponse",
    "UserWorkspaceRoleCreate", "UserWorkspaceRoleResponse",
    "UserProjectRoleCreate", "UserProjectRoleResponse",
    "LoginRequest", "TokenResponse", "TokenData",
    "ProcessingStatus", "ChunkData", "ProcessingJob", "ProcessingStats",
    "AnomalyResultV2", "ChunkResult", "ProcessResponseV2", "StatusResponseV2", "StreamResult",
]
