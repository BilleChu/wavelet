"""
Entity Node Model - Unified entity representation.

Supports conversion between PostgreSQL and Neo4j formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EntityNode:
    """
    Unified entity node representation.
    
    Supports:
    - PostgreSQL storage (full attributes)
    - Neo4j storage (reference + basic info)
    - Serialization/deserialization
    
    Usage:
        entity = EntityNode(
            entity_id="stock_000001",
            entity_type="stock",
            name="平安银行",
            code="000001",
            attributes={"industry": "银行", "market": "深交所"}
        )
        
        # Convert for different storages
        pg_data = entity.to_pg_dict()
        neo4j_data = entity.to_neo4j_dict()
    """
    
    entity_id: str
    entity_type: str
    name: str
    code: str | None = None
    aliases: list[str] = field(default_factory=list)
    description: str | None = None
    industry: str | None = None
    market: str | None = None
    market_cap: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    confidence: float = 1.0
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    def to_pg_dict(self) -> dict[str, Any]:
        """Convert to PostgreSQL format (GenericEntityModel)."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "code": self.code,
            "aliases": self.aliases,
            "description": self.description,
            "industry": self.industry,
            "market": self.market,
            "market_cap": self.market_cap,
            "attributes": self.attributes,
            "properties": self.properties,
            "source": self.source,
            "confidence": self.confidence,
            "is_active": self.is_active,
        }
    
    def to_neo4j_dict(self) -> dict[str, Any]:
        """Convert to Neo4j format (node properties)."""
        return {
            "id": self.entity_id,
            "type": self.entity_type,
            "name": self.name,
            "code": self.code,
            "pg_ref": self.entity_id,  # Reference to PostgreSQL
            "industry": self.industry,
            "market": self.market,
        }
    
    def to_d3_node(self) -> dict[str, Any]:
        """Convert to D3.js node format for visualization."""
        return {
            "id": self.entity_id,
            "label": self.name,
            "type": self.entity_type,
            "code": self.code,
            "attributes": self.attributes,
        }
    
    @classmethod
    def from_pg_model(cls, model: Any) -> "EntityNode":
        """Create from PostgreSQL model (GenericEntityModel)."""
        return cls(
            entity_id=model.entity_id,
            entity_type=model.entity_type,
            name=model.name,
            code=model.code,
            aliases=model.aliases or [],
            description=model.description,
            industry=model.industry,
            market=model.market,
            market_cap=float(model.market_cap) if model.market_cap else None,
            attributes=model.attributes or {},
            properties=model.properties or {},
            source=model.source,
            confidence=float(model.confidence) if model.confidence else 1.0,
            is_active=model.is_active if hasattr(model, 'is_active') else True,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @classmethod
    def from_neo4j_record(cls, record: dict[str, Any]) -> "EntityNode":
        """Create from Neo4j record."""
        return cls(
            entity_id=record.get("id", ""),
            entity_type=record.get("type", ""),
            name=record.get("name", ""),
            code=record.get("code"),
            industry=record.get("industry"),
            market=record.get("market"),
        )
    
    def __hash__(self) -> int:
        return hash(self.entity_id)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, EntityNode):
            return self.entity_id == other.entity_id
        return False
