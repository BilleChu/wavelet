"""
ADS Repository Layer.

Provides data access for the Analytical Data Store.
All data comes from real backend systems, NO mock data allowed.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_maker
from ..models import (
    StockDailyQuoteModel,
    FactorDataModel,
)
from openfinance.datacenter.models.analytical.base import ADSModel
from openfinance.datacenter.models.analytical.market import ADSKLineModel
from openfinance.datacenter.models.analytical.quant import ADSFactorModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ADSModel)


class ADSRepository(ABC, Generic[T]):
    """Abstract base repository for ADS data."""
    
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None
    
    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = async_session_maker()
        return self._session
    
    async def close(self) -> None:
        """Close the session if owned."""
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None


class ADSKLineRepository(ADSRepository[ADSKLineModel]):
    """Repository for K-Line data."""
    
    async def find_by_code(
        self,
        code: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[ADSKLineModel]:
        """Find K-Line data by stock code."""
        session = await self._get_session()
        
        query = select(StockDailyQuoteModel).where(
            StockDailyQuoteModel.code == code
        )
        
        if start_date:
            query = query.where(StockDailyQuoteModel.trade_date >= start_date)
        if end_date:
            query = query.where(StockDailyQuoteModel.trade_date <= end_date)
        
        query = query.order_by(StockDailyQuoteModel.trade_date.desc()).limit(limit)
        
        result = await session.execute(query)
        orm_records = result.scalars().all()
        
        return [self._to_ads_model(r) for r in orm_records]
    
    async def find_by_date(
        self,
        trade_date: date,
        codes: list[str] | None = None,
    ) -> list[ADSKLineModel]:
        """Find K-Line data by trading date."""
        session = await self._get_session()
        
        query = select(StockDailyQuoteModel).where(
            StockDailyQuoteModel.trade_date == trade_date
        )
        
        if codes:
            query = query.where(StockDailyQuoteModel.code.in_(codes))
        
        result = await session.execute(query)
        orm_records = result.scalars().all()
        
        return [self._to_ads_model(r) for r in orm_records]
    
    async def find_latest(self, code: str, count: int = 100) -> list[ADSKLineModel]:
        """Find latest K-Line data for a stock."""
        return await self.find_by_code(code=code, limit=count)
    
    async def get_trading_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        """Get list of trading dates."""
        session = await self._get_session()
        
        query = select(StockDailyQuoteModel.trade_date).distinct()
        
        if start_date:
            query = query.where(StockDailyQuoteModel.trade_date >= start_date)
        if end_date:
            query = query.where(StockDailyQuoteModel.trade_date <= end_date)
        
        query = query.order_by(StockDailyQuoteModel.trade_date.desc())
        
        result = await session.execute(query)
        return [r[0] for r in result.all()]
    
    async def get_date_range(self, code: str) -> tuple[date | None, date | None]:
        """Get the date range for a stock's data."""
        session = await self._get_session()
        
        query = select(StockDailyQuoteModel).where(
            StockDailyQuoteModel.code == code
        ).order_by(StockDailyQuoteModel.trade_date)
        
        result = await session.execute(query)
        records = result.scalars().all()
        
        if not records:
            return None, None
        
        return records[0].trade_date, records[-1].trade_date
    
    def _to_ads_model(self, orm_obj: StockDailyQuoteModel) -> ADSKLineModel:
        """Convert ORM object to ADS model."""
        return ADSKLineModel.model_validate(orm_obj)


class ADSFactorRepository(ADSRepository[ADSFactorModel]):
    """Repository for factor data."""
    
    async def find_by_factor(
        self,
        factor_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        codes: list[str] | None = None,
    ) -> list[ADSFactorModel]:
        """Find factor data by factor ID."""
        session = await self._get_session()
        
        query = select(FactorDataModel).where(
            FactorDataModel.factor_id == factor_id
        )
        
        if start_date:
            query = query.where(FactorDataModel.trade_date >= start_date)
        if end_date:
            query = query.where(FactorDataModel.trade_date <= end_date)
        if codes:
            query = query.where(FactorDataModel.code.in_(codes))
        
        result = await session.execute(query)
        orm_records = result.scalars().all()
        
        return [self._to_ads_model(r) for r in orm_records]
    
    def _to_ads_model(self, orm_obj: FactorDataModel) -> ADSFactorModel:
        """Convert ORM object to ADS model."""
        return ADSFactorModel.model_validate({
            "factor_id": orm_obj.factor_id,
            "factor_name": orm_obj.factor_name,
            "factor_type": orm_obj.factor_category or "unknown",
            "code": orm_obj.code,
            "trade_date": orm_obj.trade_date,
            "value": float(orm_obj.factor_value) if orm_obj.factor_value else None,
            "value_rank": orm_obj.factor_rank,
            "value_percentile": float(orm_obj.factor_percentile) if orm_obj.factor_percentile else None,
        })
