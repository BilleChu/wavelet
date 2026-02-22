"""
Unified Type Definitions for OpenFinance.

This module provides a single source of truth for all type definitions,
dynamically loaded from YAML configuration files.

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    YAML Configuration                        │
│         (domain/metadata/config/*.yaml)                      │
│         - entity_types.yaml                                  │
│         - relation_types.yaml                                │
│         - factor_types.yaml                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Metadata Loader                           │
│         (domain/metadata/loader.py)                          │
│         - Parse YAML files                                   │
│         - Populate registries                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Type Access Layer                         │
│         (domain/types/)                                      │
│         - entity.py: EntityType enum + helpers               │
│         - relation.py: RelationType enum + helpers           │
│         - converters.py: Type conversion utilities           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Consumers                                 │
│         - ORM models (datacenter/models/orm.py)              │
│         - Pydantic models (domain/models/)                   │
│         - API routes (api/routes/)                           │
└─────────────────────────────────────────────────────────────┘

Usage:
    from openfinance.domain.types import EntityType, RelationType
    from openfinance.domain.types import get_entity_label, to_pydantic
    
    # Entity types (from YAML)
    entity_type = EntityType.COMPANY
    label = get_entity_label("company")  # "公司"
    
    # Relation types (from YAML)
    relation_type = RelationType.BELONGS_TO
    label = get_relation_label("belongs_to")  # "属于"
    
    # Type conversion
    pydantic_obj = to_pydantic(data, MyModel)
"""

from openfinance.domain.models.enums import (
    DataSource,
    DataType,
    DataCategory,
    TaskStatus,
    TaskPriority,
    AlertSeverity,
    AlertStatus,
    FactorType,
    StrategyType,
    MessageRole,
    ToolState,
    IntentType,
    PlatformType,
    UserRole,
)
from openfinance.domain.models.chat import MessageType
from openfinance.domain.models.tool import ToolCategory

from .entity import (
    EntityType,
    VALID_ENTITY_TYPES,
    ENTITY_TYPE_LABELS,
    get_entity_type,
    get_entity_label,
    get_entity_description,
    is_valid_entity_type,
    get_all_entity_types,
    get_entity_types_with_labels,
    get_entity_definition,
)

from .relation import (
    RelationType,
    VALID_RELATION_TYPES,
    RELATION_TYPE_LABELS,
    get_relation_type,
    get_relation_label,
    get_relation_description,
    is_valid_relation_type,
    get_all_relation_types,
    get_relation_types_with_labels,
    get_relation_definition,
    is_valid_relation_pair,
    get_valid_relations_for_source,
)

from .converters import (
    to_pydantic,
    to_orm,
    to_dict,
    convert_entity,
    EntityConverter,
    entity_converter,
)

__all__ = [
    "DataSource",
    "DataType",
    "DataCategory",
    "TaskStatus",
    "TaskPriority",
    "AlertSeverity",
    "AlertStatus",
    "FactorType",
    "StrategyType",
    "MessageRole",
    "MessageType",
    "ToolCategory",
    "ToolState",
    "IntentType",
    "PlatformType",
    "UserRole",
    "EntityType",
    "VALID_ENTITY_TYPES",
    "ENTITY_TYPE_LABELS",
    "get_entity_type",
    "get_entity_label",
    "get_entity_description",
    "is_valid_entity_type",
    "get_all_entity_types",
    "get_entity_types_with_labels",
    "get_entity_definition",
    "RelationType",
    "VALID_RELATION_TYPES",
    "RELATION_TYPE_LABELS",
    "get_relation_type",
    "get_relation_label",
    "get_relation_description",
    "is_valid_relation_type",
    "get_all_relation_types",
    "get_relation_types_with_labels",
    "get_relation_definition",
    "is_valid_relation_pair",
    "get_valid_relations_for_source",
    "to_pydantic",
    "to_orm",
    "to_dict",
    "convert_entity",
    "EntityConverter",
    "entity_converter",
]
