"""
Dual-Write Coordinator - Ensures data consistency between PostgreSQL and Neo4j.

Implements:
- Synchronous dual-write with rollback
- Asynchronous dual-write with retry queue
- Query routing based on operation type
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from openfinance.datacenter.graph.storage.base import (
    GraphStorage,
    StorageBackend,
    QueryResult,
    PathResult,
    SubgraphResult,
)
from openfinance.datacenter.graph.models import EntityNode, RelationEdge


logger = logging.getLogger(__name__)


class SyncMode(str, Enum):
    """Synchronization mode."""
    SYNC = "sync"       # Synchronous dual-write
    ASYNC = "async"     # Asynchronous dual-write
    EVENTUAL = "eventual"  # Eventual consistency


class SyncStatus(str, Enum):
    """Synchronization status."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SyncTask:
    """Synchronization task for async queue."""
    
    operation: str
    data: dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_error: str | None = None


class DualWriteCoordinator(GraphStorage):
    """
    Dual-write coordinator for PostgreSQL + Neo4j.
    
    Features:
    - Primary/secondary storage pattern
    - Synchronous or asynchronous sync mode
    - Automatic retry on failure
    - Query routing to optimal backend
    
    Usage:
        pg_storage = PostgresGraphStorage(database_url)
        neo4j_storage = Neo4jGraphStorage(uri, user, password)
        
        coordinator = DualWriteCoordinator(
            primary=pg_storage,
            secondary=neo4j_storage,
            sync_mode="async"
        )
        
        # Creates in both storages
        await coordinator.create_entity(entity)
        
        # Queries route to optimal backend
        path = await coordinator.find_path(start, end)  # -> Neo4j
        entity = await coordinator.get_entity(id)       # -> PostgreSQL
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
        retry_delay: float = 1.0,
        queue_size: int = 10000,
    ):
        self._primary = primary
        self._secondary = secondary
        self._sync_mode = SyncMode(sync_mode)
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._sync_queue: deque[SyncTask] = deque(maxlen=queue_size)
        self._sync_worker_task: asyncio.Task | None = None
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
        
        if primary_ok and secondary_ok and self._sync_mode == SyncMode.ASYNC:
            self._running = True
            self._sync_worker_task = asyncio.create_task(self._sync_worker())
        
        return primary_ok
    
    async def disconnect(self) -> None:
        self._running = False
        if self._sync_worker_task:
            self._sync_worker_task.cancel()
            try:
                await self._sync_worker_task
            except asyncio.CancelledError:
                pass
        
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
            "queue_size": len(self._sync_queue),
        }
    
    # ===== Sync Worker =====
    
    async def _sync_worker(self) -> None:
        """Background worker for async synchronization."""
        while self._running:
            try:
                if self._sync_queue:
                    task = self._sync_queue.popleft()
                    await self._process_sync_task(task)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync worker error: {e}")
                await asyncio.sleep(1)
    
    async def _process_sync_task(self, task: SyncTask) -> None:
        """Process a sync task."""
        try:
            if task.operation == "create_entity":
                entity = EntityNode(**task.data)
                await self._secondary.create_entity(entity)
            elif task.operation == "create_relation":
                relation = RelationEdge(**task.data)
                await self._secondary.create_relation(relation)
            elif task.operation == "update_entity":
                await self._secondary.update_entity(
                    task.data["entity_id"],
                    task.data["attributes"]
                )
            elif task.operation == "delete_entity":
                await self._secondary.delete_entity(task.data["entity_id"])
            elif task.operation == "delete_relation":
                await self._secondary.delete_relation(task.data["relation_id"])
            
            logger.debug(f"Synced: {task.operation}")
        except Exception as e:
            task.retry_count += 1
            task.last_error = str(e)
            
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                self._sync_queue.append(task)
                logger.warning(f"Retry {task.retry_count}/{task.max_retries}: {task.operation}")
            else:
                logger.error(f"Sync failed after {task.max_retries} retries: {task.operation}")
    
    def _queue_sync(self, operation: str, data: dict[str, Any]) -> None:
        """Queue a sync task for async processing."""
        task = SyncTask(
            operation=operation,
            data=data,
            max_retries=self._max_retries,
        )
        self._sync_queue.append(task)
    
    # ===== Entity Operations =====
    
    async def create_entity(self, entity: EntityNode) -> str:
        entity_id = await self._primary.create_entity(entity)
        
        if self._sync_mode == SyncMode.SYNC:
            try:
                await self._secondary.create_entity(entity)
            except Exception as e:
                await self._primary.delete_entity(entity_id)
                raise
        else:
            self._queue_sync("create_entity", entity.__dict__)
        
        return entity_id
    
    async def get_entity(self, entity_id: str) -> EntityNode | None:
        return await self._primary.get_entity(entity_id)
    
    async def get_entities(self, entity_ids: list[str]) -> list[EntityNode]:
        return await self._primary.get_entities(entity_ids)
    
    async def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> bool:
        success = await self._primary.update_entity(entity_id, attributes)
        
        if success:
            if self._sync_mode == SyncMode.SYNC:
                await self._secondary.update_entity(entity_id, attributes)
            else:
                self._queue_sync("update_entity", {
                    "entity_id": entity_id,
                    "attributes": attributes,
                })
        
        return success
    
    async def delete_entity(self, entity_id: str) -> bool:
        success = await self._primary.delete_entity(entity_id)
        
        if success:
            if self._sync_mode == SyncMode.SYNC:
                await self._secondary.delete_entity(entity_id)
            else:
                self._queue_sync("delete_entity", {"entity_id": entity_id})
        
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
        relation_id = await self._primary.create_relation(relation)
        
        if self._sync_mode == SyncMode.SYNC:
            try:
                await self._secondary.create_relation(relation)
            except Exception as e:
                await self._primary.delete_relation(relation_id)
                raise
        else:
            self._queue_sync("create_relation", relation.__dict__)
        
        return relation_id
    
    async def get_relation(self, relation_id: str) -> RelationEdge | None:
        return await self._primary.get_relation(relation_id)
    
    async def update_relation(self, relation_id: str, attributes: dict[str, Any]) -> bool:
        success = await self._primary.update_relation(relation_id, attributes)
        
        if success:
            if self._sync_mode == SyncMode.SYNC:
                await self._secondary.update_relation(relation_id, attributes)
            else:
                self._queue_sync("update_relation", {
                    "relation_id": relation_id,
                    "attributes": attributes,
                })
        
        return success
    
    async def delete_relation(self, relation_id: str) -> bool:
        success = await self._primary.delete_relation(relation_id)
        
        if success:
            if self._sync_mode == SyncMode.SYNC:
                await self._secondary.delete_relation(relation_id)
            else:
                self._queue_sync("delete_relation", {"relation_id": relation_id})
        
        return success
    
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
        
        return await self._primary.get_neighbors(
            entity_id, relation_types, direction, limit
        )
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
        relation_types: list[str] | None = None
    ) -> PathResult:
        try:
            if self._secondary.is_connected:
                return await self._secondary.find_path(
                    start_id, end_id, max_depth, relation_types
                )
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
                return await self._secondary.get_subgraph(
                    entity_ids, depth, relation_types
                )
        except Exception as e:
            logger.warning(f"Neo4j subgraph query failed, falling back to PostgreSQL: {e}")
        
        return await self._primary.get_subgraph(entity_ids, depth, relation_types)
    
    # ===== Batch Operations =====
    
    async def batch_create_entities(self, entities: list[EntityNode]) -> list[str]:
        ids = await self._primary.batch_create_entities(entities)
        
        if self._sync_mode == SyncMode.SYNC:
            await self._secondary.batch_create_entities(entities)
        else:
            for entity in entities:
                self._queue_sync("create_entity", entity.__dict__)
        
        return ids
    
    async def batch_create_relations(self, relations: list[RelationEdge]) -> list[str]:
        ids = await self._primary.batch_create_relations(relations)
        
        if self._sync_mode == SyncMode.SYNC:
            await self._secondary.batch_create_relations(relations)
        else:
            for relation in relations:
                self._queue_sync("create_relation", relation.__dict__)
        
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
            "queue_size": len(self._sync_queue),
        }
    
    async def count_entities(self, entity_type: str | None = None) -> int:
        return await self._primary.count_entities(entity_type)
    
    async def count_relations(self, relation_type: str | None = None) -> int:
        return await self._primary.count_relations(relation_type)
    
    # ===== Reconciliation =====
    
    async def reconcile(self) -> dict[str, Any]:
        """
        Reconcile data between primary and secondary storage.
        
        Returns:
            Reconciliation report
        """
        primary_stats = await self._primary.get_stats()
        secondary_stats = await self._secondary.get_stats()
        
        entity_diff = primary_stats.get("entity_count", 0) - secondary_stats.get("entity_count", 0)
        relation_diff = primary_stats.get("relation_count", 0) - secondary_stats.get("relation_count", 0)
        
        return {
            "primary": primary_stats,
            "secondary": secondary_stats,
            "entity_diff": entity_diff,
            "relation_diff": relation_diff,
            "needs_sync": entity_diff != 0 or relation_diff != 0,
        }
