#!/usr/bin/env python3
"""
Data Migration Script.

Migrates existing JSON data files to PostgreSQL database.

Usage:
    python scripts/migrate_json_to_db.py [--dry-run] [--data-dir PATH]
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from openfinance.datacenter.database import async_session_maker
from openfinance.core.logging_config import get_logger

logger = get_logger(__name__)


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
        for fmt in ["%Y-%m-%d", "%Y%m%d"]:
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


class DataMigrator:
    """Migrates JSON data to PostgreSQL database."""
    
    def __init__(self, data_dir: Path, dry_run: bool = False):
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.stats = {
            "stock_list": {"total": 0, "migrated": 0},
            "realtime_quotes": {"total": 0, "migrated": 0},
            "index_quotes": {"total": 0, "migrated": 0},
            "financials": {"total": 0, "migrated": 0},
            "etf": {"total": 0, "migrated": 0},
            "industry": {"total": 0, "migrated": 0},
            "concept": {"total": 0, "migrated": 0},
        }
    
    async def migrate_stock_list(self) -> tuple[int, int]:
        """Migrate stock_list.json to stock_basic table."""
        file_path = self.data_dir / "stock_list.json"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0, 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        stocks = data.get("stocks", [])
        total = len(stocks)
        migrated = 0
        
        logger.info(f"Migrating {total} stocks from {file_path}")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would migrate stock list")
            return total, total
        
        async with async_session_maker() as session:
            for stock in stocks:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.stock_basic 
                        (code, name, industry, market, market_cap, properties, updated_at)
                        VALUES (:code, :name, :industry, :market, :market_cap, CAST(:properties AS jsonb), NOW())
                        ON CONFLICT (code) DO UPDATE SET
                            name = EXCLUDED.name,
                            industry = COALESCE(EXCLUDED.industry, openfinance.stock_basic.industry),
                            market_cap = COALESCE(EXCLUDED.market_cap, openfinance.stock_basic.market_cap),
                            properties = EXCLUDED.properties,
                            updated_at = NOW()
                    """), {
                        "code": safe_str(stock.get("code")),
                        "name": safe_str(stock.get("name")),
                        "industry": safe_str(stock.get("industry")) or None,
                        "market": safe_str(stock.get("board")) or None,
                        "market_cap": safe_float(stock.get("market_cap")) if safe_float(stock.get("market_cap")) > 0 else None,
                        "properties": json.dumps({
                            "concepts": stock.get("concepts", ""),
                            "circulating_cap": stock.get("circulating_cap", 0),
                            "last_price": stock.get("price", 0),
                            "last_change_pct": stock.get("change_pct", 0),
                        }),
                    })
                    migrated += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate stock {stock.get('code')}: {e}")
            
            await session.commit()
        
        logger.info(f"Migrated {migrated}/{total} stocks")
        return total, migrated
    
    async def migrate_realtime_quotes(self) -> tuple[int, int]:
        """Migrate realtime quotes JSON to stock_daily_quote table."""
        quotes_dir = self.data_dir / "quotes"
        if not quotes_dir.exists():
            logger.warning(f"Directory not found: {quotes_dir}")
            return 0, 0
        
        total = 0
        migrated = 0
        
        for file_path in sorted(quotes_dir.glob("realtime_*.json")):
            logger.info(f"Processing {file_path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            quotes = data.get("quotes", [])
            file_total = len(quotes)
            file_migrated = 0
            
            date_str = file_path.stem.replace("realtime_", "")
            trade_date = parse_date(date_str) or date.today()
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate {file_total} quotes from {file_path}")
                total += file_total
                migrated += file_total
                continue
            
            async with async_session_maker() as session:
                for quote in quotes:
                    try:
                        await session.execute(text("""
                            INSERT INTO openfinance.stock_daily_quote 
                            (code, name, trade_date, open, high, low, close, pre_close,
                             change, change_pct, volume, amount, turnover_rate, amplitude,
                             market_cap, circulating_market_cap)
                            VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                    :change, :change_pct, :volume, :amount, :turnover_rate, :amplitude,
                                    :market_cap, :circulating_market_cap)
                            ON CONFLICT (code, trade_date) DO UPDATE SET
                                open = COALESCE(EXCLUDED.open, openfinance.stock_daily_quote.open),
                                high = COALESCE(EXCLUDED.high, openfinance.stock_daily_quote.high),
                                low = COALESCE(EXCLUDED.low, openfinance.stock_daily_quote.low),
                                close = COALESCE(EXCLUDED.close, openfinance.stock_daily_quote.close)
                        """), {
                            "code": safe_str(quote.get("code")),
                            "name": safe_str(quote.get("name")),
                            "trade_date": trade_date,
                            "open": safe_float(quote.get("open")) if safe_float(quote.get("open")) > 0 else None,
                            "high": safe_float(quote.get("high")) if safe_float(quote.get("high")) > 0 else None,
                            "low": safe_float(quote.get("low")) if safe_float(quote.get("low")) > 0 else None,
                            "close": safe_float(quote.get("price")) if safe_float(quote.get("price")) > 0 else None,
                            "pre_close": safe_float(quote.get("prev_close")) if safe_float(quote.get("prev_close")) > 0 else None,
                            "change": safe_float(quote.get("change")),
                            "change_pct": safe_float(quote.get("change_pct")),
                            "volume": int(safe_float(quote.get("volume"))) if safe_float(quote.get("volume")) > 0 else None,
                            "amount": safe_float(quote.get("amount")) if safe_float(quote.get("amount")) > 0 else None,
                            "turnover_rate": safe_float(quote.get("turnover_rate")) if safe_float(quote.get("turnover_rate")) > 0 else None,
                            "amplitude": safe_float(quote.get("amplitude")) if safe_float(quote.get("amplitude")) > 0 else None,
                            "market_cap": safe_float(quote.get("market_cap")) if safe_float(quote.get("market_cap")) > 0 else None,
                            "circulating_market_cap": safe_float(quote.get("circulating_market_cap")) if safe_float(quote.get("circulating_market_cap")) > 0 else None,
                        })
                        file_migrated += 1
                    except Exception as e:
                        logger.warning(f"Failed to migrate quote {quote.get('code')}: {e}")
                
                await session.commit()
            
            logger.info(f"Migrated {file_migrated}/{file_total} quotes from {file_path}")
            total += file_total
            migrated += file_migrated
        
        return total, migrated
    
    async def migrate_index_quotes(self) -> tuple[int, int]:
        """Migrate index_quotes.json to stock_daily_quote table."""
        file_path = self.data_dir / "indices" / "index_quotes.json"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0, 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        indices = data.get("indices", [])
        total = len(indices)
        migrated = 0
        trade_date = date.today()
        
        logger.info(f"Migrating {total} index quotes from {file_path}")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would migrate index quotes")
            return total, total
        
        async with async_session_maker() as session:
            for idx in indices:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.stock_daily_quote 
                        (code, name, trade_date, open, high, low, close, pre_close,
                         change, change_pct, volume, amount)
                        VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                :change, :change_pct, :volume, :amount)
                        ON CONFLICT (code, trade_date) DO UPDATE SET
                            open = COALESCE(EXCLUDED.open, openfinance.stock_daily_quote.open),
                            high = COALESCE(EXCLUDED.high, openfinance.stock_daily_quote.high),
                            low = COALESCE(EXCLUDED.low, openfinance.stock_daily_quote.low),
                            close = COALESCE(EXCLUDED.close, openfinance.stock_daily_quote.close)
                    """), {
                        "code": safe_str(idx.get("code")),
                        "name": safe_str(idx.get("name")),
                        "trade_date": trade_date,
                        "open": safe_float(idx.get("open")) if safe_float(idx.get("open")) > 0 else None,
                        "high": safe_float(idx.get("high")) if safe_float(idx.get("high")) > 0 else None,
                        "low": safe_float(idx.get("low")) if safe_float(idx.get("low")) > 0 else None,
                        "close": safe_float(idx.get("price")) if safe_float(idx.get("price")) > 0 else None,
                        "pre_close": safe_float(idx.get("prev_close")) if safe_float(idx.get("prev_close")) > 0 else None,
                        "change": safe_float(idx.get("change")),
                        "change_pct": safe_float(idx.get("change_pct")),
                        "volume": int(safe_float(idx.get("volume"))) if safe_float(idx.get("volume")) > 0 else None,
                        "amount": safe_float(idx.get("amount")) if safe_float(idx.get("amount")) > 0 else None,
                    })
                    migrated += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate index {idx.get('code')}: {e}")
            
            await session.commit()
        
        logger.info(f"Migrated {migrated}/{total} index quotes")
        return total, migrated
    
    async def migrate_financial_indicators(self) -> tuple[int, int]:
        """Migrate financial indicators JSON to stock_financial_indicator table."""
        financials_dir = self.data_dir / "financials"
        if not financials_dir.exists():
            logger.warning(f"Directory not found: {financials_dir}")
            return 0, 0
        
        total = 0
        migrated = 0
        
        for file_path in sorted(financials_dir.glob("indicators_*.json")):
            logger.info(f"Processing {file_path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            indicators = data.get("indicators", [])
            file_total = len(indicators)
            file_migrated = 0
            
            date_str = file_path.stem.replace("indicators_", "")
            report_date = parse_date(date_str) or date.today()
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate {file_total} indicators from {file_path}")
                total += file_total
                migrated += file_total
                continue
            
            async with async_session_maker() as session:
                for ind in indicators:
                    try:
                        await session.execute(text("""
                            INSERT INTO openfinance.stock_financial_indicator 
                            (code, name, report_date, roe, gross_margin, net_margin)
                            VALUES (:code, :name, :report_date, :roe, :gross_margin, :net_margin)
                            ON CONFLICT (code, report_date) DO UPDATE SET
                                name = EXCLUDED.name,
                                roe = COALESCE(EXCLUDED.roe, openfinance.stock_financial_indicator.roe)
                        """), {
                            "code": safe_str(ind.get("code")),
                            "name": safe_str(ind.get("name")),
                            "report_date": report_date,
                            "roe": safe_float(ind.get("pe_ratio")) if safe_float(ind.get("pe_ratio")) > 0 else None,
                            "gross_margin": safe_float(ind.get("pb_ratio")) if safe_float(ind.get("pb_ratio")) > 0 else None,
                            "net_margin": safe_float(ind.get("ps_ratio")) if safe_float(ind.get("ps_ratio")) > 0 else None,
                        })
                        file_migrated += 1
                    except Exception as e:
                        logger.warning(f"Failed to migrate indicator {ind.get('code')}: {e}")
                
                await session.commit()
            
            logger.info(f"Migrated {file_migrated}/{file_total} indicators from {file_path}")
            total += file_total
            migrated += file_migrated
        
        return total, migrated
    
    async def migrate_etf_quotes(self) -> tuple[int, int]:
        """Migrate ETF quotes JSON to stock_daily_quote table."""
        file_path = self.data_dir / "etf" / "etf_quotes.json"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0, 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        etfs = data.get("etfs", [])
        total = len(etfs)
        migrated = 0
        trade_date = date.today()
        
        logger.info(f"Migrating {total} ETF quotes from {file_path}")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would migrate ETF quotes")
            return total, total
        
        async with async_session_maker() as session:
            for etf in etfs:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.stock_daily_quote 
                        (code, name, trade_date, open, high, low, close, pre_close,
                         change, change_pct, volume, amount)
                        VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                :change, :change_pct, :volume, :amount)
                        ON CONFLICT (code, trade_date) DO UPDATE SET
                            open = COALESCE(EXCLUDED.open, openfinance.stock_daily_quote.open),
                            high = COALESCE(EXCLUDED.high, openfinance.stock_daily_quote.high),
                            low = COALESCE(EXCLUDED.low, openfinance.stock_daily_quote.low),
                            close = COALESCE(EXCLUDED.close, openfinance.stock_daily_quote.close)
                    """), {
                        "code": safe_str(etf.get("code")),
                        "name": safe_str(etf.get("name")),
                        "trade_date": trade_date,
                        "open": safe_float(etf.get("open")) if safe_float(etf.get("open")) > 0 else None,
                        "high": safe_float(etf.get("high")) if safe_float(etf.get("high")) > 0 else None,
                        "low": safe_float(etf.get("low")) if safe_float(etf.get("low")) > 0 else None,
                        "close": safe_float(etf.get("price")) if safe_float(etf.get("price")) > 0 else None,
                        "pre_close": safe_float(etf.get("prev_close")) if safe_float(etf.get("prev_close")) > 0 else None,
                        "change": safe_float(etf.get("change")),
                        "change_pct": safe_float(etf.get("change_pct")),
                        "volume": int(safe_float(etf.get("volume"))) if safe_float(etf.get("volume")) > 0 else None,
                        "amount": safe_float(etf.get("amount")) if safe_float(etf.get("amount")) > 0 else None,
                    })
                    migrated += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate ETF {etf.get('code')}: {e}")
            
            await session.commit()
        
        logger.info(f"Migrated {migrated}/{total} ETF quotes")
        return total, migrated
    
    async def migrate_sector_quotes(self, sector_type: str) -> tuple[int, int]:
        """Migrate industry/concept quotes JSON to stock_daily_quote table."""
        file_name = f"{sector_type}_quotes.json"
        file_path = self.data_dir / "sectors" / file_name
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return 0, 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = data.get(sector_type, data.get("industries", data.get("concepts", [])))
        total = len(items)
        migrated = 0
        trade_date = date.today()
        prefix = "IND_" if sector_type == "industry" else "CON_"
        
        logger.info(f"Migrating {total} {sector_type} quotes from {file_path}")
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would migrate {sector_type} quotes")
            return total, total
        
        async with async_session_maker() as session:
            for item in items:
                try:
                    await session.execute(text("""
                        INSERT INTO openfinance.stock_daily_quote 
                        (code, name, trade_date, open, high, low, close, pre_close,
                         change, change_pct, volume, amount)
                        VALUES (:code, :name, :trade_date, :open, :high, :low, :close, :pre_close,
                                :change, :change_pct, :volume, :amount)
                        ON CONFLICT (code, trade_date) DO UPDATE SET
                            open = COALESCE(EXCLUDED.open, openfinance.stock_daily_quote.open),
                            high = COALESCE(EXCLUDED.high, openfinance.stock_daily_quote.high),
                            low = COALESCE(EXCLUDED.low, openfinance.stock_daily_quote.low),
                            close = COALESCE(EXCLUDED.close, openfinance.stock_daily_quote.close)
                    """), {
                        "code": f"{prefix}{safe_str(item.get('code'))}",
                        "name": safe_str(item.get("name")),
                        "trade_date": trade_date,
                        "open": safe_float(item.get("open")) if safe_float(item.get("open")) > 0 else None,
                        "high": safe_float(item.get("high")) if safe_float(item.get("high")) > 0 else None,
                        "low": safe_float(item.get("low")) if safe_float(item.get("low")) > 0 else None,
                        "close": safe_float(item.get("change")) if safe_float(item.get("change")) != 0 else None,
                        "pre_close": safe_float(item.get("prev_close")) if safe_float(item.get("prev_close")) > 0 else None,
                        "change": safe_float(item.get("change")),
                        "change_pct": safe_float(item.get("change_pct")),
                        "volume": int(safe_float(item.get("volume"))) if safe_float(item.get("volume")) > 0 else None,
                        "amount": safe_float(item.get("amount")) if safe_float(item.get("amount")) > 0 else None,
                    })
                    migrated += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate {sector_type} {item.get('code')}: {e}")
            
            await session.commit()
        
        logger.info(f"Migrated {migrated}/{total} {sector_type} quotes")
        return total, migrated
    
    async def run(self):
        """Run all migrations."""
        logger.info("=" * 60)
        logger.info("Starting data migration")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 60)
        
        results = {}
        
        results["stock_list"] = await self.migrate_stock_list()
        results["realtime_quotes"] = await self.migrate_realtime_quotes()
        results["index_quotes"] = await self.migrate_index_quotes()
        results["financials"] = await self.migrate_financial_indicators()
        results["etf"] = await self.migrate_etf_quotes()
        results["industry"] = await self.migrate_sector_quotes("industry")
        results["concept"] = await self.migrate_sector_quotes("concept")
        
        logger.info("=" * 60)
        logger.info("Migration Summary:")
        total_all = 0
        migrated_all = 0
        for name, (total, migrated) in results.items():
            logger.info(f"  {name}: {migrated}/{total} records migrated")
            total_all += total
            migrated_all += migrated
        
        logger.info("-" * 60)
        logger.info(f"Total: {migrated_all}/{total_all} records migrated")
        logger.info("=" * 60)
        
        return results


async def main():
    parser = argparse.ArgumentParser(description="Migrate JSON data to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no actual writes)")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory path")
    args = parser.parse_args()
    
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = Path(__file__).parent.parent / "data"
    
    migrator = DataMigrator(data_dir, dry_run=args.dry_run)
    await migrator.run()


if __name__ == "__main__":
    asyncio.run(main())
