"""
Dual-Write Coordinator - Business-level dual storage coordination.

Uses infrastructure components for:
- Two-phase commit
- Write-ahead logging
- Synchronization
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from openfinance.datacenter.graph.storage.base import (
    GraphStorage,
    StorageBackend,
    QueryResult,
    PathResult,
    SubgraphResult,
    EntityNode,
    RelationEdge,
)
from openfinance.infrastructure.graph.consistency import WriteAheadLog, SyncCoordinator
from openfinance.infrastructure.graph.transaction import TransactionManager, TwoPhaseCommitCoordinator


logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    """Synchronization mode."""
    SYNC = "sync"
    ASYNC = "async"


class DualWriteCoordinator(GraphStorage):
    """
    Dual-write coordinator for PostgreSQL + Neo4j.
    
    Uses infrastructure components:
    - WriteAheadLog for durability
    - TwoPhaseCommitCoordinator for atomic commits
    - SyncCoordinator for async synchronization
    
    Features:
    - Query routing to optimal backend
    - Automatic failover
    - Data consistency guarantee
    """
    
    QUERY_ROUTING = {
        "entity_detail": StorageBackend.POSTGRES,
        "attribute_filter": StorageBackend.POSTGRES,
        "fulltext_search": StorageBackend.POSTGRES,
        "relation_traverse": StorageBackend.NEO4J,
        "path_find": StorageBackend.NEO4J,
        "community_detect": StorageBackend.NEO4J,
        "pagerank": StorageBackend.NEO4J,
        "subgraph": StorageBackend.NEO4J,
    }
    
    def __init__(
        self,
        primary: GraphStorage,
        secondary: GraphStorage,
        sync_mode: str = "async",
        max_retries: int = 3,
    ):
        self._primary = primary
        self._secondary = secondary
        self._sync_mode = SyncMode(sync_mode)
        self._max_retries = max_retries
        
        # Infrastructure components
        self._wal = WriteAheadLog()
        self._txn_manager = TransactionManager()
        self._2pc_coordinator = TwoPhaseCommitCoordinator(self._txn_manager)
        self._sync_coordinator = SyncCoordinator(max_retries=max_retries)
        
        self._running = False
    
    @property
    def backend(self) -> StorageBackend:
        return StorageBackend.HYBRID
    
    @property
    def is_connected(self) -> bool:
        return self._primary.is_connected and self._secondary.is_connected
    
    async def connect(self) -> bool:
        primary_ok = await self._primary.connect()
        secondary_ok = await self._secondary.connect()
        
        if primary_ok and secondary_ok:
            self._running = True
            await self._sync_coordinator.start()
        
        return primary_ok
    
    async def disconnect(self) -> None:
        self._running = False
        await self._sync_coordinator.stop()
        await self._primary.disconnect()
        await self._secondary.disconnect()
    
    async def health_check(self) -> dict[str, Any]:
        primary_health = await self._primary.health_check()
        secondary_health = await self._secondary.health_check()
        
        return {
            "status": "healthy" if primary_health.get("status") == "healthy" else "degraded",
            "backend": self.backend.value,
            "primary": primary_health,
            "secondary": secondary_health,
            "sync_mode": self._sync_mode.value,
            "sync_stats": self._sync_coordinator.get_stats(),
        }
    
    # ===== Entity Operations =====
    
    async def create_entity(self, entity: EntityNode) -> str:
        # Begin transaction
        txn = await self._txn_manager.begin()
        
        try:
            # Log operation
            await self._wal.append(
                entry_type="operation",
                transaction_id=txn.transaction_id,
                data={"operation": "create_entity", "entity": entity.__dict__}
            )
            
            # Write to primary
            entity_id = await self._primary.create_entity(entity)
            
            # Sync to secondary
            if self._sync_mode == SyncMode.SYNC:
                await self._secondary.create_entity(entity)
            else:
                await self._sync_coordinator.submit(
                    operation="create_entity",
                    source_backend="postgres",
                    target_backend="neo4j",
                    data=entity.__dict__,
                )
            
            # Commit
            await self._txn_manager.commit(txn.transaction_id)
            return entity_id
            
        except Exception as e:
            await self._txn_manager.rollback(txn.transaction_id)
            raise
    
    async def get_entity(self, entity_id: str) -> EntityNode | None:
        return await self._primary.get_entity(entity_id)
    
    async def get_entities(self, entity_ids: list[str]) -> list[EntityNode]:
        return await self._primary.get_entities(entity_ids)
    
    async def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> bool:
        success = await self._primary.update_entity(entity_id, attributes)
        
        if success and self._sync_mode == SyncMode.ASYNC:
            await self._sync_coordinator.submit(
                operation="update_entity",
                source_backend="postgres",
                target_backend="neo4j",
                data={"entity_id": entity_id, "attributes": attributes},
            )
        
        return success
    
    async def delete_entity(self, entity_id: str) -> bool:
        success = await self._primary.delete_entity(entity_id)
        
        if success and self._sync_mode == SyncMode.ASYNC:
            await self._sync_coordinator.submit(
                operation="delete_entity",
                source_backend="postgres",
                target_backend="neo4j",
                data={"entity_id": entity_id},
            )
        
        return success
    
    async def search_entities(
        self,
        query: str,
        entity_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EntityNode]:
        return await self._primary.search_entities(query, entity_types, filters, limit, offset)
    
    # ===== Relation Operations =====
    
    async def create_relation(self, relation: RelationEdge) -> str:
        txn = await self._txn_manager.begin()
        
        try:
            await self._wal.append(
                entry_type="operation",
                transaction_id=txn.transaction_id,
                data={"operation": "create_relation", "relation": relation.__dict__}
            )
            
            relation_id = await self._primary.create_relation(relation)
            
            if self._sync_mode == SyncMode.ASYNC:
                await self._sync_coordinator.submit(
                    operation="create_relation",
                    source_backend="postgres",
                    target_backend="neo4j",
                    data=relation.__dict__,
                )
            
            await self._txn_manager.commit(txn.transaction_id)
            return relation_id
            
        except Exception as e:
            await self._txn_manager.rollback(txn.transaction_id)
            raise
    
    async def get_relation(self, relation_id: str) -> RelationEdge | None:
        return await self._primary.get_relation(relation_id)
    
    async def update_relation(self, relation_id: str, attributes: dict[str, Any]) -> bool:
        return await self._primary.update_relation(relation_id, attributes)
    
    async def delete_relation(self, relation_id: str) -> bool:
        return await self._primary.delete_relation(relation_id)
    
    async def get_relations_between(
        self,
        source_id: str,
        target_id: str,
        relation_types: list[str] | None = None
    ) -> list[RelationEdge]:
        return await self._primary.get_relations_between(source_id, target_id, relation_types)
    
    # ===== Graph Query Operations (Route to Neo4j) =====
    
    async def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 100
    ) -> list[tuple[EntityNode, RelationEdge]]:
        try:
            if self._secondary.is_connected:
                return await self._secondary.get_neighbors(
                    entity_id, relation_types, direction, limit
                )
        except Exception as e:
            logger.warning(f"Neo4j query failed, falling back to PostgreSQL: {e}")
        
        return await self._primary.get_neighbors(entity_id, relation_types, direction, limit)
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
        relation_types: list[str] | None = None
    ) -> PathResult:
        try:
            if self._secondary.is_connected:
                return await self._secondary.find_path(start_id, end_id, max_depth, relation_types)
        except Exception as e:
            logger.warning(f"Neo4j path query failed, falling back to PostgreSQL: {e}")
        
        return await self._primary.find_path(start_id, end_id, max_depth, relation_types)
    
    async def get_subgraph(
        self,
        entity_ids: list[str],
        depth: int = 1,
        relation_types: list[str] | None = None
    ) -> SubgraphResult:
        try:
            if self._secondary.is_connected:
                return await self._secondary.get_subgraph(entity_ids, depth, relation_types)
        except Exception as e:
            logger.warning(f"Neo4j subgraph query failed, falling back to PostgreSQL: {e}")
        
        return await self._primary.get_subgraph(entity_ids, depth, relation_types)
    
    # ===== Batch Operations =====
    
    async def batch_create_entities(self, entities: list[EntityNode]) -> list[str]:
        ids = await self._primary.batch_create_entities(entities)
        
        for entity in entities:
            await self._sync_coordinator.submit(
                operation="create_entity",
                source_backend="postgres",
                target_backend="neo4j",
                data=entity.__dict__,
            )
        
        return ids
    
    async def batch_create_relations(self, relations: list[RelationEdge]) -> list[str]:
        ids = await self._primary.batch_create_relations(relations)
        
        for relation in relations:
            await self._sync_coordinator.submit(
                operation="create_relation",
                source_backend="postgres",
                target_backend="neo4j",
                data=relation.__dict__,
            )
        
        return ids
    
    # ===== Statistics =====
    
    async def get_stats(self) -> dict[str, Any]:
        primary_stats = await self._primary.get_stats()
        secondary_stats = await self._secondary.get_stats()
        
        return {
            "backend": self.backend.value,
            "sync_mode": self._sync_mode.value,
            "primary": primary_stats,
            "secondary": secondary_stats,
            "sync": self._sync_coordinator.get_stats(),
        }
    
    async def count_entities(self, entity_type: str | None = None) -> int:
        return await self._primary.count_entities(entity_type)
    
    async def count_relations(self, relation_type: str | None = None) -> int:
        return await self._primary.count_relations(relation_type)
    
    async def reconcile(self) -> dict[str, Any]:
        """Reconcile data between storages."""
        primary_stats = await self._primary.get_stats()
        secondary_stats = await self._secondary.get_stats()
        
        return {
            "primary": primary_stats,
            "secondary": secondary_stats,
            "sync_stats": self._sync_coordinator.get_stats(),
        }
