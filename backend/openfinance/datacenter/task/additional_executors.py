"""
Additional task executors migrated from predefined_tasks.py.

Includes:
- Stock basic info collection (eastmoney)
- Macro economic data collection (eastmoney)
- Factor computation (using quant module)
- News collection (eastmoney)
"""

import asyncio
import logging
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
from .trading_calendar import trading_calendar, get_latest_trading_day

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
    description="从东方财富获取股票日线行情数据（仅交易日）",
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
            description="获取最近N个交易日的数据",
        ),
        TaskParameter(
            name="force",
            type="boolean",
            default=False,
            description="强制执行，即使今天不是交易日",
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
    """Executor for stock daily quotes from eastmoney (trading days only)."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import KLineCollector
        self._collector_class = KLineCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        from ..collector.implementations.market_collectors import MarketRealtimeCollector, KLineCollector
        from ..persistence import persistence
        from sqlalchemy import text
        
        days = params.get("days", 30)
        codes = params.get("codes")
        force = params.get("force", False)
        
        today = date_type.today()
        
        if not trading_calendar.is_trading_day(today) and not force:
            logger.info(f"Today ({today}) is not a trading day, skipping collection")
            progress.details["skipped"] = True
            progress.details["reason"] = "non_trading_day"
            return []
        
        end_date = get_latest_trading_day(today)
        
        trading_days = trading_calendar.get_recent_trading_days(count=days, end_date=end_date)
        if not trading_days:
            logger.warning("No trading days found")
            return []
        
        start_date = trading_days[0]
        actual_end_date = trading_days[-1]
        
        progress.details["start_date"] = str(start_date)
        progress.details["end_date"] = str(actual_end_date)
        progress.details["trading_days_count"] = len(trading_days)
        progress.details["source"] = "eastmoney"
        
        logger.info(f"Collecting data for {len(trading_days)} trading days: {start_date} to {actual_end_date}")
        
        all_data = []
        
        if codes:
            collector = KLineCollector()
            await collector.start()
            try:
                for code in codes:
                    result = await collector.collect(
                        symbols=[code],
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=actual_end_date.strftime("%Y-%m-%d"),
                    )
                    if result.data:
                        all_data.extend(result.data)
            finally:
                await collector.stop()
        else:
            codes = []
            async with persistence.session_maker() as session:
                result = await session.execute(text("""
                    SELECT DISTINCT code FROM openfinance.stock_basic 
                    WHERE code IS NOT NULL 
                    ORDER BY code
                """))
                codes = [row[0] for row in result.fetchall()]
            
            progress.details["total_stocks"] = len(codes)
            progress.total_records = len(codes)
            
            collector = KLineCollector()
            await collector.start()
            try:
                batch_size = 50
                for i in range(0, len(codes), batch_size):
                    batch = codes[i:i + batch_size]
                    try:
                        result = await collector.collect(
                            symbols=batch,
                            start_date=start_date.strftime("%Y-%m-%d"),
                            end_date=actual_end_date.strftime("%Y-%m-%d"),
                        )
                        if result.data:
                            all_data.extend(result.data)
                        progress.processed_records = min(i + batch_size, len(codes))
                    except Exception as e:
                        logger.warning(f"Failed to collect batch {i//batch_size + 1}: {e}")
                    await asyncio.sleep(0.1)
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
    description="从东方财富获取指数日线行情数据（仅交易日）",
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
            description="获取最近N个交易日的数据",
        ),
        TaskParameter(
            name="force",
            type="boolean",
            default=False,
            description="强制执行，即使今天不是交易日",
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
    """Executor for index daily quotes from eastmoney (trading days only)."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import KLineCollector
        self._collector_class = KLineCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes", ["000001", "399001", "399006", "000300", "000905"])
        days = params.get("days", 30)
        force = params.get("force", False)
        
        today = date_type.today()
        
        if not trading_calendar.is_trading_day(today) and not force:
            logger.info(f"Today ({today}) is not a trading day, skipping index collection")
            progress.details["skipped"] = True
            progress.details["reason"] = "non_trading_day"
            return []
        
        end_date = get_latest_trading_day(today)
        trading_days = trading_calendar.get_recent_trading_days(count=days, end_date=end_date)
        
        if not trading_days:
            logger.warning("No trading days found")
            return []
        
        start_date = trading_days[0]
        actual_end_date = trading_days[-1]
        
        progress.details["codes"] = codes
        progress.details["start_date"] = str(start_date)
        progress.details["end_date"] = str(actual_end_date)
        progress.details["trading_days_count"] = len(trading_days)
        progress.details["source"] = "eastmoney"
        
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(
                symbols=codes,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=actual_end_date.strftime("%Y-%m-%d"),
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
    description="使用量化引擎计算因子数据（仅交易日）",
    category=TaskCategory.FUNDAMENTAL,
    source="internal",
    priority=TaskPriority.NORMAL,
    timeout=3600.0,
    parameters=[
        TaskParameter(
            name="factor_ids",
            type="array",
            default=None,
            description="因子ID列表，为空则计算所有内置因子",
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
            description="交易日期，为空则使用最新交易日",
        ),
        TaskParameter(
            name="batch_size",
            type="integer",
            default=50,
            description="每批处理的股票数量",
        ),
        TaskParameter(
            name="force",
            type="boolean",
            default=False,
            description="强制执行，即使今天不是交易日",
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
    """Executor for factor computation using quant module (trading days only)."""
    
    BUILTIN_FACTORS = [
        "factor_momentum",
        "factor_risk_adj_momentum", 
        "factor_volatility",
        "factor_idio_volatility",
        "factor_sma",
        "factor_ema",
        "factor_macd",
        "factor_rsi",
        "factor_kdj",
        "factor_boll",
        "factor_atr",
        "factor_cci",
        "factor_wr",
        "factor_obv",
    ]
    
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
        factor_ids = params.get("factor_ids")
        codes = params.get("codes")
        trade_date_str = params.get("trade_date")
        batch_size = params.get("batch_size", 50)
        force = params.get("force", False)
        
        today = date_type.today()
        
        if trade_date_str:
            trade_date = date_type.fromisoformat(trade_date_str)
        else:
            trade_date = get_latest_trading_day(today)
        
        if not trading_calendar.is_trading_day(today) and not force:
            logger.info(f"Today ({today}) is not a trading day, skipping factor computation")
            progress.details["skipped"] = True
            progress.details["reason"] = "non_trading_day"
            return []
        
        if not factor_ids:
            factor_ids = self.BUILTIN_FACTORS
        
        progress.details["factor_ids"] = factor_ids
        progress.details["trade_date"] = str(trade_date)
        progress.details["source"] = "quant_engine"
        
        if not codes:
            from ..persistence import persistence
            async with persistence.session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("""
                    SELECT DISTINCT code FROM openfinance.stock_daily_quote 
                    WHERE trade_date = :trade_date
                    AND code NOT LIKE 'IND_%'
                    AND code NOT LIKE 'CON_%'
                    AND code NOT LIKE 'BK%'
                    AND LENGTH(code) = 6
                    ORDER BY code
                """), {"trade_date": trade_date})
                codes = [row[0] for row in result.fetchall()]
                
                if not codes:
                    logger.warning(f"No stocks found for trade_date {trade_date}, falling back to recent data")
                    result = await session.execute(text("""
                        SELECT DISTINCT code FROM openfinance.stock_daily_quote 
                        WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
                        AND code NOT LIKE 'IND_%'
                        AND code NOT LIKE 'CON_%'
                        AND code NOT LIKE 'BK%'
                        AND LENGTH(code) = 6
                        ORDER BY code
                    """))
                    codes = [row[0] for row in result.fetchall()]
        
        progress.total_records = len(codes) * len(factor_ids)
        progress.details["total_stocks"] = len(codes)
        progress.details["total_factors"] = len(factor_ids)
        
        logger.info(f"Computing factors for {len(codes)} stocks on {trade_date}")
        
        engine = await self._get_engine()
        
        all_results = []
        processed = 0
        
        for factor_id in factor_ids:
            factor_results = []
            for i in range(0, len(codes), batch_size):
                batch = codes[i:i + batch_size]
                for code in batch:
                    try:
                        result = await engine.calculate(factor_id, code, trade_date)
                        if result:
                            factor_results.append(result)
                        processed += 1
                        progress.processed_records = processed
                    except Exception as e:
                        logger.warning(f"Failed to calculate {factor_id} for {code}: {e}")
                        processed += 1
                
                await asyncio.sleep(0.05)
            
            all_results.extend(factor_results)
            logger.info(f"Calculated {factor_id}: {len(factor_results)} results")
        
        return all_results
    
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
        IncomeStatementExecutor(),
        BalanceSheetExecutor(),
        DividendDataExecutor(),
        FundamentalFactorComputeExecutor(),
    ]
    
    for executor in executors:
        TaskRegistry.register(executor)
    
    logger.info(f"Registered {len(executors)} additional task executors")


@task_executor(
    task_type="income_statement",
    name="利润表数据采集",
    description="从东方财富采集利润表数据（营业收入、净利润、归母净利润等）",
    category=TaskCategory.FUNDAMENTAL,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=1800.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则采集全部股票",
        ),
        TaskParameter(
            name="batch_size",
            type="integer",
            default=50,
            description="每批处理的股票数量",
        ),
    ],
    output=TaskOutput(
        data_type="income_statement",
        table_name="income_statement",
        description="利润表数据",
        fields=["code", "report_date", "revenue", "net_profit", "net_profit_attr"],
    ),
    tags=["fundamental", "financial", "income"],
)
class IncomeStatementExecutor(TaskExecutor[Any]):
    """Executor for income statement data collection."""
    
    def __init__(self):
        from ..collector.implementations.fundamental_collectors import IncomeStatementCollector
        self._collector_class = IncomeStatementCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes")
        batch_size = params.get("batch_size", 50)
        
        if not codes:
            from ..persistence import persistence
            async with persistence.session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("""
                    SELECT DISTINCT code FROM openfinance.stock_basic
                    WHERE LENGTH(code) = 6
                    ORDER BY code
                """))
                codes = [row[0] for row in result.fetchall()]
        
        progress.total_records = len(codes)
        progress.details["source"] = "eastmoney"
        
        collector = self._collector_class()
        await collector.start()
        
        all_data = []
        try:
            for i in range(0, len(codes), batch_size):
                batch = codes[i:i + batch_size]
                for code in batch:
                    try:
                        records = await collector._collect(code=code)
                        all_data.extend(records)
                    except Exception as e:
                        logger.debug(f"Failed to collect income statement for {code}: {e}")
                    progress.processed_records = min(i + batch_size, len(codes))
                await asyncio.sleep(0.1)
        finally:
            await collector.stop()
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("report_date")]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        
        return await persistence.save_orm("income_statement", data)


