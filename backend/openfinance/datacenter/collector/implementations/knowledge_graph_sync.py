"""
Knowledge Graph Synchronizer for Company, Industry, and Concept relationships.

Syncs company-industry and company-concept relationships to PostgreSQL and Neo4j knowledge graph.
"""

import asyncio
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.infrastructure.database.database import async_session_maker
from openfinance.datacenter.models import (
    EntityModel,
    RelationModel,
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
)

logger = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://data.eastmoney.com/",
}

EASTMONEY_INDUSTRY_LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_INDUSTRY_MEMBER_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_COMPANY_PROFILE_URL = "https://emweb.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax"

_neo4j_driver = None


async def get_neo4j_driver():
    """Get or create Neo4j driver singleton."""
    global _neo4j_driver
    
    if _neo4j_driver is not None:
        return _neo4j_driver
    
    try:
        from neo4j import AsyncGraphDatabase
        
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "openfinance123")
        
        _neo4j_driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )
        await _neo4j_driver.verify_connectivity()
        logger.info("Connected to Neo4j for dual-write")
        return _neo4j_driver
    except ImportError:
        logger.warning("neo4j driver not installed, Neo4j sync disabled")
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to Neo4j: {e}, Neo4j sync disabled")
        return None


async def sync_entity_to_neo4j(
    entity_id: str,
    name: str,
    entity_type: str,
    code: str | None = None,
    industry: str | None = None,
    source: str | None = None,
) -> bool:
    """Sync a single entity to Neo4j."""
    driver = await get_neo4j_driver()
    if driver is None:
        return False
    
    try:
        async with driver.session() as session:
            query = """
            MERGE (e:Entity {id: $entity_id})
            SET e.name = $name,
                e.type = $entity_type,
                e.code = $code,
                e.industry = $industry,
                e.source = $source
            """
            await session.run(
                query,
                entity_id=entity_id,
                name=name,
                entity_type=entity_type,
                code=code or "",
                industry=industry or "",
                source=source or "",
            )
            return True
    except Exception as e:
        logger.debug(f"Failed to sync entity to Neo4j: {e}")
        return False


async def sync_relation_to_neo4j(
    source_entity_id: str,
    target_entity_id: str,
    relation_type: str,
) -> bool:
    """Sync a single relation to Neo4j."""
    driver = await get_neo4j_driver()
    if driver is None:
        return False
    
    try:
        rel_type = relation_type.upper().replace("-", "_")
        
        async with driver.session() as session:
            query = f"""
            MATCH (source:Entity {{id: $source_id}})
            MATCH (target:Entity {{id: $target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            """
            await session.run(
                query,
                source_id=source_entity_id,
                target_id=target_entity_id,
            )
            return True
    except Exception as e:
        logger.debug(f"Failed to sync relation to Neo4j: {e}")
        return False


