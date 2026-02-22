"""
Entity Types - Dynamically loaded from YAML configuration.

This module provides a unified interface for entity types, loading
definitions from the YAML configuration files at runtime.

Usage:
    from openfinance.domain.types import EntityType, get_entity_label
    
    # Get entity type
    entity_type = EntityType.COMPANY
    
    # Get label
    label = get_entity_label("company")  # "公司"
    
    # Get all types
    all_types = get_all_entity_types()
"""

from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path

from openfinance.domain.metadata.loader import MetadataLoader
from openfinance.domain.metadata.registry import EntityTypeRegistry, EntityTypeDefinition


_config_dir = Path(__file__).parent.parent / "metadata" / "config"
_loader = MetadataLoader(_config_dir)


def _ensure_loaded() -> None:
    """Ensure entity types are loaded from YAML."""
    if not EntityTypeRegistry.get_type_ids():
        _loader.load_entity_types()


_ensure_loaded()


def _create_entity_enum() -> type[Enum]:
    """Dynamically create EntityType enum from loaded types."""
    type_names = EntityTypeRegistry.get_type_ids()
    return Enum("EntityType", {name.upper(): name for name in type_names})


EntityType = _create_entity_enum()


def get_entity_type(type_str: str) -> Optional[EntityType]:
    """Get EntityType from string, returns None if invalid."""
    try:
        return EntityType[type_str.upper()]
    except KeyError:
        return None


def get_entity_label(entity_type: str | EntityType) -> str:
    """Get Chinese display name for entity type."""
    type_str = entity_type.value if isinstance(entity_type, EntityType) else entity_type
    definition = EntityTypeRegistry.get(type_str)
    return definition.display_name if definition else type_str


def get_entity_description(entity_type: str | EntityType) -> str:
    """Get description for entity type."""
    type_str = entity_type.value if isinstance(entity_type, EntityType) else entity_type
    definition = EntityTypeRegistry.get(type_str)
    return definition.description if definition else ""


def is_valid_entity_type(type_str: str) -> bool:
    """Check if entity type is valid."""
    return EntityTypeRegistry.exists(type_str)


def get_all_entity_types() -> List[str]:
    """Get all valid entity type names."""
    return EntityTypeRegistry.get_type_ids()


def get_entity_types_with_labels() -> Dict[str, str]:
    """Get all entity types with their Chinese labels."""
    result = {}
    for type_id in EntityTypeRegistry.get_type_ids():
        definition = EntityTypeRegistry.get(type_id)
        result[type_id] = definition.display_name if definition else type_id
    return result


def get_entity_definition(entity_type: str | EntityType) -> Optional[EntityTypeDefinition]:
    """Get full entity type definition from registry."""
    type_str = entity_type.value if isinstance(entity_type, EntityType) else entity_type
    return EntityTypeRegistry.get(type_str)


VALID_ENTITY_TYPES = get_all_entity_types()
ENTITY_TYPE_LABELS = get_entity_types_with_labels()