@task_executor(
    task_type="balance_sheet",
    name="资产负债表数据采集",
    description="从东方财富采集资产负债表数据（总资产、总负债、净资产等）",
    category=TaskCategory.FUNDAMENTAL,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=1800.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则采集全部股票",
        ),
        TaskParameter(
            name="batch_size",
            type="integer",
            default=50,
            description="每批处理的股票数量",
        ),
    ],
    output=TaskOutput(
        data_type="balance_sheet",
        table_name="balance_sheet",
        description="资产负债表数据",
        fields=["code", "report_date", "total_assets", "total_equity", "net_equity_attr"],
    ),
    tags=["fundamental", "financial", "balance"],
)
class BalanceSheetExecutor(TaskExecutor[Any]):
    """Executor for balance sheet data collection."""
    
    def __init__(self):
        from ..collector.implementations.fundamental_collectors import BalanceSheetCollector
        self._collector_class = BalanceSheetCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes")
        batch_size = params.get("batch_size", 50)
        
        if not codes:
            from ..persistence import persistence
            async with persistence.session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("""
                    SELECT DISTINCT code FROM openfinance.stock_basic
                    WHERE LENGTH(code) = 6
                    ORDER BY code
                """))
                codes = [row[0] for row in result.fetchall()]
        
        progress.total_records = len(codes)
        progress.details["source"] = "eastmoney"
        
        collector = self._collector_class()
        await collector.start()
        
        all_data = []
        try:
            for i in range(0, len(codes), batch_size):
                batch = codes[i:i + batch_size]
                for code in batch:
                    try:
                        records = await collector._collect(code=code)
                        all_data.extend(records)
                    except Exception as e:
                        logger.debug(f"Failed to collect balance sheet for {code}: {e}")
                    progress.processed_records = min(i + batch_size, len(codes))
                await asyncio.sleep(0.1)
        finally:
            await collector.stop()
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("report_date")]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        
        return await persistence.save_orm("balance_sheet", data)


