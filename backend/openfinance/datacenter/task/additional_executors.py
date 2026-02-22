"""
Additional task executors migrated from predefined_tasks.py.

Includes:
- Stock basic info collection (eastmoney)
- Macro economic data collection (eastmoney)
- Factor computation (using quant module)
- News collection (eastmoney)
"""

import logging
from datetime import datetime, timedelta
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
    task_type="stock_basic_info",
    name="股票基础信息采集",
    description="从东方财富获取所有A股股票的基本信息",
    category=TaskCategory.KNOWLEDGE,
    source="eastmoney",
    priority=TaskPriority.CRITICAL,
    timeout=300.0,
    parameters=[
        TaskParameter(
            name="market",
            type="string",
            default="沪深A",
            description="市场类型",
            choices=["沪深A", "上证A", "深证A", "创业板", "科创板", "北证A"],
        ),
    ],
    output=TaskOutput(
        data_type="stock_basic",
        table_name="stock_basic",
        description="股票基本信息",
        fields=["code", "name", "industry", "market", "list_date"],
    ),
    tags=["reference", "stocks"],
)
class StockBasicInfoExecutor(TaskExecutor[Any]):
    """Executor for stock basic info collection from eastmoney."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import MarketRealtimeCollector
        self._collector_class = MarketRealtimeCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        market = params.get("market", "沪深A")
        progress.details["market"] = market
        progress.details["source"] = "eastmoney"
        
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(market=market)
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if hasattr(item, 'code') and hasattr(item, 'name'):
                validated.append(item)
            elif isinstance(item, dict) and item.get("code") and item.get("name"):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_stock_basic(data)


@task_executor(
    task_type="stock_daily_quote",
    name="股票日线行情采集",
    description="从东方财富获取股票日线行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=600.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则获取全部",
        ),
        TaskParameter(
            name="days",
            type="integer",
            default=30,
            description="获取最近N天的数据",
        ),
    ],
    output=TaskOutput(
        data_type="stock_quote",
        table_name="stock_daily_quote",
        description="股票日线行情",
        fields=["code", "trade_date", "open", "high", "low", "close", "volume"],
    ),
    tags=["market", "daily"],
)
class StockDailyQuoteExecutor(TaskExecutor[Any]):
    """Executor for stock daily quotes from eastmoney."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import KLineCollector
        self._collector_class = KLineCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from ..collector.implementations.market_collectors import MarketRealtimeCollector
        
        days = params.get("days", 30)
        codes = params.get("codes")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        progress.details["start_date"] = start_date
        progress.details["end_date"] = end_date
        progress.details["source"] = "eastmoney"
        
        all_data = []
        
        if codes:
            collector = self._collector_class()
            await collector.start()
            try:
                for code in codes:
                    result = await collector.collect(
                        symbols=[code],
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if result.data:
                        all_data.extend(result.data)
            finally:
                await collector.stop()
        else:
            collector = MarketRealtimeCollector()
            await collector.start()
            try:
                result = await collector.collect(market="沪深A")
                if result.data:
                    all_data.extend(result.data)
            finally:
                await collector.stop()
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if hasattr(item, 'code') and hasattr(item, 'trade_date'):
                validated.append(item)
            elif isinstance(item, dict) and item.get("code") and item.get("trade_date"):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_stock_quotes(data)


@task_executor(
    task_type="index_daily_quote",
    name="指数日线行情采集",
    description="从东方财富获取指数日线行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=300.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=["000001", "399001", "399006", "000300", "000905"],
            description="指数代码列表",
        ),
        TaskParameter(
            name="days",
            type="integer",
            default=30,
            description="获取最近N天的数据",
        ),
    ],
    output=TaskOutput(
        data_type="index_quote",
        table_name="stock_daily_quote",
        description="指数日线行情",
    ),
    tags=["market", "index"],
)
class IndexDailyQuoteExecutor(TaskExecutor[Any]):
    """Executor for index daily quotes from eastmoney."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import KLineCollector
        self._collector_class = KLineCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes", ["000001", "399001", "399006", "000300", "000905"])
        days = params.get("days", 30)
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        progress.details["codes"] = codes
        progress.details["start_date"] = start_date
        progress.details["source"] = "eastmoney"
        
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(
                symbols=codes,
                start_date=start_date,
                end_date=end_date,
            )
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if hasattr(item, 'code') and hasattr(item, 'trade_date'):
                validated.append(item)
            elif isinstance(item, dict) and item.get("code") and item.get("trade_date"):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_stock_quotes(data)


@task_executor(
    task_type="macro_economic_data",
    name="宏观经济数据采集",
    description="获取GDP、CPI、PMI等宏观经济指标",
    category=TaskCategory.MACRO,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=300.0,
    parameters=[
        TaskParameter(
            name="indicators",
            type="array",
            default=["gdp", "cpi", "pmi", "lpr"],
            description="指标类型列表",
        ),
    ],
    output=TaskOutput(
        data_type="macro_data",
        table_name="macro_economic",
        description="宏观经济数据",
    ),
    tags=["macro", "economic"],
)
class MacroEconomicExecutor(TaskExecutor[Any]):
    """Executor for macro economic data from eastmoney."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        try:
            from ..collector.implementations.macro_collectors import MacroDataCollector
        except ImportError:
            logger.warning("Macro collectors not available")
            return []
        
        indicators = params.get("indicators", ["gdp", "cpi", "pmi", "lpr"])
        progress.details["indicators"] = indicators
        progress.details["source"] = "eastmoney"
        
        all_data = []
        
        for indicator in indicators:
            try:
                collector = MacroDataCollector(indicator_type=indicator)
                await collector.start()
                result = await collector.collect()
                await collector.stop()
                
                if result.data:
                    for r in result.data:
                        if hasattr(r, '__dict__'):
                            r_dict = r.__dict__.copy()
                        elif isinstance(r, dict):
                            r_dict = r.copy()
                        else:
                            r_dict = {'value': r}
                        r_dict['indicator_type'] = indicator
                        all_data.append(r_dict)
            except Exception as e:
                logger.warning(f"Failed to collect {indicator}: {e}")
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if isinstance(d, dict)]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_macro_data(data)


