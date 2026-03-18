"""
Course RBAC Service
Manages roles and permissions for course management using the existing RBAC structure
"""
import logging
from typing import Optional, List, Dict
from uuid import UUID

from config.database import db_manager

logger = logging.getLogger(__name__)

# Module ID for learning (from init_learning_rbac.sql)
LEARNING_MODULE_ID = UUID("00000000-0000-0000-0000-000000000001")

# Role IDs for course roles
COURSE_CREATOR_ROLE_ID = UUID("00000000-0000-0000-0002-000000000001")
COURSE_REVIEWER_ROLE_ID = UUID("00000000-0000-0000-0002-000000000002")
COURSE_ADMIN_ROLE_ID = UUID("00000000-0000-0000-0002-000000000003")


class CourseRBACService:
    """Service for managing course-specific RBAC using the existing auth schema"""

    def __init__(self):
        # Permission definitions for reference (mapped to action names)
        self.PERMISSION_ACTIONS = {
            "create": "Crear nuevos cursos",
            "edit": "Editar cualquier curso del workspace",
            "edit_own": "Editar solo cursos propios",
            "edit_lessons": "Editar contenido de lecciones",
            "minor_edit": "Hacer correcciones menores sin aprobación",
            "review": "Revisar y aprobar/rechazar cursos",
            "delete": "Eliminar o archivar cursos",
            "publish": "Publicar cursos sin aprobación previa",
            "view_draft": "Ver cursos en borrador",
            "view_pending": "Ver cursos pendientes de revisión",
        }

    async def initialize_course_permissions(self) -> dict:
        """
        Initialize all course permissions and roles in the database.
        Uses the SQL script from init_learning_rbac.sql
        """
        try:
            # This is now handled by the SQL script
            # Just verify the data exists
            async with db_manager.postgres_pool.acquire() as conn:
                # Check if learning module exists
                module_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM auth.modules WHERE id = $1)",
                    LEARNING_MODULE_ID
                )

                if not module_exists:
                    return {
                        "status": "error",
                        "message": "Learning module not found. Run init_learning_rbac.sql script first."
                    }

                # Count permissions
                perm_count = await conn.fetchval(
                    """SELECT COUNT(*) FROM auth.permissions WHERE module_id = $1""",
                    LEARNING_MODULE_ID
                )

                # Count roles
                role_count = await conn.fetchval(
                    """SELECT COUNT(*) FROM auth.roles WHERE id IN ($1, $2, $3)""",
                    COURSE_CREATOR_ROLE_ID, COURSE_REVIEWER_ROLE_ID, COURSE_ADMIN_ROLE_ID
                )

                return {
                    "status": "success",
                    "message": "Course RBAC already initialized via SQL script",
                    "permissions_count": perm_count,
                    "roles_count": role_count,
                    "permissions_created": list(self.PERMISSION_ACTIONS.keys()),
                    "roles_created": ["course_creator", "course_reviewer", "course_admin"]
                }
        except Exception as e:
            logger.error(f"Error checking course RBAC: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def assign_course_role_to_user(
        self,
        user_id: UUID,
        workspace_id: UUID,
        role_name: str
    ) -> dict:
        """Assign a course role to a user in a workspace"""
        try:
            # Map role name to role ID
            role_ids = {
                "course_creator": COURSE_CREATOR_ROLE_ID,
                "course_reviewer": COURSE_REVIEWER_ROLE_ID,
                "course_admin": COURSE_ADMIN_ROLE_ID,
            }

            if role_name not in role_ids:
                return {
                    "status": "error",
                    "message": f"Invalid role name: {role_name}. Valid roles: {list(role_ids.keys())}"
                }

            role_id = role_ids[role_name]

            async with db_manager.postgres_pool.acquire() as conn:
                # Check if already assigned
                existing = await conn.fetchrow(
                    """SELECT 1 FROM auth.user_workspace_roles
                       WHERE user_id = $1 AND workspace_id = $2 AND role_id = $3""",
                    user_id, workspace_id, role_id
                )

                if existing:
                    return {
                        "status": "already_assigned",
                        "message": f"User already has role {role_name} in this workspace"
                    }

                # Assign role
                await conn.execute(
                    """INSERT INTO auth.user_workspace_roles (user_id, workspace_id, role_id)
                       VALUES ($1, $2, $3)""",
                    user_id, workspace_id, role_id
                )

                logger.info(f"Assigned role {role_name} to user {user_id} in workspace {workspace_id}")

                return {
                    "status": "success",
                    "role_name": role_name,
                    "user_id": str(user_id),
                    "workspace_id": str(workspace_id)
                }

        except Exception as e:
            logger.error(f"Error assigning course role: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def remove_course_role_from_user(
        self,
        user_id: UUID,
        workspace_id: UUID,
        role_name: str
    ) -> dict:
        """Remove a course role from a user in a workspace"""
        try:
            role_ids = {
                "course_creator": COURSE_CREATOR_ROLE_ID,
                "course_reviewer": COURSE_REVIEWER_ROLE_ID,
                "course_admin": COURSE_ADMIN_ROLE_ID,
            }

            if role_name not in role_ids:
                return {
                    "status": "error",
                    "message": f"Invalid role name: {role_name}"
                }

            role_id = role_ids[role_name]

            async with db_manager.postgres_pool.acquire() as conn:
                result = await conn.execute(
                    """DELETE FROM auth.user_workspace_roles
                       WHERE user_id = $1 AND workspace_id = $2 AND role_id = $3""",
                    user_id, workspace_id, role_id
                )

                if result == "DELETE 0":
                    return {
                        "status": "not_found",
                        "message": f"User does not have role {role_name} in this workspace"
                    }

                logger.info(f"Removed role {role_name} from user {user_id} in workspace {workspace_id}")

                return {
                    "status": "success",
                    "role_name": role_name,
                    "user_id": str(user_id)
                }

        except Exception as e:
            logger.error(f"Error removing course role: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def get_user_course_roles(
        self,
        user_id: UUID,
        workspace_id: UUID
    ) -> List[dict]:
        """Get all course roles for a user in a workspace"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                roles = await conn.fetch(
                    """SELECT r.id, r.name, r.description
                       FROM auth.roles r
                       JOIN auth.user_workspace_roles uwr ON r.id = uwr.role_id
                       WHERE uwr.user_id = $1 AND uwr.workspace_id = $2
                       AND r.id IN ($3, $4, $5)""",
                    user_id, workspace_id,
                    COURSE_CREATOR_ROLE_ID, COURSE_REVIEWER_ROLE_ID, COURSE_ADMIN_ROLE_ID
                )

                return [dict(row) for row in roles]

        except Exception as e:
            logger.error(f"Error getting user course roles: {e}")
            return []

    async def get_user_course_permissions(
        self,
        user_id: UUID,
        workspace_id: UUID
    ) -> dict:
        """Get all course permissions for a user in a workspace"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get user's roles in the workspace
                roles = await self.get_user_course_roles(user_id, workspace_id)

                if not roles:
                    return {
                        "user_id": str(user_id),
                        "workspace_id": str(workspace_id),
                        "roles": [],
                        "permissions": []
                    }

                # Get all permissions for these roles
                role_ids = [r["id"] for r in roles]

                permissions = await conn.fetch(
                    """SELECT DISTINCT p.action
                       FROM auth.permissions p
                       JOIN auth.role_permissions rp ON p.id = rp.permission_id
                       WHERE rp.role_id = ANY($1) AND p.module_id = $2""",
                    role_ids, LEARNING_MODULE_ID
                )

                perm_list = [f"learning:{p['action']}" for p in permissions]

                return {
                    "user_id": str(user_id),
                    "workspace_id": str(workspace_id),
                    "roles": [{"id": str(r["id"]), "name": r["name"]} for r in roles],
                    "permissions": perm_list
                }

        except Exception as e:
            logger.error(f"Error getting user course permissions: {e}")
            return {
                "user_id": str(user_id),
                "workspace_id": str(workspace_id),
                "roles": [],
                "permissions": []
            }

    async def check_course_permission(
        self,
        user_id: UUID,
        workspace_id: UUID,
        permission: str
    ) -> bool:
        """
        Check if user has a specific course permission.
        Permission format: "courses:action" or "learning:action" (e.g., "courses:create")
        """
        try:
            # Parse permission string
            parts = permission.split(":")
            if len(parts) != 2:
                logger.warning(f"Invalid permission format: {permission}")
                return False

            # Accept both "courses:" and "learning:" prefixes
            if parts[0] not in ["courses", "learning"]:
                logger.warning(f"Invalid permission prefix: {permission}")
                return False

            action = parts[1]

            async with db_manager.postgres_pool.acquire() as conn:
                # Check if user has super admin
                is_super = await conn.fetchval(
                    "SELECT is_super_admin FROM auth.users WHERE id = $1",
                    user_id
                )
                if is_super:
                    return True

                # Check permission via user_has_workspace_permission function
                has_perm = await conn.fetchval(
                    """SELECT user_has_workspace_permission($1, $2, 'learning', $3)""",
                    user_id, workspace_id, action
                )

                return bool(has_perm)

        except Exception as e:
            logger.error(f"Error checking course permission: {e}")
            return False

    async def get_workspace_course_members(
        self,
        workspace_id: UUID,
        role_name: Optional[str] = None
    ) -> List[dict]:
        """Get all users with course roles in a workspace"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                query = """
                    SELECT u.id, u.email, u.first_name, u.last_name, r.name as role_name
                    FROM auth.users u
                    JOIN auth.user_workspace_roles uwr ON u.id = uwr.user_id
                    JOIN auth.roles r ON uwr.role_id = r.id
                    WHERE uwr.workspace_id = $1
                    AND r.id IN ($2, $3, $4)
                """

                params = [workspace_id, COURSE_CREATOR_ROLE_ID, COURSE_REVIEWER_ROLE_ID, COURSE_ADMIN_ROLE_ID]

                if role_name:
                    # Add role filter
                    role_id_map = {
                        "course_creator": COURSE_CREATOR_ROLE_ID,
                        "course_reviewer": COURSE_REVIEWER_ROLE_ID,
                        "course_admin": COURSE_ADMIN_ROLE_ID,
                    }
                    if role_name in role_id_map:
                        query += " AND r.id = $" + str(len(params) + 1)
                        params.append(role_id_map[role_name])

                members = await conn.fetch(query, *params)

                return [dict(row) for row in members]

        except Exception as e:
            logger.error(f"Error getting workspace course members: {e}")
            return []

    async def get_course_role_details(self) -> dict:
        """Get all course roles and their permissions"""
        try:
            async with db_manager.postgres_pool.acquire() as conn:
                # Get all learning permissions
                permissions = await conn.fetch(
                    """SELECT action, description FROM auth.permissions
                       WHERE module_id = $1
                       ORDER BY action""",
                    LEARNING_MODULE_ID
                )

                perm_dict = {f"learning:{p['action']}": p['description'] for p in permissions}

                # Get course roles with their permissions
                roles_data = await conn.fetch("""
                    SELECT r.id, r.name, r.description,
                           ARRAY_AGG(p.action ORDER BY p.action) as permissions
                    FROM auth.roles r
                    JOIN auth.role_permissions rp ON r.id = rp.role_id
                    JOIN auth.permissions p ON rp.permission_id = p.id
                    WHERE r.id IN ($1, $2, $3)
                    AND p.module_id = $4
                    GROUP BY r.id, r.name, r.description
                    ORDER BY r.name
                """, COURSE_CREATOR_ROLE_ID, COURSE_REVIEWER_ROLE_ID,
                    COURSE_ADMIN_ROLE_ID, LEARNING_MODULE_ID)

                roles_dict = {}
                for row in roles_data:
                    role_name = row["name"]
                    # Convert action names to full permission strings
                    full_permissions = [f"learning:{action}" for action in row["permissions"]]
                    roles_dict[role_name] = {
                        "id": str(row["id"]),
                        "name": role_name,
                        "description": row["description"],
                        "permissions": full_permissions
                    }

                return {
                    "roles": roles_dict,
                    "permissions": perm_dict
                }

        except Exception as e:
            logger.error(f"Error getting course role details: {e}")
            return {"roles": {}, "permissions": {}}


# Singleton instance
course_rbac_service = CourseRBACService()
