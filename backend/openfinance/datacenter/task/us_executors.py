"""
US Stock task executors for data collection.

美股数据采集任务执行器。
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
    task_type="us_stock_list",
    name="美股列表同步",
    description="获取美股主要指数成分股列表",
    category=TaskCategory.MARKET,
    source="yfinance",
    priority=TaskPriority.HIGH,
    timeout=60.0,
    parameters=[
        TaskParameter(
            name="index",
            type="string",
            default="sp500",
            description="指数类型",
            choices=["sp500", "nasdaq100", "dow", "russell2000"],
        ),
    ],
    output=TaskOutput(
        data_type="us_stock_quote",
        table_name="us_stock_daily_quote",
        description="美股行情数据",
    ),
    tags=["us_market", "realtime"],
)
class USStockListExecutor(TaskExecutor[StockQuoteData]):
    """Executor for US stock list collection."""

    def __init__(self):
        from ..collector.implementations.us_market_collectors import USStockListCollector
        self._collector_class = USStockListCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        index = params.get("index", "sp500")
        progress.details["index"] = index

        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(index=index)
            return result.data if result.data else []
        finally:
            await collector.stop()

    async def validate(self, data: list[StockQuoteData]) -> list[StockQuoteData]:
        return [d for d in data if d.code and d.close]

    async def save(self, data: list[StockQuoteData], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_us_stock_quotes(data)


@task_executor(
    task_type="us_stock_quote",
    name="美股行情采集",
    description="获取美股历史行情数据",
    category=TaskCategory.MARKET,
    source="sina",
    priority=TaskPriority.HIGH,
    timeout=120.0,
    parameters=[
        TaskParameter(
            name="symbols",
            type="array",
            default=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"],
            description="美股代码列表",
        ),
        TaskParameter(
            name="days",
            type="integer",
            default=365,
            description="获取最近N天的数据",
        ),
    ],
    output=TaskOutput(
        data_type="us_stock_quote",
        table_name="us_stock_daily_quote",
        description="美股历史行情",
    ),
    tags=["us_market", "historical"],
)
class USStockQuoteExecutor(TaskExecutor[StockQuoteData]):
    """Executor for US stock quotes."""

    def __init__(self):
        from ..collector.implementations.us_market_collectors import USStockQuoteCollector
        self._collector_class = USStockQuoteCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        symbols = params.get("symbols", ["AAPL", "MSFT", "GOOGL"])
        days = params.get("days", 365)

        progress.details["symbols_count"] = len(symbols)
        progress.details["days"] = days

        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(
                symbols=symbols,
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
        return await persistence.save_us_stock_quotes(data)


@task_executor(
    task_type="us_financial_statement",
    name="美股财务报表采集",
    description="获取美股财务报表数据",
    category=TaskCategory.FUNDAMENTAL,
    source="yfinance",
    priority=TaskPriority.NORMAL,
    timeout=180.0,
    parameters=[
        TaskParameter(
            name="symbols",
            type="array",
            default=["AAPL", "MSFT", "GOOGL"],
            description="美股代码列表",
        ),
    ],
    output=TaskOutput(
        data_type="us_financial_statement",
        table_name="us_financial_statement",
        description="美股财务报表",
    ),
    tags=["us_fundamental", "financial"],
)
class USFinancialStatementExecutor(TaskExecutor[Any]):
    """Executor for US financial statements."""

    def __init__(self):
        from ..collector.implementations.us_market_collectors import USFinancialStatementCollector
        self._collector_class = USFinancialStatementCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        symbols = params.get("symbols", ["AAPL", "MSFT", "GOOGL"])
        progress.details["symbols_count"] = len(symbols)

        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(symbols=symbols)
            return result.data if result.data else []
        finally:
            await collector.stop()

    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("symbol") and d.get("report_date")]

    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_us_financial_statements(data)


@task_executor(
    task_type="us_company_info",
    name="美股公司信息采集",
    description="获取美股公司基本信息",
    category=TaskCategory.FUNDAMENTAL,
    source="yfinance",
    priority=TaskPriority.NORMAL,
    timeout=120.0,
    parameters=[
        TaskParameter(
            name="symbols",
            type="array",
            default=["AAPL", "MSFT", "GOOGL"],
            description="美股代码列表",
        ),
    ],
    output=TaskOutput(
        data_type="us_company_info",
        table_name="us_company_info",
        description="美股公司信息",
    ),
    tags=["us_fundamental", "company"],
)
class USCompanyInfoExecutor(TaskExecutor[Any]):
    """Executor for US company information."""

    def __init__(self):
        from ..collector.implementations.us_market_collectors import USCompanyInfoCollector
        self._collector_class = USCompanyInfoCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        symbols = params.get("symbols", ["AAPL", "MSFT", "GOOGL"])
        progress.details["symbols_count"] = len(symbols)

        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(symbols=symbols)
            return result.data if result.data else []
        finally:
            await collector.stop()

    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("symbol")]

    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_us_company_info(data)


@task_executor(
    task_type="us_macro_data",
    name="美国宏观数据采集",
    description="获取美国宏观经济数据",
    category=TaskCategory.MACRO,
    source="fred",
    priority=TaskPriority.NORMAL,
    timeout=60.0,
    parameters=[
        TaskParameter(
            name="indicators",
            type="array",
            default=["GDP", "CPIAUCSL", "UNRATE"],
            description="经济指标列表",
        ),
    ],
    output=TaskOutput(
        data_type="us_macro_data",
        table_name="us_macro_data",
        description="美国宏观经济数据",
    ),
    tags=["us_macro", "economic"],
)
class USMacroDataExecutor(TaskExecutor[Any]):
    """Executor for US macro economic data."""

    def __init__(self):
        from ..collector.implementations.us_market_collectors import USMacroDataCollector
        self._collector_class = USMacroDataCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        indicators = params.get("indicators", ["GDP", "CPIAUCSL", "UNRATE"])
        progress.details["indicators_count"] = len(indicators)

        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(indicators=indicators)
            return result.data if result.data else []
        finally:
            await collector.stop()

    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("indicator_code") and d.get("period")]

    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_us_macro_data(data)


def register_us_executors():
    """Register all US stock executors."""
    from .registry import TaskRegistry

    executors = [
        USStockListExecutor(),
        USStockQuoteExecutor(),
        USFinancialStatementExecutor(),
        USCompanyInfoExecutor(),
        USMacroDataExecutor(),
    ]

    for executor in executors:
        TaskRegistry.register(executor)

    logger.info(f"Registered {len(executors)} US stock task executors")
