"""
Knowledge Graph Service - Business-level service.

Provides high-level API for knowledge graph operations.
"""

from __future__ import annotations

import logging
from typing import Any

from openfinance.datacenter.graph.models import EntityNode, RelationEdge
from openfinance.datacenter.graph.storage import (
    GraphStorage,
    StorageBackend,
    get_graph_storage,
)


logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """
    Knowledge graph business service.
    
    Features:
    - Entity and relation management
    - Graph queries
    - Statistics and monitoring
    """
    
    def __init__(self, storage: GraphStorage | None = None):
        self._storage = storage
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the service."""
        if self._storage is None:
            self._storage = get_graph_storage()
        
        if not self._storage.is_connected:
            await self._storage.connect()
        
        self._initialized = True
        logger.info(f"KnowledgeGraphService initialized: {self._storage.backend.value}")
    
    async def shutdown(self) -> None:
        """Shutdown the service."""
        if self._storage:
            await self._storage.disconnect()
        self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def backend(self) -> StorageBackend:
        return self._storage.backend if self._storage else StorageBackend.POSTGRES
    
    # ===== Entity Operations =====
    
    async def create_entity(
        self,
        entity_type: str,
        name: str,
        code: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> str:
        """Create an entity."""
        entity = EntityNode(
            entity_id=f"{entity_type}_{code}" if code else f"{entity_type}_{name}",
            entity_type=entity_type,
            name=name,
            code=code,
            attributes=attributes or {},
        )
        return await self._storage.create_entity(entity)
    
    async def get_entity(self, entity_id: str) -> EntityNode | None:
        """Get an entity."""
        return await self._storage.get_entity(entity_id)
    
    async def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> bool:
        """Update an entity."""
        return await self._storage.update_entity(entity_id, attributes)
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity."""
        return await self._storage.delete_entity(entity_id)
    
    async def search_entities(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[EntityNode]:
        """Search entities."""
        return await self._storage.search_entities(query, entity_types, limit=limit)
    
    # ===== Relation Operations =====
    
    async def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
    ) -> str:
        """Create a relation."""
        relation = RelationEdge(
            relation_id=f"rel_{source_id}_{relation_type}_{target_id}",
            relation_type=relation_type,
            source_id=source_id,
            target_id=target_id,
            weight=weight,
        )
        return await self._storage.create_relation(relation)
    
    async def delete_relation(self, relation_id: str) -> bool:
        """Delete a relation."""
        return await self._storage.delete_relation(relation_id)
    
    # ===== Graph Query Operations =====
    
    async def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[tuple[EntityNode, RelationEdge]]:
        """Get neighbors."""
        return await self._storage.get_neighbors(entity_id, relation_types, direction, limit)
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """Find path between entities."""
        result = await self._storage.find_path(start_id, end_id, max_depth)
        return {
            "found": result.found,
            "path": result.path,
            "length": result.length,
        }
    
    async def get_subgraph(
        self,
        entity_ids: list[str],
        depth: int = 1,
    ) -> dict[str, Any]:
        """Get subgraph."""
        result = await self._storage.get_subgraph(entity_ids, depth)
        return {
            "entities": [{"id": e.entity_id, "name": e.name, "type": e.entity_type} for e in result.entities],
            "relations": [{"id": r.relation_id, "type": r.relation_type} for r in result.relations],
            "entity_count": result.entity_count,
            "relation_count": result.relation_count,
        }
    
    # ===== Statistics =====
    
    async def get_stats(self) -> dict[str, Any]:
        """Get statistics."""
        return await self._storage.get_stats()
    
    async def get_data_quality_report(self) -> dict[str, Any]:
        """Get data quality report."""
        stats = await self._storage.get_stats()
        return {
            "total_entities": stats.get("entity_count", 0),
            "total_relations": stats.get("relation_count", 0),
            "backend": self._storage.backend.value,
        }


# Singleton
_service: KnowledgeGraphService | None = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get the global service instance."""
    global _service
    if _service is None:
        _service = KnowledgeGraphService()
    return _service
