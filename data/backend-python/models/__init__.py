"""
Modelos del backend.

- rbac_models: Modelos Pydantic para API (usuarios, workspaces, proyectos, auth).
- v2_models: Modelos Pydantic para procesamiento v2.
- db_models: Modelos SQLAlchemy (ORM) para PostgreSQL; generados a partir de db/init.sql.
"""
from models.rbac_models import (  # noqa: F401
    UserBase, UserCreate, UserUpdate, UserResponse,
    WorkspaceBase, WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceWithRole,
    ProjectBase, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectWithRole,
    PermissionResponse, RoleResponse,
    UserWorkspaceRoleCreate, UserWorkspaceRoleResponse,
    UserProjectRoleCreate, UserProjectRoleResponse,
    LoginRequest, TokenResponse, TokenData,
)
from models.v2_models import (  # noqa: F401
    ProcessResponseV2, StatusResponseV2, ProcessingStatus,
)
from models.db_models import (  # noqa: F401
    Base,
    ProcessingJob,
    ProcessingStat,
    Configuration,
    User,
    UserSession,
    Module,
    Permission,
    Role,
    RolePermission,
    Workspace,
    Project,
    UserWorkspaceRole,
    UserProjectRole,
)

__all__ = [
    # Pydantic RBAC
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "WorkspaceBase", "WorkspaceCreate", "WorkspaceUpdate", "WorkspaceResponse", "WorkspaceWithRole",
    "ProjectBase", "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectWithRole",
    "PermissionResponse", "RoleResponse",
    "UserWorkspaceRoleCreate", "UserWorkspaceRoleResponse",
    "UserProjectRoleCreate", "UserProjectRoleResponse",
    "LoginRequest", "TokenResponse", "TokenData",
    # Pydantic v2
    "ProcessResponseV2", "StatusResponseV2", "ProcessingStatus",
    # SQLAlchemy ORM
    "Base",
    "ProcessingJob", "ProcessingStat", "Configuration",
    "User", "UserSession",
    "Module", "Permission", "Role", "RolePermission",
    "Workspace", "Project",
    "UserWorkspaceRole", "UserProjectRole",
]
