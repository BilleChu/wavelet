"""
Data Persistence Module.

Provides database persistence for collected data with:
- Batch insert support
- Transaction management
- Error retry with exponential backoff
- Data validation before insert
- Comprehensive logging
"""

import logging
import os
import asyncio
from datetime import date, datetime
from typing import Any, TypeVar, Generic
from functools import wraps

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://openfinance:openfinance@localhost:5432/openfinance?client_encoding=utf8"
)

T = TypeVar('T')

MAX_RETRIES = 3
RETRY_DELAY = 1.0
BATCH_SIZE = 500


def _to_dict(obj: Any) -> dict[str, Any]:
    """Convert Pydantic model or dict to dict."""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    elif isinstance(obj, dict):
        return obj
    else:
        return {}


def _parse_date(value: Any) -> date | None:
    """Parse date from various formats."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            try:
                return datetime.strptime(value, "%Y%m%d").date()
            except ValueError:
                return None
    return None


def with_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


class DataPersistence:
    """Data persistence handler for collected data.
    
    Features:
    - Batch insert with configurable batch size
    - UPSERT strategy to handle duplicates
    - Transaction management with rollback on error
    - Retry logic for transient failures
    - Comprehensive logging for audit trail
    """
    
    def __init__(self, batch_size: int = BATCH_SIZE) -> None:
        self.engine = engine
        self.session_maker = async_session_maker
        self.batch_size = batch_size
    
    @with_retry()
    async def save_stock_quotes(
        self,
        quotes: list[Any],
    ) -> int:
        """Save stock daily quotes to database with batch processing."""
        if not quotes:
            return 0
        
        saved = 0
        total = len(quotes)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = quotes[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for quote in batch:
                        try:
                            data = _to_dict(quote)
                            
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
                                    close = COALESCE(EXCLUDED.close, openfinance.stock_daily_quote.close),
                                    volume = COALESCE(EXCLUDED.volume, openfinance.stock_daily_quote.volume),
                                    amount = COALESCE(EXCLUDED.amount, openfinance.stock_daily_quote.amount),
                                    market_cap = COALESCE(EXCLUDED.market_cap, openfinance.stock_daily_quote.market_cap)
                            """), {
                                "code": data.get("code", ""),
                                "name": data.get("name", ""),
                                "trade_date": _parse_date(data.get("trade_date") or data.get("date")),
                                "open": data.get("open"),
                                "high": data.get("high"),
                                "low": data.get("low"),
                                "close": data.get("close"),
                                "pre_close": data.get("pre_close"),
                                "change": data.get("change"),
                                "change_pct": data.get("change_pct") or data.get("pct_chg"),
                                "volume": data.get("volume"),
                                "amount": data.get("amount"),
                                "turnover_rate": data.get("turnover_rate"),
                                "amplitude": data.get("amplitude"),
                                "market_cap": data.get("market_cap"),
                                "circulating_market_cap": data.get("circulating_market_cap"),
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate quote: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save quote: {e}")
                    
                    saved += batch_saved
                    logger.info(f"Saved batch {i // self.batch_size + 1}: {batch_saved}/{len(batch)} quotes")
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} stock quotes to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save stock quotes, transaction rolled back: {e}")
                raise
        
        return saved
    
    @with_retry()
    async def save_stock_basic(
        self,
        stocks: list[Any],
    ) -> int:
        """Save stock basic info to database with batch processing."""
        if not stocks:
            return 0
        
        saved = 0
        total = len(stocks)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = stocks[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for stock in batch:
                        try:
                            data = _to_dict(stock)
                            
                            await session.execute(text("""
                                INSERT INTO openfinance.stock_basic 
                                (code, name, industry, market, list_date, total_shares, 
                                 circulating_shares, market_cap, pe_ratio, pb_ratio, properties)
                                VALUES (:code, :name, :industry, :market, :list_date, :total_shares,
                                        :circulating_shares, :market_cap, :pe_ratio, :pb_ratio, CAST(:properties AS jsonb))
                                ON CONFLICT (code) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    industry = COALESCE(EXCLUDED.industry, openfinance.stock_basic.industry),
                                    market_cap = COALESCE(EXCLUDED.market_cap, openfinance.stock_basic.market_cap),
                                    pe_ratio = COALESCE(EXCLUDED.pe_ratio, openfinance.stock_basic.pe_ratio),
                                    pb_ratio = COALESCE(EXCLUDED.pb_ratio, openfinance.stock_basic.pb_ratio),
                                    updated_at = NOW()
                            """), {
                                "code": data.get("code", ""),
                                "name": data.get("name", ""),
                                "industry": data.get("industry"),
                                "market": data.get("market"),
                                "list_date": _parse_date(data.get("list_date")),
                                "total_shares": data.get("total_shares"),
                                "circulating_shares": data.get("circulating_shares"),
                                "market_cap": data.get("market_cap"),
                                "pe_ratio": data.get("pe_ratio"),
                                "pb_ratio": data.get("pb_ratio"),
                                "properties": "{}",
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate stock: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save stock: {e}")
                    
                    saved += batch_saved
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} stock basic info to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save stock basic info, transaction rolled back: {e}")
                raise
        
        return saved
    
    @with_retry()
    async def save_money_flow(
        self,
        flows: list[Any],
    ) -> int:
        """Save money flow data to database with batch processing."""
        if not flows:
            return 0
        
        saved = 0
        total = len(flows)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = flows[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for flow in batch:
                        try:
                            data = _to_dict(flow)
                            
                            await session.execute(text("""
                                INSERT INTO openfinance.stock_money_flow 
                                (code, name, trade_date, main_net_inflow, main_net_inflow_pct,
                                 super_large_net_inflow, large_net_inflow, medium_net_inflow,
                                 small_net_inflow, north_net_inflow)
                                VALUES (:code, :name, :trade_date, :main_net_inflow, :main_net_inflow_pct,
                                        :super_large_net_inflow, :large_net_inflow, :medium_net_inflow,
                                        :small_net_inflow, :north_net_inflow)
                                ON CONFLICT (code, trade_date) DO UPDATE SET
                                    main_net_inflow = COALESCE(EXCLUDED.main_net_inflow, openfinance.stock_money_flow.main_net_inflow),
                                    main_net_inflow_pct = COALESCE(EXCLUDED.main_net_inflow_pct, openfinance.stock_money_flow.main_net_inflow_pct)
                            """), {
                                "code": data.get("code", ""),
                                "name": data.get("name", ""),
                                "trade_date": _parse_date(data.get("trade_date") or data.get("date")),
                                "main_net_inflow": data.get("main_net_inflow"),
                                "main_net_inflow_pct": data.get("main_net_inflow_pct"),
                                "super_large_net_inflow": data.get("super_large_net_inflow"),
                                "large_net_inflow": data.get("large_net_inflow"),
                                "medium_net_inflow": data.get("medium_net_inflow"),
                                "small_net_inflow": data.get("small_net_inflow"),
                                "north_net_inflow": data.get("north_net_inflow"),
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate money flow: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save money flow: {e}")
                    
                    saved += batch_saved
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} money flow records to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save money flow data, transaction rolled back: {e}")
                raise
        
        return saved
    
    @with_retry()
    async def save_news(
        self,
        news_list: list[Any],
    ) -> int:
        """Save news data to database with batch processing."""
        if not news_list:
            return 0
        
        saved = 0
        total = len(news_list)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = news_list[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for news in batch:
                        try:
                            data = _to_dict(news)
                            news_id = data.get("id") or data.get("news_id") or f"news_{hash(data.get('title', ''))}"
                            published_at = data.get("published_at") or data.get("publish_time") or datetime.now()
                            
                            await session.execute(text("""
                                INSERT INTO openfinance.news 
                                (news_id, title, content, source, category, keywords, published_at)
                                VALUES (:news_id, :title, :content, :source, :category, :keywords, :published_at)
                                ON CONFLICT (news_id) DO UPDATE SET
                                    title = EXCLUDED.title,
                                    content = COALESCE(EXCLUDED.content, openfinance.news.content)
                            """), {
                                "news_id": str(news_id),
                                "title": data.get("title", "")[:500],
                                "content": data.get("content", ""),
                                "source": data.get("source", "unknown"),
                                "category": data.get("category"),
                                "keywords": data.get("keywords", []),
                                "published_at": published_at,
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate news: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save news: {e}")
                    
                    saved += batch_saved
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} news records to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save news data, transaction rolled back: {e}")
                raise
        
        return saved
    
    @with_retry()
    async def save_macro_data(
        self,
        macro_list: list[Any],
    ) -> int:
        """Save macro economic data to database with batch processing."""
        if not macro_list:
            return 0
        
        saved = 0
        total = len(macro_list)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = macro_list[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for macro in batch:
                        try:
                            data = _to_dict(macro)
                            
                            await session.execute(text("""
                                INSERT INTO openfinance.macro_economic 
                                (indicator_code, indicator_name, value, unit, period, country, source)
                                VALUES (:indicator_code, :indicator_name, :value, :unit, :period, :country, :source)
                                ON CONFLICT (indicator_code, period) DO UPDATE SET
                                    value = EXCLUDED.value,
                                    indicator_name = EXCLUDED.indicator_name
                            """), {
                                "indicator_code": data.get("indicator_code", ""),
                                "indicator_name": data.get("indicator_name", ""),
                                "value": data.get("value"),
                                "unit": data.get("unit", ""),
                                "period": data.get("period", ""),
                                "country": data.get("country", "CN"),
                                "source": data.get("source", "eastmoney"),
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate macro data: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save macro data: {e}")
                    
                    saved += batch_saved
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} macro economic records to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save macro data, transaction rolled back: {e}")
                raise
        
        return saved
    
    @with_retry()
    async def save_factor_data(
        self,
        factors: list[Any],
    ) -> int:
        """Save factor data to database with batch processing."""
        if not factors:
            return 0
        
        saved = 0
        total = len(factors)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = factors[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for factor in batch:
                        try:
                            data = _to_dict(factor)
                            
                            await session.execute(text("""
                                INSERT INTO openfinance.factor_data 
                                (factor_id, factor_name, factor_category, code, trade_date, 
                                 factor_value, factor_rank, factor_percentile, neutralized)
                                VALUES (:factor_id, :factor_name, :factor_category, :code, :trade_date,
                                        :factor_value, :factor_rank, :factor_percentile, :neutralized)
                                ON CONFLICT (factor_id, code, trade_date) DO UPDATE SET
                                    factor_value = EXCLUDED.factor_value,
                                    factor_rank = COALESCE(EXCLUDED.factor_rank, openfinance.factor_data.factor_rank)
                            """), {
                                "factor_id": data.get("factor_id", ""),
                                "factor_name": data.get("factor_name", ""),
                                "factor_category": data.get("factor_category", ""),
                                "code": data.get("code", ""),
                                "trade_date": _parse_date(data.get("trade_date")),
                                "factor_value": data.get("factor_value"),
                                "factor_rank": data.get("factor_rank"),
                                "factor_percentile": data.get("factor_percentile"),
                                "neutralized": data.get("neutralized", False),
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate factor data: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save factor data: {e}")
                    
                    saved += batch_saved
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} factor records to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save factor data, transaction rolled back: {e}")
                raise
        
        return saved
    
    @with_retry()
    async def save_financial_indicator(
        self,
        indicators: list[Any],
    ) -> int:
        """Save financial indicators to database with batch processing."""
        if not indicators:
            return 0
        
        saved = 0
        total = len(indicators)
        
        async with self.session_maker() as session:
            try:
                for i in range(0, total, self.batch_size):
                    batch = indicators[i:i + self.batch_size]
                    batch_saved = 0
                    
                    for ind in batch:
                        try:
                            data = _to_dict(ind)
                            
                            await session.execute(text("""
                                INSERT INTO openfinance.stock_financial_indicator 
                                (code, name, report_date, eps, bps, roe, roa, gross_margin, net_margin,
                                 debt_ratio, current_ratio, quick_ratio, revenue, net_profit,
                                 revenue_yoy, net_profit_yoy)
                                VALUES (:code, :name, :report_date, :eps, :bps, :roe, :roa, :gross_margin, :net_margin,
                                        :debt_ratio, :current_ratio, :quick_ratio, :revenue, :net_profit,
                                        :revenue_yoy, :net_profit_yoy)
                                ON CONFLICT (code, report_date) DO UPDATE SET
                                    eps = COALESCE(EXCLUDED.eps, openfinance.stock_financial_indicator.eps),
                                    roe = COALESCE(EXCLUDED.roe, openfinance.stock_financial_indicator.roe),
                                    revenue = COALESCE(EXCLUDED.revenue, openfinance.stock_financial_indicator.revenue),
                                    net_profit = COALESCE(EXCLUDED.net_profit, openfinance.stock_financial_indicator.net_profit)
                            """), {
                                "code": data.get("code", ""),
                                "name": data.get("name", ""),
                                "report_date": _parse_date(data.get("report_date")),
                                "eps": data.get("eps"),
                                "bps": data.get("bps"),
                                "roe": data.get("roe"),
                                "roa": data.get("roa"),
                                "gross_margin": data.get("gross_margin"),
                                "net_margin": data.get("net_margin"),
                                "debt_ratio": data.get("debt_ratio"),
                                "current_ratio": data.get("current_ratio"),
                                "quick_ratio": data.get("quick_ratio"),
                                "revenue": data.get("revenue"),
                                "net_profit": data.get("net_profit"),
                                "revenue_yoy": data.get("revenue_yoy"),
                                "net_profit_yoy": data.get("net_profit_yoy"),
                            })
                            batch_saved += 1
                        except IntegrityError as e:
                            logger.debug(f"Skipping duplicate financial indicator: {e}")
                        except Exception as e:
                            logger.warning(f"Failed to save financial indicator: {e}")
                    
                    saved += batch_saved
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} financial indicator records to database")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save financial indicators, transaction rolled back: {e}")
                raise
        
        return saved
    
    async def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        stats = {}
        async with self.session_maker() as session:
            tables = [
                "stock_daily_quote",
                "stock_basic",
                "stock_financial_indicator",
                "stock_money_flow",
                "macro_economic",
                "news",
                "factor_data",
                "entities",
                "relations",
            ]
            
            for table in tables:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM openfinance.{table}"))
                    stats[table] = result.scalar() or 0
                except Exception:
                    stats[table] = 0
        
        return stats
    
    async def get_latest_trade_date(self, code: str | None = None) -> date | None:
        """Get the latest trade date from stock_daily_quote table."""
        async with self.session_maker() as session:
            if code:
                result = await session.execute(text("""
                    SELECT MAX(trade_date) FROM openfinance.stock_daily_quote 
                    WHERE code = :code
                """), {"code": code})
            else:
                result = await session.execute(text("""
                    SELECT MAX(trade_date) FROM openfinance.stock_daily_quote
                """))
            
            max_date = result.scalar()
            return max_date if max_date else None
    
    async def check_data_freshness(self, table: str, max_age_hours: int = 24) -> bool:
        """Check if data in a table is fresh (updated within specified hours)."""
        async with self.session_maker() as session:
            try:
                if table == "stock_daily_quote":
                    result = await session.execute(text("""
                        SELECT MAX(collected_at) FROM openfinance.stock_daily_quote
                    """))
                elif table == "stock_basic":
                    result = await session.execute(text("""
                        SELECT MAX(updated_at) FROM openfinance.stock_basic
                    """))
                else:
                    return False
                
                last_update = result.scalar()
                if not last_update:
                    return False
                
                age = datetime.now(last_update.tzinfo) - last_update
                return age.total_seconds() < max_age_hours * 3600
                
            except Exception as e:
                logger.warning(f"Failed to check data freshness for {table}: {e}")
                return False


persistence = DataPersistence()
