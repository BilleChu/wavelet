"""
OpenFinance Metadata Package.

Provides metadata-driven architecture for:
- Entity types
- Relation types
- Factor types
- Strategy types
- Tool types
- Data source types
"""

from .base import (
    MetadataDefinition,
    PropertyDefinition,
    PropertyType,
    Severity,
    ValidationResult,
)
from .registry import (
    MetadataRegistry,
    EntityTypeRegistry,
    RelationTypeRegistry,
    FactorTypeRegistry,
    StrategyTypeRegistry,
    ToolTypeRegistry,
    DataSourceRegistry,
    initialize_registries,
)
from .loader import MetadataLoader
from .compat import (
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
    ENTITY_TYPE_LABELS,
    RELATION_TYPE_LABELS,
    get_entity_type_label,
    get_relation_type_label,
    is_valid_entity_type,
    is_valid_relation_type,
    LegacyEntityAdapter,
    LegacyRelationAdapter,
)

__all__ = [
    # Base
    "MetadataDefinition",
    "PropertyDefinition",
    "PropertyType",
    "Severity",
    "ValidationResult",
    # Registry
    "MetadataRegistry",
    "EntityTypeRegistry",
    "RelationTypeRegistry",
    "FactorTypeRegistry",
    "StrategyTypeRegistry",
    "ToolTypeRegistry",
    "DataSourceRegistry",
    "initialize_registries",
    # Loader
    "MetadataLoader",
    # Compatibility
    "VALID_ENTITY_TYPES",
    "VALID_RELATION_TYPES",
    "ENTITY_TYPE_LABELS",
    "RELATION_TYPE_LABELS",
    "get_entity_type_label",
    "get_relation_type_label",
    "is_valid_entity_type",
    "is_valid_relation_type",
    "LegacyEntityAdapter",
    "LegacyRelationAdapter",
]
