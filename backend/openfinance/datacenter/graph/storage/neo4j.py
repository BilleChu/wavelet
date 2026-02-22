"""
Neo4j Graph Storage Adapter.

Implements GraphStorage interface using Neo4j graph database.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Any

from openfinance.datacenter.graph.storage.base import (
    GraphStorage,
    StorageBackend,
    QueryResult,
    PathResult,
    SubgraphResult,
)
from openfinance.datacenter.graph.models import EntityNode, RelationEdge


logger = logging.getLogger(__name__)

_neo4j_available = False
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    _neo4j_available = True
except ImportError:
    logger.warning("neo4j driver not installed. Neo4jGraphStorage will not be available.")


class Neo4jGraphStorage(GraphStorage):
    """
    Neo4j graph storage adapter.
    
    Features:
    - Native graph operations
    - Efficient path finding
    - Graph algorithms support
    - Relationship traversal
    
    Usage:
        storage = Neo4jGraphStorage(uri, user, password)
        await storage.connect()
        
        entity = EntityNode(entity_id="stock_000001", ...)
        await storage.create_entity(entity)
        
        # Find path
        path = await storage.find_path("stock_000001", "industry_bank")
    """
    
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str = "neo4j",
    ):
        if not _neo4j_available:
            raise ImportError("neo4j driver is required. Install with: pip install neo4j")
        
        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "")
        self._database = database
        self._driver: AsyncDriver | None = None
        self._connected = False
    
    @property
    def backend(self) -> StorageBackend:
        return StorageBackend.NEO4J
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> bool:
        try:
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            await self._driver.verify_connectivity()
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        if self._driver:
            await self._driver.close()
        self._connected = False
    
    async def health_check(self) -> dict[str, Any]:
        try:
            if not self._driver:
                return {
                    "status": "disconnected",
                    "backend": self.backend.value,
                    "connected": False,
                }
            
            result = await self._driver.execute_query(
                "RETURN 1 as test",
                database_=self._database,
            )
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
    
    # ===== Entity Operations =====
    
    async def create_entity(self, entity: EntityNode) -> str:
        query = """
        MERGE (n:Entity {id: $entity_id})
        SET n += $props
        SET n:`%s`
        RETURN n.id
        """ % entity.entity_type.upper()
        
        result = await self._driver.execute_query(
            query,
            entity_id=entity.entity_id,
            props=entity.to_neo4j_dict(),
            database_=self._database,
        )
        return entity.entity_id
    
    async def get_entity(self, entity_id: str) -> EntityNode | None:
        query = """
        MATCH (n:Entity {id: $entity_id})
        RETURN n
        """
        
        result = await self._driver.execute_query(
            query,
            entity_id=entity_id,
            database_=self._database,
        )
        
        if result.records:
            node = result.records[0]["n"]
            return EntityNode.from_neo4j_record(dict(node))
        return None
    
    async def get_entities(self, entity_ids: list[str]) -> list[EntityNode]:
        query = """
        MATCH (n:Entity)
        WHERE n.id IN $entity_ids
        RETURN n
        """
        
        result = await self._driver.execute_query(
            query,
            entity_ids=entity_ids,
            database_=self._database,
        )
        
        return [
            EntityNode.from_neo4j_record(dict(record["n"]))
            for record in result.records
        ]
    
    async def update_entity(self, entity_id: str, attributes: dict[str, Any]) -> bool:
        query = """
        MATCH (n:Entity {id: $entity_id})
        SET n += $attributes
        RETURN n.id
        """
        
        result = await self._driver.execute_query(
            query,
            entity_id=entity_id,
            attributes=attributes,
            database_=self._database,
        )
        return len(result.records) > 0
    
    async def delete_entity(self, entity_id: str) -> bool:
        query = """
        MATCH (n:Entity {id: $entity_id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        
        result = await self._driver.execute_query(
            query,
            entity_id=entity_id,
            database_=self._database,
        )
        return len(result.records) > 0
    
    async def search_entities(
        self,
        query: str,
        entity_types: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EntityNode]:
        where_clauses = []
        params = {"limit": limit, "offset": offset}
        
        if query:
            where_clauses.append("(n.name CONTAINS $query OR n.code CONTAINS $query)")
            params["query"] = query
        
        if entity_types:
            type_labels = [t.upper() for t in entity_types]
            params["types"] = type_labels
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        
        cypher = f"""
        MATCH (n:Entity)
        WHERE {where_clause}
        RETURN n
        SKIP $offset
        LIMIT $limit
        """
        
        if entity_types:
            cypher = f"""
            MATCH (n:Entity)
            WHERE {where_clause}
            AND any(label IN labels(n) WHERE label IN $types)
            RETURN n
            SKIP $offset
            LIMIT $limit
            """
        
        result = await self._driver.execute_query(
            cypher,
            database_=self._database,
            **params,
        )
        
        return [
            EntityNode.from_neo4j_record(dict(record["n"]))
            for record in result.records
        ]
    
    # ===== Relation Operations =====
    
    async def create_relation(self, relation: RelationEdge) -> str:
        rel_type = relation.relation_type.upper()
        query = f"""
        MATCH (source:Entity {{id: $source_id}})
        MATCH (target:Entity {{id: $target_id}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $props
        RETURN type(r)
        """
        
        await self._driver.execute_query(
            query,
            source_id=relation.source_id,
            target_id=relation.target_id,
            props=relation.to_neo4j_dict(),
            database_=self._database,
        )
        return relation.relation_id
    
    async def get_relation(self, relation_id: str) -> RelationEdge | None:
        query = """
        MATCH ()-[r {id: $relation_id}]->()
        RETURN r, startNode(r) as source, endNode(r) as target
        """
        
        result = await self._driver.execute_query(
            query,
            relation_id=relation_id,
            database_=self._database,
        )
        
        if result.records:
            record = result.records[0]
            rel = dict(record["r"])
            return RelationEdge.from_neo4j_record(
                {
                    **rel,
                    "source_id": dict(record["source"]).get("id"),
                    "target_id": dict(record["target"]).get("id"),
                },
                relation_id,
            )
        return None
    
    async def update_relation(self, relation_id: str, attributes: dict[str, Any]) -> bool:
        query = """
        MATCH ()-[r {id: $relation_id}]->()
        SET r += $attributes
        RETURN r.id
        """
        
        result = await self._driver.execute_query(
            query,
            relation_id=relation_id,
            attributes=attributes,
            database_=self._database,
        )
        return len(result.records) > 0
    
    async def delete_relation(self, relation_id: str) -> bool:
        query = """
        MATCH ()-[r {id: $relation_id}]->()
        DELETE r
        RETURN count(r) as deleted
        """
        
        result = await self._driver.execute_query(
            query,
            relation_id=relation_id,
            database_=self._database,
        )
        return len(result.records) > 0
    
    async def get_relations_between(
        self,
        source_id: str,
        target_id: str,
        relation_types: list[str] | None = None
    ) -> list[RelationEdge]:
        if relation_types:
            rel_pattern = "|".join(t.upper() for t in relation_types)
            query = f"""
            MATCH (source:Entity {{id: $source_id}})-[r:{rel_pattern}]->(target:Entity {{id: $target_id}})
            RETURN r, source.id as source_id, target.id as target_id
            """
        else:
            query = """
            MATCH (source:Entity {id: $source_id})-[r]->(target:Entity {id: $target_id})
            RETURN r, source.id as source_id, target.id as target_id
            """
        
        result = await self._driver.execute_query(
            query,
            source_id=source_id,
            target_id=target_id,
            database_=self._database,
        )
        
        relations = []
        for record in result.records:
            rel = dict(record["r"])
            relations.append(RelationEdge.from_neo4j_record(
                {
                    **rel,
                    "source_id": record["source_id"],
                    "target_id": record["target_id"],
                },
                rel.get("id", ""),
            ))
        return relations
    
    # ===== Graph Query Operations =====
    
    async def get_neighbors(
        self,
        entity_id: str,
        relation_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 100
    ) -> list[tuple[EntityNode, RelationEdge]]:
        if relation_types:
            rel_pattern = "|".join(t.upper() for t in relation_types)
        else:
            rel_pattern = ""
        
        if direction == "out":
            pattern = f"-[r:{rel_pattern}]->(n)"
        elif direction == "in":
            pattern = f"<-[r:{rel_pattern}]-(n)"
        else:
            pattern = f"-[r:{rel_pattern}]-(n)"
        
        query = f"""
        MATCH (start:Entity {{id: $entity_id}}){pattern}
        RETURN start, r, n
        LIMIT $limit
        """
        
        result = await self._driver.execute_query(
            query,
            entity_id=entity_id,
            limit=limit,
            database_=self._database,
        )
        
        neighbors = []
        for record in result.records:
            neighbor = EntityNode.from_neo4j_record(dict(record["n"]))
            rel = dict(record["r"])
            relation = RelationEdge.from_neo4j_record(
                {
                    **rel,
                    "source_id": dict(record["start"]).get("id"),
                    "target_id": dict(record["n"]).get("id"),
                },
                rel.get("id", ""),
            )
            neighbors.append((neighbor, relation))
        
        return neighbors
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
        relation_types: list[str] | None = None
    ) -> PathResult:
        if relation_types:
            rel_pattern = "|".join(t.upper() for t in relation_types)
            path_query = f"""
            MATCH path = shortestPath(
                (start:Entity {{id: $start_id}})-[:{rel_pattern}*1..{max_depth}]->
                (end:Entity {{id: $end_id}})
            )
            RETURN path
            """
        else:
            path_query = f"""
            MATCH path = shortestPath(
                (start:Entity {{id: $start_id}})-[*1..{max_depth}]->
                (end:Entity {{id: $end_id}})
            )
            RETURN path
            """
        
        result = await self._driver.execute_query(
            path_query,
            start_id=start_id,
            end_id=end_id,
            database_=self._database,
        )
        
        if not result.records:
            return PathResult(found=False)
        
        path = result.records[0]["path"]
        nodes = [dict(n) for n in path.nodes]
        relationships = [dict(r) for r in path.relationships]
        
        entities = [EntityNode.from_neo4j_record(n) for n in nodes]
        entity_ids = [e.entity_id for e in entities]
        
        return PathResult(
            found=True,
            path=entity_ids,
            entities=entities,
            length=len(relationships),
        )
    
    async def get_subgraph(
        self,
        entity_ids: list[str],
        depth: int = 1,
        relation_types: list[str] | None = None
    ) -> SubgraphResult:
        if relation_types:
            rel_pattern = "|".join(t.upper() for t in relation_types)
            query = f"""
            MATCH (n:Entity)
            WHERE n.id IN $entity_ids
            CALL apoc.path.subgraphAll(n, {{
                maxDepth: $depth,
                relationshipFilter: '{rel_pattern}'
            }})
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
        else:
            query = """
            MATCH (n:Entity)
            WHERE n.id IN $entity_ids
            CALL apoc.path.subgraphAll(n, {
                maxDepth: $depth
            })
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
        
        try:
            result = await self._driver.execute_query(
                query,
                entity_ids=entity_ids,
                depth=depth,
                database_=self._database,
            )
            
            if not result.records:
                entities = await self.get_entities(entity_ids)
                return SubgraphResult(
                    entities=entities,
                    relations=[],
                    entity_count=len(entities),
                    relation_count=0,
                )
            
            record = result.records[0]
            nodes = [dict(n) for n in record["nodes"]]
            relationships = [dict(r) for r in record["relationships"]]
            
            entities = [EntityNode.from_neo4j_record(n) for n in nodes]
            
            return SubgraphResult(
                entities=entities,
                relations=[],  # TODO: convert relationships
                entity_count=len(entities),
                relation_count=len(relationships),
            )
        except Exception as e:
            logger.warning(f"Subgraph query failed: {e}, using fallback")
            entities = await self.get_entities(entity_ids)
            return SubgraphResult(
                entities=entities,
                relations=[],
                entity_count=len(entities),
                relation_count=0,
            )
    
    # ===== Batch Operations =====
    
    async def batch_create_entities(self, entities: list[EntityNode]) -> list[str]:
        query = """
        UNWIND $entities AS entity
        MERGE (n:Entity {id: entity.entity_id})
        SET n += entity.props
        SET n:`%s`
        RETURN n.id
        """
        
        params = {
            "entities": [
                {
                    "entity_id": e.entity_id,
                    "props": e.to_neo4j_dict(),
                    "type": e.entity_type.upper(),
                }
                for e in entities
            ]
        }
        
        await self._driver.execute_query(
            query,
            database_=self._database,
            **params,
        )
        return [e.entity_id for e in entities]
    
    async def batch_create_relations(self, relations: list[RelationEdge]) -> list[str]:
        query = """
        UNWIND $relations AS rel
        MATCH (source:Entity {id: rel.source_id})
        MATCH (target:Entity {id: rel.target_id})
        CALL apoc.create.relationship(source, rel.type, rel.props, target) YIELD r
        RETURN r.id
        """
        
        params = {
            "relations": [
                {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "type": r.relation_type.upper(),
                    "props": r.to_neo4j_dict(),
                }
                for r in relations
            ]
        }
        
        try:
            await self._driver.execute_query(
                query,
                database_=self._database,
                **params,
            )
        except Exception:
            for r in relations:
                await self.create_relation(r)
        
        return [r.relation_id for r in relations]
    
    # ===== Statistics =====
    
    async def get_stats(self) -> dict[str, Any]:
        query = """
        MATCH (n:Entity)
        WITH count(n) as entity_count
        MATCH ()-[r]->()
        RETURN entity_count, count(r) as relation_count
        """
        
        result = await self._driver.execute_query(
            query,
            database_=self._database,
        )
        
        if result.records:
            record = result.records[0]
            return {
                "backend": self.backend.value,
                "entity_count": record["entity_count"],
                "relation_count": record["relation_count"],
            }
        
        return {
            "backend": self.backend.value,
            "entity_count": 0,
            "relation_count": 0,
        }
    
    async def count_entities(self, entity_type: str | None = None) -> int:
        if entity_type:
            query = f"""
            MATCH (n:`{entity_type.upper()}`)
            RETURN count(n) as count
            """
        else:
            query = "MATCH (n:Entity) RETURN count(n) as count"
        
        result = await self._driver.execute_query(
            query,
            database_=self._database,
        )
        
        if result.records:
            return result.records[0]["count"]
        return 0
    
    async def count_relations(self, relation_type: str | None = None) -> int:
        if relation_type:
            query = f"""
            MATCH ()-[r:`{relation_type.upper()}`]->()
            RETURN count(r) as count
            """
        else:
            query = "MATCH ()-[r]->() RETURN count(r) as count"
        
        result = await self._driver.execute_query(
            query,
            database_=self._database,
        )
        
        if result.records:
            return result.records[0]["count"]
        return 0
