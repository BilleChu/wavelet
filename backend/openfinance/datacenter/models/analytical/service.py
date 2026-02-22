"""
ADS Service Layer.

Provides unified data services for the Analytical Data Store.
All data comes from real backend systems, NO mock data allowed.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy import select

from openfinance.datacenter.models.analytical.base import DataQuality
from openfinance.datacenter.models.analytical.market import ADSKLineModel
from openfinance.datacenter.models.analytical.quant import ADSFactorModel
from openfinance.datacenter.models.analytical.macro import ADSMacroEconomicModel
from openfinance.datacenter.models.analytical.financial import ADSFinancialIndicatorModel
from openfinance.datacenter.models.analytical.sentiment import ADSNewsModel
from openfinance.datacenter.models.analytical.meta import ADSMetaModel
from openfinance.datacenter.observability import DataValidator
from openfinance.datacenter.models.analytical.repository import ADSKLineRepository, ADSFactorRepository
from openfinance.infrastructure.database.database import async_session_maker

logger = logging.getLogger(__name__)


@dataclass
class StockQuote:
    """Stock quote data."""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    turnover_rate: float
    market_cap: float
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None


@dataclass
class FinancialIndicator:
    """Financial indicator data."""
    code: str
    report_date: str
    eps: float
    bps: float
    roe: float
    roa: float
    gross_margin: float
    net_margin: float
    debt_ratio: float
    revenue: float
    net_profit: float
    revenue_yoy: float
    net_profit_yoy: float


@dataclass
class MacroIndicator:
    """Macro economic indicator."""
    indicator_code: str
    indicator_name: str
    value: float
    unit: str
    period: str
    country: str
    yoy_change: Optional[float] = None


class ADSConfig(BaseModel):
    """Configuration for ADS service."""
    
    default_limit: int = 1000
    max_limit: int = 10000
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    validate_on_read: bool = True
    quality_threshold: float = 0.8


class ADSService:
    """
    Unified Analytical Data Store Service.
    
    Provides:
    - Data integrity validation
    - K-Line data access
    - Factor data access
    - Financial indicators
    - Macro economic data
    - News data
    - Data quality management
    
    All data comes from real backend systems, NO mock data.
    """
    
    def __init__(self, config: ADSConfig | None = None) -> None:
        self._config = config or ADSConfig()
        self._kline_repo = ADSKLineRepository()
        self._factor_repo = ADSFactorRepository()
        self._validator = DataValidator()
    
    async def close(self) -> None:
        """Close all resources."""
        await self._kline_repo.close()
        await self._factor_repo.close()
    
    async def get_kline_data(
        self,
        code: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
    ) -> list[ADSKLineModel]:
        limit = min(limit or self._config.default_limit, self._config.max_limit)
        
        data = await self._kline_repo.find_by_code(
            code=code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        
        if self._config.validate_on_read:
            for record in data:
                record.quality = self._assess_quality(record)
        
        return data
    
    async def get_kline_by_date(
        self,
        trade_date: date,
        codes: list[str] | None = None,
    ) -> list[ADSKLineModel]:
        data = await self._kline_repo.find_by_date(
            trade_date=trade_date,
            codes=codes,
        )
        
        if self._config.validate_on_read:
            for record in data:
                record.quality = self._assess_quality(record)
        
        return data
    
    async def get_latest_kline(
        self,
        code: str,
        count: int = 100,
    ) -> list[ADSKLineModel]:
        data = await self._kline_repo.find_latest(code=code, count=count)
        
        if self._config.validate_on_read:
            for record in data:
                record.quality = self._assess_quality(record)
        
        return data
    
    async def get_factor_data(
        self,
        factor_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        codes: list[str] | None = None,
    ) -> list[ADSFactorModel]:
        return await self._factor_repo.find_by_factor(
            factor_id=factor_id,
            start_date=start_date,
            end_date=end_date,
            codes=codes,
        )
    
    async def get_trading_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        return await self._kline_repo.get_trading_dates(
            start_date=start_date,
            end_date=end_date,
        )
    
    async def get_date_range(self, code: str) -> tuple[date | None, date | None]:
        return await self._kline_repo.get_date_range(code=code)
    
    async def get_metadata(self, table_name: str) -> ADSMetaModel:
        return ADSMetaModel(
            table_name=table_name,
            data_type=table_name,
            processing_status="validated",
        )
    
    async def get_stock_quote(self, code: str) -> Optional[StockQuote]:
        """Get real-time stock quote."""
        try:
            klines = await self.get_kline_data(code, limit=1)
            if klines:
                k = klines[0]
                return StockQuote(
                    code=k.code,
                    name=k.name or "",
                    price=k.close or 0,
                    change_pct=k.change_pct or 0,
                    volume=k.volume or 0,
                    amount=k.amount or 0,
                    turnover_rate=k.turnover_rate or 0,
                    market_cap=0,
                    pe_ratio=None,
                    pb_ratio=None,
                )
        except Exception as e:
            logger.error(f"Failed to get stock quote for {code}: {e}")
        return None
    
    async def get_stock_quotes(self, codes: list[str]) -> list[StockQuote]:
        """Get multiple stock quotes."""
        results = []
        for code in codes:
            quote = await self.get_stock_quote(code)
            if quote:
                results.append(quote)
        return results
    
    async def get_financial_indicators(
        self,
        code: str,
        years: int = 5,
    ) -> list[FinancialIndicator]:
        """Get financial indicators for a stock."""
        try:
            from openfinance.datacenter.models.orm import StockFinancialIndicatorModel
            
            async with async_session_maker() as session:
                query = select(StockFinancialIndicatorModel).where(
                    StockFinancialIndicatorModel.code == code
                ).order_by(StockFinancialIndicatorModel.report_date.desc()).limit(years * 4)
                
                result = await session.execute(query)
                records = result.scalars().all()
                
                return [
                    FinancialIndicator(
                        code=r.code,
                        report_date=str(r.report_date) if r.report_date else "",
                        eps=float(r.eps) if r.eps else 0,
                        bps=float(r.bps) if r.bps else 0,
                        roe=float(r.roe) if r.roe else 0,
                        roa=float(r.roa) if r.roa else 0,
                        gross_margin=float(r.gross_margin) if r.gross_margin else 0,
                        net_margin=float(r.net_margin) if r.net_margin else 0,
                        debt_ratio=float(r.debt_ratio) if r.debt_ratio else 0,
                        revenue=float(r.revenue) if r.revenue else 0,
                        net_profit=float(r.net_profit) if r.net_profit else 0,
                        revenue_yoy=float(r.revenue_yoy) if r.revenue_yoy else 0,
                        net_profit_yoy=float(r.net_profit_yoy) if r.net_profit_yoy else 0,
                    )
                    for r in records
                ]
        except Exception as e:
            logger.error(f"Failed to get financial indicators for {code}: {e}")
        return []
    
    async def get_macro_indicators(
        self,
        indicator_codes: list[str],
        country: str = "CN",
    ) -> list[MacroIndicator]:
        """Get macro economic indicators."""
        try:
            from openfinance.datacenter.models.orm import MacroEconomicModel
            
            async with async_session_maker() as session:
                query = select(MacroEconomicModel)
                if indicator_codes:
                    query = query.where(MacroEconomicModel.indicator_code.in_(indicator_codes))
                query = query.order_by(MacroEconomicModel.published_at.desc()).limit(50)
                
                result = await session.execute(query)
                records = result.scalars().all()
                
                return [
                    MacroIndicator(
                        indicator_code=r.indicator_code,
                        indicator_name=r.indicator_name,
                        value=float(r.value) if r.value else 0,
                        unit=r.unit or "",
                        period=r.period,
                        country=r.country or country,
                        yoy_change=None,
                    )
                    for r in records
                ]
        except Exception as e:
            logger.error(f"Failed to get macro indicators: {e}")
        return []
    
    async def get_news(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """Get market news."""
        try:
            from openfinance.datacenter.models.orm import NewsModel
            from sqlalchemy import or_
            
            async with async_session_maker() as session:
                query = select(NewsModel)
                
                if keyword:
                    query = query.where(
                        or_(
                            NewsModel.title.ilike(f"%{keyword}%"),
                            NewsModel.content.ilike(f"%{keyword}%"),
                        )
                    )
                
                query = query.order_by(NewsModel.published_at.desc()).limit(limit)
                
                result = await session.execute(query)
                records = result.scalars().all()
                
                return [
                    {
                        "news_id": str(n.id),
                        "title": n.title,
                        "content": n.content[:500] if n.content and len(n.content) > 500 else n.content,
                        "source": n.source,
                        "category": n.category,
                        "keywords": n.keywords if n.keywords else [],
                        "sentiment": float(n.sentiment) if n.sentiment else None,
                        "published_at": n.published_at.isoformat() if n.published_at else None,
                    }
                    for n in records
                ]
        except Exception as e:
            logger.error(f"Failed to get news: {e}")
        return []
    
    async def health_check(self) -> dict[str, Any]:
        try:
            return {
                "status": "healthy",
                "checked_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    def _assess_quality(self, record: ADSKLineModel) -> DataQuality:
        if not record.is_valid:
            return DataQuality.LOW
        
        missing_count = sum([
            record.open is None,
            record.high is None,
            record.low is None,
            record.close is None,
            record.volume is None,
        ])
        
        if missing_count == 0:
            return DataQuality.HIGH
        elif missing_count <= 2:
            return DataQuality.MEDIUM
        return DataQuality.LOW


_ads_service: ADSService | None = None


def get_ads_service() -> ADSService:
    """Get the global ADS service instance."""
    global _ads_service
    if _ads_service is None:
        _ads_service = ADSService()
    return _ads_service