@task_executor(
    task_type="dividend_data",
    name="股息分红数据采集",
    description="从东方财富采集历史分红数据（每股股息、分红方案等）",
    category=TaskCategory.FUNDAMENTAL,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=1800.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=None,
            description="股票代码列表，为空则采集全部股票",
        ),
        TaskParameter(
            name="batch_size",
            type="integer",
            default=50,
            description="每批处理的股票数量",
        ),
    ],
    output=TaskOutput(
        data_type="dividend_data",
        table_name="dividend_data",
        description="股息分红数据",
        fields=["code", "report_year", "dividend_per_share", "dividend_yield"],
    ),
    tags=["fundamental", "dividend"],
)
class DividendDataExecutor(TaskExecutor[Any]):
    """Executor for dividend data collection."""
    
    def __init__(self):
        from ..collector.implementations.fundamental_collectors import DividendDataCollector
        self._collector_class = DividendDataCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes")
        batch_size = params.get("batch_size", 50)
        
        if not codes:
            from ..persistence import persistence
            async with persistence.session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("""
                    SELECT DISTINCT code FROM openfinance.stock_basic
                    WHERE LENGTH(code) = 6
                    ORDER BY code
                """))
                codes = [row[0] for row in result.fetchall()]
        
        progress.total_records = len(codes)
        progress.details["source"] = "eastmoney"
        
        collector = self._collector_class()
        await collector.start()
        
        all_data = []
        try:
            for i in range(0, len(codes), batch_size):
                batch = codes[i:i + batch_size]
                for code in batch:
                    try:
                        records = await collector._collect(code=code)
                        all_data.extend(records)
                    except Exception as e:
                        logger.debug(f"Failed to collect dividend data for {code}: {e}")
                    progress.processed_records = min(i + batch_size, len(codes))
                await asyncio.sleep(0.1)
        finally:
            await collector.stop()
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("report_year")]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        
        return await persistence.save_orm("dividend_data", data)


