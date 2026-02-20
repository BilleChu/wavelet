"""
Strategy Engine - Metadata-driven strategy management.

Provides operations for managing strategy configurations.
Fully compatible with Strategy Pydantic model in models/quant.py.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.domain.metadata.registry import StrategyTypeRegistry, StrategyTypeDefinition
from .repository import StrategyRepository
from openfinance.domain.schemas.generic_model import GenericStrategyModel

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Strategy Engine - Metadata-driven strategy configuration management.
    
    Fully compatible with Strategy Pydantic model in models/quant.py.
    All original fields preserved.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        registry: StrategyTypeRegistry | None = None,
    ):
        self.session = session
        self.registry = registry or StrategyTypeRegistry()
        self.repository = StrategyRepository(session)
    
    async def create(
        self,
        name: str,
        code: str,
        strategy_type: str,
        description: str | None = None,
        factors: list[str] | None = None,
        factor_weights: dict[str, float] | None = None,
        weight_method: str = "equal",
        parameters: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        rebalance_freq: str = "monthly",
        max_positions: int = 50,
        position_size: float = 0.02,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        status: str = "draft",
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GenericStrategyModel:
        """Create a new strategy configuration.
        
        Args:
            name: Strategy name
            code: Strategy code (unique identifier)
            strategy_type: Strategy type
            description: Strategy description
            factors: List of factor IDs
            factor_weights: Factor weights
            weight_method: Weight method (equal, market_cap, risk_parity, etc.)
            parameters: Strategy parameters
            config: Strategy configuration
            rebalance_freq: Rebalance frequency
            max_positions: Maximum positions
            position_size: Default position size
            stop_loss: Stop loss percentage
            take_profit: Take profit percentage
            status: Strategy status
            created_by: Creator ID
            metadata: Additional metadata
        """
        return await self.repository.create_strategy(
            name=name,
            code=code,
            strategy_type=strategy_type,
            description=description,
            factors=factors,
            factor_weights=factor_weights,
            weight_method=weight_method,
            parameters=parameters,
            config=config,
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=status,
            created_by=created_by,
            metadata=metadata,
        )
    
    async def get(self, strategy_id: str) -> GenericStrategyModel | None:
        """Get strategy by ID."""
        return await self.repository.get_by_strategy_id(strategy_id)
    
    async def get_by_code(self, code: str) -> GenericStrategyModel | None:
        """Get strategy by code."""
        return await self.repository.get_by_code(code)
    
    async def list(
        self,
        strategy_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenericStrategyModel]:
        """List strategies with filters."""
        return await self.repository.list_strategies(
            strategy_type=strategy_type,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
    
    async def list_by_type(
        self,
        strategy_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[GenericStrategyModel]:
        """List strategies by type."""
        return await self.repository.list_by_type(
            strategy_type=strategy_type,
            status=status,
            limit=limit,
        )
    
    async def update(
        self,
        strategy_id: str,
        **kwargs,
    ) -> GenericStrategyModel | None:
        """Update strategy."""
        return await self.repository.update_strategy(strategy_id, **kwargs)
    
    async def update_status(
        self,
        strategy_id: str,
        status: str,
    ) -> GenericStrategyModel | None:
        """Update strategy status."""
        return await self.repository.update_status(strategy_id, status)
    
    async def delete(self, strategy_id: str) -> bool:
        """Delete strategy."""
        return await self.repository.delete_strategy(strategy_id)
    
    def get_type_definition(self, strategy_type: str) -> StrategyTypeDefinition | None:
        """Get strategy type definition."""
        return self.registry.get(strategy_type)
    
    def list_types(self) -> list[StrategyTypeDefinition]:
        """List all strategy types."""
        return self.registry.list_all()
