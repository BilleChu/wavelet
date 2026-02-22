"""
Data Validator - Schema and rule-based validation.

Provides:
- Schema validation using Pydantic
- Rule-based validation
- Custom validation functions
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue."""
    
    field_name: str
    level: ValidationLevel
    message: str
    value: Any = None
    constraint: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "level": self.level.value,
            "message": self.message,
            "value": str(self.value) if self.value is not None else None,
            "constraint": self.constraint,
        }


class ValidationResult(BaseModel):
    """Result of data validation."""
    
    valid: bool = Field(..., description="Whether validation passed")
    issues: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Validation issues found"
    )
    
    error_count: int = Field(default=0, description="Number of errors")
    warning_count: int = Field(default=0, description="Number of warnings")
    
    validated_at: datetime = Field(default_factory=datetime.now)
    duration_ms: float | None = Field(default=None)


class ValidationRule(BaseModel):
    """A validation rule."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    
    field_name: str = Field(..., description="Target field name")
    rule_type: str = Field(..., description="Type of validation")
    
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Rule parameters"
    )
    
    level: ValidationLevel = Field(
        default=ValidationLevel.ERROR,
        description="Issue level when rule fails"
    )
    
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class SchemaValidator:
    """
    Schema-based validator using Pydantic models.
    """
    
    def __init__(self, schema: type[BaseModel]) -> None:
        self.schema = schema
    
    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate data against schema."""
        start_time = time.time()
        
        issues: list[dict[str, Any]] = []
        
        try:
            self.schema(**data)
            valid = True
        except ValidationError as e:
            valid = False
            for error in e.errors():
                field_name = ".".join(str(loc) for loc in error["loc"])
                issues.append({
                    "field_name": field_name,
                    "level": ValidationLevel.ERROR.value,
                    "message": error["msg"],
                    "value": error.get("input"),
                    "constraint": error.get("type"),
                })
        
        return ValidationResult(
            valid=valid,
            issues=issues,
            error_count=sum(1 for i in issues if i["level"] == ValidationLevel.ERROR.value),
            warning_count=sum(1 for i in issues if i["level"] == ValidationLevel.WARNING.value),
            duration_ms=(time.time() - start_time) * 1000,
        )
    
    def validate_batch(
        self,
        data_list: list[dict[str, Any]],
    ) -> list[ValidationResult]:
        """Validate multiple records."""
        return [self.validate(data) for data in data_list]


