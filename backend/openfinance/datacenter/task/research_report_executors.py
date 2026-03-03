"""
Research report task executors.

Includes:
- Research report collection from multiple sources
- Research report processing (entity extraction, sentiment analysis)
- Research report storage (PostgreSQL + Elasticsearch)
- Knowledge graph synchronization
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, date as date_type
from typing import Any

from .registry import (
    TaskExecutor,
    TaskCategory,
    TaskPriority,
    TaskParameter,
    TaskOutput,
    TaskProgress,
    task_executor,
)

logger = logging.getLogger(__name__)


@task_executor(
    task_type="research_report",
    name="研报数据采集",
    description="从东方财富等数据源采集研报数据，进行实体提取和情感分析",
    category=TaskCategory.FUNDAMENTAL,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=600.0,
    parameters=[
        TaskParameter(
            name="source",
            type="string",
            default="eastmoney",
            description="数据源",
            choices=["eastmoney", "thshy", "all"],
        ),
        TaskParameter(
            name="days_back",
            type="integer",
            default=7,
            description="采集最近N天的研报",
        ),
        TaskParameter(
            name="start_date",
            type="string",
            default=None,
            description="开始日期 (YYYY-MM-DD)",
        ),
        TaskParameter(
            name="end_date",
            type="string",
            default=None,
            description="结束日期 (YYYY-MM-DD)",
        ),
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则采集全部",
        ),
        TaskParameter(
            name="process_content",
            type="boolean",
            default=True,
            description="是否处理研报内容（实体提取、情感分析）",
        ),
        TaskParameter(
            name="sync_to_kg",
            type="boolean",
            default=True,
            description="是否同步到知识图谱",
        ),
    ],
    output=TaskOutput(
        data_type="research_reports",
        table_name="research_reports",
        description="研报数据",
        fields=["report_id", "title", "institution", "rating", "publish_date"],
    ),
    tags=["research", "report", "analysis"],
)
class ResearchReportExecutor(TaskExecutor[Any]):
    """
    Executor for research report collection and processing.
    
    Workflow:
    1. Collect reports from data sources
    2. Process reports (entity extraction, sentiment analysis)
    3. Save to PostgreSQL
    4. Index to Elasticsearch
    5. Sync to knowledge graph
    """
    
    def __init__(self):
        from ..collector.implementations.research_report_collectors import ResearchReportCollector
        self._collector_class = ResearchReportCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from ..collector.implementations.research_report_collectors import ResearchReportCollector
        
        source = params.get("source", "eastmoney")
        days_back = params.get("days_back", 7)
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        codes = params.get("codes")
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        progress.details["source"] = source
        progress.details["start_date"] = start_date
        progress.details["end_date"] = end_date
        
        sources = [source] if source != "all" else ["eastmoney"]
        all_reports = []
        
        for src in sources:
            try:
                collector = ResearchReportCollector()
                await collector.start()
                try:
                    result = await collector.collect(
                        source=src,
                        start_date=start_date,
                        end_date=end_date,
                        codes=codes,
                    )
                    if result.data:
                        all_reports.extend(result.data)
                finally:
                    await collector.stop()
            except Exception as e:
                logger.warning(f"Failed to collect from {src}: {e}")
        
        progress.total_records = len(all_reports)
        progress.details["total_collected"] = len(all_reports)
        
        logger.info(f"Collected {len(all_reports)} research reports")
        return all_reports
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        seen_ids = set()
        
        for item in data:
            if isinstance(item, dict):
                report_id = item.get("report_id")
                if report_id and report_id not in seen_ids:
                    if item.get("title"):
                        validated.append(item)
                        seen_ids.add(report_id)
        
        logger.info(f"Validated {len(validated)} unique research reports")
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        process_content = progress.details.get("process_content", True)
        sync_to_kg = progress.details.get("sync_to_kg", True)
        
        processed_data = []
        if process_content:
            processed_data = await self._process_reports(data, progress)
        else:
            processed_data = data
        
        saved_pg = await self._save_to_postgres(processed_data, progress)
        
        saved_es = await self._save_to_elasticsearch(processed_data, progress)
        
        if sync_to_kg:
            await self._sync_to_knowledge_graph(processed_data, progress)
        
        progress.details["saved_postgres"] = saved_pg
        progress.details["saved_elasticsearch"] = saved_es
        
        logger.info(f"Saved {saved_pg} reports to PostgreSQL, {saved_es} to Elasticsearch")
        return saved_pg
    
    async def _process_reports(
        self,
        reports: list[dict[str, Any]],
        progress: TaskProgress,
    ) -> list[dict[str, Any]]:
        """Process reports with entity extraction and sentiment analysis."""
        from ..graph.extract.research_processor import ResearchReportProcessor
        
        processor = ResearchReportProcessor()
        processed = []
        
        for i, report in enumerate(reports):
            try:
                entities = processor.extract_entities(report)
                relations = processor.extract_relations(report, entities)
                sentiment = processor.analyze_sentiment(report)
                summary = processor.summarize(report)
                
                report["extracted_entities"] = [e.to_dict() for e in entities]
                report["extracted_relations"] = [r.to_dict() for r in relations]
                report["sentiment_score"] = sentiment.score
                report["sentiment_label"] = sentiment.label
                report["summary"] = summary or report.get("summary", "")
                
                processed.append(report)
                
            except Exception as e:
                logger.warning(f"Failed to process report {report.get('report_id')}: {e}")
                processed.append(report)
            
            progress.processed_records = i + 1
        
        return processed
    
    async def _save_to_postgres(
        self,
        reports: list[dict[str, Any]],
        progress: TaskProgress,
    ) -> int:
        """Save reports to PostgreSQL."""
        from openfinance.infrastructure.database import get_db
        from ..models.orm import ResearchReportModel
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert
        
        saved = 0
        
        async for db in get_db():
            if db is None:
                logger.warning("Database not available")
                return 0
            
            for report in reports:
                try:
                    report_id = report.get("report_id")
                    
                    existing = await db.execute(
                        select(ResearchReportModel).where(
                            ResearchReportModel.report_id == report_id
                        )
                    )
                    existing_report = existing.scalar_one_or_none()
                    
                    publish_date = report.get("publish_date")
                    if isinstance(publish_date, str):
                        try:
                            publish_date = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
                        except ValueError:
                            publish_date = None
                    
                    report_date = report.get("report_date")
                    if isinstance(report_date, str):
                        try:
                            report_date = date_type.fromisoformat(report_date)
                        except ValueError:
                            report_date = None
                    
                    if existing_report:
                        existing_report.title = report.get("title", existing_report.title)
                        existing_report.summary = report.get("summary")
                        existing_report.content = report.get("content")
                        existing_report.institution = report.get("institution")
                        existing_report.analyst = report.get("analyst")
                        existing_report.rating = report.get("rating")
                        existing_report.target_price = report.get("target_price")
                        existing_report.sentiment_score = report.get("sentiment_score")
                        existing_report.sentiment_label = report.get("sentiment_label")
                        existing_report.extracted_entities = report.get("extracted_entities", {})
                        existing_report.extracted_relations = report.get("extracted_relations", {})
                        existing_report.updated_at = datetime.utcnow()
                    else:
                        new_report = ResearchReportModel(
                            id=str(uuid.uuid4()),
                            report_id=report_id,
                            title=report.get("title", ""),
                            summary=report.get("summary"),
                            content=report.get("content"),
                            source=report.get("source", "unknown"),
                            source_url=report.get("source_url"),
                            related_codes=report.get("related_codes", []),
                            related_names=report.get("related_names", []),
                            industry=report.get("industry"),
                            institution=report.get("institution"),
                            analyst=report.get("analyst"),
                            rating=report.get("rating"),
                            target_price=report.get("target_price"),
                            sentiment_score=report.get("sentiment_score"),
                            sentiment_label=report.get("sentiment_label"),
                            extracted_entities=report.get("extracted_entities", {}),
                            extracted_relations=report.get("extracted_relations", {}),
                            publish_date=publish_date,
                            report_date=report_date,
                            report_type=report.get("report_type"),
                            page_count=report.get("page_count"),
                        )
                        db.add(new_report)
                    
                    saved += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to save report {report.get('report_id')}: {e}")
            
            await db.commit()
            break
        
        return saved
    
    async def _save_to_elasticsearch(
        self,
        reports: list[dict[str, Any]],
        progress: TaskProgress,
    ) -> int:
        """Index reports to Elasticsearch."""
        try:
            from openfinance.infrastructure.search import (
                get_research_report_index,
                init_es_client,
            )
            
            await init_es_client()
            
            index = get_research_report_index()
            await index.create_index()
            
            success, failed = await index.bulk_index_reports(reports)
            
            return success
            
        except Exception as e:
            logger.warning(f"Elasticsearch indexing failed: {e}")
            return 0
    
    async def _sync_to_knowledge_graph(
        self,
        reports: list[dict[str, Any]],
        progress: TaskProgress,
    ) -> None:
        """Sync research report entities and relations to knowledge graph."""
        from openfinance.infrastructure.database import get_db
        from ..models.orm import EntityModel, RelationModel
        from sqlalchemy import select
        import uuid as uuid_lib
        
        async for db in get_db():
            if db is None:
                logger.warning("Database not available for KG sync")
                return
            
            entities_created = 0
            relations_created = 0
            
            for report in reports:
                try:
                    extracted_entities = report.get("extracted_entities", [])
                    extracted_relations = report.get("extracted_relations", [])
                    
                    for entity_data in extracted_entities:
                        entity_type = entity_data.get("entity_type")
                        entity_name = entity_data.get("entity_name")
                        entity_code = entity_data.get("entity_code")
                        
                        if not entity_name:
                            continue
                        
                        if entity_type == "stock" and entity_code:
                            existing = await db.execute(
                                select(EntityModel).where(
                                    EntityModel.code == entity_code,
                                    EntityModel.entity_type == "stock"
                                )
                            )
                            if existing.scalar_one_or_none():
                                continue
                        
                        existing = await db.execute(
                            select(EntityModel).where(
                                EntityModel.name == entity_name,
                                EntityModel.entity_type == entity_type
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue
                        
                        new_entity = EntityModel(
                            id=str(uuid_lib.uuid4()),
                            entity_id=f"{entity_type}_{uuid_lib.uuid4().hex[:8]}",
                            entity_type=entity_type,
                            name=entity_name,
                            code=entity_code,
                            source="research_report",
                            confidence=entity_data.get("confidence", 0.8),
                        )
                        db.add(new_entity)
                        entities_created += 1
                    
                    for relation_data in extracted_relations:
                        source_entity = relation_data.get("source_entity")
                        target_entity = relation_data.get("target_entity")
                        relation_type = relation_data.get("relation_type")
                        
                        if not all([source_entity, target_entity, relation_type]):
                            continue
                        
                        relations_created += 1
                    
                except Exception as e:
                    logger.debug(f"Failed to sync KG for report {report.get('report_id')}: {e}")
            
            await db.commit()
            progress.details["kg_entities_created"] = entities_created
            progress.details["kg_relations_created"] = relations_created
            logger.info(f"Synced {entities_created} entities and {relations_created} relations to KG")
            break


@task_executor(
    task_type="research_report_search",
    name="研报检索",
    description="从Elasticsearch检索研报数据",
    category=TaskCategory.QUERY,
    source="elasticsearch",
    priority=TaskPriority.NORMAL,
    timeout=30.0,
    parameters=[
        TaskParameter(
            name="query",
            type="string",
            default="",
            description="搜索关键词",
        ),
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表过滤",
        ),
        TaskParameter(
            name="institution",
            type="string",
            default=None,
            description="机构名称过滤",
        ),
        TaskParameter(
            name="rating",
            type="string",
            default=None,
            description="评级过滤",
        ),
        TaskParameter(
            name="size",
            type="integer",
            default=10,
            description="返回结果数量",
        ),
        TaskParameter(
            name="from_",
            type="integer",
            default=0,
            description="分页偏移量",
        ),
    ],
    output=TaskOutput(
        data_type="research_reports",
        table_name="research_reports",
        description="研报搜索结果",
    ),
    tags=["research", "search", "query"],
)
class ResearchReportSearchExecutor(TaskExecutor[Any]):
    """Executor for searching research reports in Elasticsearch."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from openfinance.infrastructure.search import (
            get_research_report_index,
            init_es_client,
        )
        
        await init_es_client()
        
        query = params.get("query", "")
        codes = params.get("codes")
        institution = params.get("institution")
        rating = params.get("rating")
        size = params.get("size", 10)
        from_ = params.get("from_", 0)
        
        progress.details["query"] = query
        progress.details["size"] = size
        
        index = get_research_report_index()
        
        filters = {}
        if codes:
            filters["related_codes"] = codes[0] if len(codes) == 1 else codes
        if institution:
            filters["institution"] = institution
        if rating:
            filters["rating"] = rating
        
        if codes and not query:
            result = await index.search_by_code(codes[0], size=size, from_=from_)
        elif institution and not query:
            result = await index.search_by_institution(institution, size=size, from_=from_)
        else:
            result = await index.search_reports(
                query=query,
                filters=filters if filters else None,
                size=size,
                from_=from_,
            )
        
        progress.details["total"] = result.get("total", 0)
        
        return result.get("hits", [])
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return data
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        return len(data)


def register_research_report_executors():
    """Register research report executors."""
    from .registry import TaskRegistry
    
    executors = [
        ResearchReportExecutor(),
        ResearchReportSearchExecutor(),
    ]
    
    for executor in executors:
        TaskRegistry.register(executor)
    
    logger.info(f"Registered {len(executors)} research report task executors")