@task_executor(
    task_type="financial_news",
    name="财经新闻采集",
    description="从东方财富、财联社等采集财经新闻",
    category=TaskCategory.NEWS,
    source="eastmoney",
    priority=TaskPriority.LOW,
    timeout=300.0,
    parameters=[
        TaskParameter(
            name="limit",
            type="integer",
            default=100,
            description="获取新闻数量",
        ),
    ],
    output=TaskOutput(
        data_type="news",
        table_name="news",
        description="财经新闻",
        fields=["title", "content", "source", "publish_time"],
    ),
    tags=["news", "information"],
)
class FinancialNewsExecutor(TaskExecutor[Any]):
    """Executor for financial news from eastmoney."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        try:
            from ..collector.implementations.news_collectors import CLSNewsCollector, JinshiNewsCollector
        except ImportError:
            logger.warning("News collectors not available")
            return []
        
        limit = params.get("limit", 100)
        progress.details["limit"] = limit
        progress.details["source"] = "eastmoney"
        
        all_news = []
        
        try:
            collector = CLSNewsCollector()
            await collector.start()
            result = await collector.collect(limit=limit)
            await collector.stop()
            if result.data:
                all_news.extend(result.data)
        except Exception as e:
            logger.warning(f"CLS news collection failed: {e}")
        
        try:
            collector = JinshiNewsCollector()
            await collector.start()
            result = await collector.collect(limit=limit)
            await collector.stop()
            if result.data:
                all_news.extend(result.data)
        except Exception as e:
            logger.warning(f"Jinshi news collection failed: {e}")
        
        return all_news
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if hasattr(item, 'title'):
                validated.append(item)
            elif isinstance(item, dict) and item.get('title'):
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_news(data)


@task_executor(
    task_type="factor_compute",
    name="因子计算",
    description="使用量化引擎计算因子数据",
    category=TaskCategory.FUNDAMENTAL,
    source="internal",
    priority=TaskPriority.NORMAL,
    timeout=1200.0,
    parameters=[
        TaskParameter(
            name="factor_id",
            type="string",
            default="momentum_20d",
            description="因子ID",
        ),
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则计算全部",
        ),
        TaskParameter(
            name="trade_date",
            type="string",
            default=None,
            description="交易日期，为空则使用最新日期",
        ),
    ],
    output=TaskOutput(
        data_type="factor_data",
        table_name="factor_data",
        description="因子数据",
        fields=["factor_id", "code", "trade_date", "value", "signal"],
    ),
    tags=["factor", "quant"],
)
class FactorComputeExecutor(TaskExecutor[Any]):
    """Executor for factor computation using quant module."""
    
    def __init__(self):
        self._engine = None
    
    async def _get_engine(self):
        if self._engine is None:
            from openfinance.quant.factors.engine import FactorEngine, EngineConfig
            config = EngineConfig(max_workers=4, use_cache=True, save_to_db=True)
            self._engine = FactorEngine(config)
            await self._engine.initialize()
        return self._engine
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from datetime import date as date_type
        
        factor_id = params.get("factor_id", "momentum_20d")
        codes = params.get("codes")
        trade_date_str = params.get("trade_date")
        
        if trade_date_str:
            trade_date = date_type.fromisoformat(trade_date_str)
        else:
            trade_date = date_type.today()
        
        progress.details["factor_id"] = factor_id
        progress.details["trade_date"] = str(trade_date)
        progress.details["source"] = "quant_engine"
        
        engine = await self._get_engine()
        
        if not codes:
            from ..persistence import persistence
            async with persistence.session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("""
                    SELECT DISTINCT code FROM openfinance.stock_daily_quote 
                    WHERE trade_date >= CURRENT_DATE - INTERVAL '7 days'
                    LIMIT 100
                """))
                codes = [row[0] for row in result.fetchall()]
        
        progress.total_records = len(codes)
        
        results = []
        for i, code in enumerate(codes):
            try:
                result = await engine.calculate(factor_id, code, trade_date)
                if result:
                    results.append(result)
                progress.processed_records = i + 1
            except Exception as e:
                logger.warning(f"Failed to calculate factor for {code}: {e}")
        
        return results
    
    async def validate(self, data: list[Any]) -> list[Any]:
        validated = []
        for item in data:
            if hasattr(item, 'code') and hasattr(item, 'value'):
                validated.append(item)
            elif isinstance(item, dict) and item.get("code") and "value" in item:
                validated.append(item)
        return validated
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        storage = await get_factor_storage()
        
        factor_results = []
        for item in data:
            if hasattr(item, '__dict__'):
                factor_results.append(item)
            else:
                from openfinance.quant.factors.base import FactorResult
                result = FactorResult(
                    factor_id=item.get("factor_id", "unknown"),
                    code=item.get("code", ""),
                    trade_date=item.get("trade_date"),
                    value=item.get("value"),
                    signal=item.get("signal", 0),
                )
                factor_results.append(result)
        
        return await storage.save_factor_data_batch(factor_results)


@task_executor(
    task_type="sync_stock_entities",
    name="股票实体同步",
    description="将股票基础数据同步到知识图谱实体表",
    category=TaskCategory.KNOWLEDGE,
    source="internal",
    priority=TaskPriority.HIGH,
    timeout=600.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则同步全部股票",
        ),
        TaskParameter(
            name="batch_size",
            type="integer",
            default=500,
            description="每批处理的股票数量",
        ),
    ],
    output=TaskOutput(
        data_type="entities",
        table_name="entities",
        description="知识图谱实体",
        fields=["entity_id", "name", "entity_type", "code", "industry"],
    ),
    tags=["knowledge", "sync", "entities"],
)
class SyncStockEntitiesExecutor(TaskExecutor[Any]):
    """Executor for syncing stock data to knowledge graph entities."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from ..persistence import persistence
        from sqlalchemy import text
        
        codes = params.get("codes")
        batch_size = params.get("batch_size", 500)
        
        progress.details["batch_size"] = batch_size
        progress.details["codes_provided"] = codes is not None
        
        async with persistence.session_maker() as session:
            if codes:
                progress.details["codes_count"] = len(codes)
                placeholders = ",".join([f":code_{i}" for i in range(len(codes))])
                query = text(f"""
                    SELECT code, name, industry, market, list_date 
                    FROM openfinance.stock_basic 
                    WHERE code IS NOT NULL AND name IS NOT NULL
                    AND code IN ({placeholders})
                    ORDER BY code
                """)
                params_dict = {f"code_{i}": code for i, code in enumerate(codes)}
                result = await session.execute(query, params_dict)
            else:
                result = await session.execute(text("""
                    SELECT code, name, industry, market, list_date 
                    FROM openfinance.stock_basic 
                    WHERE code IS NOT NULL AND name IS NOT NULL
                    ORDER BY code
                """))
            
            rows = result.fetchall()
            progress.total_records = len(rows)
            progress.details["source"] = "stock_basic"
            
            entities = []
            for row in rows:
                code, name, industry, market, list_date = row
                entity = {
                    "entity_type": "stock",
                    "code": code,
                    "name": name,
                    "industry": industry,
                    "market": market,
                    "list_date": list_date.isoformat() if list_date else None,
                    "is_active": True,
                    "properties": {},
                }
                entities.append(entity)
            
            return entities
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("name")]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.infrastructure.database import get_db
        from openfinance.datacenter.models import EntityModel
        from sqlalchemy import select
        import uuid
        
        batch_size = progress.details.get("batch_size", 500)
        saved = 0
        
        async for db in get_db():
            if db is None:
                logger.warning("Database not available")
                return 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                for entity_data in batch:
                    try:
                        code = entity_data.get("code")
                        
                        existing = await db.execute(
                            select(EntityModel).where(EntityModel.code == code)
                        )
                        existing_entity = existing.scalar_one_or_none()
                        
                        if existing_entity:
                            existing_entity.name = entity_data.get("name")
                            existing_entity.industry = entity_data.get("industry")
                            existing_entity.updated_at = datetime.now()
                            if existing_entity.properties is None:
                                existing_entity.properties = {}
                            existing_entity.properties.update({
                                "market": entity_data.get("market"),
                                "list_date": entity_data.get("list_date"),
                                "is_active": entity_data.get("is_active", True),
                            })
                        else:
                            new_entity = EntityModel(
                                id=str(uuid.uuid4()),
                                entity_id=str(uuid.uuid4()),
                                entity_type="stock",
                                code=code,
                                name=entity_data.get("name"),
                                industry=entity_data.get("industry"),
                                properties={
                                    "market": entity_data.get("market"),
                                    "list_date": entity_data.get("list_date"),
                                    "is_active": entity_data.get("is_active", True),
                                },
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                            )
                            db.add(new_entity)
                        
                        saved += 1
                        progress.saved_records = saved
                        
                    except Exception as e:
                        logger.warning(f"Failed to save entity {entity_data.get('code')}: {e}")
                
                await db.commit()
                logger.info(f"Synced batch {i // batch_size + 1}: {len(batch)} entities")
            
            break
        
        logger.info(f"Synced {saved} stock entities to knowledge graph")
        return saved


