"""
Fábrica para conversión Project ORM/dict <-> esquemas API.
"""
from typing import Any, Dict, List

from models.base.abstract_factory import AbstractModelFactory
from models.schemas.rbac import ProjectResponse, ProjectWithRole


class ProjectModelFactory(AbstractModelFactory):
    """Convierte entidad Project (ORM o dict) en ProjectResponse o ProjectWithRole."""

    def to_response(self, entity: Any, role: str | None = None) -> Any:
        role = role if role is not None else (entity.get("role") if isinstance(entity, dict) else getattr(entity, "role", None))
        if hasattr(entity, "__dict__") and not isinstance(entity, dict):
            data = {
                "id": entity.id,
                "workspace_id": entity.workspace_id,
                "name": entity.name,
                "slug": entity.slug,
                "description": getattr(entity, "description", None),
                "is_active": entity.is_active,
                "created_by": getattr(entity, "created_by", None),
                "created_at": entity.created_at,
                "updated_at": entity.updated_at,
            }
        else:
            data = dict(entity)
            if "project_id" in data and "id" not in data:
                data["id"] = data["project_id"]
        if role is not None:
            data["role"] = role
            return ProjectWithRole(**data)
        return ProjectResponse(**data)

    def to_list_response(self, entities: List[Any]) -> List[Any]:
        result = []
        for e in entities:
            role = e.get("role", None) if isinstance(e, dict) else getattr(e, "role", None)
            result.append(self.to_response(e, role=role))
        return result

    def from_create(self, dto: Any) -> Dict[str, Any]:
        return dto.model_dump(exclude_unset=True)
