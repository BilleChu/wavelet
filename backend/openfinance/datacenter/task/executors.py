"""
Built-in task executors for data collection.

Each executor is self-contained with:
- Metadata (name, description, parameters, output)
- Collection logic
- Validation logic
- Storage logic
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
from ..collector.core.base_collector import StockQuoteData

logger = logging.getLogger(__name__)


@task_executor(
    task_type="stock_list",
    name="股票列表同步",
    description="从东方财富获取A股市场股票列表和实时行情",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=60.0,
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
        data_type="stock_quote",
        table_name="stock_daily_quote",
        description="股票日线行情数据",
        fields=["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount"],
    ),
    tags=["market", "realtime", "stocks"],
)
class StockListExecutor(TaskExecutor[StockQuoteData]):
    """Executor for stock list collection."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import MarketRealtimeCollector
        self._collector_class = MarketRealtimeCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        market = params.get("market", "沪深A")
        progress.details["market"] = market
        
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(market=market)
            progress.details["source"] = "eastmoney"
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[StockQuoteData]) -> list[StockQuoteData]:
        validated = []
        for item in data:
            if item.code and item.name:
                validated.append(item)
        return validated
    
    async def save(self, data: list[StockQuoteData], progress: TaskProgress) -> int:
        from ..persistence import persistence
        saved = await persistence.save_stock_quotes(data)
        progress.saved_records = saved
        return saved


@task_executor(
    task_type="realtime_quote",
    name="实时行情采集",
    description="获取指定股票的实时行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.CRITICAL,
    timeout=30.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=["000001", "600000", "600519"],
            description="股票代码列表",
        ),
    ],
    output=TaskOutput(
        data_type="stock_quote",
        table_name="stock_daily_quote",
        description="实时股票行情",
    ),
    tags=["market", "realtime"],
)
class RealtimeQuoteExecutor(TaskExecutor[StockQuoteData]):
    """Executor for realtime stock quotes."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import StockRealtimeCollector
        self._collector_class = StockRealtimeCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        codes = params.get("codes", ["000001", "600000", "600519"])
        progress.details["codes_count"] = len(codes)
        
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(codes=codes)
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[StockQuoteData]) -> list[StockQuoteData]:
        return [d for d in data if d.code and d.close]
    
    async def save(self, data: list[StockQuoteData], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_stock_quotes(data)


@task_executor(
    task_type="index_quote",
    name="指数行情同步",
    description="获取主要指数的K线数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=60.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=["000001", "399001", "399006", "000016", "000300"],
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
        description="指数K线数据",
    ),
    tags=["market", "index"],
)
class IndexQuoteExecutor(TaskExecutor[StockQuoteData]):
    """Executor for index quotes."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import KLineCollector
        self._collector_class = KLineCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        codes = params.get("codes", ["000001", "399001", "399006"])
        days = params.get("days", 30)
        
        progress.details["codes"] = codes
        progress.details["days"] = days
        
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(
                symbols=codes,
                start_date=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
            )
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[StockQuoteData]) -> list[StockQuoteData]:
        return [d for d in data if d.code and d.trade_date]
    
    async def save(self, data: list[StockQuoteData], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_stock_quotes(data)


@task_executor(
    task_type="north_money",
    name="北向资金采集",
    description="获取北向资金流入流出数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=30.0,
    output=TaskOutput(
        data_type="north_money",
        table_name="north_money",
        description="北向资金数据",
        fields=["trade_date", "sh_net_inflow", "sz_net_inflow", "total_net_inflow"],
    ),
    tags=["market", "money_flow"],
)
class NorthMoneyExecutor(TaskExecutor[Any]):
    """Executor for north money data."""
    
    def __init__(self):
        from ..collector.implementations.money_flow_collectors import NorthMoneyCollector
        self._collector_class = NorthMoneyCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect()
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if hasattr(d, 'trade_date') or (isinstance(d, dict) and d.get('trade_date'))]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_north_money(data)


@task_executor(
    task_type="etf_quote",
    name="ETF行情同步",
    description="获取ETF基金行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=60.0,
    output=TaskOutput(
        data_type="etf_quote",
        table_name="stock_daily_quote",
        description="ETF行情数据",
    ),
    tags=["market", "etf"],
)
class ETFQuoteExecutor(TaskExecutor[StockQuoteData]):
    """Executor for ETF quotes."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import MarketRealtimeCollector
        self._collector_class = MarketRealtimeCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(market="ETF")
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[StockQuoteData]) -> list[StockQuoteData]:
        return [d for d in data if d.code and d.name]
    
    async def save(self, data: list[StockQuoteData], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_stock_quotes(data)


@task_executor(
    task_type="industry_quote",
    name="行业板块数据",
    description="获取行业板块行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=60.0,
    output=TaskOutput(
        data_type="industry_quote",
        table_name="industry_quote",
        description="行业板块行情",
    ),
    tags=["market", "sector"],
)
class IndustryQuoteExecutor(TaskExecutor[Any]):
    """Executor for industry quotes."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import MarketRealtimeCollector
        self._collector_class = MarketRealtimeCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(market="行业板块")
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if hasattr(d, 'code') or (isinstance(d, dict) and d.get('code'))]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_industry_quotes(data)


