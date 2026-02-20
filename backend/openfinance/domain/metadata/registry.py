"""
Metadata registries for different types.

Provides specialized registries for:
- Entity types
- Relation types
- Factor types
- Strategy types
- Tool types
- Data source types
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .base import (
    MetadataDefinition,
    MetadataRegistry,
    MetadataCategory,
    PropertyDefinition,
    QualityRule,
    ValidationResult,
)

logger = logging.getLogger(__name__)


# ============ Entity Type ============

@dataclass
class RelationConstraint:
    """Relation constraint for entity types."""
    target_types: list[str]
    cardinality: str = "many-to-many"
    properties: dict[str, PropertyDefinition] = field(default_factory=dict)


@dataclass
class EntityTypeDefinition(MetadataDefinition["EntityTypeDefinition"]):
    """Entity type definition."""
    
    relations: dict[str, RelationConstraint] = field(default_factory=dict)
    searchable_fields: list[str] = field(default_factory=list)
    default_sort: str | None = None
    list_fields: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "relations": {
                k: {
                    "target_types": v.target_types,
                    "cardinality": v.cardinality,
                }
                for k, v in self.relations.items()
            },
            "searchable_fields": self.searchable_fields,
            "default_sort": self.default_sort,
            "list_fields": self.list_fields,
        })
        return result


class EntityTypeRegistry(MetadataRegistry[EntityTypeDefinition]):
    """Entity type registry."""
    
    _types: dict[str, EntityTypeDefinition] = {}
    
    @classmethod
    def list_by_category(cls, category: MetadataCategory) -> list[EntityTypeDefinition]:
        return [t for t in cls._types.values() if t.category == category]
    
    @classmethod
    def get_searchable_types(cls) -> list[str]:
        return [
            t.type_id for t in cls._types.values() 
            if t.searchable_fields
        ]
    
    @classmethod
    def get_quality_check_types(cls) -> list[str]:
        return [
            t.type_id for t in cls._types.values() 
            if t.quality_rules
        ]


# ============ Relation Type ============

@dataclass
class RelationTypeDefinition(MetadataDefinition["RelationTypeDefinition"]):
    """Relation type definition."""
    
    source_types: list[str] = field(default_factory=list)
    target_types: list[str] = field(default_factory=list)
    symmetric: bool = False
    unique_per_source_target: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "source_types": self.source_types,
            "target_types": self.target_types,
            "symmetric": self.symmetric,
            "unique_per_source_target": self.unique_per_source_target,
        })
        return result
    
    def is_valid_for(
        self, 
        source_type: str, 
        target_type: str
    ) -> bool:
        source_valid = not self.source_types or source_type in self.source_types
        target_valid = not self.target_types or target_type in self.target_types
        return source_valid and target_valid


class RelationTypeRegistry(MetadataRegistry[RelationTypeDefinition]):
    """Relation type registry."""
    
    _types: dict[str, RelationTypeDefinition] = {}
    
    @classmethod
    def get_valid_relations(
        cls,
        source_type: str,
        target_type: str,
    ) -> list[RelationTypeDefinition]:
        return [
            r for r in cls._types.values()
            if r.is_valid_for(source_type, target_type)
        ]
    
    @classmethod
    def get_relations_for_source(
        cls,
        source_type: str,
    ) -> list[RelationTypeDefinition]:
        return [
            r for r in cls._types.values()
            if not r.source_types or source_type in r.source_types
        ]


# ============ Factor Type ============

@dataclass
class FactorParameter:
    """Factor parameter definition."""
    name: str
    type: str = "float"
    default: Any = None
    min: float | None = None
    max: float | None = None
    description: str = ""


@dataclass
class FactorTypeDefinition(MetadataDefinition["FactorTypeDefinition"]):
    """Factor type definition."""
    
    factor_category: str = "technical"
    formula: str | None = None
    parameters: dict[str, FactorParameter] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    output_type: str = "float"
    normalize_method: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "factor_category": self.factor_category,
            "formula": self.formula,
            "parameters": {
                k: {
                    "name": v.name,
                    "type": v.type,
                    "default": v.default,
                    "min": v.min,
                    "max": v.max,
                    "description": v.description,
                }
                for k, v in self.parameters.items()
            },
            "dependencies": self.dependencies,
            "output_type": self.output_type,
            "normalize_method": self.normalize_method,
        })
        return result


class FactorTypeRegistry(MetadataRegistry[FactorTypeDefinition]):
    """Factor type registry."""
    
    _types: dict[str, FactorTypeDefinition] = {}
    
    @classmethod
    def list_by_category(cls, category: str) -> list[FactorTypeDefinition]:
        return [
            f for f in cls._types.values() 
            if f.factor_category == category
        ]
    
    @classmethod
    def get_dependencies(cls, factor_id: str) -> list[str]:
        factor = cls.get(factor_id)
        return factor.dependencies if factor else []


# ============ Strategy Type ============

@dataclass
class StrategyParameter:
    """Strategy parameter definition."""
    name: str
    type: str = "float"
    default: Any = None
    min: float | None = None
    max: float | None = None
    description: str = ""


@dataclass
class StrategyTypeDefinition(MetadataDefinition["StrategyTypeDefinition"]):
    """Strategy type definition."""
    
    strategy_category: str = "quant"
    parameters: dict[str, StrategyParameter] = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    risk_rules: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "strategy_category": self.strategy_category,
            "parameters": {
                k: {
                    "name": v.name,
                    "type": v.type,
                    "default": v.default,
                    "description": v.description,
                }
                for k, v in self.parameters.items()
            },
            "signals": self.signals,
            "risk_rules": self.risk_rules,
        })
        return result


class StrategyTypeRegistry(MetadataRegistry[StrategyTypeDefinition]):
    """Strategy type registry."""
    
    _types: dict[str, StrategyTypeDefinition] = {}
    
    @classmethod
    def list_by_category(cls, category: str) -> list[StrategyTypeDefinition]:
        return [
            s for s in cls._types.values() 
            if s.strategy_category == category
        ]


# ============ Tool Type ============

@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""


@dataclass
class ToolTypeDefinition(MetadataDefinition["ToolTypeDefinition"]):
    """Tool type definition."""
    
    tool_category: str = "query"
    parameters: dict[str, ToolParameter] = field(default_factory=dict)
    returns: str = "object"
    timeout_ms: int = 30000
    cache_ttl: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "tool_category": self.tool_category,
            "parameters": {
                k: {
                    "name": v.name,
                    "type": v.type,
                    "required": v.required,
                    "default": v.default,
                    "description": v.description,
                }
                for k, v in self.parameters.items()
            },
            "returns": self.returns,
            "timeout_ms": self.timeout_ms,
            "cache_ttl": self.cache_ttl,
        })
        return result
    
    def to_openai_tool_schema(self) -> dict[str, Any]:
        properties = {}
        required = []
        
        for name, param in self.parameters.items():
            properties[name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(name)
        
        return {
            "type": "function",
            "function": {
                "name": self.type_id,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolTypeRegistry(MetadataRegistry[ToolTypeDefinition]):
    """Tool type registry."""
    
    _types: dict[str, ToolTypeDefinition] = {}
    
    @classmethod
    def list_by_category(cls, category: str) -> list[ToolTypeDefinition]:
        return [
            t for t in cls._types.values() 
            if t.tool_category == category
        ]
    
    @classmethod
    def get_openai_tools_schema(cls) -> list[dict[str, Any]]:
        return [
            t.to_openai_tool_schema() 
            for t in cls._types.values()
        ]


# ============ Data Source ============

@dataclass
class DataSourceDefinition(MetadataDefinition["DataSourceDefinition"]):
    """Data source definition."""
    
    source_type: str = "api"
    endpoint: str | None = None
    auth_type: str | None = None
    rate_limit: int = 100
    timeout_ms: int = 30000
    data_types: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "source_type": self.source_type,
            "endpoint": self.endpoint,
            "auth_type": self.auth_type,
            "rate_limit": self.rate_limit,
            "timeout_ms": self.timeout_ms,
            "data_types": self.data_types,
        })
        return result


class DataSourceRegistry(MetadataRegistry[DataSourceDefinition]):
    """Data source registry."""
    
    _types: dict[str, DataSourceDefinition] = {}
    
    @classmethod
    def get_for_data_type(cls, data_type: str) -> list[DataSourceDefinition]:
        return [
            s for s in cls._types.values()
            if data_type in s.data_types
        ]


# ============ Initialization ============

def initialize_registries(config_dir: Path | None = None) -> None:
    """Initialize all registries from config files."""
    from .loader import MetadataLoader
    
    if config_dir is None:
        config_dir = Path(__file__).parent / "config"
    
    loader = MetadataLoader(config_dir)
    
    loader.load_entity_types()
    loader.load_relation_types()
    loader.load_factor_types()
    loader.load_strategy_types()
    loader.load_tool_types()
    loader.load_data_sources()
    
    logger.info(
        f"Initialized registries: "
        f"entities={len(EntityTypeRegistry.list_all())}, "
        f"relations={len(RelationTypeRegistry.list_all())}, "
        f"factors={len(FactorTypeRegistry.list_all())}, "
        f"strategies={len(StrategyTypeRegistry.list_all())}, "
        f"tools={len(ToolTypeRegistry.list_all())}, "
        f"sources={len(DataSourceRegistry.list_all())}"
    )
