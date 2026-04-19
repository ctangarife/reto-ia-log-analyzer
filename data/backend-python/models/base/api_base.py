"""
Base Pydantic para esquemas de API (request/response).

Funcionalidad común: configuración para crear respuestas desde ORM (from_attributes),
y punto único para extender validadores o configuración global de esquemas.
"""
from pydantic import BaseModel, ConfigDict


class ApiSchemaBase(BaseModel):
    """
    Base para esquemas de API que se construyen desde entidades ORM
    o comparten configuración común.
    """
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )
