"""
Abstract Factory: contrato para fábricas que convierten entre ORM y esquemas API.

Cada fábrica concreta (UserModelFactory, WorkspaceModelFactory, etc.) implementa
estos métodos para su entidad, centralizando la lógica de conversión.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar

# Tipos genéricos: Entity = ORM, ResponseSchema = Pydantic response, CreateSchema = Pydantic create
EntityT = TypeVar("EntityT")
ResponseT = TypeVar("ResponseT")
CreateT = TypeVar("CreateT")


class AbstractModelFactory(ABC):
    """
    Interfaz abstracta para fábricas que construyen esquemas API a partir de
    entidades ORM y viceversa (datos para crear/actualizar).
    """

    @abstractmethod
    def to_response(self, entity: Any) -> Any:
        """
        Convierte una entidad ORM en el esquema de respuesta API.

        Args:
            entity: Instancia del modelo ORM (ej. User, Workspace, Project).

        Returns:
            Instancia del schema Pydantic de respuesta (ej. UserResponse, WorkspaceResponse).
        """
        ...

    def to_list_response(self, entities: List[Any]) -> List[Any]:
        """
        Convierte una lista de entidades ORM en lista de esquemas de respuesta.
        Por defecto aplica to_response a cada elemento; las fábricas pueden sobrescribir.
        """
        return [self.to_response(e) for e in entities]

    def from_create(self, dto: Any) -> Dict[str, Any]:
        """
        Convierte un DTO de creación (ej. UserCreate, WorkspaceCreate) en un
        diccionario apto para insertar en BD o para construir entidad ORM.

        Args:
            dto: Schema Pydantic de creación.

        Returns:
            Diccionario con campos listos para ORM/BD (sin password en claro si se hashea aparte).
        """
        return dto.model_dump(exclude_unset=True)
