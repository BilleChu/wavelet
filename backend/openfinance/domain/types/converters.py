"""
Type Converters for OpenFinance.

Provides conversion utilities between different representations:
- ORM models (SQLAlchemy)
- Pydantic models
- Dict/JSON
- YAML definitions

Usage:
    from openfinance.domain.types import to_pydantic, to_orm, to_dict
"""

from typing import Any, Dict, Type, TypeVar, Optional
from datetime import datetime

T = TypeVar("T")


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert any object to dictionary.
    
    Handles:
    - Pydantic models: model_dump()
    - SQLAlchemy models: __dict__ with _sa_instance_state removal
    - Enums: .value
    - datetime: isoformat()
    - Others: dict() or str()
    """
    if obj is None:
        return None
    
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    
    if hasattr(obj, "__dict__"):
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        return {k: to_dict(v) for k, v in data.items()}
    
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    
    if isinstance(obj, (list, tuple)):
        return [to_dict(item) for item in obj]
    
    if hasattr(obj, "value"):
        return obj.value
    
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    return obj


def to_pydantic(data: Dict[str, Any], model_class: Type[T]) -> T:
    """Convert dictionary to Pydantic model.
    
    Args:
        data: Dictionary with model data
        model_class: Pydantic model class
        
    Returns:
        Instance of model_class
    """
    return model_class(**data)


def to_orm(data: Dict[str, Any], orm_class: Type[T]) -> T:
    """Convert dictionary to SQLAlchemy ORM model.
    
    Args:
        data: Dictionary with model data
        orm_class: SQLAlchemy model class
        
    Returns:
        Instance of orm_class
    """
    return orm_class(**data)


def convert_entity(
    source: Any,
    target_class: Type[T],
    field_mapping: Optional[Dict[str, str]] = None
) -> T:
    """Convert entity between different representations with field mapping.
    
    Args:
        source: Source object (ORM, Pydantic, or dict)
        target_class: Target class
        field_mapping: Optional field name mapping {source_field: target_field}
        
    Returns:
        Instance of target_class
    """
    data = to_dict(source)
    
    if field_mapping:
        data = {
            field_mapping.get(k, k): v
            for k, v in data.items()
        }
    
    return target_class(**data)


class EntityConverter:
    """Entity converter with caching and validation."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def orm_to_pydantic(
        self,
        orm_obj: Any,
        pydantic_class: Type[T],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> T:
        """Convert ORM model to Pydantic model."""
        return convert_entity(orm_obj, pydantic_class, field_mapping)
    
    def pydantic_to_orm(
        self,
        pydantic_obj: Any,
        orm_class: Type[T],
        field_mapping: Optional[Dict[str, str]] = None
    ) -> T:
        """Convert Pydantic model to ORM model."""
        return convert_entity(pydantic_obj, orm_class, field_mapping)
    
    def dict_to_pydantic(
        self,
        data: Dict[str, Any],
        pydantic_class: Type[T]
    ) -> T:
        """Convert dictionary to Pydantic model."""
        return pydantic_class(**data)
    
    def dict_to_orm(
        self,
        data: Dict[str, Any],
        orm_class: Type[T]
    ) -> T:
        """Convert dictionary to ORM model."""
        return orm_class(**data)


entity_converter = EntityConverter()
