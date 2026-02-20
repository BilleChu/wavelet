"""
Entity Types for Data Processing.

Provides entity and relation type definitions for the processing pipeline.
Enums are imported from the centralized models/enums.py to avoid duplication.
"""

from typing import Any

from pydantic import BaseModel, Field

from openfinance.models.enums import EntityType, RelationType


__all__ = ["EntityType", "RelationType", "BaseEntity", "Relation", "create_entity"]


class BaseEntity(BaseModel):
    """Base class for all entities."""

    entity_id: str = Field(..., description="Unique entity identifier")
    entity_type: EntityType = Field(..., description="Entity type")
    name: str = Field(..., description="Entity name")
    aliases: list[str] = Field(default_factory=list, description="Alternative names")
    description: str | None = Field(default=None, description="Entity description")
    source: str = Field(default="unknown", description="Data source")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Relation(BaseModel):
    """Relation between two entities."""

    relation_id: str = Field(..., description="Unique relation identifier")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relation_type: RelationType = Field(..., description="Relation type")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relation weight")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    evidence: str | None = Field(default=None, description="Evidence text")
    source: str = Field(default="unknown", description="Data source")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


def create_entity(entity_type: EntityType, **kwargs: Any) -> BaseEntity:
    """Create an entity of the specified type."""
    return BaseEntity(entity_type=entity_type, **kwargs)