@task_executor(
    task_type="sync_industry_entities",
    name="行业实体同步",
    description="将行业板块数据同步到知识图谱实体表",
    category=TaskCategory.KNOWLEDGE,
    source="internal",
    priority=TaskPriority.NORMAL,
    timeout=300.0,
    output=TaskOutput(
        data_type="entities",
        table_name="entities",
        description="知识图谱实体",
        fields=["entity_id", "name", "entity_type", "code"],
    ),
    tags=["knowledge", "sync", "industry"],
)
class SyncIndustryEntitiesExecutor(TaskExecutor[Any]):
    """Executor for syncing industry data to knowledge graph entities."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from ..persistence import persistence
        from sqlalchemy import text
        
        async with persistence.session_maker() as session:
            try:
                result = await session.execute(text("""
                    SELECT DISTINCT code, name 
                    FROM openfinance.industry_quote 
                    WHERE code IS NOT NULL AND name IS NOT NULL
                    ORDER BY code
                """))
                rows = result.fetchall()
            except Exception as e:
                logger.warning(f"industry_quote table not found or query failed: {e}")
                rows = []
            
            progress.total_records = len(rows)
            progress.details["source"] = "industry_quote"
            
            entities = []
            for row in rows:
                code, name = row
                entity = {
                    "entity_type": "industry",
                    "code": code,
                    "name": name,
                    "industry": None,
                    "properties": {},
                }
                entities.append(entity)
            
            return entities
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("name")]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.infrastructure.database import get_db
        from openfinance.datacenter.models import EntityModel
        from sqlalchemy import select
        import uuid
        
        saved = 0
        async for db in get_db():
            if db is None:
                logger.warning("Database not available")
                return 0
            
            for entity_data in data:
                try:
                    code = entity_data.get("code")
                    
                    existing = await db.execute(
                        select(EntityModel).where(
                            EntityModel.code == code,
                            EntityModel.entity_type == "industry"
                        )
                    )
                    existing_entity = existing.scalar_one_or_none()
                    
                    if not existing_entity:
                        new_entity = EntityModel(
                            id=str(uuid.uuid4()),
                            entity_id=str(uuid.uuid4()),
                            entity_type="industry",
                            code=code,
                            name=entity_data.get("name"),
                            properties={},
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )
                        db.add(new_entity)
                        saved += 1
                    
                    progress.saved_records = saved
                    
                except Exception as e:
                    logger.warning(f"Failed to save entity {entity_data.get('code')}: {e}")
            
            await db.commit()
            break
        
        logger.info(f"Synced {saved} industry entities to knowledge graph")
        return saved


@task_executor(
    task_type="sync_concept_entities",
    name="概念实体同步",
    description="将概念板块数据同步到知识图谱实体表",
    category=TaskCategory.KNOWLEDGE,
    source="internal",
    priority=TaskPriority.NORMAL,
    timeout=300.0,
    output=TaskOutput(
        data_type="entities",
        table_name="entities",
        description="知识图谱实体",
        fields=["entity_id", "name", "entity_type", "code"],
    ),
    tags=["knowledge", "sync", "concept"],
)
class SyncConceptEntitiesExecutor(TaskExecutor[Any]):
    """Executor for syncing concept data to knowledge graph entities."""
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from ..persistence import persistence
        from sqlalchemy import text
        
        async with persistence.session_maker() as session:
            try:
                result = await session.execute(text("""
                    SELECT DISTINCT code, name 
                    FROM openfinance.concept_quote 
                    WHERE code IS NOT NULL AND name IS NOT NULL
                    ORDER BY code
                """))
                rows = result.fetchall()
            except Exception as e:
                logger.warning(f"concept_quote table not found or query failed: {e}")
                rows = []
            
            progress.total_records = len(rows)
            progress.details["source"] = "concept_quote"
            
            entities = []
            for row in rows:
                code, name = row
                entity = {
                    "entity_type": "concept",
                    "code": code,
                    "name": name,
                    "industry": None,
                    "properties": {},
                }
                entities.append(entity)
            
            return entities
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("name")]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from openfinance.infrastructure.database import get_db
        from openfinance.datacenter.models import EntityModel
        from sqlalchemy import select
        import uuid
        
        saved = 0
        async for db in get_db():
            if db is None:
                logger.warning("Database not available")
                return 0
            
            for entity_data in data:
                try:
                    code = entity_data.get("code")
                    
                    existing = await db.execute(
                        select(EntityModel).where(
                            EntityModel.code == code,
                            EntityModel.entity_type == "concept"
                        )
                    )
                    existing_entity = existing.scalar_one_or_none()
                    
                    if not existing_entity:
                        new_entity = EntityModel(
                            id=str(uuid.uuid4()),
                            entity_id=str(uuid.uuid4()),
                            entity_type="concept",
                            code=code,
                            name=entity_data.get("name"),
                            properties={},
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                        )
                        db.add(new_entity)
                        saved += 1
                    
                    progress.saved_records = saved
                    
                except Exception as e:
                    logger.warning(f"Failed to save entity {entity_data.get('code')}: {e}")
            
            await db.commit()
            break
        
        logger.info(f"Synced {saved} concept entities to knowledge graph")
        return saved


def register_additional_executors():
    """Register additional executors from predefined_tasks."""
    from .registry import TaskRegistry
    
    executors = [
        StockBasicInfoExecutor(),
        StockDailyQuoteExecutor(),
        IndexDailyQuoteExecutor(),
        MacroEconomicExecutor(),
        FinancialNewsExecutor(),
        FactorComputeExecutor(),
        SyncStockEntitiesExecutor(),
        SyncIndustryEntitiesExecutor(),
        SyncConceptEntitiesExecutor(),
    ]
    
    for executor in executors:
        TaskRegistry.register(executor)
    
    logger.info(f"Registered {len(executors)} additional task executors")
