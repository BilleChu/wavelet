"""
Task handlers for data collection.

Provides handlers for different types of data collection tasks.
All handlers fetch data directly from EastMoney API and save to PostgreSQL database.
"""

import uuid
import asyncio
import json
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

import aiohttp
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.datacenter.task.queue import TaskDefinition
from openfinance.infrastructure.database.database import async_session_maker
from openfinance.datacenter.models import (
    EntityModel,
    RelationModel,
    StockBasicModel,
    StockDailyQuoteModel,
    StockFinancialIndicatorModel,
    StockMoneyFlowModel,
    MacroEconomicModel,
    NewsModel,
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
)

logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

GRAPH_DIR = DATA_DIR / "knowledge_graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "-" or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_str(val: Any, default: str = "") -> str:
    if val is None or val == "-":
        return default
    return str(val).strip()


def parse_date(val: Any) -> date | None:
    if val is None or val == "-" or val == "":
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(val, "%Y%m%d").date()
            except ValueError:
                return None
    return None


class DataCollectionHandler:
    """Base handler for data collection tasks."""

    def __init__(self) -> None:
        self._session = None

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class StockListHandler(DataCollectionHandler):
    """
    Handler for stock list collection.
    
    Data Chain:
    1. Fetch all A-share stocks from EastMoney API
    2. Save to PostgreSQL database (stock_basic table)
    3. Return stock count and database stats
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting stock list collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "10000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
                "fields": "f12,f14,f100,f102,f103,f2,f3,f5,f6,f20,f21",
            }
            
            stocks = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            stocks.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "industry": safe_str(item.get("f100")),
                                "board": safe_str(item.get("f102")),
                                "concepts": safe_str(item.get("f103")),
                                "price": safe_float(item.get("f2")),
                                "change_pct": safe_float(item.get("f3")),
                                "volume": safe_float(item.get("f5")),
                                "amount": safe_float(item.get("f6")),
                                "market_cap": safe_float(item.get("f20")),
                                "circulating_cap": safe_float(item.get("f21")),
                            })
            
            saved_count = 0
            failed_count = 0
            async with async_session_maker() as db:
                for stock in stocks:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_basic 
                            (code, name, industry, market, market_cap, properties, updated_at)
                            VALUES (:code, :name, :industry, :market, :market_cap, CAST(:properties AS jsonb), NOW())
                            ON CONFLICT (code) DO UPDATE SET
                                name = EXCLUDED.name,
                                industry = COALESCE(EXCLUDED.industry, openfinance.stock_basic.industry),
                                market_cap = EXCLUDED.market_cap,
                                properties = EXCLUDED.properties,
                                updated_at = NOW()
                        """)
                        await db.execute(stmt, {
                            "code": stock["code"],
                            "name": stock["name"],
                            "industry": stock["industry"] or None,
                            "market": stock["board"] or None,
                            "market_cap": stock["market_cap"] if stock["market_cap"] > 0 else None,
                            "properties": json.dumps({
                                "concepts": stock["concepts"],
                                "circulating_cap": stock["circulating_cap"],
                                "last_price": stock["price"],
                                "last_change_pct": stock["change_pct"],
                            }),
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save stock {stock['code']}: {e}")
                
                await db.commit()
            
            if len(stocks) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(stocks)} stocks failed to save to database")
            
            logger.info_with_context(
                "Stock list collection completed",
                context={"task_id": task.task_id, "count": len(stocks), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(stocks),
                "saved": saved_count,
                "failed": failed_count,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Stock list collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class RealtimeQuoteHandler(DataCollectionHandler):
    """
    Handler for real-time quote collection.
    
    Saves data to stock_daily_quote table with today's date.
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting real-time quote collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "10000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
                "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f12,f14,f15,f16,f17,f18,f20,f21",
            }
            
            quotes = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            quotes.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "price": safe_float(item.get("f2")),
                                "change_pct": safe_float(item.get("f3")),
                                "change": safe_float(item.get("f4")),
                                "volume": safe_float(item.get("f5")),
                                "amount": safe_float(item.get("f6")),
                                "amplitude": safe_float(item.get("f7")),
                                "turnover_rate": safe_float(item.get("f8")),
                                "pe_ratio": safe_float(item.get("f9")),
                                "high": safe_float(item.get("f15")),
                                "low": safe_float(item.get("f16")),
                                "open": safe_float(item.get("f17")),
                                "prev_close": safe_float(item.get("f18")),
                                "market_cap": safe_float(item.get("f20")),
                                "circulating_market_cap": safe_float(item.get("f21")),
                            })
            
            trade_date = date.today()
            saved_count = 0
            failed_count = 0
            
            async with async_session_maker() as db:
                for quote in quotes:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, pre_close,
                             change, change_pct, volume, amount, turnover_rate, amplitude,
                             market_cap, circulating_market_cap)
                            VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                    :change, :change_pct, :volume, :amount, :turnover_rate, :amplitude,
                                    :market_cap, :circulating_market_cap)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume,
                                amount = EXCLUDED.amount,
                                market_cap = EXCLUDED.market_cap
                        """)
                        await db.execute(stmt, {
                            "code": quote["code"],
                            "name": quote["name"],
                            "trade_date": trade_date,
                            "open": quote["open"] if quote["open"] > 0 else None,
                            "high": quote["high"] if quote["high"] > 0 else None,
                            "low": quote["low"] if quote["low"] > 0 else None,
                            "close": quote["price"] if quote["price"] > 0 else None,
                            "pre_close": quote["prev_close"] if quote["prev_close"] > 0 else None,
                            "change": quote["change"],
                            "change_pct": quote["change_pct"],
                            "volume": int(quote["volume"]) if quote["volume"] > 0 else None,
                            "amount": quote["amount"] if quote["amount"] > 0 else None,
                            "turnover_rate": quote["turnover_rate"] if quote["turnover_rate"] > 0 else None,
                            "amplitude": quote["amplitude"] if quote["amplitude"] > 0 else None,
                            "market_cap": quote["market_cap"] if quote["market_cap"] > 0 else None,
                            "circulating_market_cap": quote["circulating_market_cap"] if quote["circulating_market_cap"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save quote {quote['code']}: {e}")
                
                await db.commit()
            
            if len(quotes) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(quotes)} quotes failed to save to database")
            
            logger.info_with_context(
                "Real-time quote collection completed",
                context={"task_id": task.task_id, "count": len(quotes), "saved": saved_count, "failed": failed_count, "date": str(trade_date)}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(quotes),
                "saved": saved_count,
                "failed": failed_count,
                "trade_date": str(trade_date),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Real-time quote collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class IndexQuoteHandler(DataCollectionHandler):
    """
    Handler for index quote collection.
    
    Saves index data to stock_daily_quote table (indices are treated as special stocks).
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting index quote collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "100",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:1 s:2,m:0 t:5",
                "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18",
            }
            
            indices = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            indices.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "price": safe_float(item.get("f2")),
                                "change_pct": safe_float(item.get("f3")),
                                "change": safe_float(item.get("f4")),
                                "volume": safe_float(item.get("f5")),
                                "amount": safe_float(item.get("f6")),
                                "high": safe_float(item.get("f15")),
                                "low": safe_float(item.get("f16")),
                                "open": safe_float(item.get("f17")),
                                "prev_close": safe_float(item.get("f18")),
                            })
            
            trade_date = date.today()
            saved_count = 0
            failed_count = 0
            
            async with async_session_maker() as db:
                for idx in indices:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, pre_close,
                             change, change_pct, volume, amount)
                            VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                    :change, :change_pct, :volume, :amount)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume
                        """)
                        await db.execute(stmt, {
                            "code": idx["code"],
                            "name": idx["name"],
                            "trade_date": trade_date,
                            "open": idx["open"] if idx["open"] > 0 else None,
                            "high": idx["high"] if idx["high"] > 0 else None,
                            "low": idx["low"] if idx["low"] > 0 else None,
                            "close": idx["price"] if idx["price"] > 0 else None,
                            "pre_close": idx["prev_close"] if idx["prev_close"] > 0 else None,
                            "change": idx["change"],
                            "change_pct": idx["change_pct"],
                            "volume": int(idx["volume"]) if idx["volume"] > 0 else None,
                            "amount": idx["amount"] if idx["amount"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save index {idx['code']}: {e}")
                
                await db.commit()
            
            if len(indices) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(indices)} indices failed to save to database")
            
            logger.info_with_context(
                "Index quote collection completed",
                context={"task_id": task.task_id, "count": len(indices), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(indices),
                "saved": saved_count,
                "failed": failed_count,
                "trade_date": str(trade_date),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Index quote collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class NorthMoneyHandler(DataCollectionHandler):
    """
    Handler for north-bound money flow collection.
    
    Saves K-line data to stock_daily_quote table for index 000001.
    
    Source: https://push2his.eastmoney.com/api/qt/stock/kline/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting north money collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params_dict = {
                "secid": "1.000001",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
                "klt": "101",
                "fqt": "1",
                "end": "20500101",
                "lmt": "30",
            }
            
            records = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("klines"):
                        for line in data["data"]["klines"]:
                            parts = line.split(",")
                            if len(parts) >= 7:
                                records.append({
                                    "date": parts[0],
                                    "open": safe_float(parts[1]),
                                    "close": safe_float(parts[2]),
                                    "high": safe_float(parts[3]),
                                    "low": safe_float(parts[4]),
                                    "volume": safe_float(parts[5]),
                                    "amount": safe_float(parts[6]),
                                })
            
            saved_count = 0
            failed_count = 0
            async with async_session_maker() as db:
                for rec in records:
                    try:
                        trade_date = parse_date(rec["date"])
                        if not trade_date:
                            continue
                        
                        stmt = text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, volume, amount)
                            VALUES ('000001', '上证指数', :trade_date, :open, :high, :low, :close, :volume, :amount)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume,
                                amount = EXCLUDED.amount
                        """)
                        await db.execute(stmt, {
                            "trade_date": trade_date,
                            "open": rec["open"] if rec["open"] > 0 else None,
                            "high": rec["high"] if rec["high"] > 0 else None,
                            "low": rec["low"] if rec["low"] > 0 else None,
                            "close": rec["close"] if rec["close"] > 0 else None,
                            "volume": int(rec["volume"]) if rec["volume"] > 0 else None,
                            "amount": rec["amount"] if rec["amount"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save index kline {rec['date']}: {e}")
                
                await db.commit()
            
            if len(records) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(records)} records failed to save to database")
            
            logger.info_with_context(
                "North money collection completed",
                context={"task_id": task.task_id, "count": len(records), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(records),
                "saved": saved_count,
                "failed": failed_count,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"North money collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class FinancialIndicatorHandler(DataCollectionHandler):
    """
    Handler for financial indicator collection.
    
    Saves financial indicators to stock_financial_indicator table.
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting financial indicator collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "1000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
                "fields": "f12,f14,f9,f23,f162,f167,f173,f187,f116,f117",
            }
            
            indicators = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            indicators.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "pe_ratio": safe_float(item.get("f9")),
                                "pb_ratio": safe_float(item.get("f23")),
                                "ps_ratio": safe_float(item.get("f167")),
                                "total_mv": safe_float(item.get("f116")),
                                "circ_mv": safe_float(item.get("f117")),
                            })
            
            report_date = date.today()
            saved_count = 0
            failed_count = 0
            
            async with async_session_maker() as db:
                for ind in indicators:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_financial_indicator 
                            (code, name, report_date, roe, gross_margin, net_margin)
                            VALUES (:code, :name, :report_date, :roe, :gross_margin, :net_margin)
                            ON CONFLICT (code, report_date) DO UPDATE SET
                                name = EXCLUDED.name,
                                roe = EXCLUDED.roe
                        """)
                        await db.execute(stmt, {
                            "code": ind["code"],
                            "name": ind["name"],
                            "report_date": report_date,
                            "roe": ind["pe_ratio"] if ind["pe_ratio"] > 0 else None,
                            "gross_margin": ind["pb_ratio"] if ind["pb_ratio"] > 0 else None,
                            "net_margin": ind["ps_ratio"] if ind["ps_ratio"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save financial indicator {ind['code']}: {e}")
                
                await db.commit()
            
            if len(indicators) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(indicators)} indicators failed to save to database")
            
            logger.info_with_context(
                "Financial indicator collection completed",
                context={"task_id": task.task_id, "count": len(indicators), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(indicators),
                "saved": saved_count,
                "failed": failed_count,
                "report_date": str(report_date),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Financial indicator collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class ETFQuoteHandler(DataCollectionHandler):
    """
    Handler for ETF quote collection.
    
    Saves ETF quotes to stock_daily_quote table.
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting ETF quote collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "1000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "b:MK0404",
                "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18",
            }
            
            etfs = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            etfs.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "price": safe_float(item.get("f2")),
                                "change_pct": safe_float(item.get("f3")),
                                "change": safe_float(item.get("f4")),
                                "volume": safe_float(item.get("f5")),
                                "amount": safe_float(item.get("f6")),
                                "high": safe_float(item.get("f15")),
                                "low": safe_float(item.get("f16")),
                                "open": safe_float(item.get("f17")),
                                "prev_close": safe_float(item.get("f18")),
                            })
            
            trade_date = date.today()
            saved_count = 0
            failed_count = 0
            
            async with async_session_maker() as db:
                for etf in etfs:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, pre_close,
                             change, change_pct, volume, amount)
                            VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                    :change, :change_pct, :volume, :amount)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume
                        """)
                        await db.execute(stmt, {
                            "code": etf["code"],
                            "name": etf["name"],
                            "trade_date": trade_date,
                            "open": etf["open"] if etf["open"] > 0 else None,
                            "high": etf["high"] if etf["high"] > 0 else None,
                            "low": etf["low"] if etf["low"] > 0 else None,
                            "close": etf["price"] if etf["price"] > 0 else None,
                            "pre_close": etf["prev_close"] if etf["prev_close"] > 0 else None,
                            "change": etf["change"],
                            "change_pct": etf["change_pct"],
                            "volume": int(etf["volume"]) if etf["volume"] > 0 else None,
                            "amount": etf["amount"] if etf["amount"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save ETF {etf['code']}: {e}")
                
                await db.commit()
            
            if len(etfs) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(etfs)} ETFs failed to save to database")
            
            logger.info_with_context(
                "ETF quote collection completed",
                context={"task_id": task.task_id, "count": len(etfs), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(etfs),
                "saved": saved_count,
                "failed": failed_count,
                "trade_date": str(trade_date),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"ETF quote collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class IndustryQuoteHandler(DataCollectionHandler):
    """
    Handler for industry sector quote collection.
    
    Saves industry sector data to stock_daily_quote table.
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting industry quote collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "500",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90 t:2",
                "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18",
            }
            
            industries = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            industries.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "change_pct": safe_float(item.get("f3")),
                                "change": safe_float(item.get("f4")),
                                "volume": safe_float(item.get("f5")),
                                "amount": safe_float(item.get("f6")),
                                "high": safe_float(item.get("f15")),
                                "low": safe_float(item.get("f16")),
                                "open": safe_float(item.get("f17")),
                                "prev_close": safe_float(item.get("f18")),
                            })
            
            trade_date = date.today()
            saved_count = 0
            failed_count = 0
            
            async with async_session_maker() as db:
                for ind in industries:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, pre_close,
                             change, change_pct, volume, amount)
                            VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                    :change, :change_pct, :volume, :amount)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume
                        """)
                        await db.execute(stmt, {
                            "code": f"IND_{ind['code']}",
                            "name": ind["name"],
                            "trade_date": trade_date,
                            "open": ind["open"] if ind["open"] > 0 else None,
                            "high": ind["high"] if ind["high"] > 0 else None,
                            "low": ind["low"] if ind["low"] > 0 else None,
                            "close": ind["change"] if ind["change"] != 0 else None,
                            "pre_close": ind["prev_close"] if ind["prev_close"] > 0 else None,
                            "change": ind["change"],
                            "change_pct": ind["change_pct"],
                            "volume": int(ind["volume"]) if ind["volume"] > 0 else None,
                            "amount": ind["amount"] if ind["amount"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save industry {ind['code']}: {e}")
                
                await db.commit()
            
            if len(industries) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(industries)} industries failed to save to database")
            
            logger.info_with_context(
                "Industry quote collection completed",
                context={"task_id": task.task_id, "count": len(industries), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(industries),
                "saved": saved_count,
                "failed": failed_count,
                "trade_date": str(trade_date),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Industry quote collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class ConceptQuoteHandler(DataCollectionHandler):
    """
    Handler for concept sector quote collection.
    
    Saves concept sector data to stock_daily_quote table.
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context("Starting concept quote collection", context={"task_id": task.task_id})
        
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "500",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:90 t:3",
                "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f17,f18",
            }
            
            concepts = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            concepts.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "change_pct": safe_float(item.get("f3")),
                                "change": safe_float(item.get("f4")),
                                "volume": safe_float(item.get("f5")),
                                "amount": safe_float(item.get("f6")),
                                "high": safe_float(item.get("f15")),
                                "low": safe_float(item.get("f16")),
                                "open": safe_float(item.get("f17")),
                                "prev_close": safe_float(item.get("f18")),
                            })
            
            trade_date = date.today()
            saved_count = 0
            failed_count = 0
            
            async with async_session_maker() as db:
                for con in concepts:
                    try:
                        stmt = text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, pre_close,
                             change, change_pct, volume, amount)
                            VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                    :change, :change_pct, :volume, :amount)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = EXCLUDED.open,
                                high = EXCLUDED.high,
                                low = EXCLUDED.low,
                                close = EXCLUDED.close,
                                volume = EXCLUDED.volume
                        """)
                        await db.execute(stmt, {
                            "code": f"CON_{con['code']}",
                            "name": con["name"],
                            "trade_date": trade_date,
                            "open": con["open"] if con["open"] > 0 else None,
                            "high": con["high"] if con["high"] > 0 else None,
                            "low": con["low"] if con["low"] > 0 else None,
                            "close": con["change"] if con["change"] != 0 else None,
                            "pre_close": con["prev_close"] if con["prev_close"] > 0 else None,
                            "change": con["change"],
                            "change_pct": con["change_pct"],
                            "volume": int(con["volume"]) if con["volume"] > 0 else None,
                            "amount": con["amount"] if con["amount"] > 0 else None,
                        })
                        saved_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to save concept {con['code']}: {e}")
                
                await db.commit()
            
            if len(concepts) > 0 and saved_count == 0:
                raise RuntimeError(f"All {len(concepts)} concepts failed to save to database")
            
            logger.info_with_context(
                "Concept quote collection completed",
                context={"task_id": task.task_id, "count": len(concepts), "saved": saved_count, "failed": failed_count}
            )
            
            return {
                "success": saved_count > 0,
                "count": len(concepts),
                "saved": saved_count,
                "failed": failed_count,
                "trade_date": str(trade_date),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Concept quote collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


class KnowledgeGraphBuilder:
    """
    Knowledge Graph Builder for Company Data.
    
    Entity Types: company, industry, board (sector), concept
    Relation Types: belongs_to, listed_on, has_concept
    
    Writes entities and relations directly to PostgreSQL database.
    """

    @staticmethod
    def generate_entity_key(entity_type: str, entity_name: str) -> str:
        normalized_name = entity_name.strip().lower().replace(" ", "_")
        return f"{entity_type}_{normalized_name}"
    
    @staticmethod
    def generate_entity_key_with_code(entity_type: str, code: str) -> str:
        return f"{entity_type}_{code}"
    
    async def save_entity_to_db(
        self,
        db: AsyncSession,
        entity_key: str,
        entity_type: str,
        name: str,
        code: Optional[str] = None,
        industry: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
        source: str = "eastmoney",
        confidence: float = 1.0,
    ) -> EntityModel:
        existing_query = select(EntityModel).where(EntityModel.entity_id == entity_key)
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            if properties:
                existing.properties = {**(existing.properties or {}), **properties}
            existing.updated_at = datetime.utcnow()
            return existing
        
        entity = EntityModel(
            id=str(uuid.uuid4()),
            entity_id=entity_key,
            entity_type=entity_type,
            name=name,
            code=code,
            industry=industry,
            properties=properties or {},
            source=source,
            confidence=confidence,
        )
        db.add(entity)
        return entity
    
    async def save_relation_to_db(
        self,
        db: AsyncSession,
        source_key: str,
        target_key: str,
        relation_type: str,
        evidence: str = "",
        weight: float = 1.0,
        confidence: float = 1.0,
        source: str = "eastmoney",
    ) -> Optional[RelationModel]:
        existing_query = select(RelationModel).where(
            RelationModel.source_entity_id == source_key,
            RelationModel.target_entity_id == target_key,
            RelationModel.relation_type == relation_type,
        )
        result = await db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        source_exists = await db.execute(
            select(EntityModel).where(EntityModel.entity_id == source_key)
        )
        target_exists = await db.execute(
            select(EntityModel).where(EntityModel.entity_id == target_key)
        )
        
        if not source_exists.scalar_one_or_none() or not target_exists.scalar_one_or_none():
            return None
        
        relation = RelationModel(
            id=str(uuid.uuid4()),
            relation_id=f"rel_{uuid.uuid4().hex[:8]}",
            source_entity_id=source_key,
            target_entity_id=target_key,
            relation_type=relation_type,
            weight=weight,
            confidence=confidence,
            evidence=evidence,
            source=source,
        )
        db.add(relation)
        return relation
    
    async def build_and_save_to_db(
        self,
        db: AsyncSession,
        stocks: list[dict],
    ) -> tuple[int, int]:
        entity_count = 0
        relation_count = 0
        
        for stock in stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            industry = stock.get("industry", "")
            board = stock.get("board", "")
            concepts_str = stock.get("concepts", "")
            
            company_key = self.generate_entity_key_with_code("company", code)
            
            await self.save_entity_to_db(
                db=db,
                entity_key=company_key,
                entity_type="company",
                name=name,
                code=code,
                industry=industry if industry else None,
                properties={
                    "market_cap": stock.get("market_cap", 0),
                    "circulating_cap": stock.get("circulating_cap", 0),
                    "price": stock.get("price", 0),
                    "change_pct": stock.get("change_pct", 0),
                },
            )
            entity_count += 1
            
            if industry:
                industry_key = self.generate_entity_key("industry", industry)
                await self.save_entity_to_db(
                    db=db,
                    entity_key=industry_key,
                    entity_type="industry",
                    name=industry,
                )
                entity_count += 1
                
                await self.save_relation_to_db(
                    db=db,
                    source_key=company_key,
                    target_key=industry_key,
                    relation_type="belongs_to",
                    evidence=f"{name}属于{industry}行业",
                )
                relation_count += 1
            
            if board:
                board_key = self.generate_entity_key("sector", board)
                await self.save_entity_to_db(
                    db=db,
                    entity_key=board_key,
                    entity_type="sector",
                    name=board,
                )
                entity_count += 1
                
                await self.save_relation_to_db(
                    db=db,
                    source_key=company_key,
                    target_key=board_key,
                    relation_type="listed_on",
                    evidence=f"{name}上市于{board}",
                )
                relation_count += 1
            
            if concepts_str:
                concepts = [c.strip() for c in concepts_str.split(",") if c.strip()]
                for concept in concepts[:10]:
                    concept_key = self.generate_entity_key("concept", concept)
                    await self.save_entity_to_db(
                        db=db,
                        entity_key=concept_key,
                        entity_type="concept",
                        name=concept,
                    )
                    entity_count += 1
                    
                    await self.save_relation_to_db(
                        db=db,
                        source_key=company_key,
                        target_key=concept_key,
                        relation_type="has_concept",
                        evidence=f"{name}具有{concept}概念",
                    )
                    relation_count += 1
        
        await db.commit()
        return entity_count, relation_count


class CompanyProfileHandler(DataCollectionHandler):
    """
    Handler for company profile collection and knowledge graph construction.
    
    Data Chain:
    1. Fetch all A-share stock list from EastMoney
    2. Build knowledge graph entities and relations
    3. Save to PostgreSQL database
    
    Source: https://push2.eastmoney.com/api/qt/clist/get
    """

    async def execute(self, task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
        logger.info_with_context(
            "Starting company profile collection",
            context={"task_id": task.task_id}
        )
        
        try:
            limit = params.get("limit", 0)
            builder = KnowledgeGraphBuilder()
            
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params_dict = {
                "pn": "1",
                "pz": "10000",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
                "fields": "f12,f14,f100,f102,f103,f2,f3,f20,f21",
            }
            
            stocks = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params_dict, timeout=30) as response:
                    data = await response.json()
                    
                    if data.get("data") and data["data"].get("diff"):
                        for item in data["data"]["diff"]:
                            stocks.append({
                                "code": safe_str(item.get("f12")),
                                "name": safe_str(item.get("f14")),
                                "industry": safe_str(item.get("f100")),
                                "board": safe_str(item.get("f102")),
                                "concepts": safe_str(item.get("f103")),
                                "price": safe_float(item.get("f2")),
                                "change_pct": safe_float(item.get("f3")),
                                "market_cap": safe_float(item.get("f20")),
                                "circulating_cap": safe_float(item.get("f21")),
                            })
            
            stocks_to_process = stocks[:limit] if limit > 0 else stocks
            
            logger.info_with_context(
                f"Found {len(stocks_to_process)} stocks",
                context={"task_id": task.task_id}
            )
            
            async with async_session_maker() as db:
                entity_count, relation_count = await builder.build_and_save_to_db(
                    db, stocks_to_process
                )
            
            if len(stocks_to_process) > 0 and entity_count == 0:
                raise RuntimeError(f"Failed to build knowledge graph for {len(stocks_to_process)} stocks")
            
            logger.info_with_context(
                "Company profile collection completed",
                context={
                    "task_id": task.task_id,
                    "stock_count": len(stocks_to_process),
                    "entity_count": entity_count,
                    "relation_count": relation_count,
                }
            )
            
            return {
                "success": entity_count > 0,
                "stock_count": len(stocks_to_process),
                "entity_count": entity_count,
                "relation_count": relation_count,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error_with_context(
                f"Company profile collection failed: {e}",
                context={"task_id": task.task_id, "error": str(e)}
            )
            raise


HANDLERS: dict[str, type[DataCollectionHandler]] = {
    "stock_list": StockListHandler,
    "realtime_quote": RealtimeQuoteHandler,
    "index_quote": IndexQuoteHandler,
    "north_money": NorthMoneyHandler,
    "financial_indicator": FinancialIndicatorHandler,
    "etf_quote": ETFQuoteHandler,
    "industry_quote": IndustryQuoteHandler,
    "concept_quote": ConceptQuoteHandler,
    "company_profile": CompanyProfileHandler,
}


def get_handler(task_type: str) -> DataCollectionHandler | None:
    """Get handler for task type."""
    handler_class = HANDLERS.get(task_type)
    if handler_class:
        return handler_class()
    return None
