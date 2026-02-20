"""
Model Transformer - Automatic conversion between ADS and ORM models.

Provides automatic transformation between:
- ADS models (Pydantic) <-> ORM models (SQLAlchemy)
- Dict <-> ADS models
- Custom transformations with field mappings
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel

from openfinance.datacenter.models.framework.registry import (
    ModelRegistry,
    ModelMetadata,
)

logger = logging.getLogger(__name__)

S = TypeVar("S")
T = TypeVar("T")


@dataclass
class FieldMapping:
    """
    Field mapping configuration for transformation.
    
    Attributes:
        source_field: Field name in source model
        target_field: Field name in target model
        transform: Optional transformation function
        default: Default value if source field is None
        required: Whether the field is required
    """
    source_field: str
    target_field: str
    transform: Callable[[Any], Any] | None = None
    default: Any = None
    required: bool = False


class ModelTransformer(Generic[S, T]):
    """
    Automatic model transformer between ADS and ORM models.
    
    Features:
    - Automatic field mapping
    - Type conversion
    - Custom transformation functions
    - Nested model support
    
    Usage:
        transformer = ModelTransformer(
            source_type=StockDailyQuoteModel,
            target_type=ADSKLineModel,
            field_mappings=[
                FieldMapping("turnover_rate", "turnover"),
                FieldMapping("collected_at", "updated_at"),
            ],
        )
        
        # Transform ORM to ADS
        ads_model = transformer.transform(orm_object)
        
        # Transform list
        ads_models = transformer.transform_list(orm_objects)
    """
    
    def __init__(
        self,
        source_type: type[S],
        target_type: type[T],
        field_mappings: list[FieldMapping] | None = None,
        exclude_fields: list[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize transformer.
        
        Args:
            source_type: Source model class
            target_type: Target model class
            field_mappings: Custom field mappings
            exclude_fields: Fields to exclude from transformation
            extra_fields: Extra fields to add to target
        """
        self.source_type = source_type
        self.target_type = target_type
        self.field_mappings = field_mappings or []
        self.exclude_fields = exclude_fields or []
        self.extra_fields = extra_fields or {}
        
        self._mapping_dict: dict[str, FieldMapping] = {
            m.source_field: m for m in self.field_mappings
        }
        
        self._build_auto_mappings()
    
    def _build_auto_mappings(self) -> None:
        """Build automatic field mappings for unmapped fields."""
        source_fields = self._get_fields(self.source_type)
        target_fields = self._get_fields(self.target_type)
        
        if not source_fields and self.source_type is dict:
            source_fields = target_fields
        
        for field_name in source_fields:
            if field_name in self._mapping_dict:
                continue
            if field_name in self.exclude_fields:
                continue
            if field_name in target_fields:
                self._mapping_dict[field_name] = FieldMapping(
                    source_field=field_name,
                    target_field=field_name,
                )
    
    def _get_fields(self, model_type: type) -> set[str]:
        """Get field names from a model type."""
        if hasattr(model_type, "model_fields"):
            return set(model_type.model_fields.keys())
        elif hasattr(model_type, "__table__"):
            return set(model_type.__table__.columns.keys())
        elif hasattr(model_type, "__dataclass_fields__"):
            return set(model_type.__dataclass_fields__.keys())
        elif model_type is dict:
            return set()
        return set()
    
    def _get_source_fields(self, source: Any) -> set[str]:
        """Get field names from a source object."""
        if isinstance(source, dict):
            return set(source.keys())
        elif hasattr(source, "model_fields"):
            return set(source.model_fields.keys())
        elif hasattr(source, "__table__"):
            return set(source.__table__.columns.keys())
        elif hasattr(source, "__dataclass_fields__"):
            return set(source.__dataclass_fields__.keys())
        return set()
    
    def _get_field_value(self, obj: Any, field_name: str) -> Any:
        """Get field value from source object."""
        if hasattr(obj, field_name):
            return getattr(obj, field_name)
        elif isinstance(obj, dict):
            return obj.get(field_name)
        return None
    
    def _convert_value(self, value: Any, target_type: type | None = None) -> Any:
        """Convert value to appropriate type."""
        if value is None:
            return None
        
        if isinstance(value, Decimal):
            return float(value)
        
        if isinstance(value, (date, datetime)):
            return value
        
        return value
    
    def transform(self, source: S) -> T:
        """
        Transform source object to target type.
        
        Args:
            source: Source object (ORM model, dict, or Pydantic model)
        
        Returns:
            Target model instance
        """
        data: dict[str, Any] = {}
        
        source_fields = self._get_source_fields(source)
        
        for mapping in self._mapping_dict.values():
            if mapping.source_field not in source_fields and mapping.default is None:
                continue
            
            source_value = self._get_field_value(source, mapping.source_field)
            
            if source_value is None:
                if mapping.required:
                    raise ValueError(
                        f"Required field '{mapping.source_field}' is None"
                    )
                source_value = mapping.default
            
            if source_value is not None and mapping.transform:
                source_value = mapping.transform(source_value)
            else:
                source_value = self._convert_value(source_value)
            
            data[mapping.target_field] = source_value
        
        if isinstance(source, dict):
            target_fields = self._get_fields(self.target_type)
            for key, value in source.items():
                if key not in data and key in target_fields:
                    data[key] = self._convert_value(value)
        
        data.update(self.extra_fields)
        
        if hasattr(self.target_type, "model_validate"):
            return self.target_type.model_validate(data)
        else:
            return self.target_type(**data)
    
    def transform_list(self, sources: list[S]) -> list[T]:
        """Transform a list of source objects."""
        return [self.transform(source) for source in sources]
    
    def reverse_transform(self, target: T) -> dict[str, Any]:
        """
        Transform target object back to source-compatible dict.
        
        Useful for creating ORM objects from ADS models.
        
        Args:
            target: Target model instance
        
        Returns:
            Dictionary suitable for creating source model
        """
        data: dict[str, Any] = {}
        
        for mapping in self._mapping_dict.values():
            target_value = self._get_field_value(target, mapping.target_field)
            
            if target_value is not None:
                if mapping.transform:
                    target_value = mapping.transform(target_value)
                else:
                    target_value = self._convert_value(target_value)
            
            data[mapping.source_field] = target_value
        
        return data


