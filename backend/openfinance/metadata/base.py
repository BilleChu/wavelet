"""
Metadata base models.

Provides the foundational dataclasses and types for metadata definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, TypeVar


class PropertyType(str, Enum):
    """Property type enumeration."""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TEXT = "text"
    JSON = "json"
    ENUM = "enum"
    ARRAY = "array"
    OBJECT = "object"


class Severity(str, Enum):
    """Validation severity level."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class MetadataCategory(str, Enum):
    """Metadata category."""
    CORE = "core"
    CLASSIFICATION = "classification"
    REFERENCE = "reference"
    DERIVED = "derived"
    CUSTOM = "custom"
    BUSINESS = "business"
    PERSONNEL = "personnel"
    CORPORATE = "corporate"
    IMPACT = "impact"
    MARKET = "market"
    GENERAL = "general"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    ALTERNATIVE = "alternative"
    SENTIMENT = "sentiment"
    MONEY_FLOW = "money_flow"


@dataclass
class PropertyDefinition:
    """Property definition for metadata types."""
    type: PropertyType
    required: bool = False
    unique: bool = False
    index: bool = False
    default: Any = None
    description: str = ""
    
    max_length: int | None = None
    min_length: int | None = None
    format: str | None = None
    
    min: int | float | Decimal | None = None
    max: int | float | Decimal | None = None
    precision: int | None = None
    scale: int | None = None
    
    values: list[str] | None = None
    items: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "required": self.required,
            "unique": self.unique,
            "index": self.index,
            "default": self.default,
            "description": self.description,
            "max_length": self.max_length,
            "min_length": self.min_length,
            "format": self.format,
            "min": self.min,
            "max": self.max,
            "precision": self.precision,
            "scale": self.scale,
            "values": self.values,
            "items": self.items,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PropertyDefinition:
        return cls(
            type=PropertyType(data["type"]),
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


@dataclass
class QualityRule:
    """Data quality rule definition."""
    name: str
    severity: Severity = Severity.WARNING
    condition: str = ""
    message: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity.value,
            "condition": self.condition,
            "message": self.message,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityRule:
        return cls(
            name=data["name"],
            severity=Severity(data.get("severity", "warning")),
            condition=data.get("condition", ""),
            message=data.get("message", ""),
        )


@dataclass
class ValidationResult:
    """Validation result."""
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def merge(self, other: ValidationResult) -> ValidationResult:
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


T = TypeVar("T")


@dataclass
class MetadataDefinition(Generic[T]):
    """Base metadata definition."""
    type_id: str
    display_name: str
    category: MetadataCategory
    description: str = ""
    version: str = "1.0.0"
    extends: str | None = None
    
    properties: dict[str, PropertyDefinition] = field(default_factory=dict)
    quality_rules: list[QualityRule] = field(default_factory=list)
    
    _resolved_properties: dict[str, PropertyDefinition] | None = field(
        default=None, repr=False, compare=False
    )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type_id": self.type_id,
            "display_name": self.display_name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "extends": self.extends,
            "properties": {k: v.to_dict() for k, v in self.properties.items()},
            "quality_rules": [r.to_dict() for r in self.quality_rules],
        }
    
    def get_resolved_properties(
        self, 
        registry: MetadataRegistry[T]
    ) -> dict[str, PropertyDefinition]:
        if self._resolved_properties is not None:
            return self._resolved_properties
        
        properties = {}
        
        if self.extends:
            parent = registry.get(self.extends)
            if parent:
                properties.update(parent.get_resolved_properties(registry))
        
        properties.update(self.properties)
        self._resolved_properties = properties
        return properties
    
    def get_indexed_properties(
        self, 
        registry: MetadataRegistry[T]
    ) -> list[str]:
        properties = self.get_resolved_properties(registry)
        return [
            name for name, prop in properties.items()
            if prop.index or prop.unique
        ]
    
    def validate_data(
        self, 
        data: dict[str, Any],
        registry: MetadataRegistry[T] | None = None,
    ) -> ValidationResult:
        errors = []
        warnings = []
        
        properties = self.properties
        if registry:
            properties = self.get_resolved_properties(registry)
        
        for prop_name, prop_def in properties.items():
            value = data.get(prop_name)
            prop_errors = self._validate_property(prop_name, prop_def, value)
            errors.extend(prop_errors)
        
        known_props = set(properties.keys())
        extra_props = set(data.keys()) - known_props - {"type_id", "name", "code"}
        if extra_props:
            warnings.append(f"Unknown properties: {extra_props}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def _validate_property(
        self, 
        name: str, 
        prop: PropertyDefinition, 
        value: Any
    ) -> list[str]:
        errors = []
        
        if value is None:
            if prop.required:
                errors.append(f"{name}: Property is required")
            return errors
        
        if prop.type == PropertyType.STRING:
            if not isinstance(value, str):
                errors.append(f"{name}: Expected string, got {type(value).__name__}")
            elif prop.max_length and len(value) > prop.max_length:
                errors.append(f"{name}: String too long: {len(value)} > {prop.max_length}")
                
        elif prop.type == PropertyType.INTEGER:
            if not isinstance(value, int):
                errors.append(f"{name}: Expected integer, got {type(value).__name__}")
            elif prop.min is not None and value < prop.min:
                errors.append(f"{name}: Value too small: {value} < {prop.min}")
            elif prop.max is not None and value > prop.max:
                errors.append(f"{name}: Value too large: {value} > {prop.max}")
                
        elif prop.type == PropertyType.DECIMAL:
            try:
                dec_value = Decimal(str(value))
                if prop.min is not None and dec_value < Decimal(str(prop.min)):
                    errors.append(f"{name}: Value too small")
                if prop.max is not None and dec_value > Decimal(str(prop.max)):
                    errors.append(f"{name}: Value too large")
            except Exception:
                errors.append(f"{name}: Invalid decimal value: {value}")
                
        elif prop.type == PropertyType.ENUM:
            if prop.values and value not in prop.values:
                errors.append(f"{name}: Invalid enum value: {value}. Valid: {prop.values}")
                
        elif prop.type == PropertyType.BOOLEAN:
            if not isinstance(value, bool):
                errors.append(f"{name}: Expected boolean, got {type(value).__name__}")
                
        elif prop.type == PropertyType.ARRAY:
            if not isinstance(value, list):
                errors.append(f"{name}: Expected array, got {type(value).__name__}")
        
        return errors


class MetadataRegistry(Generic[T]):
    """Generic metadata registry."""
    
    _types: dict[str, T] = {}
    _loaded: bool = False
    
    @classmethod
    def register(cls, definition: T) -> None:
        if hasattr(definition, 'type_id'):
            cls._types[definition.type_id] = definition
    
    @classmethod
    def get(cls, type_id: str) -> T | None:
        return cls._types.get(type_id)
    
    @classmethod
    def get_or_raise(cls, type_id: str) -> T:
        definition = cls._types.get(type_id)
        if definition is None:
            raise ValueError(f"Unknown type: {type_id}")
        return definition
    
    @classmethod
    def list_all(cls) -> list[T]:
        return list(cls._types.values())
    
    @classmethod
    def exists(cls, type_id: str) -> bool:
        return type_id in cls._types
    
    @classmethod
    def clear(cls) -> None:
        cls._types.clear()
        cls._loaded = False
    
    @classmethod
    def get_type_ids(cls) -> list[str]:
        return list(cls._types.keys())
