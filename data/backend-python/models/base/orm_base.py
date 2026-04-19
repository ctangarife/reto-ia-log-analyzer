"""
Base SQLAlchemy para entidades de base de datos.

Todas las entidades ORM heredan de OrmBase.
"""
from sqlalchemy.orm import DeclarativeBase


class OrmBase(DeclarativeBase):
    """Base declarativa para todos los modelos ORM (PostgreSQL)."""
    pass
