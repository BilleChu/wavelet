"""
Strategy Engine for Quantitative Analysis.

Provides strategy construction, signal generation, and portfolio management.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from openfinance.domain.models.quant import (
    Strategy,
    StrategyType,
    WeightMethod,
    FactorValue,
    FactorStatus,
)

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Strategy engine for quantitative trading.

    Provides:
    - Single factor strategy construction
    - Multi-factor strategy construction
    - Signal generation
    - Portfolio weight calculation
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._register_builtin_strategies()
    
    def _register_builtin_strategies(self) -> None:
        """Register built-in strategies."""
        momentum_strategy = Strategy(
            strategy_id="strategy_momentum_rsi",
            name="动量RSI策略",
            code="momentum_rsi",
            description="基于RSI指标的动量策略，买入超卖股票，卖出超买股票",
            strategy_type=StrategyType.SINGLE_FACTOR,
            factors=["factor_rsi"],
            factor_weights={"factor_rsi": 1.0},
            weight_method=WeightMethod.EQUAL,
            max_positions=30,
            rebalance_freq="weekly",
            parameters={
                "rsi_period": 14,
                "oversold_threshold": 30,
                "overbought_threshold": 70,
            },
            status=FactorStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._strategies[momentum_strategy.strategy_id] = momentum_strategy
        
        multi_factor_strategy = Strategy(
            strategy_id="strategy_multi_factor_tech",
            name="多因子技术策略",
            code="multi_factor_tech",
            description="综合RSI、MACD、ATR多因子的技术分析策略",
            strategy_type=StrategyType.MULTI_FACTOR,
            factors=["factor_rsi", "factor_macd", "factor_atr"],
            factor_weights={
                "factor_rsi": 0.4,
                "factor_macd": 0.4,
                "factor_atr": 0.2,
            },
            weight_method=WeightMethod.EQUAL,
            max_positions=50,
            rebalance_freq="monthly",
            parameters={
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "atr_period": 14,
            },
            status=FactorStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._strategies[multi_factor_strategy.strategy_id] = multi_factor_strategy
        
        logger.info(f"Registered {len(self._strategies)} built-in strategies")

    def register_strategy(self, strategy: Strategy) -> None:
        """Register a strategy."""
        self._strategies[strategy.strategy_id] = strategy

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Get a registered strategy."""
        return self._strategies.get(strategy_id)

    def generate_signals(
        self,
        strategy: Strategy,
        factor_values: dict[str, list[FactorValue]],
        date: datetime | None = None,
    ) -> dict[str, float]:
        """Generate trading signals for stocks.

        Args:
            strategy: Strategy definition.
            factor_values: Factor values by factor ID.
            date: Target date (uses latest if None).

        Returns:
            Dictionary of stock_code -> signal value.
        """
        if strategy.strategy_type == StrategyType.SINGLE_FACTOR:
            return self._generate_single_factor_signals(
                strategy,
                factor_values,
                date,
            )
        elif strategy.strategy_type == StrategyType.MULTI_FACTOR:
            return self._generate_multi_factor_signals(
                strategy,
                factor_values,
                date,
            )
        else:
            return self._generate_combo_signals(strategy, factor_values, date)

    def _generate_single_factor_signals(
        self,
        strategy: Strategy,
        factor_values: dict[str, list[FactorValue]],
        date: datetime | None,
    ) -> dict[str, float]:
        """Generate signals for single factor strategy."""
        if not strategy.factors:
            return {}

        factor_id = strategy.factors[0]
        values = factor_values.get(factor_id, [])

        if date:
            if hasattr(date, 'date'):
                values = [v for v in values if v.trade_date.date() == date.date()]
            else:
                from datetime import datetime as dt
                values = [v for v in values if v.trade_date.date() == date]

        signals = {}
        for v in values:
            if v.zscore is not None:
                signals[v.stock_code] = v.zscore
            elif v.value is not None:
                signals[v.stock_code] = v.value

        return signals

    def _generate_multi_factor_signals(
        self,
        strategy: Strategy,
        factor_values: dict[str, list[FactorValue]],
        date: datetime | None,
    ) -> dict[str, float]:
        """Generate signals for multi-factor strategy."""
        if not strategy.factors:
            return {}

        weights = strategy.factor_weights
        if not weights:
            weights = {f: 1.0 / len(strategy.factors) for f in strategy.factors}

        combined_signals: dict[str, float] = {}
        factor_counts: dict[str, int] = {}

        for factor_id in strategy.factors:
            values = factor_values.get(factor_id, [])
            if date:
                if hasattr(date, 'date'):
                    values = [v for v in values if v.trade_date.date() == date.date()]
                else:
                    values = [v for v in values if v.trade_date.date() == date]

            factor_weight = weights.get(factor_id, 0.0)

            for v in values:
                signal = v.zscore if v.zscore is not None else v.value
                if signal is not None:
                    if v.stock_code not in combined_signals:
                        combined_signals[v.stock_code] = 0.0
                        factor_counts[v.stock_code] = 0

                    combined_signals[v.stock_code] += signal * factor_weight
                    factor_counts[v.stock_code] += 1

        return combined_signals

    def _generate_combo_signals(
        self,
        strategy: Strategy,
        factor_values: dict[str, list[FactorValue]],
        date: datetime | None,
    ) -> dict[str, float]:
        """Generate signals for combo strategy."""
        return self._generate_multi_factor_signals(strategy, factor_values, date)

    def calculate_weights(
        self,
        strategy: Strategy,
        signals: dict[str, float],
        market_data: pd.DataFrame | None = None,
    ) -> dict[str, float]:
        """Calculate portfolio weights based on signals.

        Args:
            strategy: Strategy definition.
            signals: Trading signals by stock.
            market_data: Optional market data for market-cap weighting.

        Returns:
            Dictionary of stock_code -> weight.
        """
        if not signals:
            return {}

        if strategy.weight_method == WeightMethod.EQUAL:
            return self._equal_weights(signals, strategy.max_positions)
        elif strategy.weight_method == WeightMethod.MARKET_CAP:
            return self._market_cap_weights(
                signals,
                market_data,
                strategy.max_positions,
            )
        elif strategy.weight_method == WeightMethod.RISK_PARITY:
            return self._risk_parity_weights(signals, strategy.max_positions)
        else:
            return self._equal_weights(signals, strategy.max_positions)

    def _equal_weights(
        self,
        signals: dict[str, float],
        max_positions: int,
    ) -> dict[str, float]:
        """Calculate equal weights."""
        sorted_stocks = sorted(
            signals.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:max_positions]

        if not sorted_stocks:
            return {}

        weight = 1.0 / len(sorted_stocks)
        return {stock: weight for stock, _ in sorted_stocks}

    def _market_cap_weights(
        self,
        signals: dict[str, float],
        market_data: pd.DataFrame | None,
        max_positions: int,
    ) -> dict[str, float]:
        """Calculate market-cap weighted weights."""
        sorted_stocks = sorted(
            signals.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:max_positions]

        if not sorted_stocks or market_data is None:
            return self._equal_weights(signals, max_positions)

        market_caps = {}
        for stock, _ in sorted_stocks:
            stock_data = market_data[market_data["stock_code"] == stock]
            if not stock_data.empty and "market_cap" in stock_data.columns:
                market_caps[stock] = stock_data["market_cap"].iloc[-1]

        if not market_caps:
            return self._equal_weights(signals, max_positions)

        total_cap = sum(market_caps.values())
        return {stock: cap / total_cap for stock, cap in market_caps.items()}

    def _risk_parity_weights(
        self,
        signals: dict[str, float],
        max_positions: int,
    ) -> dict[str, float]:
        """Calculate risk parity weights.

        Simple implementation using inverse volatility.
        """
        sorted_stocks = sorted(
            signals.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:max_positions]

        if not sorted_stocks:
            return {}

        inv_volatility = {stock: 1.0 / (abs(signal) + 0.01) for stock, signal in sorted_stocks}
        total_inv_vol = sum(inv_volatility.values())

        return {stock: vol / total_inv_vol for stock, vol in inv_volatility.items()}

    def select_stocks(
        self,
        signals: dict[str, float],
        weights: dict[str, float],
        top_n: int = 50,
    ) -> list[tuple[str, float, float]]:
        """Select top stocks based on signals and weights.

        Returns:
            List of (stock_code, signal, weight) tuples.
        """
        selected = []
        for stock, weight in weights.items():
            signal = signals.get(stock, 0.0)
            selected.append((stock, signal, weight))

        selected.sort(key=lambda x: x[1], reverse=True)
        return selected[:top_n]

    def get_strategy_count(self) -> int:
        """Get number of registered strategies."""
        return len(self._strategies)

    def list_strategies(self) -> list[Strategy]:
        """List all registered strategies."""
        return list(self._strategies.values())