class ADSORMTransformer:
    """
    Central transformer manager for ADS <-> ORM conversions.
    
    Uses ModelRegistry to find mappings and transformers.
    
    Usage:
        transformer = ADSORMTransformer()
        
        # ORM to ADS
        ads_kline = transformer.orm_to_ads(orm_quote, ADSKLineModel)
        
        # ADS to ORM dict
        orm_dict = transformer.ads_to_orm_dict(ads_kline, "kline")
    """
    
    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self.registry = registry or ModelRegistry.get_instance()
        self._transformers: dict[tuple[type, type], ModelTransformer] = {}
    
    def get_transformer(
        self,
        source_type: type,
        target_type: type,
    ) -> ModelTransformer:
        """Get or create a transformer between two types."""
        key = (source_type, target_type)
        
        if key not in self._transformers:
            self._transformers[key] = ModelTransformer(
                source_type=source_type,
                target_type=target_type,
            )
        
        return self._transformers[key]
    
    def orm_to_ads(
        self,
        orm_obj: Any,
        ads_type: type[T],
        model_id: str | None = None,
    ) -> T:
        """
        Transform ORM object to ADS model.
        
        Args:
            orm_obj: SQLAlchemy ORM object
            ads_type: Target ADS model type
            model_id: Optional model ID for custom mappings
        
        Returns:
            ADS model instance
        """
        orm_type = type(orm_obj)
        
        field_mappings = []
        if model_id:
            metadata = self.registry.get_metadata(model_id)
            if metadata and metadata.field_mappings:
                field_mappings = [
                    FieldMapping(src, tgt)
                    for src, tgt in metadata.field_mappings.items()
                ]
        
        transformer = ModelTransformer(
            source_type=orm_type,
            target_type=ads_type,
            field_mappings=field_mappings,
        )
        
        return transformer.transform(orm_obj)
    
    def orm_list_to_ads_list(
        self,
        orm_objs: list[Any],
        ads_type: type[T],
        model_id: str | None = None,
    ) -> list[T]:
        """Transform a list of ORM objects to ADS models."""
        return [
            self.orm_to_ads(obj, ads_type, model_id)
            for obj in orm_objs
        ]
    
    def ads_to_orm_dict(
        self,
        ads_obj: BaseModel,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Convert ADS model to dict suitable for ORM creation.
        
        Args:
            ads_obj: ADS model instance
            model_id: Optional model ID for custom mappings
        
        Returns:
            Dictionary with ORM-compatible field names
        """
        data = ads_obj.model_dump(exclude_unset=True)
        
        if model_id:
            metadata = self.registry.get_metadata(model_id)
            if metadata and metadata.field_mappings:
                reverse_mappings = {
                    v: k for k, v in metadata.field_mappings.items()
                }
                
                result = {}
                for key, value in data.items():
                    orm_key = reverse_mappings.get(key, key)
                    result[orm_key] = value
                
                return result
        
        return data


def create_orm_to_ads_transformer(
    orm_model: type,
    ads_model: type,
    field_mappings: dict[str, str] | None = None,
) -> ModelTransformer:
    """
    Factory function to create ORM to ADS transformer.
    
    Args:
        orm_model: SQLAlchemy ORM model class
        ads_model: ADS model class
        field_mappings: Dict mapping ORM field names to ADS field names
    
    Returns:
        Configured ModelTransformer
    
    Example:
        transformer = create_orm_to_ads_transformer(
            orm_model=StockDailyQuoteModel,
            ads_model=ADSKLineModel,
            field_mappings={
                "turnover_rate": "turnover",
                "collected_at": "updated_at",
            },
        )
    """
    mappings = [
        FieldMapping(source_field=src, target_field=tgt)
        for src, tgt in (field_mappings or {}).items()
    ]
    
    return ModelTransformer(
        source_type=orm_model,
        target_type=ads_model,
        field_mappings=mappings,
    )


def register_ads_orm_mapping(
    ads_model: type,
    orm_model: type,
    model_id: str,
    category: str,
    field_mappings: dict[str, str] | None = None,
) -> None:
    """
    Register ADS-ORM mapping in the registry.
    
    Args:
        ads_model: ADS model class
        orm_model: ORM model class
        model_id: Unique model identifier
        category: Model category
        field_mappings: Field name mappings (ORM -> ADS)
    
    Example:
        register_ads_orm_mapping(
            ads_model=ADSKLineModel,
            orm_model=StockDailyQuoteModel,
            model_id="kline",
            category="market",
            field_mappings={
                "turnover_rate": "turnover",
                "collected_at": "updated_at",
            },
        )
    """
    registry = ModelRegistry.get_instance()
    
    registry.register(
        model_class=ads_model,
        category=category,
        model_id=model_id,
        orm_model=orm_model,
        field_mappings=field_mappings,
    )
    
    transformer = create_orm_to_ads_transformer(
        orm_model=orm_model,
        ads_model=ads_model,
        field_mappings=field_mappings,
    )
    
    registry.register_transformer(
        source_model_id=orm_model.__name__,
        target_model_id=model_id,
        transformer=transformer,
    )