class DataValidator:
    """
    Comprehensive data validator with rule-based validation.
    
    Supports:
    - Type validation
    - Range validation
    - Pattern validation
    - Custom validation functions
    - Required field validation
    """
    
    def __init__(self) -> None:
        self._rules: dict[str, ValidationRule] = {}
        self._custom_validators: dict[str, Callable[[Any], bool]] = {}
        
        self._add_default_rules()
    
    def _add_default_rules(self) -> None:
        """Add default validation rules."""
        default_rules = [
            ValidationRule(
                rule_id="default_code_required",
                name="Stock Code Required",
                field_name="code",
                rule_type="required",
                level=ValidationLevel.ERROR,
            ),
            ValidationRule(
                rule_id="default_code_pattern",
                name="Stock Code Format",
                field_name="code",
                rule_type="pattern",
                params={"pattern": r"^\d{6}$"},
                level=ValidationLevel.WARNING,
            ),
            ValidationRule(
                rule_id="default_name_required",
                name="Stock Name Required",
                field_name="name",
                rule_type="required",
                level=ValidationLevel.ERROR,
            ),
        ]
        
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self._rules[rule.rule_id] = rule
        logger.info(f"Added validation rule: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a validation rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def register_custom_validator(
        self,
        validator_id: str,
        validator: Callable[[Any], bool],
    ) -> None:
        """Register a custom validator function."""
        self._custom_validators[validator_id] = validator
    
    def validate(self, data: dict[str, Any]) -> ValidationResult:
        """Validate data against all rules."""
        start_time = time.time()
        
        issues: list[dict[str, Any]] = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            issue = self._apply_rule(rule, data)
            if issue:
                issues.append(issue)
        
        error_count = sum(1 for i in issues if i["level"] == ValidationLevel.ERROR.value)
        warning_count = sum(1 for i in issues if i["level"] == ValidationLevel.WARNING.value)
        
        return ValidationResult(
            valid=error_count == 0,
            issues=issues,
            error_count=error_count,
            warning_count=warning_count,
            duration_ms=(time.time() - start_time) * 1000,
        )
    
    def validate_batch(
        self,
        data_list: list[dict[str, Any]],
        fail_fast: bool = False,
    ) -> list[ValidationResult]:
        """Validate multiple records."""
        results = []
        
        for data in data_list:
            result = self.validate(data)
            results.append(result)
            
            if fail_fast and not result.valid:
                break
        
        return results
    
    def _apply_rule(
        self,
        rule: ValidationRule,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Apply a validation rule to data."""
        value = data.get(rule.field_name)
        
        if rule.rule_type == "required":
            if value is None or value == "":
                return ValidationIssue(
                    field_name=rule.field_name,
                    level=rule.level,
                    message=f"Field '{rule.field_name}' is required",
                    value=value,
                ).to_dict()
        
        elif rule.rule_type == "type":
            expected_type = rule.params.get("type")
            if value is not None and not self._check_type(value, expected_type):
                return ValidationIssue(
                    field_name=rule.field_name,
                    level=rule.level,
                    message=f"Expected type {expected_type}, got {type(value).__name__}",
                    value=value,
                    constraint=f"type:{expected_type}",
                ).to_dict()
        
        elif rule.rule_type == "pattern":
            pattern = rule.params.get("pattern", "")
            if value is not None and not re.match(pattern, str(value)):
                return ValidationIssue(
                    field_name=rule.field_name,
                    level=rule.level,
                    message=f"Value does not match pattern: {pattern}",
                    value=value,
                    constraint=f"pattern:{pattern}",
                ).to_dict()
        
        elif rule.rule_type == "range":
            if value is not None:
                min_val = rule.params.get("min")
                max_val = rule.params.get("max")
                exclusive_min = rule.params.get("exclusive_min", False)
                exclusive_max = rule.params.get("exclusive_max", False)
                
                try:
                    num_value = float(value)
                    
                    if min_val is not None:
                        if exclusive_min and num_value <= min_val:
                            return ValidationIssue(
                                field_name=rule.field_name,
                                level=rule.level,
                                message=f"Value must be greater than {min_val}",
                                value=value,
                                constraint=f"range:>{min_val}",
                            ).to_dict()
                        elif not exclusive_min and num_value < min_val:
                            return ValidationIssue(
                                field_name=rule.field_name,
                                level=rule.level,
                                message=f"Value must be at least {min_val}",
                                value=value,
                                constraint=f"range:>={min_val}",
                            ).to_dict()
                    
                    if max_val is not None:
                        if exclusive_max and num_value >= max_val:
                            return ValidationIssue(
                                field_name=rule.field_name,
                                level=rule.level,
                                message=f"Value must be less than {max_val}",
                                value=value,
                                constraint=f"range:<{max_val}",
                            ).to_dict()
                        elif not exclusive_max and num_value > max_val:
                            return ValidationIssue(
                                field_name=rule.field_name,
                                level=rule.level,
                                message=f"Value must be at most {max_val}",
                                value=value,
                                constraint=f"range:<={max_val}",
                            ).to_dict()
                except (ValueError, TypeError):
                    pass
        
        elif rule.rule_type == "enum":
            allowed = rule.params.get("values", [])
            if value is not None and value not in allowed:
                return ValidationIssue(
                    field_name=rule.field_name,
                    level=rule.level,
                    message=f"Value must be one of: {allowed}",
                    value=value,
                    constraint=f"enum:{allowed}",
                ).to_dict()
        
        elif rule.rule_type == "custom":
            validator_id = rule.params.get("validator_id")
            if validator_id and validator_id in self._custom_validators:
                validator = self._custom_validators[validator_id]
                if not validator(value):
                    return ValidationIssue(
                        field_name=rule.field_name,
                        level=rule.level,
                        message=f"Custom validation failed: {validator_id}",
                        value=value,
                        constraint=f"custom:{validator_id}",
                    ).to_dict()
        
        return None
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "integer": int,
            "float": (int, float),
            "boolean": bool,
            "list": list,
            "dict": dict,
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        
        if expected_type == "float":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        
        return isinstance(value, expected)
    
    def get_rules(self) -> list[ValidationRule]:
        """Get all validation rules."""
        return list(self._rules.values())
    
    def get_rules_for_field(self, field_name: str) -> list[ValidationRule]:
        """Get rules for a specific field."""
        return [r for r in self._rules.values() if r.field_name == field_name]
