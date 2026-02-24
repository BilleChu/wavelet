"""
Unified Factor Registry.

Centralized registry for factor management with:
- Thread-safe singleton pattern
- Dynamic factor registration and discovery
- Factor persistence and versioning
- Parameter validation
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .base import (
    FactorBase,
    FactorCategory,
    FactorMetadata,
    FactorStatus,
    FactorType,
    NormalizeMethod,
    ParameterDefinition,
    ValidationResult,
)

logger = logging.getLogger(__name__)


@dataclass
class FactorDefinition:
    """Factor definition for registry storage."""
    
    factor_id: str
    name: str
    code: str
    description: str = ""
    factor_type: FactorType = FactorType.TECHNICAL
    category: FactorCategory = FactorCategory.CUSTOM
    expression: str = ""
    formula: str = ""
    parameters: dict[str, ParameterDefinition] = field(default_factory=dict)
    default_params: dict[str, Any] = field(default_factory=dict)
    lookback_period: int = 20
    required_fields: list[str] = field(default_factory=lambda: ["close"])
    normalize_method: NormalizeMethod = NormalizeMethod.ZSCORE
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "system"
    is_builtin: bool = False
    status: FactorStatus = FactorStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    factor_class: type[FactorBase] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "factor_type": self.factor_type.value,
            "category": self.category.value,
            "expression": self.expression,
            "formula": self.formula,
            "parameters": {k: v.model_dump() for k, v in self.parameters.items()},
            "default_params": self.default_params,
            "lookback_period": self.lookback_period,
            "required_fields": self.required_fields,
            "normalize_method": self.normalize_method.value,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "is_builtin": self.is_builtin,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "FactorDefinition":
        """Create from dictionary."""
        parameters = {}
        for k, v in data.get("parameters", {}).items():
            if isinstance(v, dict):
                parameters[k] = ParameterDefinition(**v)
            elif isinstance(v, ParameterDefinition):
                parameters[k] = v
        
        return cls(
            factor_id=data["factor_id"],
            name=data["name"],
            code=data["code"],
            description=data.get("description", ""),
            factor_type=FactorType(data.get("factor_type", "technical")),
            category=FactorCategory(data.get("category", "custom")),
            expression=data.get("expression", ""),
            formula=data.get("formula", ""),
            parameters=parameters,
            default_params=data.get("default_params", {}),
            lookback_period=data.get("lookback_period", 20),
            required_fields=data.get("required_fields", ["close"]),
            normalize_method=NormalizeMethod(data.get("normalize_method", "zscore")),
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "system"),
            is_builtin=data.get("is_builtin", False),
            status=FactorStatus(data.get("status", "active")),
        )
    
    def to_metadata(self) -> FactorMetadata:
        """Convert to FactorMetadata."""
        return FactorMetadata(
            factor_id=self.factor_id,
            name=self.name,
            description=self.description,
            factor_type=self.factor_type,
            category=self.category,
            version=self.version,
            author=self.author,
            tags=self.tags,
            required_fields=self.required_fields,
            lookback_period=self.lookback_period,
            normalize_method=self.normalize_method,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class UnifiedFactorRegistry:
    """
    Unified centralized registry for factor management.
    
    All built-in factors are registered via @register_factor decorator
    in their respective indicator files under factors/indicators/.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._factors: dict[str, FactorDefinition] = {}
        self._code_index: dict[str, str] = {}
        self._category_index: dict[str, set[str]] = {}
        self._type_index: dict[str, set[str]] = {}
        self._tag_index: dict[str, set[str]] = {}
        self._storage_path: Path | None = None
        self._initialized = True
        
        logger.info("UnifiedFactorRegistry initialized")
    
    def set_storage_path(self, path: str | Path) -> None:
        """Set storage path for factor persistence."""
        self._storage_path = Path(path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
    
    def _register_factor_def(self, factor_def: FactorDefinition) -> None:
        """Register a factor definition internally."""
        factor_id = factor_def.factor_id
        code = factor_def.code
        
        self._factors[factor_id] = factor_def
        self._code_index[code] = factor_id
        
        category = factor_def.category.value
        if category not in self._category_index:
            self._category_index[category] = set()
        self._category_index[category].add(factor_id)
        
        factor_type = factor_def.factor_type.value
        if factor_type not in self._type_index:
            self._type_index[factor_type] = set()
        self._type_index[factor_type].add(factor_id)
        
        for tag in factor_def.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(factor_id)
    
    def register(
        self,
        name: str,
        code: str,
        expression: str,
        description: str = "",
        factor_type: FactorType = FactorType.CUSTOM,
        category: FactorCategory = FactorCategory.CUSTOM,
        parameters: dict[str, ParameterDefinition] | None = None,
        default_params: dict[str, Any] | None = None,
        lookback_period: int = 20,
        required_fields: list[str] | None = None,
        tags: list[str] | None = None,
        author: str | None = None,
        factor_class: type[FactorBase] | None = None,
    ) -> FactorDefinition:
        """Register a new custom factor."""
        if code in self._code_index:
            raise ValueError(f"Factor code already exists: {code}")
        
        factor_id = f"factor_{code}"
        
        factor_def = FactorDefinition(
            factor_id=factor_id,
            name=name,
            code=code,
            description=description,
            factor_type=factor_type,
            category=category,
            expression=expression,
            formula=expression,
            parameters=parameters or {},
            default_params=default_params or {},
            lookback_period=lookback_period,
            required_fields=required_fields or ["close"],
            tags=tags or [],
            author=author or "user",
            is_builtin=False,
            factor_class=factor_class,
        )
        
        with self._lock:
            self._register_factor_def(factor_def)
        
        self._persist_factor(factor_def)
        
        logger.info(f"Registered factor: {code} ({factor_id})")
        return factor_def
    
    def register_class(
        self,
        factor_class: type[FactorBase],
        is_builtin: bool = False,
    ) -> FactorDefinition:
        """Register a factor class (called by @register_factor decorator)."""
        instance = factor_class()
        metadata = instance.metadata
        
        factor_def = FactorDefinition(
            factor_id=metadata.factor_id,
            name=metadata.name,
            code=metadata.factor_id.replace("factor_", ""),
            description=metadata.description,
            factor_type=metadata.factor_type,
            category=metadata.category,
            parameters=getattr(instance, "parameter_definitions", {}),
            default_params={},
            lookback_period=metadata.lookback_period,
            required_fields=metadata.required_fields,
            tags=metadata.tags,
            author=metadata.author,
            is_builtin=is_builtin,
            factor_class=factor_class,
        )
        
        with self._lock:
            self._register_factor_def(factor_def)
        
        logger.debug(f"Registered factor class: {metadata.factor_id}")
        return factor_def
    
    def unregister(self, factor_id: str) -> bool:
        """Unregister a factor (cannot unregister built-in factors)."""
        with self._lock:
            if factor_id not in self._factors:
                return False
            
            factor_def = self._factors[factor_id]
            
            if factor_def.is_builtin:
                raise ValueError("Cannot unregister built-in factor")
            
            code = factor_def.code
            category = factor_def.category.value
            factor_type = factor_def.factor_type.value
            tags = factor_def.tags
            
            del self._factors[factor_id]
            self._code_index.pop(code, None)
            
            self._category_index.get(category, set()).discard(factor_id)
            self._type_index.get(factor_type, set()).discard(factor_id)
            
            for tag in tags:
                self._tag_index.get(tag, set()).discard(factor_id)
            
            self._delete_factor_file(factor_id)
            
            logger.info(f"Unregistered factor: {code}")
            return True
    
    def get(self, factor_id: str) -> FactorDefinition | None:
        """Get factor by ID."""
        return self._factors.get(factor_id)
    
    def get_by_code(self, code: str) -> FactorDefinition | None:
        """Get factor by code."""
        factor_id = self._code_index.get(code)
        if factor_id:
            return self._factors.get(factor_id)
        return None
    
    def get_factor_instance(self, factor_id: str) -> FactorBase | None:
        """Get a factor instance for calculation."""
        factor_def = self._factors.get(factor_id)
        if not factor_def:
            return None
        
        if factor_def.factor_class:
            return factor_def.factor_class()
        
        return None
    
    def list_factors(
        self,
        factor_type: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        search: str | None = None,
        include_builtin: bool = True,
    ) -> list[FactorDefinition]:
        """List factors with optional filters."""
        factor_ids = set(self._factors.keys())
        
        if factor_type:
            factor_ids &= self._type_index.get(factor_type, set())
        
        if category:
            factor_ids &= self._category_index.get(category, set())
        
        if tags:
            for tag in tags:
                factor_ids &= self._tag_index.get(tag, set())
        
        results = []
        for fid in factor_ids:
            factor_def = self._factors.get(fid)
            if not factor_def:
                continue
            
            if not include_builtin and factor_def.is_builtin:
                continue
            
            if status and factor_def.status.value != status:
                continue
            
            if search:
                search_lower = search.lower()
                if (search_lower not in factor_def.name.lower() and
                    search_lower not in factor_def.code.lower() and
                    search_lower not in factor_def.description.lower()):
                    continue
            
            results.append(factor_def)
        
        return sorted(results, key=lambda f: f.updated_at, reverse=True)
    
    def list_all(self) -> list[str]:
        """List all registered factor IDs."""
        return list(self._factors.keys())
    
    def list_by_type(self, factor_type: FactorType) -> list[str]:
        """List factors by type."""
        return list(self._type_index.get(factor_type.value, set()))
    
    def list_by_category(self, category: FactorCategory) -> list[str]:
        """List factors by category."""
        return list(self._category_index.get(category.value, set()))
    
    def search(self, query: str) -> list[str]:
        """Search factors by name or description."""
        query_lower = query.lower()
        results = []
        
        for fid, factor_def in self._factors.items():
            if (query_lower in factor_def.name.lower() or
                query_lower in factor_def.description.lower() or
                query_lower in factor_def.code.lower()):
                results.append(fid)
        
        return results
    
    def update(
        self,
        factor_id: str,
        name: str | None = None,
        description: str | None = None,
        expression: str | None = None,
        parameters: dict[str, ParameterDefinition] | None = None,
        default_params: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        status: FactorStatus | None = None,
    ) -> FactorDefinition | None:
        """Update a factor (cannot update built-in factors)."""
        with self._lock:
            factor_def = self._factors.get(factor_id)
            if not factor_def:
                return None
            
            if factor_def.is_builtin:
                raise ValueError("Cannot modify built-in factor")
            
            if name:
                factor_def.name = name
            if description is not None:
                factor_def.description = description
            if expression:
                factor_def.expression = expression
                factor_def.formula = expression
            if parameters is not None:
                factor_def.parameters = parameters
            if default_params is not None:
                factor_def.default_params = default_params
            if status:
                factor_def.status = status
            
            if tags is not None:
                old_tags = set(factor_def.tags)
                new_tags = set(tags)
                
                for tag in old_tags - new_tags:
                    self._tag_index.get(tag, set()).discard(factor_id)
                for tag in new_tags - old_tags:
                    if tag not in self._tag_index:
                        self._tag_index[tag] = set()
                    self._tag_index[tag].add(factor_id)
                
                factor_def.tags = tags
            
            factor_def.updated_at = datetime.now()
            factor_def.version = f"{int(factor_def.version.split('.')[0]) + 1}.0.0"
            
            self._persist_factor(factor_def)
            
            logger.info(f"Updated factor: {factor_def.code}")
            return factor_def
    
    def validate_expression(self, expression: str) -> ValidationResult:
        """Validate a factor expression."""
        errors = []
        warnings = []
        
        try:
            from .expression_engine import get_expression_engine
            
            engine = get_expression_engine()
            is_valid, error = engine.validate(expression)
            
            if not is_valid:
                errors.append(error or "Invalid expression syntax")
        except ImportError:
            warnings.append("Expression engine not available")
            is_valid = True
        except Exception as e:
            errors.append(str(e))
            is_valid = False
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_factors": len(self._factors),
            "builtin_factors": sum(1 for f in self._factors.values() if f.is_builtin),
            "custom_factors": sum(1 for f in self._factors.values() if not f.is_builtin),
            "by_type": {t: len(ids) for t, ids in self._type_index.items()},
            "by_category": {c: len(ids) for c, ids in self._category_index.items()},
        }
    
    def _persist_factor(self, factor_def: FactorDefinition) -> None:
        """Persist factor to storage."""
        if not self._storage_path:
            return
        
        factor_file = self._storage_path / f"{factor_def.factor_id}.json"
        
        with open(factor_file, "w", encoding="utf-8") as f:
            json.dump(factor_def.to_dict(), f, ensure_ascii=False, indent=2, default=str)
    
    def _delete_factor_file(self, factor_id: str) -> None:
        """Delete factor file from storage."""
        if not self._storage_path:
            return
        
        factor_file = self._storage_path / f"{factor_id}.json"
        if factor_file.exists():
            factor_file.unlink()
    
    def load_from_storage(self) -> int:
        """Load factors from storage."""
        if not self._storage_path:
            return 0
        
        loaded = 0
        for factor_file in self._storage_path.glob("*.json"):
            try:
                with open(factor_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                factor_def = FactorDefinition.from_dict(data)
                
                if factor_def.factor_id not in self._factors:
                    self._register_factor_def(factor_def)
                    loaded += 1
                    
            except Exception as e:
                logger.error(f"Failed to load factor from {factor_file}: {e}")
        
        return loaded
    
    def reload_custom_factors(self) -> int:
        """
        Reload all custom factors from the custom indicators directory.
        
        This method discovers and re-imports all Python files in the
        factors/indicators/custom/ directory, triggering the @register_factor
        decorator to register any new or updated factors.
        
        Returns:
            int: Number of custom factors loaded
        """
        import importlib
        import sys
        from pathlib import Path
        
        custom_dir = Path(__file__).parent / "indicators" / "custom"
        if not custom_dir.exists():
            logger.warning(f"Custom factors directory not found: {custom_dir}")
            return 0
        
        loaded = 0
        for py_file in custom_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            
            module_name = f"openfinance.quant.factors.indicators.custom.{py_file.stem}"
            
            try:
                if module_name in sys.modules:
                    module = importlib.reload(sys.modules[module_name])
                else:
                    module = importlib.import_module(module_name)
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, FactorBase) and attr is not FactorBase:
                        if attr.__module__ == module_name:
                            loaded += 1
                            logger.debug(f"Loaded custom factor class: {attr_name}")
                            
            except Exception as e:
                logger.error(f"Failed to load custom factor module {module_name}: {e}")
        
        logger.info(f"Reloaded {loaded} custom factor(s)")
        return loaded
    
    def refresh(self) -> dict:
        """
        Refresh the registry by reloading custom factors.
        
        Returns:
            dict: Statistics about the refresh
        """
        custom_loaded = self.reload_custom_factors()
        storage_loaded = self.load_from_storage()
        
        return {
            "custom_factors_loaded": custom_loaded,
            "storage_factors_loaded": storage_loaded,
            "total_factors": len(self._factors),
        }


def get_factor_registry() -> UnifiedFactorRegistry:
    """Get the global factor registry instance."""
    return UnifiedFactorRegistry()


def register_factor(
    factor_class: type[FactorBase] | None = None,
    *,
    is_builtin: bool = False,
) -> Callable[[type[FactorBase]], type[FactorBase]] | type[FactorBase]:
    """
    Decorator to register a factor class.
    
    Usage:
        @register_factor(is_builtin=True)
        class RSIFactor(FactorBase):
            ...
    """
    def decorator(cls: type[FactorBase]) -> type[FactorBase]:
        registry = get_factor_registry()
        registry.register_class(cls, is_builtin=is_builtin)
        return cls
    
    if factor_class is not None:
        return decorator(factor_class)
    
    return decorator
