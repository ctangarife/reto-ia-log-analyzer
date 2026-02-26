"""
Entidades SQLAlchemy (ORM) para PostgreSQL. Generadas a partir de db/init.sql.
Todas heredan de OrmBase. Schemas: processing, auth.
"""
from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import (
    String, Text, Boolean, BigInteger, Integer, Float, DateTime, ForeignKey,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.sql import text

from models.base.orm_base import OrmBase


# =============================================================================
# SCHEMA: PROCESSING
# =============================================================================


class ProcessingJob(OrmBase):
    """processing.processing_jobs - Trabajos de procesamiento de logs."""
    __tablename__ = "processing_jobs"
    __table_args__ = {"schema": "processing"}

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)
    chunks_processed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stats: Mapped[List["ProcessingStat"]] = relationship("ProcessingStat", back_populates="job")


class ProcessingStat(OrmBase):
    """processing.processing_stats - Estadísticas por chunk."""
    __tablename__ = "processing_stats"
    __table_args__ = {"schema": "processing"}

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    job_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("processing_jobs.id"), nullable=False
    )
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomalies_found: Mapped[int] = mapped_column(Integer, default=0)
    memory_used: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["ProcessingJob"] = relationship("ProcessingJob", back_populates="stats")


class Configuration(OrmBase):
    """processing.configurations - Configuración del modelo de anomalías."""
    __tablename__ = "configurations"
    __table_args__ = (
        {"schema": "processing"},
        Index("idx_config_active", "is_active"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contamination: Mapped[float] = mapped_column(Float, default=0.1)
    n_estimators: Mapped[int] = mapped_column(Integer, default=100)
    random_state: Mapped[int] = mapped_column(Integer, default=42)
    suspicious_keywords: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    model_params: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# SCHEMA: AUTH - Usuarios y sesiones
# =============================================================================


class User(OrmBase):
    """auth.users - Usuarios del sistema."""
    __tablename__ = "users"
    __table_args__ = (
        {"schema": "auth"},
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
        Index("idx_users_active", "is_active"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions: Mapped[List["UserSession"]] = relationship("UserSession", back_populates="user")
    created_workspaces: Mapped[List["Workspace"]] = relationship(
        "Workspace", back_populates="created_by_user", foreign_keys="Workspace.created_by"
    )
    created_projects: Mapped[List["Project"]] = relationship(
        "Project", back_populates="created_by_user", foreign_keys="Project.created_by"
    )
    user_workspace_roles: Mapped[List["UserWorkspaceRole"]] = relationship(
        "UserWorkspaceRole", back_populates="user"
    )
    user_project_roles: Mapped[List["UserProjectRole"]] = relationship(
        "UserProjectRole", back_populates="user"
    )


class UserSession(OrmBase):
    """auth.user_sessions - Sesiones / tokens JWT."""
    __tablename__ = "user_sessions"
    __table_args__ = {"schema": "auth"}

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


# =============================================================================
# SCHEMA: AUTH - Módulos y permisos
# =============================================================================


class Module(OrmBase):
    """auth.modules - Módulos funcionales."""
    __tablename__ = "modules"
    __table_args__ = {"schema": "auth"}

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    permissions: Mapped[List["Permission"]] = relationship("Permission", back_populates="module")


class Permission(OrmBase):
    """auth.permissions - Acciones por módulo."""
    __tablename__ = "permissions"
    __table_args__ = (
        {"schema": "auth"},
        UniqueConstraint("module_id", "action", name="uq_permissions_module_action"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    module_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.modules.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    module: Mapped["Module"] = relationship("Module", back_populates="permissions")
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission"
    )


class Role(OrmBase):
    """auth.roles - Roles del sistema."""
    __tablename__ = "roles"
    __table_args__ = {"schema": "auth"}

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role_permissions: Mapped[List["RolePermission"]] = relationship(
        "RolePermission", back_populates="role"
    )
    user_workspace_roles: Mapped[List["UserWorkspaceRole"]] = relationship(
        "UserWorkspaceRole", back_populates="role"
    )
    user_project_roles: Mapped[List["UserProjectRole"]] = relationship(
        "UserProjectRole", back_populates="role"
    )


class RolePermission(OrmBase):
    """auth.role_permissions - Relación roles -> permisos."""
    __tablename__ = "role_permissions"
    __table_args__ = (
        {"schema": "auth"},
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    role_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.permissions.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions")


# =============================================================================
# SCHEMA: AUTH - Workspaces y proyectos
# =============================================================================


class Workspace(OrmBase):
    """auth.workspaces - Espacios de trabajo."""
    __tablename__ = "workspaces"
    __table_args__ = (
        {"schema": "auth"},
        Index("idx_workspaces_slug", "slug"),
        Index("idx_workspaces_active", "is_active"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[Any]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="created_workspaces", foreign_keys=[created_by]
    )
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="workspace")
    user_workspace_roles: Mapped[List["UserWorkspaceRole"]] = relationship(
        "UserWorkspaceRole", back_populates="workspace"
    )


class Project(OrmBase):
    """auth.projects - Proyectos (hijos de workspaces)."""
    __tablename__ = "projects"
    __table_args__ = (
        {"schema": "auth"},
        Index("idx_projects_workspace", "workspace_id"),
        Index("idx_projects_slug", "slug"),
        Index("idx_projects_active", "is_active"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    workspace_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[Any]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="projects")
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="created_projects", foreign_keys=[created_by]
    )
    user_project_roles: Mapped[List["UserProjectRole"]] = relationship(
        "UserProjectRole", back_populates="project"
    )


class UserWorkspaceRole(OrmBase):
    """auth.user_workspace_roles - Asignación usuario -> workspace -> rol."""
    __tablename__ = "user_workspace_roles"
    __table_args__ = (
        {"schema": "auth"},
        UniqueConstraint("user_id", "workspace_id", "role_id", name="uq_user_workspace_roles"),
        Index("idx_user_workspace_roles_user", "user_id"),
        Index("idx_user_workspace_roles_workspace", "workspace_id"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.workspaces.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[Optional[Any]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="user_workspace_roles")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="user_workspace_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_workspace_roles")


class UserProjectRole(OrmBase):
    """auth.user_project_roles - Asignación usuario -> proyecto -> rol."""
    __tablename__ = "user_project_roles"
    __table_args__ = (
        {"schema": "auth"},
        UniqueConstraint("user_id", "project_id", "role_id", name="uq_user_project_roles"),
        Index("idx_user_project_roles_user", "user_id"),
        Index("idx_user_project_roles_project", "project_id"),
    )

    id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.projects.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[Any] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[Optional[Any]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("auth.users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="user_project_roles")
    project: Mapped["Project"] = relationship("Project", back_populates="user_project_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_project_roles")
