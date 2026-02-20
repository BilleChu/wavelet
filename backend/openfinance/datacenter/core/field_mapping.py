"""
Field Mapping Registry.

Provides unified field mapping management for converting API responses
to standardized data models.

Usage:
    from datacenter.core import FieldMappingRegistry, FieldMapping
    
    registry = FieldMappingRegistry()
    
    registry.register(
        source="eastmoney",
        data_type="stock_quote",
        mapping={
            "f12": "code",
            "f14": "name",
            "f15": "high",
            "f16": "low",
        },
    )
    
    mapped = registry.apply("eastmoney", "stock_quote", api_response)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from .converters import ValueConverter, DateConverter


class FieldType(str, Enum):
    """Field data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    RAW = "raw"


@dataclass
class FieldMappingRule:
    """
    Single field mapping rule.
    
    Attributes:
        source_field: Field name in source data
        target_field: Field name in target model
        field_type: Data type for conversion
        default: Default value if source is None
        converter: Custom converter function
        required: Whether field is required
    """
    source_field: str
    target_field: str
    field_type: FieldType = FieldType.RAW
    default: Any = None
    converter: Callable[[Any], Any] | None = None
    required: bool = False
    
    def apply(self, source_data: dict[str, Any]) -> tuple[str, Any]:
        """Apply mapping rule to source data."""
        value = source_data.get(self.source_field)
        
        if value is None:
            if self.required and self.default is None:
                raise ValueError(f"Required field '{self.source_field}' is missing")
            return self.target_field, self.default
        
        if self.converter:
            try:
                converted = self.converter(value)
            except Exception:
                converted = self.default
        else:
            converted = self._convert_by_type(value)
        
        return self.target_field, converted
    
    def _convert_by_type(self, value: Any) -> Any:
        """Convert value based on field type."""
        if self.field_type == FieldType.RAW:
            return value
        elif self.field_type == FieldType.STRING:
            return ValueConverter.to_str(value, default=self.default)
        elif self.field_type == FieldType.INTEGER:
            return ValueConverter.to_int(value, default=self.default)
        elif self.field_type == FieldType.FLOAT:
            return ValueConverter.to_float(value, default=self.default)
        elif self.field_type == FieldType.DECIMAL:
            return ValueConverter.to_decimal(value, default=self.default)
        elif self.field_type == FieldType.DATE:
            return DateConverter.to_date(value, default=self.default)
        elif self.field_type == FieldType.DATETIME:
            return DateConverter.to_datetime(value, default=self.default)
        elif self.field_type == FieldType.BOOLEAN:
            return ValueConverter.to_bool(value, default=self.default)
        elif self.field_type == FieldType.PERCENTAGE:
            from .converters import PercentageConverter
            return PercentageConverter.to_decimal(value, default=self.default)
        
        return value


@dataclass
class FieldMapping:
    """
    Complete field mapping for a data type.
    
    Attributes:
        source: Data source identifier
        data_type: Data type identifier
        rules: List of field mapping rules
        post_processor: Optional post-processing function
    """
    source: str
    data_type: str
    rules: list[FieldMappingRule] = field(default_factory=list)
    post_processor: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    
    def add_rule(
        self,
        source_field: str,
        target_field: str,
        field_type: FieldType = FieldType.RAW,
        default: Any = None,
        converter: Callable[[Any], Any] | None = None,
        required: bool = False,
    ) -> "FieldMapping":
        """Add a field mapping rule."""
        rule = FieldMappingRule(
            source_field=source_field,
            target_field=target_field,
            field_type=field_type,
            default=default,
            converter=converter,
            required=required,
        )
        self.rules.append(rule)
        return self
    
    def apply(self, source_data: dict[str, Any]) -> dict[str, Any]:
        """Apply all mapping rules to source data."""
        result: dict[str, Any] = {}
        
        for rule in self.rules:
            target_field, value = rule.apply(source_data)
            result[target_field] = value
        
        if self.post_processor:
            result = self.post_processor(result)
        
        return result


class FieldMappingRegistry:
    """
    Central registry for field mappings.
    
    Manages field mappings for different data sources and types,
    enabling configuration-driven data transformation.
    """
    
    def __init__(self) -> None:
        self._mappings: dict[str, dict[str, FieldMapping]] = {}
    
    def register(self, mapping: FieldMapping) -> None:
        """Register a field mapping."""
        if mapping.source not in self._mappings:
            self._mappings[mapping.source] = {}
        self._mappings[mapping.source][mapping.data_type] = mapping
    
    def register_simple(
        self,
        source: str,
        data_type: str,
        field_map: dict[str, str | tuple[str, FieldType]],
        defaults: dict[str, Any] | None = None,
    ) -> None:
        """
        Register a simple field mapping.
        
        Args:
            source: Data source identifier
            data_type: Data type identifier
            field_map: Mapping of source_field -> target_field or (target_field, type)
            defaults: Default values for fields
        """
        mapping = FieldMapping(source=source, data_type=data_type)
        defaults = defaults or {}
        
        for source_field, target_spec in field_map.items():
            if isinstance(target_spec, str):
                target_field = target_spec
                field_type = FieldType.RAW
            else:
                target_field, field_type = target_spec
            
            mapping.add_rule(
                source_field=source_field,
                target_field=target_field,
                field_type=field_type,
                default=defaults.get(target_field),
            )
        
        self.register(mapping)
    
    def get(self, source: str, data_type: str) -> FieldMapping | None:
        """Get field mapping for source and data type."""
        return self._mappings.get(source, {}).get(data_type)
    
    def apply(
        self,
        source: str,
        data_type: str,
        source_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply field mapping to source data.
        
        Args:
            source: Data source identifier
            data_type: Data type identifier
            source_data: Source data dictionary
            
        Returns:
            Mapped data dictionary
        """
        mapping = self.get(source, data_type)
        
        if mapping:
            return mapping.apply(source_data)
        
        return dict(source_data)
    
    def apply_batch(
        self,
        source: str,
        data_type: str,
        source_data_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply field mapping to multiple records."""
        return [
            self.apply(source, data_type, data)
            for data in source_data_list
        ]
    
    def list_sources(self) -> list[str]:
        """List all registered sources."""
        return list(self._mappings.keys())
    
    def list_data_types(self, source: str) -> list[str]:
        """List all data types for a source."""
        return list(self._mappings.get(source, {}).keys())


def apply_field_mapping(
    source: str,
    data_type: str,
    source_data: dict[str, Any],
    registry: FieldMappingRegistry | None = None,
) -> dict[str, Any]:
    """
    Convenience function for applying field mapping.
    
    Args:
        source: Data source identifier
        data_type: Data type identifier
        source_data: Source data dictionary
        registry: Optional registry instance (uses global if None)
    
    Returns:
        Mapped data dictionary
    """
    if registry is None:
        registry = _global_registry
    return registry.apply(source, data_type, source_data)


_global_registry = FieldMappingRegistry()


def get_global_registry() -> FieldMappingRegistry:
    """Get the global field mapping registry."""
    return _global_registry
