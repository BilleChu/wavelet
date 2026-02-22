"""
Graph Storage Base - Abstract storage interface.

Defines the unified interface for graph storage backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from openfinance.datacenter.graph.models import EntityNode, RelationEdge


class StorageBackend(str, Enum):
    """Storage backend types."""
    POSTGRES = "postgres"
    NEO4J = "neo4j"
    HYBRID = "hybrid"


@dataclass
class QueryResult:
    """Query result container."""
    
    success: bool
    data: Any = None
    error: str | None = None
    count: int = 0
    backend: StorageBackend = StorageBackend.POSTGRES
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PathResult:
    """Path query result."""
    
    found: bool
    path: list[str] = field(default_factory=list)
    entities: list[EntityNode] = field(default_factory=list)
    relations: list[RelationEdge] = field(default_factory=list)
    length: int = 0


@dataclass
class SubgraphResult:
    """Subgraph query result."""
    
    entities: list[EntityNode] = field(default_factory=list)
    relations: list[RelationEdge] = field(default_factory=list)
    entity_count: int = 0
    relation_count: int = 0


class GraphStorage(ABC):
    """
    Abstract graph storage interface.
    
    Defines unified operations for:
    - Entity CRUD
    - Relation CRUD
    - Graph queries (neighbors, paths, subgraphs)
    
    Implementations:
    - PostgresGraphStorage: PostgreSQL backend
    - Neo4jGraphStorage: Neo4j backend
    - DualWriteCoordinator: Hybrid dual-write
    """
    
    @property
    @abstractmethod
    def backend(self) -> StorageBackend:
        """Return storage backend type."""
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if storage is connected."""
        pass
    
    # ===== Connection Management =====
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to storage backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to storage backend."""
        pass
    
    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check storage health status."""
        pass
    
    # ===== Entity Operations =====
    
    @abstractmethod
    async def create_entity(self, entity: EntityNode) -> str:
        """
        Create an entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            entity_id of created entity
            
        Raises:
            IntegrityError: If entity already exists
        """
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> EntityNode | None:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            EntityNode if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_entities(
        self, 
        entity_ids: list[str]
    ) -> list[EntityNode]:
        """
        Get multiple entities by IDs.
        
        Args:
            entity_ids: List of entity IDs
            
        Returns:
            List of found entities
        """
        pass
    
    @abstractmethod
    async def update_entity(
        self, 
        entity_id: str, 
        attributes: dict[str, Any]
    ) -> bool:
        """
        Update entity attributes.
        
        Args:
            entity_id: Entity ID
            attributes: Attributes to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def search_entities(
        self,
        query: str,
        entity_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EntityNode]:
        """
        Search entities by query.
        
        Args:
            query: Search query string
            entity_types: Filter by entity types
            filters: Additional filters
            limit: Max results
            offset: Offset for pagination
            
        Returns:
            List of matching entities
        """
        pass
    
    # ===== Relation Operations =====
    
    @abstractmethod
    async def create_relation(self, relation: RelationEdge) -> str:
        """
        Create a relation.
        
        Args:
            relation: Relation to create
            
        Returns:
            relation_id of created relation
        """
        pass
    
    @abstractmethod
    async def get_relation(self, relation_id: str) -> RelationEdge | None:
        """
        Get a relation by ID.
        
        Args:
            relation_id: Relation ID
            
        Returns:
            RelationEdge if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_relation(
        self,
        relation_id: str,
        attributes: dict[str, Any]
    ) -> bool:
        """
        Update relation attributes.
        
        Args:
            relation_id: Relation ID
            attributes: Attributes to update
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    async def delete_relation(self, relation_id: str) -> bool:
        """
        Delete a relation.
        
        Args:
            relation_id: Relation ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def get_relations_between(
        self,
        source_id: str,
        target_id: str,
        relation_types: list[str] | None = None
    ) -> list[RelationEdge]:
        """
        Get relations between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relation_types: Filter by relation types
            
        Returns:
            List of relations
        """
        pass
    
    # ===== Graph Query Operations =====
    
    @abstractmethod
    async def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 100
    ) -> list[tuple[EntityNode, RelationEdge]]:
        """
        Get neighbor entities and relations.
        
        Args:
            entity_id: Entity ID
            relation_types: Filter by relation types
            direction: "in", "out", or "both"
            limit: Max results
            
        Returns:
            List of (neighbor_entity, relation) tuples
        """
        pass
    
    @abstractmethod
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
        relation_types: list[str] | None = None
    ) -> PathResult:
        """
        Find path between two entities.
        
        Args:
            start_id: Start entity ID
            end_id: End entity ID
            max_depth: Maximum path depth
            relation_types: Filter by relation types
            
        Returns:
            PathResult with path and entities
        """
        pass
    
    @abstractmethod
    async def get_subgraph(
        self,
        entity_ids: list[str],
        depth: int = 1,
        relation_types: list[str] | None = None
    ) -> SubgraphResult:
        """
        Get subgraph around entities.
        
        Args:
            entity_ids: Seed entity IDs
            depth: Expansion depth
            relation_types: Filter by relation types
            
        Returns:
            SubgraphResult with entities and relations
        """
        pass
    
    # ===== Batch Operations =====
    
    @abstractmethod
    async def batch_create_entities(
        self,
        entities: list[EntityNode]
    ) -> list[str]:
        """
        Batch create entities.
        
        Args:
            entities: Entities to create
            
        Returns:
            List of created entity IDs
        """
        pass
    
    @abstractmethod
    async def batch_create_relations(
        self,
        relations: list[RelationEdge]
    ) -> list[str]:
        """
        Batch create relations.
        
        Args:
            relations: Relations to create
            
        Returns:
            List of created relation IDs
        """
        pass
    
    # ===== Statistics =====
    
    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            Dict with entity count, relation count, etc.
        """
        pass
    
    @abstractmethod
    async def count_entities(
        self,
        entity_type: str | None = None
    ) -> int:
        """
        Count entities.
        
        Args:
            entity_type: Filter by type (optional)
            
        Returns:
            Entity count
        """
        pass
    
    @abstractmethod
    async def count_relations(
        self,
        relation_type: str | None = None
    ) -> int:
        """
        Count relations.
        
        Args:
            relation_type: Filter by type (optional)
            
        Returns:
            Relation count
        """
        pass
