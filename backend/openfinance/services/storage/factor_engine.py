"""
Factor Engine - Metadata-driven factor management.

Provides operations for storing and retrieving factor data.
Fully compatible with FactorDataModel in orm.py.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.domain.metadata.registry import FactorTypeRegistry, FactorTypeDefinition
from .repository import FactorRepository
from openfinance.domain.schemas.generic_model import GenericFactorModel

logger = logging.getLogger(__name__)


class FactorEngine:
    """Factor Engine - Metadata-driven factor data management.
    
    Fully compatible with FactorDataModel in orm.py.
    Uses original field names: factor_id, factor_name, factor_category, code, etc.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        registry: FactorTypeRegistry | None = None,
    ):
        self.session = session
        self.registry = registry or FactorTypeRegistry()
        self.repository = FactorRepository(session)
    
    async def save(
        self,
        factor_id: str,
        code: str,
        trade_date: date,
        factor_value: float,
        factor_name: str | None = None,
        factor_category: str | None = None,
        factor_rank: int | None = None,
        factor_percentile: float | None = None,
        neutralized: bool = False,
        attributes: dict[str, Any] | None = None,
    ) -> GenericFactorModel:
        """Save factor data.
        
        Args:
            factor_id: Factor identifier
            code: Stock code
            trade_date: Trade date
            factor_value: Factor value
            factor_name: Factor name
            factor_category: Factor category
            factor_rank: Rank among all stocks
            factor_percentile: Percentile rank
            neutralized: Whether neutralized
            attributes: Additional attributes
        """
        return await self.repository.save_factor_data(
            factor_id=factor_id,
            code=code,
            trade_date=trade_date,
            factor_value=factor_value,
            factor_name=factor_name,
            factor_category=factor_category,
            factor_rank=factor_rank,
            factor_percentile=factor_percentile,
            neutralized=neutralized,
            attributes=attributes,
        )
    
    async def save_with_alias(
        self,
        factor_type: str,
        symbol: str,
        trade_date: date,
        value: float,
        factor_name: str | None = None,
        factor_rank: int | None = None,
        factor_percentile: float | None = None,
        neutralized: bool = False,
        parameters: dict[str, Any] | None = None,
    ) -> GenericFactorModel:
        """Save factor data using alias field names.
        
        Alias compatibility method for legacy code.
        - factor_type -> factor_category
        - symbol -> code
        - value -> factor_value
        """
        factor_id = f"{factor_type}_{symbol}_{trade_date.strftime('%Y%m%d')}"
        
        return await self.repository.save_factor_data(
            factor_id=factor_id,
            code=symbol,
            trade_date=trade_date,
            factor_value=value,
            factor_name=factor_name,
            factor_category=factor_type,
            factor_rank=factor_rank,
            factor_percentile=factor_percentile,
            neutralized=neutralized,
            attributes=parameters or {},
        )
    
    async def get_data(
        self,
        factor_id: str | None = None,
        factor_category: str | None = None,
        code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 1000,
    ) -> list[GenericFactorModel]:
        """Get factor data.
        
        Args:
            factor_id: Filter by factor ID
            factor_category: Filter by factor category
            code: Filter by stock code
            start_date: Start date
            end_date: End date
            limit: Maximum number of records
        """
        return await self.repository.get_factor_data(
            factor_id=factor_id,
            factor_category=factor_category,
            code=code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    
    async def get_latest(
        self,
        factor_id: str,
        code: str,
    ) -> GenericFactorModel | None:
        """Get latest factor value for a stock."""
        return await self.repository.get_latest_factor_value(
            factor_id=factor_id,
            code=code,
        )
    
    async def batch_save(
        self,
        factor_data_list: list[dict[str, Any]],
    ) -> int:
        """Batch save factor data."""
        return await self.repository.batch_save_factor_data(factor_data_list)
    
    async def delete(
        self,
        factor_id: str,
        code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """Delete factor data."""
        return await self.repository.delete_factor_data(
            factor_id=factor_id,
            code=code,
            start_date=start_date,
            end_date=end_date,
        )
    
    def get_type_definition(self, factor_type: str) -> FactorTypeDefinition | None:
        """Get factor type definition."""
        return self.registry.get(factor_type)
    
    def list_types(self) -> list[FactorTypeDefinition]:
        """List all factor types."""
        return self.registry.list_all()
    
    def list_by_category(self, category: str) -> list[FactorTypeDefinition]:
        """List factor types by category."""
        return self.registry.list_by_category(category)
