"""
Data Model Framework for Data Center.

Provides a generic, business-agnostic framework for:
- Model registration and discovery
- Model transformation and mapping
- Schema management and validation
- Version control and compatibility

Design Principles:
1. Framework contains NO business logic
2. All business models register via plugin mechanism
3. Provides standardized model lifecycle management
4. High cohesion, low coupling

Note: DataValidator, ValidationRule, and ValidationResult are imported from
quality/validator.py to avoid code duplication.
"""

from .registry import (
    ModelRegistry,
    ModelMetadata,
    ModelCapability,
    register_model,
)
from .transformer import (
    ModelTransformer,
    FieldMapping,
    ADSORMTransformer,
    create_orm_to_ads_transformer,
    register_ads_orm_mapping,
)

__all__ = [
    "ModelRegistry",
    "ModelMetadata",
    "ModelCapability",
    "register_model",
    "ModelTransformer",
    "FieldMapping",
    "ADSORMTransformer",
    "create_orm_to_ads_transformer",
    "register_ads_orm_mapping",
]
