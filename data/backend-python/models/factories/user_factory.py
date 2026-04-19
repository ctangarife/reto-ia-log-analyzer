"""
Fábrica para conversión User ORM/dict <-> esquemas API.
"""
from typing import Any, Dict, List

from models.base.abstract_factory import AbstractModelFactory
from models.schemas.rbac import UserResponse


class UserModelFactory(AbstractModelFactory):
    """Convierte entidad User (ORM o dict) en UserResponse."""

    def to_response(self, entity: Any) -> UserResponse:
        if hasattr(entity, "__dict__") and not isinstance(entity, dict):
            data = {
                "id": entity.id,
                "email": entity.email,
                "username": entity.username,
                "full_name": getattr(entity, "full_name", None),
                "is_active": entity.is_active,
                "is_super_admin": entity.is_super_admin,
                "last_login": getattr(entity, "last_login", None),
                "created_at": entity.created_at,
                "updated_at": entity.updated_at,
            }
        else:
            data = dict(entity)
            if "user_id" in data and "id" not in data:
                data["id"] = data["user_id"]
        return UserResponse(**data)

    def to_list_response(self, entities: List[Any]) -> List[UserResponse]:
        return [self.to_response(e) for e in entities]

    def from_create(self, dto: Any) -> Dict[str, Any]:
        return dto.model_dump(exclude_unset=True, exclude={"password"})
