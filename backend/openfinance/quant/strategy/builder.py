"""
Strategy Builder for Quantitative Analysis.

Provides tools for constructing trading strategies.
"""

import logging
from datetime import datetime
from typing import Any

from openfinance.domain.models.quant import (
    Strategy,
    StrategyType,
    WeightMethod,
    FactorStatus,
)

logger = logging.getLogger(__name__)


class StrategyBuilder:
    """Builder for constructing trading strategies.

    Provides fluent interface for strategy creation.
    """

    def __init__(self) -> None:
        self._name: str = ""
        self._code: str = ""
        self._description: str = ""
        self._strategy_type: StrategyType = StrategyType.SINGLE_FACTOR
        self._factors: list[str] = []
        self._factor_weights: dict[str, float] = {}
        self._weight_method: WeightMethod = WeightMethod.EQUAL
        self._parameters: dict[str, Any] = {}
        self._rebalance_freq: str = "monthly"
        self._max_positions: int = 50
        self._position_size: float = 0.02
        self._stop_loss: float | None = None
        self._take_profit: float | None = None
        self._created_by: str | None = None

    def name(self, name: str) -> "StrategyBuilder":
        """Set strategy name."""
        self._name = name
        return self

    def code(self, code: str) -> "StrategyBuilder":
        """Set strategy code."""
        self._code = code
        return self

    def description(self, description: str) -> "StrategyBuilder":
        """Set strategy description."""
        self._description = description
        return self

    def type(self, strategy_type: StrategyType) -> "StrategyBuilder":
        """Set strategy type."""
        self._strategy_type = strategy_type
        return self

    def add_factor(
        self,
        factor_id: str,
        weight: float = 1.0,
    ) -> "StrategyBuilder":
        """Add a factor to the strategy."""
        self._factors.append(factor_id)
        self._factor_weights[factor_id] = weight
        return self

    def factors(
        self,
        factors: list[str],
        weights: dict[str, float] | None = None,
    ) -> "StrategyBuilder":
        """Set all factors at once."""
        self._factors = factors
        if weights:
            self._factor_weights = weights
        else:
            self._factor_weights = {f: 1.0 / len(factors) for f in factors}
        return self

    def factor_weights(self, weights: dict[str, float]) -> "StrategyBuilder":
        """Set factor weights."""
        self._factor_weights = weights
        return self

    def weight_method(self, method: WeightMethod) -> "StrategyBuilder":
        """Set portfolio weight method."""
        self._weight_method = method
        return self

    def parameters(self, params: dict[str, Any]) -> "StrategyBuilder":
        """Set strategy parameters."""
        self._parameters = params
        return self

    def rebalance_frequency(self, freq: str) -> "StrategyBuilder":
        """Set rebalance frequency (daily/weekly/monthly/quarterly)."""
        self._rebalance_freq = freq
        return self

    def max_positions(self, n: int) -> "StrategyBuilder":
        """Set maximum number of positions."""
        self._max_positions = n
        return self

    def position_size(self, size: float) -> "StrategyBuilder":
        """Set default position size (as fraction of portfolio)."""
        self._position_size = size
        return self

    def stop_loss(self, pct: float) -> "StrategyBuilder":
        """Set stop loss percentage."""
        self._stop_loss = pct
        return self

    def take_profit(self, pct: float) -> "StrategyBuilder":
        """Set take profit percentage."""
        self._take_profit = pct
        return self

    def created_by(self, user_id: str) -> "StrategyBuilder":
        """Set creator ID."""
        self._created_by = user_id
        return self

    def build(self) -> Strategy:
        """Build the strategy."""
        if not self._name:
            raise ValueError("Strategy name is required")
        if not self._code:
            raise ValueError("Strategy code is required")
        if not self._factors:
            raise ValueError("At least one factor is required")

        if self._strategy_type == StrategyType.SINGLE_FACTOR and len(self._factors) > 1:
            self._strategy_type = StrategyType.MULTI_FACTOR

        return Strategy(
            name=self._name,
            code=self._code,
            description=self._description,
            strategy_type=self._strategy_type,
            factors=self._factors,
            factor_weights=self._factor_weights,
            weight_method=self._weight_method,
            parameters=self._parameters,
            rebalance_freq=self._rebalance_freq,
            max_positions=self._max_positions,
            position_size=self._position_size,
            stop_loss=self._stop_loss,
            take_profit=self._take_profit,
            status=FactorStatus.DRAFT,
            created_by=self._created_by,
        )

    def reset(self) -> "StrategyBuilder":
        """Reset builder to initial state."""
        self._name = ""
        self._code = ""
        self._description = ""
        self._strategy_type = StrategyType.SINGLE_FACTOR
        self._factors = []
        self._factor_weights = {}
        self._weight_method = WeightMethod.EQUAL
        self._parameters = {}
        self._rebalance_freq = "monthly"
        self._max_positions = 50
        self._position_size = 0.02
        self._stop_loss = None
        self._take_profit = None
        self._created_by = None
        return self


def create_momentum_strategy(
    lookback: int = 20,
    max_positions: int = 30,
) -> Strategy:
    """Create a momentum strategy."""
    return (
        StrategyBuilder()
        .name("Momentum Strategy")
        .code("momentum_default")
        .description("Price momentum based strategy")
        .type(StrategyType.SINGLE_FACTOR)
        .add_factor("factor_momentum")
        .weight_method(WeightMethod.EQUAL)
        .rebalance_frequency("monthly")
        .max_positions(max_positions)
        .parameters({"lookback": lookback})
        .build()
    )


def create_value_strategy(
    max_positions: int = 30,
) -> Strategy:
    """Create a value strategy."""
    return (
        StrategyBuilder()
        .name("Value Strategy")
        .code("value_default")
        .description("Value investing strategy based on P/E and P/B")
        .type(StrategyType.MULTI_FACTOR)
        .factors(["factor_pe", "factor_pb"])
        .weight_method(WeightMethod.EQUAL)
        .rebalance_frequency("quarterly")
        .max_positions(max_positions)
        .build()
    )


def create_quality_strategy(
    max_positions: int = 30,
) -> Strategy:
    """Create a quality strategy."""
    return (
        StrategyBuilder()
        .name("Quality Strategy")
        .code("quality_default")
        .description("Quality investing based on ROE and margins")
        .type(StrategyType.MULTI_FACTOR)
        .factors(["factor_roe", "factor_gross_margin", "factor_net_margin"])
        .weight_method(WeightMethod.EQUAL)
        .rebalance_frequency("quarterly")
        .max_positions(max_positions)
        .build()
    )


def create_multi_factor_strategy(
    max_positions: int = 50,
) -> Strategy:
    """Create a comprehensive multi-factor strategy."""
    return (
        StrategyBuilder()
        .name("Multi-Factor Strategy")
        .code("multifactor_default")
        .description("Combined momentum, value, and quality strategy")
        .type(StrategyType.MULTI_FACTOR)
        .factors([
            "factor_momentum",
            "factor_pe",
            "factor_roe",
            "factor_volatility",
        ])
        .factor_weights({
            "factor_momentum": 0.3,
            "factor_pe": 0.25,
            "factor_roe": 0.25,
            "factor_volatility": 0.2,
        })
        .weight_method(WeightMethod.RISK_PARITY)
        .rebalance_frequency("monthly")
        .max_positions(max_positions)
        .stop_loss(0.15)
        .build()
    )
