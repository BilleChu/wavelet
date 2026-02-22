"""
Relation Types - Dynamically loaded from YAML configuration.

This module provides a unified interface for relation types, loading
definitions from the YAML configuration files at runtime.

Usage:
    from openfinance.domain.types import RelationType, get_relation_label
    
    # Get relation type
    relation_type = RelationType.BELONGS_TO
    
    # Get label
    label = get_relation_label("belongs_to")  # "属于"
    
    # Get all types
    all_types = get_all_relation_types()
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path

from openfinance.domain.metadata.loader import MetadataLoader
from openfinance.domain.metadata.registry import RelationTypeRegistry, RelationTypeDefinition


_config_dir = Path(__file__).parent.parent / "metadata" / "config"
_loader = MetadataLoader(_config_dir)


def _ensure_loaded() -> None:
    """Ensure relation types are loaded from YAML."""
    if not RelationTypeRegistry.get_type_ids():
        _loader.load_relation_types()


_ensure_loaded()


def _create_relation_enum() -> type[Enum]:
    """Dynamically create RelationType enum from loaded types."""
    type_names = RelationTypeRegistry.get_type_ids()
    return Enum("RelationType", {name.upper(): name for name in type_names})


RelationType = _create_relation_enum()


def get_relation_type(type_str: str) -> Optional[RelationType]:
    """Get RelationType from string, returns None if invalid."""
    try:
        return RelationType[type_str.upper()]
    except KeyError:
        return None


def get_relation_label(relation_type: str | RelationType) -> str:
    """Get Chinese display name for relation type."""
    type_str = relation_type.value if isinstance(relation_type, RelationType) else relation_type
    definition = RelationTypeRegistry.get(type_str)
    return definition.display_name if definition else type_str


def get_relation_description(relation_type: str | RelationType) -> str:
    """Get description for relation type."""
    type_str = relation_type.value if isinstance(relation_type, RelationType) else relation_type
    definition = RelationTypeRegistry.get(type_str)
    return definition.description if definition else ""


def is_valid_relation_type(type_str: str) -> bool:
    """Check if relation type is valid."""
    return RelationTypeRegistry.exists(type_str)


def get_all_relation_types() -> List[str]:
    """Get all valid relation type names."""
    return RelationTypeRegistry.get_type_ids()


def get_relation_types_with_labels() -> Dict[str, str]:
    """Get all relation types with their Chinese labels."""
    result = {}
    for type_id in RelationTypeRegistry.get_type_ids():
        definition = RelationTypeRegistry.get(type_id)
        result[type_id] = definition.display_name if definition else type_id
    return result


def get_relation_definition(relation_type: str | RelationType) -> Optional[RelationTypeDefinition]:
    """Get full relation type definition from registry."""
    type_str = relation_type.value if isinstance(relation_type, RelationType) else relation_type
    return RelationTypeRegistry.get(type_str)


def is_valid_relation_pair(source_type: str, relation_type: str, target_type: str) -> bool:
    """Check if relation pair is valid based on source_types and target_types."""
    definition = RelationTypeRegistry.get(relation_type)
    if not definition:
        return False
    
    source_valid = source_type in definition.source_types
    target_valid = target_type in definition.target_types
    
    return source_valid and target_valid


def get_valid_relations_for_source(source_type: str) -> List[Tuple[str, List[str]]]:
    """Get valid (relation_type, target_types) pairs for a source type."""
    result = []
    for type_id in RelationTypeRegistry.get_type_ids():
        definition = RelationTypeRegistry.get(type_id)
        if definition and source_type in definition.source_types:
            result.append((type_id, definition.target_types))
    return result


VALID_RELATION_TYPES = get_all_relation_types()
RELATION_TYPE_LABELS = get_relation_types_with_labels()
