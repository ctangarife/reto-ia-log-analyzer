"""
Entidades ORM (SQLAlchemy) para PostgreSQL.

Todas heredan de OrmBase. Esquemas: processing, auth.
"""
from models.base.orm_base import OrmBase
from models.orm.entities import (
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

# Alias para compatibilidad: Base = OrmBase para entidades
Base = OrmBase

__all__ = [
    "OrmBase",
    "Base",
    "ProcessingJob",
    "ProcessingStat",
    "Configuration",
    "User",
    "UserSession",
    "Module",
    "Permission",
    "Role",
    "RolePermission",
    "Workspace",
    "Project",
    "UserWorkspaceRole",
    "UserProjectRole",
]
