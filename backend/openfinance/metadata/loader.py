"""
Metadata loader for YAML configuration files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .base import (
    PropertyDefinition,
    PropertyType,
    QualityRule,
    Severity,
    MetadataCategory,
)
from .registry import (
    EntityTypeDefinition,
    EntityTypeRegistry,
    RelationTypeDefinition,
    RelationTypeRegistry,
    FactorTypeDefinition,
    FactorTypeRegistry,
    FactorParameter,
    StrategyTypeDefinition,
    StrategyTypeRegistry,
    StrategyParameter,
    ToolTypeDefinition,
    ToolTypeRegistry,
    ToolParameter,
    DataSourceDefinition,
    DataSourceRegistry,
    RelationConstraint,
)

logger = logging.getLogger(__name__)


class MetadataLoader:
    """Load metadata definitions from YAML files."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
    
    def _load_yaml(self, filename: str) -> dict[str, Any]:
        filepath = self.config_dir / filename
        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return data or {}
    
    def _parse_property(self, name: str, data: dict[str, Any]) -> PropertyDefinition:
        return PropertyDefinition(
            type=PropertyType(data.get("type", "string")),
            required=data.get("required", False),
            unique=data.get("unique", False),
            index=data.get("index", False),
            default=data.get("default"),
            description=data.get("description", ""),
            max_length=data.get("max_length"),
            min_length=data.get("min_length"),
            format=data.get("format"),
            min=data.get("min"),
            max=data.get("max"),
            precision=data.get("precision"),
            scale=data.get("scale"),
            values=data.get("values"),
            items=data.get("items"),
        )
    
    def _parse_quality_rule(self, data: dict[str, Any]) -> QualityRule:
        return QualityRule(
            name=data["name"],
            severity=Severity(data.get("severity", "warning")),
            condition=data.get("condition", ""),
            message=data.get("message", ""),
        )
    
    def load_entity_types(self) -> None:
        data = self._load_yaml("entity_types.yaml")
        
        for type_id, type_data in data.get("entity_types", {}).items():
            properties = {
                name: self._parse_property(name, prop)
                for name, prop in type_data.get("properties", {}).items()
            }
            
            relations = {}
            for rel_name, rel_data in type_data.get("relations", {}).items():
                relations[rel_name] = RelationConstraint(
                    target_types=rel_data.get("target_types", []),
                    cardinality=rel_data.get("cardinality", "many-to-many"),
                )
            
            quality_rules = [
                self._parse_quality_rule(r)
                for r in type_data.get("quality_rules", [])
            ]
            
            definition = EntityTypeDefinition(
                type_id=type_id,
                display_name=type_data.get("display_name", type_id),
                category=MetadataCategory(type_data.get("category", "reference")),
                description=type_data.get("description", ""),
                version=type_data.get("version", "1.0.0"),
                extends=type_data.get("extends"),
                properties=properties,
                relations=relations,
                quality_rules=quality_rules,
                searchable_fields=type_data.get("searchable_fields", []),
                default_sort=type_data.get("default_sort"),
                list_fields=type_data.get("list_fields", []),
            )
            
            EntityTypeRegistry.register(definition)
        
        logger.info(f"Loaded {len(EntityTypeRegistry.list_all())} entity types")
    
    def load_relation_types(self) -> None:
        data = self._load_yaml("relation_types.yaml")
        
        for type_id, type_data in data.get("relation_types", {}).items():
            properties = {
                name: self._parse_property(name, prop)
                for name, prop in type_data.get("properties", {}).items()
            }
            
            definition = RelationTypeDefinition(
                type_id=type_id,
                display_name=type_data.get("display_name", type_id),
                category=MetadataCategory(type_data.get("category", "reference")),
                description=type_data.get("description", ""),
                version=type_data.get("version", "1.0.0"),
                properties=properties,
                source_types=type_data.get("source_types", []),
                target_types=type_data.get("target_types", []),
                symmetric=type_data.get("symmetric", False),
                unique_per_source_target=type_data.get("unique_per_source_target", False),
            )
            
            RelationTypeRegistry.register(definition)
        
        logger.info(f"Loaded {len(RelationTypeRegistry.list_all())} relation types")
    
    def load_factor_types(self) -> None:
        data = self._load_yaml("factor_types.yaml")
        
        for type_id, type_data in data.get("factor_types", {}).items():
            parameters = {}
            for name, param in type_data.get("parameters", {}).items():
                parameters[name] = FactorParameter(
                    name=name,
                    type=param.get("type", "float"),
                    default=param.get("default"),
                    min=param.get("min"),
                    max=param.get("max"),
                    description=param.get("description", ""),
                )
            
            definition = FactorTypeDefinition(
                type_id=type_id,
                display_name=type_data.get("display_name", type_id),
                category=MetadataCategory(type_data.get("category", "derived")),
                description=type_data.get("description", ""),
                version=type_data.get("version", "1.0.0"),
                factor_category=type_data.get("factor_category", "technical"),
                formula=type_data.get("formula"),
                parameters=parameters,
                dependencies=type_data.get("dependencies", []),
                output_type=type_data.get("output_type", "float"),
                normalize_method=type_data.get("normalize_method"),
            )
            
            FactorTypeRegistry.register(definition)
        
        logger.info(f"Loaded {len(FactorTypeRegistry.list_all())} factor types")
    
    def load_strategy_types(self) -> None:
        data = self._load_yaml("strategy_types.yaml")
        
        for type_id, type_data in data.get("strategy_types", {}).items():
            parameters = {}
            for name, param in type_data.get("parameters", {}).items():
                parameters[name] = StrategyParameter(
                    name=name,
                    type=param.get("type", "float"),
                    default=param.get("default"),
                    min=param.get("min"),
                    max=param.get("max"),
                    description=param.get("description", ""),
                )
            
            definition = StrategyTypeDefinition(
                type_id=type_id,
                display_name=type_data.get("display_name", type_id),
                category=MetadataCategory(type_data.get("category", "custom")),
                description=type_data.get("description", ""),
                version=type_data.get("version", "1.0.0"),
                strategy_category=type_data.get("strategy_category", "quant"),
                parameters=parameters,
                signals=type_data.get("signals", []),
                risk_rules=type_data.get("risk_rules", []),
            )
            
            StrategyTypeRegistry.register(definition)
        
        logger.info(f"Loaded {len(StrategyTypeRegistry.list_all())} strategy types")
    
    def load_tool_types(self) -> None:
        data = self._load_yaml("tool_types.yaml")
        
        for type_id, type_data in data.get("tool_types", {}).items():
            parameters = {}
            for name, param in type_data.get("parameters", {}).items():
                parameters[name] = ToolParameter(
                    name=name,
                    type=param.get("type", "string"),
                    required=param.get("required", False),
                    default=param.get("default"),
                    description=param.get("description", ""),
                )
            
            definition = ToolTypeDefinition(
                type_id=type_id,
                display_name=type_data.get("display_name", type_id),
                category=MetadataCategory(type_data.get("category", "reference")),
                description=type_data.get("description", ""),
                version=type_data.get("version", "1.0.0"),
                tool_category=type_data.get("tool_category", "query"),
                parameters=parameters,
                returns=type_data.get("returns", "object"),
                timeout_ms=type_data.get("timeout_ms", 30000),
                cache_ttl=type_data.get("cache_ttl", 0),
            )
            
            ToolTypeRegistry.register(definition)
        
        logger.info(f"Loaded {len(ToolTypeRegistry.list_all())} tool types")
    
    def load_data_sources(self) -> None:
        data = self._load_yaml("data_sources.yaml")
        
        for type_id, source_data in data.get("data_sources", {}).items():
            definition = DataSourceDefinition(
                type_id=type_id,
                display_name=source_data.get("display_name", type_id),
                category=MetadataCategory(source_data.get("category", "reference")),
                description=source_data.get("description", ""),
                version=source_data.get("version", "1.0.0"),
                source_type=source_data.get("source_type", "api"),
                endpoint=source_data.get("endpoint"),
                auth_type=source_data.get("auth_type"),
                rate_limit=source_data.get("rate_limit", 100),
                timeout_ms=source_data.get("timeout_ms", 30000),
                data_types=source_data.get("data_types", []),
            )
            
            DataSourceRegistry.register(definition)
        
        logger.info(f"Loaded {len(DataSourceRegistry.list_all())} data sources")
    
    def load_all(self) -> None:
        """Load all metadata types."""
        self.load_entity_types()
        self.load_relation_types()
        self.load_factor_types()
        self.load_strategy_types()
        self.load_tool_types()
        self.load_data_sources()
