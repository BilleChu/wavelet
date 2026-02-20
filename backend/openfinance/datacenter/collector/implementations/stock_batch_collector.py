"""
Stock Batch Collector for Data Center.

Provides efficient batch collection of stock data with:
- K-line data collection
- Financial indicator collection
- Money flow data collection
- Incremental update support
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Any
from enum import Enum

import aiohttp
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.datacenter.collector.core.batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchResult,
    ProcessResult,
)
from openfinance.infrastructure.database.database import async_session_maker
from openfinance.datacenter.models import (
    StockBasicModel,
    StockDailyQuoteModel,
    StockFinancialIndicatorModel,
    StockMoneyFlowModel,
)

logger = get_logger(__name__)


class DataType(str, Enum):
    """Stock data types for collection."""
    
    KLINE_DAILY = "kline_daily"
    KLINE_WEEKLY = "kline_weekly"
    KLINE_MONTHLY = "kline_monthly"
    FINANCIAL_INDICATOR = "financial_indicator"
    MONEY_FLOW = "money_flow"
    REALTIME_QUOTE = "realtime_quote"


@dataclass
class StockDataItem:
    """Stock data item for batch processing."""
    
    code: str
    name: str
    data_type: DataType
    start_date: date | None = None
    end_date: date | None = None


@dataclass
class StockDataResult:
    """Result of processing stock data."""
    
    code: str
    data_type: str
    records_count: int
    records_inserted: int
    records_updated: int
    latest_date: date | None = None


EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_FINANCIAL_URL = "https://emweb.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
EASTMONEY_MONEY_FLOW_URL = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"


class StockBatchCollector(BatchProcessor[StockDataItem, StockDataResult]):
    """
    Batch collector for stock data.
    
    Features:
    - Collects K-line, financial indicators, money flow data
    - Supports incremental updates (only fetch new data)
    - Efficient batch processing with concurrency control
    - Error isolation per stock
    
    Data Types:
    - K-line: Daily, weekly, monthly
    - Financial indicators: Quarterly reports
    - Money flow: Daily main force flow
    """
    
    KLINE_TYPE_MAP = {
        DataType.KLINE_DAILY: "101",
        DataType.KLINE_WEEKLY: "102",
        DataType.KLINE_MONTHLY: "103",
    }
    
    def __init__(
        self,
        config: BatchConfig | None = None,
        incremental: bool = True,
    ) -> None:
        super().__init__(config or BatchConfig(batch_size=100, max_concurrent=5))
        self.incremental = incremental
        self._session: aiohttp.ClientSession | None = None
        self._stats = {
            "total_records": 0,
            "total_inserted": 0,
            "total_updated": 0,
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    def get_item_id(self, item: StockDataItem) -> str:
        return f"{item.code}_{item.data_type.value}"
    
    async def get_latest_date(
        self,
        session: AsyncSession,
        code: str,
        data_type: DataType,
    ) -> date | None:
        """Get the latest date for incremental update."""
        if data_type in (DataType.KLINE_DAILY, DataType.KLINE_WEEKLY, DataType.KLINE_MONTHLY):
            stmt = select(StockDailyQuoteModel).where(
                StockDailyQuoteModel.code == code
            ).order_by(StockDailyQuoteModel.trade_date.desc()).limit(1)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            return record.trade_date if record else None
        
        elif data_type == DataType.FINANCIAL_INDICATOR:
            stmt = select(StockFinancialIndicatorModel).where(
                StockFinancialIndicatorModel.code == code
            ).order_by(StockFinancialIndicatorModel.report_date.desc()).limit(1)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            return record.report_date if record else None
        
        elif data_type == DataType.MONEY_FLOW:
            stmt = select(StockMoneyFlowModel).where(
                StockMoneyFlowModel.code == code
            ).order_by(StockMoneyFlowModel.trade_date.desc()).limit(1)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            return record.trade_date if record else None
        
        return None
    
    async def process_item(self, item: StockDataItem) -> ProcessResult[StockDataResult]:
        """Process a single stock data item."""
        async with async_session_maker() as session:
            try:
                if self.incremental:
                    latest = await self.get_latest_date(session, item.code, item.data_type)
                    if latest:
                        item.start_date = latest + timedelta(days=1)
                
                if item.data_type in self.KLINE_TYPE_MAP:
                    result = await self._collect_kline(session, item)
                elif item.data_type == DataType.FINANCIAL_INDICATOR:
                    result = await self._collect_financial(session, item)
                elif item.data_type == DataType.MONEY_FLOW:
                    result = await self._collect_money_flow(session, item)
                else:
                    return ProcessResult(
                        success=False,
                        item_id=self.get_item_id(item),
                        error=f"Unknown data type: {item.data_type}",
                    )
                
                await session.commit()
                
                return ProcessResult(
                    success=True,
                    item_id=self.get_item_id(item),
                    data=result,
                )
                
            except Exception as e:
                await session.rollback()
                logger.error_with_context(
                    "Failed to process stock data",
                    context={"code": item.code, "data_type": item.data_type.value, "error": str(e)}
                )
                return ProcessResult(
                    success=False,
                    item_id=self.get_item_id(item),
                    error=str(e),
                )
    
    async def _collect_kline(
        self,
        session: AsyncSession,
        item: StockDataItem,
    ) -> StockDataResult:
        """Collect K-line data."""
        http_session = await self._get_session()
        
        market = "1" if item.code.startswith("6") else "0"
        secid = f"{market}.{item.code}"
        
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
            "klt": self.KLINE_TYPE_MAP[item.data_type],
            "fqt": "1",
            "end": "20500000",
            "lmt": "500",
        }
        
        if item.start_date:
            params["beg"] = item.start_date.strftime("%Y%m%d")
        
        async with http_session.get(EASTMONEY_KLINE_URL, params=params) as resp:
            data = await resp.json()
        
        records = []
        if data.get("data") and data["data"].get("klines"):
            for line in data["data"]["klines"]:
                parts = line.split(",")
                if len(parts) >= 7:
                    try:
                        trade_date = datetime.strptime(parts[0], "%Y-%m-%d").date()
                        records.append({
                            "code": item.code,
                            "trade_date": trade_date,
                            "open": float(parts[1]) if parts[1] != "-" else None,
                            "close": float(parts[2]) if parts[2] != "-" else None,
                            "high": float(parts[3]) if parts[3] != "-" else None,
                            "low": float(parts[4]) if parts[4] != "-" else None,
                            "volume": float(parts[5]) if parts[5] != "-" else None,
                            "amount": float(parts[6]) if parts[6] != "-" else None,
                        })
                    except (ValueError, IndexError):
                        continue
        
        inserted = 0
        updated = 0
        latest_date = None
        
        for record in records:
            stmt = select(StockDailyQuoteModel).where(
                and_(
                    StockDailyQuoteModel.code == record["code"],
                    StockDailyQuoteModel.trade_date == record["trade_date"],
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.open = record["open"]
                existing.close = record["close"]
                existing.high = record["high"]
                existing.low = record["low"]
                existing.volume = record["volume"]
                existing.amount = record["amount"]
                updated += 1
            else:
                new_record = StockDailyQuoteModel(**record)
                session.add(new_record)
                inserted += 1
            
            if latest_date is None or record["trade_date"] > latest_date:
                latest_date = record["trade_date"]
        
        self._stats["total_records"] += len(records)
        self._stats["total_inserted"] += inserted
        self._stats["total_updated"] += updated
        
        return StockDataResult(
            code=item.code,
            data_type=item.data_type.value,
            records_count=len(records),
            records_inserted=inserted,
            records_updated=updated,
            latest_date=latest_date,
        )
    
    async def _collect_financial(
        self,
        session: AsyncSession,
        item: StockDataItem,
    ) -> StockDataResult:
        """Collect financial indicator data."""
        http_session = await self._get_session()
        
        market = "1" if item.code.startswith("6") else "0"
        secid = f"{market}.{item.code}"
        
        params = {
            "code": secid,
            "type": "0",
        }
        
        async with http_session.get(EASTMONEY_FINANCIAL_URL, params=params) as resp:
            data = await resp.json()
        
        records = []
        if data.get("data") and data["data"].get("data"):
            for item_data in data["data"]["data"]:
                try:
                    report_date_str = item_data.get("date", "")
                    if not report_date_str:
                        continue
                    
                    report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
                    
                    def safe_float(val):
                        if val is None or val == "-" or val == "":
                            return None
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return None
                    
                    records.append({
                        "code": item.code,
                        "report_date": report_date,
                        "eps": safe_float(item_data.get("eps")),
                        "roe": safe_float(item_data.get("roe")),
                        "roa": safe_float(item_data.get("roa")),
                        "gross_margin": safe_float(item_data.get("xsmll")),
                        "net_margin": safe_float(item_data.get("jll")),
                        "revenue": safe_float(item_data.get("yysr")),
                        "net_profit": safe_float(item_data.get("jlr")),
                    })
                except (ValueError, KeyError):
                    continue
        
        inserted = 0
        updated = 0
        latest_date = None
        
        for record in records:
            stmt = select(StockFinancialIndicatorModel).where(
                and_(
                    StockFinancialIndicatorModel.code == record["code"],
                    StockFinancialIndicatorModel.report_date == record["report_date"],
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                for key, value in record.items():
                    if key not in ("code", "report_date"):
                        setattr(existing, key, value)
                updated += 1
            else:
                new_record = StockFinancialIndicatorModel(**record)
                session.add(new_record)
                inserted += 1
            
            if latest_date is None or record["report_date"] > latest_date:
                latest_date = record["report_date"]
        
        self._stats["total_records"] += len(records)
        self._stats["total_inserted"] += inserted
        self._stats["total_updated"] += updated
        
        return StockDataResult(
            code=item.code,
            data_type=item.data_type.value,
            records_count=len(records),
            records_inserted=inserted,
            records_updated=updated,
            latest_date=latest_date,
        )
    
    async def _collect_money_flow(
        self,
        session: AsyncSession,
        item: StockDataItem,
    ) -> StockDataResult:
        """Collect money flow data."""
        http_session = await self._get_session()
        
        market = "1" if item.code.startswith("6") else "0"
        secid = f"{market}.{item.code}"
        
        params = {
            "lmt": "0",
            "klt": "101",
            "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        }
        
        async with http_session.get(EASTMONEY_MONEY_FLOW_URL, params=params) as resp:
            data = await resp.json()
        
        records = []
        if data.get("data") and data["data"].get("klines"):
            for line in data["data"]["klines"]:
                parts = line.split(",")
                if len(parts) >= 8:
                    try:
                        trade_date = datetime.strptime(parts[0], "%Y-%m-%d").date()
                        
                        def safe_float(val):
                            if val is None or val == "-" or val == "":
                                return None
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                return None
                        
                        records.append({
                            "code": item.code,
                            "trade_date": trade_date,
                            "main_net_inflow": safe_float(parts[1]),
                            "retail_net_inflow": safe_float(parts[2]),
                            "super_net_inflow": safe_float(parts[3]),
                            "big_net_inflow": safe_float(parts[4]),
                            "medium_net_inflow": safe_float(parts[5]),
                            "small_net_inflow": safe_float(parts[6]),
                        })
                    except (ValueError, IndexError):
                        continue
        
        inserted = 0
        updated = 0
        latest_date = None
        
        for record in records:
            stmt = select(StockMoneyFlowModel).where(
                and_(
                    StockMoneyFlowModel.code == record["code"],
                    StockMoneyFlowModel.trade_date == record["trade_date"],
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                for key, value in record.items():
                    if key not in ("code", "trade_date"):
                        setattr(existing, key, value)
                updated += 1
            else:
                new_record = StockMoneyFlowModel(**record)
                session.add(new_record)
                inserted += 1
            
            if latest_date is None or record["trade_date"] > latest_date:
                latest_date = record["trade_date"]
        
        self._stats["total_records"] += len(records)
        self._stats["total_inserted"] += inserted
        self._stats["total_updated"] += updated
        
        return StockDataResult(
            code=item.code,
            data_type=item.data_type.value,
            records_count=len(records),
            records_inserted=inserted,
            records_updated=updated,
            latest_date=latest_date,
        )
    
    async def on_batch_complete(self, result: BatchResult[StockDataResult]) -> None:
        """Log batch completion."""
        total_records = sum(r.data.records_count for r in result.results if r.data)
        
        logger.info_with_context(
            "Stock data batch completed",
            context={
                "batch_id": result.batch_id,
                "total_items": result.total_items,
                "successful": result.successful,
                "failed": result.failed,
                "total_records": total_records,
            }
        )
    
    async def collect_all_stocks(
        self,
        data_types: list[DataType] | None = None,
        stock_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Collect data for all or specified stocks.
        
        Args:
            data_types: Types of data to collect
            stock_codes: Specific stock codes (None for all)
            
        Returns:
            Collection statistics
        """
        data_types = data_types or [DataType.KLINE_DAILY]
        
        async with async_session_maker() as session:
            if stock_codes is None:
                stmt = select(StockBasicModel.code, StockBasicModel.name)
                result = await session.execute(stmt)
                stocks = [(row.code, row.name) for row in result]
            else:
                stocks = [(code, "") for code in stock_codes]
        
        items = []
        for code, name in stocks:
            for data_type in data_types:
                items.append(StockDataItem(
                    code=code,
                    name=name,
                    data_type=data_type,
                ))
        
        logger.info_with_context(
            "Starting stock data collection",
            context={"total_items": len(items), "data_types": [dt.value for dt in data_types]}
        )
        
        results = await self.process_all(items)
        
        total_successful = sum(r.successful for r in results)
        total_failed = sum(r.failed for r in results)
        
        stats = {
            **self._stats,
            "total_items": len(items),
            "total_successful": total_successful,
            "total_failed": total_failed,
            "success_rate": total_successful / len(items) if items else 0,
        }
        
        logger.info_with_context(
            "Stock data collection completed",
            context=stats
        )
        
        return stats
    
    async def close(self) -> None:
        """Close resources."""
        if self._session and not self._session.closed:
            await self._session.close()
