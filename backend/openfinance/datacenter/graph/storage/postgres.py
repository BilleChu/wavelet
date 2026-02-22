"""
PostgreSQL Graph Storage Adapter.

Implements GraphStorage interface using PostgreSQL with JSONB.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Any

from sqlalchemy import select, delete, update, or_, and_, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError

from openfinance.datacenter.graph.storage.base import (
    GraphStorage,
    StorageBackend,
    QueryResult,
    PathResult,
    SubgraphResult,
)
from openfinance.datacenter.graph.models import EntityNode, RelationEdge


logger = logging.getLogger(__name__)


class PostgresGraphStorage(GraphStorage):
    """
    PostgreSQL graph storage adapter.
    
    Features:
    - Full entity/relation storage with JSONB attributes
    - Full-text search via GIN index
    - Batch operations
    - Transaction support
    
    Usage:
        storage = PostgresGraphStorage(database_url)
        await storage.connect()
        
        entity = EntityNode(entity_id="stock_000001", ...)
        await storage.create_entity(entity)
    """
    
    def __init__(
        self,
        database_url: str | None = None,
        session_maker: async_sessionmaker | None = None,
    ):
        self._database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://openfinance:openfinance@localhost:5432/openfinance"
        )
        self._session_maker = session_maker
        self._engine = None
        self._connected = False
    
    @property
    def backend(self) -> StorageBackend:
        return StorageBackend.POSTGRES
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> bool:
        if self._session_maker is not None:
            self._connected = True
            return True
        
        self._engine = create_async_engine(
            self._database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
        self._session_maker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
        self._connected = False
    
    async def health_check(self) -> dict[str, Any]:
        try:
            async with self._session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "backend": self.backend.value,
                    "connected": True,
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": self.backend.value,
                "connected": False,
                "error": str(e),
            }
    
    def _get_session(self) -> AsyncSession:
        if self._session_maker is None:
            raise RuntimeError("Storage not connected. Call connect() first.")
        return self._session_maker()
    
    # ===== Entity Operations =====
    
    async def create_entity(self, entity: EntityNode) -> str:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        import uuid
        
        async with self._get_session() as session:
            try:
                model = GenericEntityModel(
                    id=str(uuid.uuid4()),
                    **entity.to_pg_dict()
                )
                session.add(model)
                await session.commit()
                return entity.entity_id
            except IntegrityError:
                await session.rollback()
                raise
    
    async def get_entity(self, entity_id: str) -> EntityNode | None:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        
        async with self._get_session() as session:
            result = await session.execute(
                select(GenericEntityModel).where(
                    GenericEntityModel.entity_id == entity_id
                )
            )
            model = result.scalar_one_or_none()
            if model:
                return EntityNode.from_pg_model(model)
            return None
    
    async def get_entities(self, entity_ids: list[str]) -> list[EntityNode]:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        
        async with self._get_session() as session:
            result = await session.execute(
                select(GenericEntityModel).where(
                    GenericEntityModel.entity_id.in_(entity_ids)
                )
            )
            models = result.scalars().all()
            return [EntityNode.from_pg_model(m) for m in models]
    
    async def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> bool:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        
        async with self._get_session() as session:
            result = await session.execute(
                update(GenericEntityModel)
                .where(GenericEntityModel.entity_id == entity_id)
                .values(attributes=attributes, updated_at=datetime.utcnow())
            )
            await session.commit()
            return result.rowcount > 0
    
    async def delete_entity(self, entity_id: str) -> bool:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        
        async with self._get_session() as session:
            result = await session.execute(
                delete(GenericEntityModel).where(
                    GenericEntityModel.entity_id == entity_id
                )
            )
            await session.commit()
            return result.rowcount > 0
    
    async def search_entities(
        self,
        query: str,
        entity_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EntityNode]:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        
        async with self._get_session() as session:
            stmt = select(GenericEntityModel)
            
            if query:
                stmt = stmt.where(
                    or_(
                        GenericEntityModel.name.ilike(f"%{query}%"),
                        GenericEntityModel.code.ilike(f"%{query}%"),
                    )
                )
            
            if entity_types:
                stmt = stmt.where(GenericEntityModel.entity_type.in_(entity_types))
            
            stmt = stmt.offset(offset).limit(limit)
            
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [EntityNode.from_pg_model(m) for m in models]
    
    # ===== Relation Operations =====
    
    async def create_relation(self, relation: RelationEdge) -> str:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        import uuid
        
        async with self._get_session() as session:
            try:
                model = GenericRelationModel(
                    id=str(uuid.uuid4()),
                    **relation.to_pg_dict()
                )
                session.add(model)
                await session.commit()
                return relation.relation_id
            except IntegrityError:
                await session.rollback()
                raise
    
    async def get_relation(self, relation_id: str) -> RelationEdge | None:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        
        async with self._get_session() as session:
            result = await session.execute(
                select(GenericRelationModel).where(
                    GenericRelationModel.relation_id == relation_id
                )
            )
            model = result.scalar_one_or_none()
            if model:
                return RelationEdge.from_pg_model(model)
            return None
    
    async def update_relation(self, relation_id: str, attributes: dict[str, Any]) -> bool:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        
        async with self._get_session() as session:
            result = await session.execute(
                update(GenericRelationModel)
                .where(GenericRelationModel.relation_id == relation_id)
                .values(attributes=attributes, updated_at=datetime.utcnow())
            )
            await session.commit()
            return result.rowcount > 0
    
    async def delete_relation(self, relation_id: str) -> bool:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        
        async with self._get_session() as session:
            result = await session.execute(
                delete(GenericRelationModel).where(
                    GenericRelationModel.relation_id == relation_id
                )
            )
            await session.commit()
            return result.rowcount > 0
    
    async def get_relations_between(
        self,
        source_id: str,
        target_id: str,
        relation_types: list[str] | None = None
    ) -> list[RelationEdge]:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        
        async with self._get_session() as session:
            stmt = select(GenericRelationModel).where(
                and_(
                    GenericRelationModel.source_entity_id == source_id,
                    GenericRelationModel.target_entity_id == target_id,
                )
            )
            if relation_types:
                stmt = stmt.where(GenericRelationModel.relation_type.in_(relation_types))
            
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [RelationEdge.from_pg_model(m) for m in models]
    
    # ===== Graph Query Operations =====
    
    async def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 100
    ) -> list[tuple[EntityNode, RelationEdge]]:
        from openfinance.domain.schemas.generic_model import (
            GenericEntityModel,
            GenericRelationModel,
        )
        
        async with self._get_session() as session:
            conditions = []
            if direction in ("out", "both"):
                conditions.append(GenericRelationModel.source_entity_id == entity_id)
            if direction in ("in", "both"):
                conditions.append(GenericRelationModel.target_entity_id == entity_id)
            
            stmt = select(GenericRelationModel).where(or_(*conditions))
            if relation_types:
                stmt = stmt.where(GenericRelationModel.relation_type.in_(relation_types))
            stmt = stmt.limit(limit)
            
            result = await session.execute(stmt)
            relations = result.scalars().all()
            
            neighbor_ids = set()
            for rel in relations:
                if rel.source_entity_id != entity_id:
                    neighbor_ids.add(rel.source_entity_id)
                if rel.target_entity_id != entity_id:
                    neighbor_ids.add(rel.target_entity_id)
            
            if not neighbor_ids:
                return []
            
            entities_result = await session.execute(
                select(GenericEntityModel).where(
                    GenericEntityModel.entity_id.in_(neighbor_ids)
                )
            )
            entities = {e.entity_id: e for e in entities_result.scalars().all()}
            
            results = []
            for rel in relations:
                neighbor_id = (
                    rel.target_entity_id 
                    if rel.source_entity_id == entity_id 
                    else rel.source_entity_id
                )
                if neighbor_id in entities:
                    neighbor = EntityNode.from_pg_model(entities[neighbor_id])
                    relation = RelationEdge.from_pg_model(rel)
                    results.append((neighbor, relation))
            
            return results
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
        relation_types: list[str] | None = None
    ) -> PathResult:
        """
        Find path using BFS.
        
        Note: For complex path queries, Neo4j is recommended.
        """
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        
        if start_id == end_id:
            entity = await self.get_entity(start_id)
            return PathResult(
                found=True,
                path=[start_id],
                entities=[entity] if entity else [],
                length=0,
            )
        
        visited = {start_id}
        queue = deque([(start_id, [start_id])])
        
        async with self._get_session() as session:
            while queue and len(queue[0][1]) <= max_depth:
                current_id, path = queue.popleft()
                
                if current_id == end_id:
                    entities = await self.get_entities(path)
                    return PathResult(
                        found=True,
                        path=path,
                        entities=entities,
                        length=len(path) - 1,
                    )
                
                stmt = select(GenericRelationModel).where(
                    or_(
                        GenericRelationModel.source_entity_id == current_id,
                        GenericRelationModel.target_entity_id == current_id,
                    )
                )
                if relation_types:
                    stmt = stmt.where(
                        GenericRelationModel.relation_type.in_(relation_types)
                    )
                
                result = await session.execute(stmt)
                relations = result.scalars().all()
                
                for rel in relations:
                    neighbor_id = (
                        rel.target_entity_id 
                        if rel.source_entity_id == current_id 
                        else rel.source_entity_id
                    )
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, path + [neighbor_id]))
        
        return PathResult(found=False)
    
    async def get_subgraph(
        self,
        entity_ids: list[str],
        depth: int = 1,
        relation_types: list[str] | None = None
    ) -> SubgraphResult:
        from openfinance.domain.schemas.generic_model import (
            GenericEntityModel,
            GenericRelationModel,
        )
        
        all_entity_ids = set(entity_ids)
        all_relations = []
        
        async with self._get_session() as session:
            current_ids = set(entity_ids)
            
            for _ in range(depth):
                if not current_ids:
                    break
                
                conditions = [
                    GenericRelationModel.source_entity_id.in_(current_ids),
                    GenericRelationModel.target_entity_id.in_(current_ids),
                ]
                stmt = select(GenericRelationModel).where(or_(*conditions))
                if relation_types:
                    stmt = stmt.where(
                        GenericRelationModel.relation_type.in_(relation_types)
                    )
                
                result = await session.execute(stmt)
                relations = result.scalars().all()
                
                new_ids = set()
                for rel in relations:
                    all_relations.append(rel)
                    if rel.source_entity_id not in all_entity_ids:
                        new_ids.add(rel.source_entity_id)
                    if rel.target_entity_id not in all_entity_ids:
                        new_ids.add(rel.target_entity_id)
                
                current_ids = new_ids
                all_entity_ids.update(new_ids)
            
            entities_result = await session.execute(
                select(GenericEntityModel).where(
                    GenericEntityModel.entity_id.in_(all_entity_ids)
                )
            )
            entities = entities_result.scalars().all()
            
            return SubgraphResult(
                entities=[EntityNode.from_pg_model(e) for e in entities],
                relations=[RelationEdge.from_pg_model(r) for r in all_relations],
                entity_count=len(entities),
                relation_count=len(all_relations),
            )
    
    # ===== Batch Operations =====
    
    async def batch_create_entities(self, entities: list[EntityNode]) -> list[str]:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        import uuid
        
        async with self._get_session() as session:
            models = [
                GenericEntityModel(id=str(uuid.uuid4()), **e.to_pg_dict())
                for e in entities
            ]
            session.add_all(models)
            await session.commit()
            return [e.entity_id for e in entities]
    
    async def batch_create_relations(self, relations: list[RelationEdge]) -> list[str]:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        import uuid
        
        async with self._get_session() as session:
            models = [
                GenericRelationModel(id=str(uuid.uuid4()), **r.to_pg_dict())
                for r in relations
            ]
            session.add_all(models)
            await session.commit()
            return [r.relation_id for r in relations]
    
    # ===== Statistics =====
    
    async def get_stats(self) -> dict[str, Any]:
        from openfinance.domain.schemas.generic_model import (
            GenericEntityModel,
            GenericRelationModel,
        )
        
        async with self._get_session() as session:
            entity_count = await session.scalar(
                select(func.count()).select_from(GenericEntityModel)
            )
            relation_count = await session.scalar(
                select(func.count()).select_from(GenericRelationModel)
            )
            
            type_counts = await session.execute(
                select(
                    GenericEntityModel.entity_type,
                    func.count().label("count")
                ).group_by(GenericEntityModel.entity_type)
            )
            
            return {
                "backend": self.backend.value,
                "entity_count": entity_count or 0,
                "relation_count": relation_count or 0,
                "entity_types": {row[0]: row[1] for row in type_counts},
            }
    
    async def count_entities(self, entity_type: str | None = None) -> int:
        from openfinance.domain.schemas.generic_model import GenericEntityModel
        
        async with self._get_session() as session:
            stmt = select(func.count()).select_from(GenericEntityModel)
            if entity_type:
                stmt = stmt.where(GenericEntityModel.entity_type == entity_type)
            return await session.scalar(stmt) or 0
    
    async def count_relations(self, relation_type: str | None = None) -> int:
        from openfinance.domain.schemas.generic_model import GenericRelationModel
        
        async with self._get_session() as session:
            stmt = select(func.count()).select_from(GenericRelationModel)
            if relation_type:
                stmt = stmt.where(GenericRelationModel.relation_type == relation_type)
            return await session.scalar(stmt) or 0
