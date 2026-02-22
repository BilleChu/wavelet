"""
Relation Edge Model - Unified relation representation.

Supports conversion between PostgreSQL and Neo4j formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class RelationEdge:
    """
    Unified relation edge representation.
    
    Supports:
    - PostgreSQL storage (full attributes)
    - Neo4j storage (relationship properties)
    - Serialization/deserialization
    
    Usage:
        relation = RelationEdge(
            relation_id="rel_001",
            relation_type="belongs_to",
            source_id="stock_000001",
            target_id="industry_bank",
            weight=1.0,
            confidence=0.95
        )
    """
    
    relation_id: str
    relation_type: str
    source_id: str
    target_id: str
    weight: float = 1.0
    confidence: float = 1.0
    evidence: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    def __post_init__(self):
        if not self.relation_id:
            self.relation_id = f"rel_{uuid.uuid4().hex[:12]}"
    
    def to_pg_dict(self) -> dict[str, Any]:
        """Convert to PostgreSQL format (GenericRelationModel)."""
        return {
            "relation_id": self.relation_id,
            "relation_type": self.relation_type,
            "source_entity_id": self.source_id,
            "target_entity_id": self.target_id,
            "weight": self.weight,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "attributes": self.attributes,
            "properties": self.properties,
            "source": self.source,
        }
    
    def to_neo4j_dict(self) -> dict[str, Any]:
        """Convert to Neo4j format (relationship properties)."""
        return {
            "id": self.relation_id,
            "type": self.relation_type,
            "weight": self.weight,
            "confidence": self.confidence,
            "pg_ref": self.relation_id,  # Reference to PostgreSQL
        }
    
    def to_d3_link(self) -> dict[str, Any]:
        """Convert to D3.js link format for visualization."""
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type,
            "weight": self.weight,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_pg_model(cls, model: Any) -> "RelationEdge":
        """Create from PostgreSQL model (GenericRelationModel)."""
        return cls(
            relation_id=model.relation_id,
            relation_type=model.relation_type,
            source_id=model.source_entity_id,
            target_id=model.target_entity_id,
            weight=float(model.weight) if model.weight else 1.0,
            confidence=float(model.confidence) if model.confidence else 1.0,
            evidence=model.evidence,
            attributes=model.attributes or {},
            properties=model.properties or {},
            source=model.source,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @classmethod
    def from_neo4j_record(cls, record: dict[str, Any], rel_id: str) -> "RelationEdge":
        """Create from Neo4j relationship record."""
        return cls(
            relation_id=rel_id,
            relation_type=record.get("type", ""),
            source_id=record.get("source_id", ""),
            target_id=record.get("target_id", ""),
            weight=record.get("weight", 1.0),
            confidence=record.get("confidence", 1.0),
        )
    
    def __hash__(self) -> int:
        return hash(self.relation_id)
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, RelationEdge):
            return self.relation_id == other.relation_id
        return False
