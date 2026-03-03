"""
Hong Kong Stock task executors for data collection.

港股数据采集任务执行器。
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
    task_type="hk_stock_list",
    name="港股列表同步",
    description="获取港股市场股票列表",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=60.0,
    parameters=[
        TaskParameter(
            name="market",
            type="string",
            default="港股",
            description="市场类型",
            choices=["港股", "港股主板", "港股创业板"],
        ),
    ],
    output=TaskOutput(
        data_type="hk_stock_quote",
        table_name="hk_stock_daily_quote",
        description="港股行情数据",
    ),
    tags=["hk_market", "realtime"],
)
class HKStockListExecutor(TaskExecutor[StockQuoteData]):
    """Executor for HK stock list collection."""

    def __init__(self):
        from ..collector.implementations.hk_market_collectors import HKStockListCollector
        self._collector_class = HKStockListCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        market = params.get("market", "港股")
        progress.details["market"] = market

        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect(market=market)
            return result.data if result.data else []
        finally:
            await collector.stop()

    async def validate(self, data: list[StockQuoteData]) -> list[StockQuoteData]:
        return [d for d in data if d.code and d.name]

    async def save(self, data: list[StockQuoteData], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_hk_stock_quotes(data)


@task_executor(
    task_type="hk_stock_quote",
    name="港股行情采集",
    description="获取港股历史行情数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.HIGH,
    timeout=120.0,
    parameters=[
        TaskParameter(
            name="symbols",
            type="array",
            default=["00700", "00941", "09988"],
            description="港股代码列表",
        ),
        TaskParameter(
            name="days",
            type="integer",
            default=365,
            description="获取最近N天的数据",
        ),
    ],
    output=TaskOutput(
        data_type="hk_stock_quote",
        table_name="hk_stock_daily_quote",
        description="港股历史行情",
    ),
    tags=["hk_market", "historical"],
)
class HKStockQuoteExecutor(TaskExecutor[StockQuoteData]):
    """Executor for HK stock quotes."""

    def __init__(self):
        from ..collector.implementations.hk_market_collectors import HKStockQuoteCollector
        self._collector_class = HKStockQuoteCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[StockQuoteData]:
        symbols = params.get("symbols", ["00700", "00941", "09988"])
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
        return await persistence.save_hk_stock_quotes(data)


@task_executor(
    task_type="hk_money_flow",
    name="港股资金流向采集",
    description="获取港股资金流向数据",
    category=TaskCategory.MARKET,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=60.0,
    output=TaskOutput(
        data_type="hk_money_flow",
        table_name="hk_money_flow",
        description="港股资金流向",
    ),
    tags=["hk_market", "money_flow"],
)
class HKMoneyFlowExecutor(TaskExecutor[Any]):
    """Executor for HK money flow."""

    def __init__(self):
        from ..collector.implementations.hk_market_collectors import HKMoneyFlowCollector
        self._collector_class = HKMoneyFlowCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        collector = self._collector_class()
        await collector.start()
        try:
            result = await collector.collect()
            return result.data if result.data else []
        finally:
            await collector.stop()

    async def validate(self, data: list[Any]) -> list[Any]:
        return [d for d in data if d.get("code") and d.get("trade_date")]

    async def save(self, data: list[Any], progress: TaskProgress) -> int:
        from ..persistence import persistence
        return await persistence.save_hk_money_flow(data)


@task_executor(
    task_type="hk_financial_statement",
    name="港股财务报表采集",
    description="获取港股财务报表数据",
    category=TaskCategory.FUNDAMENTAL,
    source="eastmoney",
    priority=TaskPriority.NORMAL,
    timeout=180.0,
    parameters=[
        TaskParameter(
            name="symbols",
            type="array",
            default=["00700", "00941", "09988"],
            description="港股代码列表",
        ),
    ],
    output=TaskOutput(
        data_type="hk_financial_statement",
        table_name="hk_financial_statement",
        description="港股财务报表",
    ),
    tags=["hk_fundamental", "financial"],
)
class HKFinancialStatementExecutor(TaskExecutor[Any]):
    """Executor for HK financial statements."""

    def __init__(self):
        from ..collector.implementations.hk_market_collectors import HKFinancialStatementCollector
        self._collector_class = HKFinancialStatementCollector

    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[Any]:
        symbols = params.get("symbols", ["00700", "00941", "09988"])
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
        return await persistence.save_hk_financial_statements(data)


def register_hk_executors():
    """Register all HK stock executors."""
    from .registry import TaskRegistry

    executors = [
        HKStockListExecutor(),
        HKStockQuoteExecutor(),
        HKMoneyFlowExecutor(),
        HKFinancialStatementExecutor(),
    ]

    for executor in executors:
        TaskRegistry.register(executor)

    logger.info(f"Registered {len(executors)} HK stock task executors")