@dataclass
class SyncStats:
    """Statistics for sync operation."""
    
    industries_created: int = 0
    concepts_created: int = 0
    companies_updated: int = 0
    relations_created: int = 0
    relations_updated: int = 0
    errors: list[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class KnowledgeGraphSynchronizer:
    """
    Synchronizes company, industry, and concept relationships to knowledge graph.
    
    Features:
    - Fetches industry/concept lists from EastMoney
    - Fetches industry/concept member stocks
    - Syncs entities and relations to PostgreSQL knowledge graph
    - Supports incremental updates
    """
    
    def __init__(self, batch_size: int = 100, max_concurrent: int = 5) -> None:
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self._session: aiohttp.ClientSession | None = None
        self._stats = SyncStats()
        self._industry_cache: dict[str, str] = {}
        self._concept_cache: dict[str, str] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                connector=connector,
            )
        return self._session
    
    async def _fetch_with_retry(
        self,
        url: str,
        params: dict[str, Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        session = await self._get_session()
        
        for attempt in range(max_retries):
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.debug(f"Failed to fetch {url}: {e}")
        
        return {}
    
    async def fetch_industry_list(self, industry_type: str = "industry") -> list[dict[str, Any]]:
        """Fetch industry or concept list from EastMoney."""
        fs_map = {
            "industry": "m:90 t:2 f:!50",
            "concept": "m:90 t:3 f:!50",
        }
        
        params = {
            "pn": 1,
            "pz": 500,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs_map.get(industry_type, fs_map["industry"]),
            "fields": "f12,f14",
        }
        
        data = await self._fetch_with_retry(EASTMONEY_INDUSTRY_LIST_URL, params)
        
        results = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                results.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "type": industry_type,
                })
        
        return results
    
    async def fetch_industry_members(self, industry_code: str) -> list[dict[str, Any]]:
        """Fetch member stocks of an industry/concept."""
        fs = f"b:{industry_code} f:!50"
        
        all_members = []
        page = 1
        
        while True:
            params = {
                "pn": page,
                "pz": 100,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": fs,
                "fields": "f12,f14",
            }
            
            data = await self._fetch_with_retry(EASTMONEY_INDUSTRY_MEMBER_URL, params)
            
            if not data.get("data") or not data["data"].get("diff"):
                break
            
            total = data["data"].get("total", 0)
            diff = data["data"].get("diff", [])
            
            for item in diff:
                all_members.append({
                    "stock_code": item.get("f12", ""),
                    "stock_name": item.get("f14", ""),
                })
            
            if len(all_members) >= total:
                break
            
            page += 1
        
        return all_members
    
    async def fetch_company_industry(self, stock_code: str) -> dict[str, str | None]:
        """Fetch industry classification for a single stock."""
        secid = ""
        if stock_code.startswith("6"):
            secid = f"SH{stock_code}"
        elif stock_code.startswith(("0", "3")):
            secid = f"SZ{stock_code}"
        elif stock_code.startswith(("4", "8")):
            secid = f"BJ{stock_code}"
        else:
            return {"industry": None, "sector": None}
        
        params = {"code": secid}
        data = await self._fetch_with_retry(EASTMONEY_COMPANY_PROFILE_URL, params)
        
        jbzl = data.get("jbzl", {})
        return {
            "industry": jbzl.get("hymc"),
            "sector": jbzl.get("sshy"),
        }
    
    async def sync_industry_entities(
        self,
        session: AsyncSession,
        industries: list[dict[str, Any]],
        entity_type: str = "industry",
    ) -> dict[str, str]:
        """Sync industry/concept entities to knowledge graph (PostgreSQL + Neo4j)."""
        entity_map = {}
        
        for industry in industries:
            code = industry.get("code", "")
            name = industry.get("name", "")
            
            if not code or not name:
                continue
            
            entity_id = f"{entity_type}_{code}"
            
            stmt = select(EntityModel).where(EntityModel.entity_id == entity_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if not existing:
                entity = EntityModel(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    entity_type=entity_type,
                    name=name,
                    code=code,
                    properties={"type": industry.get("type", entity_type)},
                    source="eastmoney",
                )
                session.add(entity)
                
                if entity_type == "industry":
                    self._stats.industries_created += 1
                else:
                    self._stats.concepts_created += 1
            
            entity_map[code] = entity_id
            
            await sync_entity_to_neo4j(
                entity_id=entity_id,
                name=name,
                entity_type=entity_type,
                code=code,
                source="eastmoney",
            )
        
        return entity_map
    
    async def sync_company_entity(
        self,
        session: AsyncSession,
        stock_code: str,
        stock_name: str,
        industry: str | None = None,
        sector: str | None = None,
    ) -> str:
        """Sync or update company entity in knowledge graph (PostgreSQL + Neo4j)."""
        entity_id = f"company_{stock_code}"
        
        stmt = insert(EntityModel).values(
            id=str(uuid.uuid4()),
            entity_id=entity_id,
            entity_type="company",
            name=stock_name,
            code=stock_code,
            industry=industry,
            properties={"sector": sector} if sector else {},
            source="eastmoney",
        ).on_conflict_do_update(
            index_elements=["entity_id"],
            set_={
                "name": stock_name,
                "industry": industry,
                "updated_at": datetime.now(),
            },
        )
        
        await session.execute(stmt)
        self._stats.companies_updated += 1
        
        await sync_entity_to_neo4j(
            entity_id=entity_id,
            name=stock_name,
            entity_type="company",
            code=stock_code,
            industry=industry,
            source="eastmoney",
        )
        
        return entity_id
    
    async def sync_relation(
        self,
        session: AsyncSession,
        source_entity_id: str,
        target_entity_id: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Sync relation between entities (PostgreSQL + Neo4j)."""
        relation_id = f"{source_entity_id}_{relation_type}_{target_entity_id}"
        
        stmt = insert(RelationModel).values(
            id=str(uuid.uuid4()),
            relation_id=relation_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
            properties=properties or {},
            source="eastmoney",
        ).on_conflict_do_update(
            index_elements=["relation_id"],
            set_={
                "properties": properties or {},
                "updated_at": datetime.now(),
            },
        )
        
        await session.execute(stmt)
        self._stats.relations_created += 1
        
        await sync_relation_to_neo4j(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
        )
        
        return True
    
    async def sync_all_industries(self) -> dict[str, Any]:
        """Sync all industries and their member stocks to knowledge graph."""
        logger.info("Starting industry sync...")
        
        async with async_session_maker() as session:
            industries = await self.fetch_industry_list("industry")
            logger.info(f"Fetched {len(industries)} industries")
            
            self._industry_cache = await self.sync_industry_entities(session, industries, "industry")
            await session.commit()
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def sync_industry_members(industry: dict[str, Any]):
            async with semaphore:
                code = industry.get("code", "")
                name = industry.get("name", "")
                
                if not code:
                    return
                
                try:
                    members = await self.fetch_industry_members(code)
                    logger.debug(f"Industry {name}: {len(members)} members")
                    
                    async with async_session_maker() as session:
                        for member in members:
                            stock_code = member.get("stock_code", "")
                            stock_name = member.get("stock_name", "")
                            
                            if not stock_code:
                                continue
                            
                            company_entity_id = await self.sync_company_entity(
                                session, stock_code, stock_name, industry=name
                            )
                            
                            industry_entity_id = self._industry_cache.get(code)
                            if industry_entity_id:
                                await self.sync_relation(
                                    session,
                                    company_entity_id,
                                    industry_entity_id,
                                    "belongs_to_industry",
                                    {"industry_name": name},
                                )
                        
                        await session.commit()
                except Exception as e:
                    logger.error(f"Failed to sync industry {name}: {e}")
                    self._stats.errors.append(f"Industry {name}: {str(e)}")
        
        await asyncio.gather(*[sync_industry_members(ind) for ind in industries])
        
        logger.info(f"Industry sync completed: {self._stats.industries_created} industries created")
        return {
            "industries_created": self._stats.industries_created,
            "relations_created": self._stats.relations_created,
            "errors": self._stats.errors,
        }
    
    async def sync_all_concepts(self) -> dict[str, Any]:
        """Sync all concepts and their member stocks to knowledge graph."""
        logger.info("Starting concept sync...")
        
        concept_stats = SyncStats()
        
        async with async_session_maker() as session:
            concepts = await self.fetch_industry_list("concept")
            logger.info(f"Fetched {len(concepts)} concepts")
            
            self._concept_cache = await self.sync_industry_entities(session, concepts, "concept")
            await session.commit()
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def sync_concept_members(concept: dict[str, Any]):
            async with semaphore:
                code = concept.get("code", "")
                name = concept.get("name", "")
                
                if not code:
                    return
                
                try:
                    members = await self.fetch_industry_members(code)
                    logger.debug(f"Concept {name}: {len(members)} members")
                    
                    async with async_session_maker() as session:
                        for member in members:
                            stock_code = member.get("stock_code", "")
                            stock_name = member.get("stock_name", "")
                            
                            if not stock_code:
                                continue
                            
                            company_entity_id = f"company_{stock_code}"
                            
                            stmt = select(EntityModel).where(EntityModel.entity_id == company_entity_id)
                            result = await session.execute(stmt)
                            existing = result.scalar_one_or_none()
                            
                            if not existing:
                                entity = EntityModel(
                                    id=str(uuid.uuid4()),
                                    entity_id=company_entity_id,
                                    entity_type="company",
                                    name=stock_name,
                                    code=stock_code,
                                    source="eastmoney",
                                )
                                session.add(entity)
                                concept_stats.companies_updated += 1
                            
                            concept_entity_id = self._concept_cache.get(code)
                            if concept_entity_id:
                                await self.sync_relation(
                                    session,
                                    company_entity_id,
                                    concept_entity_id,
                                    "has_concept",
                                    {"concept_name": name},
                                )
                        
                        await session.commit()
                except Exception as e:
                    logger.error(f"Failed to sync concept {name}: {e}")
                    concept_stats.errors.append(f"Concept {name}: {str(e)}")
        
        await asyncio.gather(*[sync_concept_members(c) for c in concepts])
        
        logger.info(f"Concept sync completed: {self._stats.concepts_created} concepts created")
        return {
            "concepts_created": self._stats.concepts_created + concept_stats.concepts_created,
            "relations_created": self._stats.relations_created + concept_stats.relations_created,
            "errors": concept_stats.errors,
        }
    
    async def sync_all(self) -> dict[str, Any]:
        """
        Sync all companies, industries, and concepts to knowledge graph.
        
        Returns:
            Statistics about the sync operation
        """
        logger.info("Starting full knowledge graph sync...")
        
        self._stats = SyncStats()
        
        industry_result = await self.sync_all_industries()
        
        initial_relations = self._stats.relations_created
        concept_result = await self.sync_all_concepts()
        
        result = {
            "industries_created": industry_result.get("industries_created", 0),
            "concepts_created": concept_result.get("concepts_created", 0),
            "companies_updated": self._stats.companies_updated,
            "relations_created": self._stats.relations_created,
            "errors": list(set(self._stats.errors + concept_result.get("errors", []))),
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(f"Knowledge graph sync completed: {result}")
        return result
    
    async def close(self) -> None:
        """Close resources."""
        if self._session and not self._session.closed:
            await self._session.close()