@task_executor(
    task_type="fundamental_factor_compute",
    name="基本面因子计算",
    description="计算 PE、ROE、股息率、筹码分布等基本面因子",
    category=TaskCategory.FUNDAMENTAL,
    source="internal",
    priority=TaskPriority.NORMAL,
    timeout=3600.0,
    parameters=[
        TaskParameter(
            name="factor_ids",
            type="array",
            default=None,
            description="因子ID列表，为空则计算所有基本面因子",
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
            description="交易日期，为空则使用最新交易日",
        ),
    ],
    output=TaskOutput(
        data_type="factor_data",
        table_name="factor_data",
        description="基本面因子数据",
        fields=["factor_id", "code", "trade_date", "factor_value"],
    ),
    tags=["factor", "fundamental"],
)
class FundamentalFactorComputeExecutor(TaskExecutor[Any]):
    """Executor for computing fundamental factors (PE, ROE, Dividend Yield, Chip Distribution)."""
    
    FUNDAMENTAL_FACTORS = [
        "factor_value_pe",
        "factor_quality_roe",
        "factor_dividend_yield",
        "factor_chip_distribution_2y",
    ]
    
    def __init__(self):
        pass
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        factor_ids = params.get("factor_ids") or self.FUNDAMENTAL_FACTORS
        codes = params.get("codes")
        trade_date_str = params.get("trade_date")
        
        if trade_date_str:
            trade_date = date_type.fromisoformat(trade_date_str)
        else:
            trade_date = get_latest_trading_day(date_type.today())
        
        progress.details["factor_ids"] = factor_ids
        progress.details["trade_date"] = str(trade_date)
        
        import asyncpg
        conn = await asyncpg.connect(
            "postgresql://openfinance:openfinance@localhost:5432/openfinance"
        )
        
        if not codes:
            rows = await conn.fetch('''
                SELECT DISTINCT code FROM openfinance.stock_daily_quote
                WHERE trade_date = $1
                AND LENGTH(code) = 6
                ORDER BY code
            ''', trade_date)
            codes = [row["code"] for row in rows]
        
        progress.total_records = len(codes) * len(factor_ids)
        
        all_results = []
        
        for factor_id in factor_ids:
            if factor_id == "factor_value_pe":
                results = await self._compute_pe_factor(conn, codes, trade_date)
            elif factor_id == "factor_quality_roe":
                results = await self._compute_roe_factor(conn, codes, trade_date)
            elif factor_id == "factor_dividend_yield":
                results = await self._compute_dividend_yield_factor(conn, codes, trade_date)
            elif factor_id == "factor_chip_distribution_2y":
                results = await self._compute_chip_distribution_factor(conn, codes, trade_date)
            else:
                results = []
            
            all_results.extend(results)
            logger.info(f"Computed {factor_id}: {len(results)} results")
        
        await conn.close()
        return all_results
    
    async def _compute_pe_factor(self, conn, codes: list[str], trade_date: date_type) -> list[dict]:
        """计算 PE 因子: PE = 市值 / 归母净利润"""
        results = []
        
        for code in codes:
            try:
                quote = await conn.fetchrow('''
                    SELECT close, market_cap FROM openfinance.stock_daily_quote
                    WHERE code = $1 AND trade_date = $2
                ''', code, trade_date)
                
                if not quote or not quote["close"]:
                    continue
                
                income = await conn.fetchrow('''
                    SELECT net_profit_attr FROM openfinance.income_statement
                    WHERE code = $1
                    ORDER BY report_date DESC LIMIT 1
                ''', code)
                
                if not income or not income["net_profit_attr"]:
                    continue
                
                net_profit_attr = float(income["net_profit_attr"])
                if net_profit_attr <= 0:
                    continue
                
                close = float(quote["close"])
                
                total_shares_row = await conn.fetchrow('''
                    SELECT total_shares FROM openfinance.stock_basic WHERE code = $1
                ''', code)
                
                if total_shares_row and total_shares_row["total_shares"]:
                    total_shares = float(total_shares_row["total_shares"])
                    market_cap = close * total_shares
                else:
                    continue
                
                pe = market_cap / net_profit_attr
                pe_factor = 1.0 / pe if pe > 0 else None
                
                if pe_factor is not None:
                    results.append({
                        "factor_id": "factor_value_pe",
                        "code": code,
                        "trade_date": trade_date,
                        "factor_value": pe_factor,
                    })
            except Exception as e:
                logger.debug(f"Failed to compute PE for {code}: {e}")
        
        return results
    
    async def _compute_roe_factor(self, conn, codes: list[str], trade_date: date_type) -> list[dict]:
        """计算 ROE 因子: ROE = 归母净利润 / 归母净资产"""
        results = []
        
        for code in codes:
            try:
                income = await conn.fetchrow('''
                    SELECT net_profit_attr FROM openfinance.income_statement
                    WHERE code = $1
                    ORDER BY report_date DESC LIMIT 1
                ''', code)
                
                balance = await conn.fetchrow('''
                    SELECT net_equity_attr FROM openfinance.balance_sheet
                    WHERE code = $1
                    ORDER BY report_date DESC LIMIT 1
                ''', code)
                
                if not income or not balance:
                    continue
                
                net_profit_attr = float(income["net_profit_attr"]) if income["net_profit_attr"] else None
                net_equity_attr = float(balance["net_equity_attr"]) if balance["net_equity_attr"] else None
                
                if net_profit_attr is None or net_equity_attr is None or net_equity_attr <= 0:
                    continue
                
                roe = net_profit_attr / net_equity_attr
                
                results.append({
                    "factor_id": "factor_quality_roe",
                    "code": code,
                    "trade_date": trade_date,
                    "factor_value": roe,
                })
            except Exception as e:
                logger.debug(f"Failed to compute ROE for {code}: {e}")
        
        return results
    
    async def _compute_dividend_yield_factor(self, conn, codes: list[str], trade_date: date_type) -> list[dict]:
        """计算股息率因子: 股息率 = 每股股息 / 收盘价"""
        results = []
        
        for code in codes:
            try:
                quote = await conn.fetchrow('''
                    SELECT close FROM openfinance.stock_daily_quote
                    WHERE code = $1 AND trade_date = $2
                ''', code, trade_date)
                
                if not quote or not quote["close"]:
                    continue
                
                dividend = await conn.fetchrow('''
                    SELECT dividend_per_share FROM openfinance.dividend_data
                    WHERE code = $1
                    ORDER BY report_year DESC LIMIT 1
                ''', code)
                
                if not dividend or not dividend["dividend_per_share"]:
                    continue
                
                close = float(quote["close"])
                dps = float(dividend["dividend_per_share"])
                
                dividend_yield = dps / close if close > 0 else None
                
                if dividend_yield is not None:
                    results.append({
                        "factor_id": "factor_dividend_yield",
                        "code": code,
                        "trade_date": trade_date,
                        "factor_value": dividend_yield,
                    })
            except Exception as e:
                logger.debug(f"Failed to compute dividend yield for {code}: {e}")
        
        return results
    
    async def _compute_chip_distribution_factor(self, conn, codes: list[str], trade_date: date_type) -> list[dict]:
        """计算筹码分布因子: 基于历史K线计算筹码集中度"""
        import math
        
        results = []
        
        for code in codes:
            try:
                klines = await conn.fetch('''
                    SELECT trade_date, high, low, close, volume
                    FROM openfinance.stock_daily_quote
                    WHERE code = $1 AND trade_date <= $2
                    ORDER BY trade_date DESC
                    LIMIT 480
                ''', code, trade_date)
                
                if len(klines) < 60:
                    continue
                
                klines = list(reversed(klines))
                
                price_min = min(float(k["low"]) for k in klines if k["low"])
                price_max = max(float(k["high"]) for k in klines if k["high"])
                
                if price_max <= price_min:
                    continue
                
                num_bins = 20
                bin_size = (price_max - price_min) / num_bins
                volume_distribution = [0.0] * num_bins
                
                total_volume = 0
                for k in klines:
                    close = float(k["close"]) if k["close"] else None
                    volume = int(k["volume"]) if k["volume"] else 0
                    
                    if close is None or volume == 0:
                        continue
                    
                    bin_idx = min(int((close - price_min) / bin_size), num_bins - 1)
                    volume_distribution[bin_idx] += volume
                    total_volume += volume
                
                if total_volume == 0:
                    continue
                
                sorted_volumes = sorted(volume_distribution, reverse=True)
                cumulative = 0
                bins_for_50_percent = 0
                for v in sorted_volumes:
                    cumulative += v
                    bins_for_50_percent += 1
                    if cumulative >= total_volume * 0.5:
                        break
                
                chip_concentration = 1.0 - (bins_for_50_percent / num_bins)
                
                results.append({
                    "factor_id": "factor_chip_distribution_2y",
                    "code": code,
                    "trade_date": trade_date,
                    "factor_value": chip_concentration,
                })
            except Exception as e:
                logger.debug(f"Failed to compute chip distribution for {code}: {e}")
        
        return results
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("factor_value") is not None]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        import asyncpg
        
        conn = await asyncpg.connect(
            "postgresql://openfinance:openfinance@localhost:5432/openfinance"
        )
        
        saved = 0
        for record in data:
            try:
                await conn.execute('''
                    INSERT INTO openfinance.factor_data (
                        factor_id, code, trade_date, factor_name, factor_category,
                        factor_value, collected_at
                    ) VALUES ($1, $2, $3, $1, 'fundamental', $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (factor_id, code, trade_date) DO UPDATE SET
                        factor_value = EXCLUDED.factor_value,
                        collected_at = CURRENT_TIMESTAMP
                ''',
                    record.get("factor_id"),
                    record.get("code"),
                    record.get("trade_date"),
                    record.get("factor_value"),
                )
                saved += 1
            except Exception as e:
                logger.debug(f"Failed to save factor data: {e}")
        
        await conn.close()
        return saved
