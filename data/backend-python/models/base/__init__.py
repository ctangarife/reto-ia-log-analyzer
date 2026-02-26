"""
Clases base y contrato Abstract Factory para la capa de modelos.

- ApiSchemaBase: base Pydantic para esquemas de API (respuestas desde ORM).
- OrmBase: base SQLAlchemy para entidades de BD.
- AbstractModelFactory: interfaz para fábricas que convierten ORM <-> API.
"""
from models.base.api_base import ApiSchemaBase
from models.base.orm_base import OrmBase
from models.base.abstract_factory import AbstractModelFactory

__all__ = ["ApiSchemaBase", "OrmBase", "AbstractModelFactory"]
