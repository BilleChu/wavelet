"""
Company Preloader for Data Center.

Preloads all listed company information and syncs to knowledge graph.
Provides unique company identification system.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.core.logging_config import get_logger
from openfinance.datacenter.collector.core.batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchResult,
    ProcessResult,
)
from openfinance.datacenter.database import async_session_maker
from openfinance.datacenter.models import (
    EntityModel,
    RelationModel,
    StockBasicModel,
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
)

logger = get_logger(__name__)


@dataclass
class CompanyInfo:
    """Company information data structure."""
    
    code: str
    name: str
    market: str
    industry: str | None = None
    sector: str | None = None
    list_date: str | None = None
    credit_code: str | None = None
    province: str | None = None
    city: str | None = None
    website: str | None = None
    employees: int | None = None
    main_business: str | None = None
    concepts: list[str] | None = None


@dataclass
class CompanyProcessResult:
    """Result of processing a company."""
    
    company_id: str
    code: str
    name: str
    created: bool
    updated: bool
    graph_synced: bool
    concepts_added: int = 0


EASTMONEY_STOCK_LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_COMPANY_PROFILE_URL = "https://emweb.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax"
EASTMONEY_CONCEPT_URL = "https://push2.eastmoney.com/api/qt/slist/get"


class CompanyPreloader(BatchProcessor[CompanyInfo, CompanyProcessResult]):
    """
    Preloader for company information.
    
    Features:
    - Fetches all listed company basic info
    - Establishes unique company identification (credit code + stock code)
    - Syncs to PostgreSQL and Neo4j knowledge graph
    - Supports incremental updates with diff detection
    
    Data Flow:
    EastMoney API → BatchProcessor → PostgreSQL (stock_basic)
                                    ↓
                               Neo4j (entities/relations)
    """
    
    MARKET_MAP = {
        "SH": "上海证券交易所",
        "SZ": "深圳证券交易所",
        "BJ": "北京证券交易所",
    }
    
    def __init__(
        self,
        config: BatchConfig | None = None,
        sync_to_graph: bool = True,
    ) -> None:
        super().__init__(config or BatchConfig(batch_size=50, max_concurrent=3))
        self.sync_to_graph = sync_to_graph
        self._session: aiohttp.ClientSession | None = None
        self._stats = {
            "total_fetched": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_graph_synced": 0,
            "total_concepts_added": 0,
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    def get_item_id(self, item: CompanyInfo) -> str:
        return item.code
    
    async def fetch_all_companies(self) -> list[CompanyInfo]:
        """
        Fetch all listed companies from EastMoney API.
        
        Returns:
            List of CompanyInfo objects
        """
        session = await self._get_session()
        companies: list[CompanyInfo] = []
        
        market_configs = [
            {"fs": "m:1+t:2,m:1+t:23", "market": "SH"},
            {"fs": "m:0+t:6,m:0+t:80", "market": "SZ"},
            {"fs": "m:0+t:81+s:2048", "market": "BJ"},
        ]
        
        for market_config in market_configs:
            params = {
                "pn": 1,
                "pz": 5000,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": market_config["fs"],
                "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13",
            }
            
            try:
                async with session.get(EASTMONEY_STOCK_LIST_URL, params=params) as resp:
                    data = await resp.json()
                    
                if data.get("data") and data["data"].get("diff"):
                    for item in data["data"]["diff"]:
                        code = item.get("f12", "")
                        name = item.get("f14", "")
                        
                        if not code or not name:
                            continue
                        
                        companies.append(CompanyInfo(
                            code=code,
                            name=name,
                            market=market_config["market"],
                        ))
                        
            except Exception as e:
                logger.error_with_context(
                    "Failed to fetch company list",
                    context={"market": market_config["market"], "error": str(e)}
                )
        
        self._stats["total_fetched"] = len(companies)
        logger.info_with_context(
            "Fetched company list",
            context={"total": len(companies)}
        )
        
        return companies
    
    async def fetch_company_detail(self, code: str) -> dict[str, Any]:
        """Fetch detailed company information."""
        session = await self._get_session()
        
        secid = ""
        if code.startswith("6"):
            secid = f"1.{code}"
        elif code.startswith(("0", "3")):
            secid = f"0.{code}"
        elif code.startswith(("4", "8")):
            secid = f"0.{code}"
        
        if not secid:
            return {}
        
        params = {"code": secid}
        
        try:
            async with session.get(EASTMONEY_COMPANY_PROFILE_URL, params=params) as resp:
                data = await resp.json()
                return data.get("jbzl", {})
        except Exception as e:
            logger.debug(f"Failed to fetch company detail for {code}: {e}")
            return {}
    
    async def fetch_company_concepts(self, code: str) -> list[str]:
        """Fetch concept tags for a company."""
        session = await self._get_session()
        
        market = "1" if code.startswith("6") else "0"
        secid = f"{market}.{code}"
        
        params = {
            "np": 1,
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "fltt": 2,
            "invt": 2,
            "fields": "f12,f14",
            "secid": secid,
            "spt": 3,
        }
        
        try:
            async with session.get(EASTMONEY_CONCEPT_URL, params=params) as resp:
                data = await resp.json()
                
            concepts = []
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    concept_name = item.get("f14", "")
                    if concept_name:
                        concepts.append(concept_name)
            
            return concepts
        except Exception:
            return []
    
    async def process_item(self, item: CompanyInfo) -> ProcessResult[CompanyProcessResult]:
        """Process a single company."""
        async with async_session_maker() as session:
            try:
                detail = await self.fetch_company_detail(item.code)
                concepts = await self.fetch_company_concepts(item.code)
                
                item.industry = detail.get("hymc")
                item.sector = detail.get("sshy")
                item.list_date = detail.get("ssrq")
                item.credit_code = detail.get("xydm")
                item.province = detail.get("ssdq")
                item.city = detail.get("sssf")
                item.website = detail.get("gswz")
                item.main_business = detail.get("jyfw")
                
                try:
                    item.employees = int(detail.get("ygrs", 0)) if detail.get("ygrs") else None
                except (ValueError, TypeError):
                    item.employees = None
                
                item.concepts = concepts
                
                result = await self._save_company(session, item)
                
                if self.sync_to_graph:
                    await self._sync_to_graph(session, item, concepts)
                
                await session.commit()
                
                return ProcessResult(
                    success=True,
                    item_id=item.code,
                    data=result,
                )
                
            except Exception as e:
                await session.rollback()
                return ProcessResult(
                    success=False,
                    item_id=item.code,
                    error=str(e),
                )
    
    async def _save_company(
        self,
        session: AsyncSession,
        company: CompanyInfo,
    ) -> CompanyProcessResult:
        """Save company to database."""
        created = False
        updated = False
        
        stmt = select(StockBasicModel).where(StockBasicModel.code == company.code)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            if self._has_changes(existing, company):
                existing.name = company.name
                existing.industry = company.industry
                existing.market = company.market
                existing.list_date = company.list_date
                updated = True
        else:
            new_company = StockBasicModel(
                code=company.code,
                name=company.name,
                industry=company.industry,
                market=company.market,
                list_date=company.list_date,
            )
            session.add(new_company)
            created = True
        
        company_id = f"company_{company.code}"
        
        return CompanyProcessResult(
            company_id=company_id,
            code=company.code,
            name=company.name,
            created=created,
            updated=updated,
            graph_synced=False,
            concepts_added=len(company.concepts or []),
        )
    
    async def _sync_to_graph(
        self,
        session: AsyncSession,
        company: CompanyInfo,
        concepts: list[str],
    ) -> None:
        """Sync company to knowledge graph."""
        company_id = f"company_{company.code}"
        
        entity_stmt = select(EntityModel).where(EntityModel.entity_id == company_id)
        entity_result = await session.execute(entity_stmt)
        existing_entity = entity_result.scalar_one_or_none()
        
        entity_props = {
            "code": company.code,
            "name": company.name,
            "market": company.market,
            "industry": company.industry,
            "sector": company.sector,
            "credit_code": company.credit_code,
            "province": company.province,
            "city": company.city,
            "website": company.website,
            "employees": company.employees,
            "main_business": company.main_business,
        }
        
        if not existing_entity:
            entity = EntityModel(
                id=str(uuid.uuid4()),
                entity_id=company_id,
                entity_type="company",
                name=company.name,
                properties=entity_props,
            )
            session.add(entity)
        
        concepts_added = 0
        for concept_name in concepts:
            concept_id = f"concept_{concept_name}"
            
            concept_stmt = select(EntityModel).where(EntityModel.entity_id == concept_id)
            concept_result = await session.execute(concept_stmt)
            concept_entity = concept_result.scalar_one_or_none()
            
            if not concept_entity:
                concept_entity = EntityModel(
                    id=str(uuid.uuid4()),
                    entity_id=concept_id,
                    entity_type="concept",
                    name=concept_name,
                    properties={},
                )
                session.add(concept_entity)
            
            relation_stmt = select(RelationModel).where(
                RelationModel.source_entity_id == company_id,
                RelationModel.target_entity_id == concept_id,
                RelationModel.relation_type == "has_concept",
            )
            relation_result = await session.execute(relation_stmt)
            existing_relation = relation_result.scalar_one_or_none()
            
            if not existing_relation:
                relation = RelationModel(
                    id=str(uuid.uuid4()),
                    source_entity_id=company_id,
                    target_entity_id=concept_id,
                    relation_type="has_concept",
                    properties={},
                )
                session.add(relation)
                concepts_added += 1
        
        self._stats["total_graph_synced"] += 1
        self._stats["total_concepts_added"] += concepts_added
    
    def _has_changes(self, existing: StockBasicModel, new: CompanyInfo) -> bool:
        """Check if company info has changes."""
        return (
            existing.name != new.name or
            existing.industry != new.industry or
            existing.market != new.market
        )
    
    async def on_batch_complete(self, result: BatchResult[CompanyProcessResult]) -> None:
        """Log batch completion."""
        created = sum(1 for r in result.results if r.data and r.data.created)
        updated = sum(1 for r in result.results if r.data and r.data.updated)
        
        self._stats["total_created"] += created
        self._stats["total_updated"] += updated
        
        logger.info_with_context(
            "Company batch completed",
            context={
                "batch_id": result.batch_id,
                "total": result.total_items,
                "successful": result.successful,
                "failed": result.failed,
                "created": created,
                "updated": updated,
            }
        )
    
    async def preload_all(self, resume: bool = True) -> dict[str, Any]:
        """
        Execute full company preload process.
        
        Args:
            resume: Whether to resume from checkpoint
            
        Returns:
            Processing statistics
        """
        logger.info_with_context("Starting company preload", context={})
        
        companies = await self.fetch_all_companies()
        
        results = await self.process_all(companies, resume=resume)
        
        total_successful = sum(r.successful for r in results)
        total_failed = sum(r.failed for r in results)
        
        stats = {
            **self._stats,
            "total_processed": len(companies),
            "total_successful": total_successful,
            "total_failed": total_failed,
            "success_rate": total_successful / len(companies) if companies else 0,
        }
        
        logger.info_with_context(
            "Company preload completed",
            context=stats
        )
        
        return stats
    
    async def close(self) -> None:
        """Close resources."""
        if self._session and not self._session.closed:
            await self._session.close()
