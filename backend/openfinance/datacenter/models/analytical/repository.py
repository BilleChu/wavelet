"""
ADS Repository Layer.

Provides data access for the Analytical Data Store.
All data comes from real backend systems, NO mock data allowed.

Architecture:
- GenericADSRepository: 泛型基类，自动处理 ORM ↔ ADS 转换
- 具体 Repository: 继承基类，提供特定业务方法
"""

import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.infrastructure.database.database import async_session_maker
from openfinance.datacenter.models.orm import (
    StockDailyQuoteModel,
    FactorDataModel,
)
from openfinance.datacenter.models.analytical.base import ADSModel
from openfinance.datacenter.models.analytical.market import ADSKLineModel
from openfinance.datacenter.models.analytical.quant import ADSFactorModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ADSModel)
ORMModel = TypeVar("ORMModel")


class GenericADSRepository(ABC, Generic[T, ORMModel]):
    """
    泛型 ADS Repository 基类。
    
    自动处理:
    - Session 管理
    - ORM ↔ ADS 模型转换
    - 通用查询方法
    """
    
    orm_model_class: type[ORMModel]
    ads_model_class: type[T]
    
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None
    
    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = async_session_maker()
        return self._session
    
    async def close(self) -> None:
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None
    
    def _to_ads_model(self, orm_obj: ORMModel) -> T:
        """Convert ORM object to ADS model. Override for custom mapping."""
        return self.ads_model_class.model_validate(orm_obj)
    
    def _to_ads_models(self, orm_objects: list[ORMModel]) -> list[T]:
        """Convert list of ORM objects to ADS models."""
        return [self._to_ads_model(obj) for obj in orm_objects]


class ADSKLineRepository(GenericADSRepository[ADSKLineModel, StockDailyQuoteModel]):
    """Repository for K-Line data."""
    
    orm_model_class = StockDailyQuoteModel
    ads_model_class = ADSKLineModel
    
    async def find_by_code(
        self,
        code: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[ADSKLineModel]:
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
        
        return self._to_ads_models(orm_records)
    
    async def find_by_date(
        self,
        trade_date: date,
        codes: list[str] | None = None,
    ) -> list[ADSKLineModel]:
        session = await self._get_session()
        
        query = select(StockDailyQuoteModel).where(
            StockDailyQuoteModel.trade_date == trade_date
        )
        
        if codes:
            query = query.where(StockDailyQuoteModel.code.in_(codes))
        
        result = await session.execute(query)
        orm_records = result.scalars().all()
        
        return self._to_ads_models(orm_records)
    
    async def find_latest(self, code: str, count: int = 100) -> list[ADSKLineModel]:
        return await self.find_by_code(code=code, limit=count)
    
    async def get_trading_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
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
        session = await self._get_session()
        
        query = select(StockDailyQuoteModel).where(
            StockDailyQuoteModel.code == code
        ).order_by(StockDailyQuoteModel.trade_date)
        
        result = await session.execute(query)
        records = result.scalars().all()
        
        if not records:
            return None, None
        
        return records[0].trade_date, records[-1].trade_date


class ADSFactorRepository(GenericADSRepository[ADSFactorModel, FactorDataModel]):
    """
    Repository for factor data.
    
    统一字段映射:
    - ORM: factor_category, factor_value, factor_rank, factor_percentile
    - ADS: factor_type, value, value_rank, value_percentile
    """
    
    orm_model_class = FactorDataModel
    ads_model_class = ADSFactorModel
    
    async def find_by_factor(
        self,
        factor_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        codes: list[str] | None = None,
    ) -> list[ADSFactorModel]:
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
        
        return self._to_ads_models(orm_records)
    
    async def find_by_category(
        self,
        factor_category: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 1000,
    ) -> list[ADSFactorModel]:
        session = await self._get_session()
        
        query = select(FactorDataModel).where(
            FactorDataModel.factor_category == factor_category
        )
        
        if start_date:
            query = query.where(FactorDataModel.trade_date >= start_date)
        if end_date:
            query = query.where(FactorDataModel.trade_date <= end_date)
        
        query = query.limit(limit)
        
        result = await session.execute(query)
        orm_records = result.scalars().all()
        
        return self._to_ads_models(orm_records)
    
    def _to_ads_model(self, orm_obj: FactorDataModel) -> ADSFactorModel:
        """Convert ORM object to ADS model with field alias support."""
        return ADSFactorModel.model_validate({
            "factor_id": orm_obj.factor_id,
            "factor_name": orm_obj.factor_name,
            "factor_category": orm_obj.factor_category or "unknown",
            "code": orm_obj.code,
            "trade_date": orm_obj.trade_date,
            "factor_value": float(orm_obj.factor_value) if orm_obj.factor_value else None,
            "factor_rank": orm_obj.factor_rank,
            "factor_percentile": float(orm_obj.factor_percentile) if orm_obj.factor_percentile else None,
            "neutralized": orm_obj.neutralized,
            "collected_at": orm_obj.collected_at,
            "quality": "unknown",
            "source": "database",
        })


class ADSRepository(ABC, Generic[T]):
    """
    Legacy base repository for ADS data.
    
    Deprecated: Use GenericADSRepository instead.
    Kept for backward compatibility.
    """
    
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None
    
    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = async_session_maker()
        return self._session
    
    async def close(self) -> None:
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None