@task_executor(
    task_type="concept_quote",
    name="概念板块数据",
    description="获取概念板块行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=60.0,
    output=TaskOutput(
        data_type="concept_quote",
        table_name="concept_quote",
        description="概念板块行情",
    ),
    tags=["market", "sector"],
)
class ConceptQuoteExecutor(TaskExecutor[Any]):
    """Executor for concept quotes."""
    
    def __init__(self):
        from ..collector.implementations.market_collectors import MarketRealtimeCollector
        self._collector_class = MarketRealtimeCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(market="概念板块")
            return result.data if result.data else []
        finally:
            await collector.stop()
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if hasattr(d, 'code') or (isinstance(d, dict) and d.get('code'))]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_concept_quotes(data)


@task_executor(
    task_type="financial_indicator",
    name="财务指标数据",
    description="获取上市公司财务指标数据",
    category=TaskCategory.FUNDAMENTAL,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=120.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=["000001", "600000", "600519"],
            description="股票代码列表",
        ),
    ],
    output=TaskOutput(
        data_type="financial_indicator",
        table_name="stock_financial_indicator",
        description="财务指标数据",
        fields=["code", "name", "report_date", "eps", "roe", "revenue", "net_profit"],
    ),
    tags=["fundamental", "financial"],
)
class FinancialIndicatorExecutor(TaskExecutor[Any]):
    """Executor for financial indicators."""
    
    def __init__(self):
        from ..collector.implementations.fundamental_collectors import FinancialIndicatorCollector
        self._collector_class = FinancialIndicatorCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes", ["000001", "600000", "600519"])
        progress.details["codes_count"] = len(codes)
        
        all_data = []
        for code in codes:
            try:
                collector = self._collector_class()
                await collector.start()
                result = await collector.collect(code=code)
                await collector.stop()
                if result.data:
                    all_data.extend(result.data)
            except Exception as e:
                logger.warning(f"Failed to collect financial indicator for {code}: {e}")
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if hasattr(d, 'code') or (isinstance(d, dict) and d.get('code'))]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_financial_indicator(data)


@task_executor(
    task_type="company_profile",
    name="公司档案同步",
    description="获取上市公司基本信息档案",
    category=TaskCategory.KNOWLEDGE,
    source="eastmoney",
    priority=TaskPriority.LOW,
    timeout=120.0,
    parameters=[
        TaskParameter(
            name="codes",
            type="array",
            default=["000001", "600000", "600519"],
            description="股票代码列表",
        ),
    ],
    output=TaskOutput(
        data_type="company_profile",
        table_name="company_profile",
        description="公司档案数据",
        fields=["code", "name", "industry", "description", "website"],
    ),
    tags=["knowledge", "company"],
)
class CompanyProfileExecutor(TaskExecutor[Any]):
    """Executor for company profiles."""
    
    def __init__(self):
        from ..collector.implementations.fundamental_collectors import MainBusinessCollector
        self._collector_class = MainBusinessCollector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        codes = params.get("codes", ["000001", "600000", "600519"])
        progress.details["codes_count"] = len(codes)
        
        all_data = []
        for code in codes:
            try:
                collector = self._collector_class()
                await collector.start()
                result = await collector.collect(code=code)
                await collector.stop()
                if result.data:
                    all_data.extend(result.data)
            except Exception as e:
                logger.warning(f"Failed to collect company profile for {code}: {e}")
        
        return all_data
    
    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if hasattr(d, 'code') or (isinstance(d, dict) and d.get('code'))]
    
    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_company_profiles(data)


def register_all_executors():
    """Register all built-in executors."""
    from .registry import TaskRegistry
    
    executors = [
        StockListExecutor(),
        RealtimeQuoteExecutor(),
        IndexQuoteExecutor(),
        NorthMoneyExecutor(),
        ETFQuoteExecutor(),
        IndustryQuoteExecutor(),
        ConceptQuoteExecutor(),
        FinancialIndicatorExecutor(),
        CompanyProfileExecutor(),
    ]
    
    for executor in executors:
        TaskRegistry.register(executor)
    
    try:
        from .additional_executors import register_additional_executors
        register_additional_executors()
    except Exception as e:
        logger.warning(f"Failed to register additional executors: {e}")
    
    logger.info(f"Registered {len(TaskRegistry._executors)} task executors")
