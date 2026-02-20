"""
Model Registry - Central registration for all data models.

Provides a generic, business-agnostic model registration system with:
- Model discovery and lookup
- Metadata management
- Capability declaration
- ORM model mapping
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ModelCapability(str, Enum):
    """Capabilities that a model can declare."""
    
    SERIALIZATION = "serialization"
    DESERIALIZATION = "deserialization"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    STORAGE = "storage"
    QUERY = "query"
    AGGREGATION = "aggregation"
    STREAMING = "streaming"


@dataclass
class ModelMetadata:
    """
    Metadata for a registered model.
    
    Contains all information needed to manage the model
    throughout its lifecycle.
    """
    
    model_id: str
    model_class: type
    category: str
    
    version: str = "1.0.0"
    description: str = ""
    
    orm_model: type | None = None
    schema: dict[str, Any] | None = None
    
    capabilities: list[ModelCapability] = field(default_factory=list)
    
    field_mappings: dict[str, str] = field(default_factory=dict)
    computed_fields: dict[str, str] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deprecated: bool = False
    deprecation_message: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "category": self.category,
            "version": self.version,
            "description": self.description,
            "has_orm_model": self.orm_model is not None,
            "has_schema": self.schema is not None,
            "capabilities": [c.value for c in self.capabilities],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "deprecated": self.deprecated,
        }


class ModelRegistry:
    """
    Central registry for all data models.
    
    Thread-safe singleton that provides:
    - Model registration and discovery
    - Model metadata management
    - ORM model mapping
    - Transformer registration
    
    Usage:
        registry = ModelRegistry.get_instance()
        
        # Register a model
        registry.register(
            model_class=StockQuoteData,
            category="market",
            model_id="stock_quote",
            orm_model=StockDailyQuoteModel,
        )
        
        # Get model
        model_class = registry.get_model("stock_quote")
        metadata = registry.get_metadata("stock_quote")
    
    Design Principles:
    - No business logic in the registry
    - Models are registered, not hardcoded
    - Supports any Pydantic/SQLAlchemy model
    - Plugin-based extensibility
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "ModelRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._models: dict[str, ModelMetadata] = {}
        self._categories: dict[str, list[str]] = {}
        self._transformers: dict[tuple[str, str], Any] = {}
        self._version_index: dict[str, list[str]] = {}
        
        self._initialized = True
        logger.info("ModelRegistry initialized")
    
    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Get the singleton instance."""
        return cls()
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        with cls._lock:
            cls._instance = None
    
    def register(
        self,
        model_class: type,
        category: str,
        model_id: str | None = None,
        version: str = "1.0.0",
        description: str = "",
        orm_model: type | None = None,
        schema: dict[str, Any] | None = None,
        capabilities: list[ModelCapability] | None = None,
        field_mappings: dict[str, str] | None = None,
    ) -> ModelMetadata:
        """
        Register a model with the registry.
        
        Args:
            model_class: The Pydantic model class
            category: Business category (e.g., "quant", "market", "graph")
            model_id: Unique identifier (defaults to class name)
            version: Model version
            description: Human-readable description
            orm_model: Corresponding SQLAlchemy ORM model
            schema: JSON Schema definition
            capabilities: List of model capabilities
            field_mappings: Custom field mappings for transformation
        
        Returns:
            ModelMetadata for the registered model
        """
        model_id = model_id or model_class.__name__
        
        if model_id in self._models:
            logger.warning(f"Model {model_id} already registered, updating")
        
        metadata = ModelMetadata(
            model_id=model_id,
            model_class=model_class,
            category=category,
            version=version,
            description=description,
            orm_model=orm_model,
            schema=schema,
            capabilities=capabilities or [],
            field_mappings=field_mappings or {},
        )
        
        self._models[model_id] = metadata
        
        if category not in self._categories:
            self._categories[category] = []
        if model_id not in self._categories[category]:
            self._categories[category].append(model_id)
        
        version_key = f"{model_id}@{version}"
        if model_id not in self._version_index:
            self._version_index[model_id] = []
        self._version_index[model_id].append(version_key)
        
        logger.info(f"Registered model: {model_id} (category={category}, version={version})")
        
        return metadata
    
    def unregister(self, model_id: str) -> bool:
        """Unregister a model."""
        if model_id not in self._models:
            return False
        
        metadata = self._models[model_id]
        
        if metadata.category in self._categories:
            self._categories[metadata.category] = [
                m for m in self._categories[metadata.category] if m != model_id
            ]
        
        del self._models[model_id]
        logger.info(f"Unregistered model: {model_id}")
        
        return True
    
    def get_model(self, model_id: str) -> type | None:
        """Get a model class by ID."""
        metadata = self._models.get(model_id)
        return metadata.model_class if metadata else None
    
    def get_metadata(self, model_id: str) -> ModelMetadata | None:
        """Get model metadata by ID."""
        return self._models.get(model_id)
    
    def get_orm_model(self, model_id: str) -> type | None:
        """Get the ORM model for a business model."""
        metadata = self._models.get(model_id)
        return metadata.orm_model if metadata else None
    
    def get_model_ids(self, category: str | None = None) -> list[str]:
        """Get list of model IDs, optionally filtered by category."""
        if category:
            return self._categories.get(category, [])
        return list(self._models.keys())
    
    def list_models(self, category: str | None = None) -> list[ModelMetadata]:
        """List all models, optionally filtered by category."""
        if category:
            model_ids = self._categories.get(category, [])
            return [self._models[mid] for mid in model_ids if mid in self._models]
        return list(self._models.values())
    
    def get_categories(self) -> list[str]:
        """Get all registered categories."""
        return list(self._categories.keys())
    
    def has_model(self, model_id: str) -> bool:
        """Check if a model is registered."""
        return model_id in self._models
    
    def register_transformer(
        self,
        source_model_id: str,
        target_model_id: str,
        transformer: Any,
    ) -> None:
        """
        Register a transformer between two models.
        
        Args:
            source_model_id: Source model ID
            target_model_id: Target model ID
            transformer: ModelTransformer instance
        """
        key = (source_model_id, target_model_id)
        self._transformers[key] = transformer
        logger.info(f"Registered transformer: {source_model_id} -> {target_model_id}")
    
    def get_transformer(
        self,
        source_model_id: str,
        target_model_id: str,
    ) -> Any | None:
        """Get a transformer between two models."""
        return self._transformers.get((source_model_id, target_model_id))
    
    def deprecate_model(
        self,
        model_id: str,
        message: str | None = None,
    ) -> bool:
        """Mark a model as deprecated."""
        if model_id not in self._models:
            return False
        
        self._models[model_id].deprecated = True
        self._models[model_id].deprecation_message = message
        self._models[model_id].updated_at = datetime.now()
        
        logger.warning(f"Deprecated model: {model_id}")
        return True
    
    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_models": len(self._models),
            "categories": {
                cat: len(models)
                for cat, models in self._categories.items()
            },
            "models_with_orm": sum(
                1 for m in self._models.values()
                if m.orm_model is not None
            ),
            "models_with_schema": sum(
                1 for m in self._models.values()
                if m.schema is not None
            ),
            "deprecated_models": sum(
                1 for m in self._models.values()
                if m.deprecated
            ),
            "transformers": len(self._transformers),
        }


def register_model(
    category: str,
    model_id: str | None = None,
    version: str = "1.0.0",
    orm_model: type | None = None,
    **kwargs: Any,
) -> Callable[[type], type]:
    """
    Decorator for registering a model.
    
    Usage:
        @register_model("market", "stock_quote", orm_model=StockDailyQuoteModel)
        class StockQuoteData(BaseModel):
            code: str
            close: float
    """
    def decorator(cls: type) -> type:
        registry = ModelRegistry.get_instance()
        registry.register(
            model_class=cls,
            category=category,
            model_id=model_id,
            version=version,
            orm_model=orm_model,
            **kwargs,
        )
        return cls
    
    return decorator


from typing import Callable
