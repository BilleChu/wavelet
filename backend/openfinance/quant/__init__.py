"""
Quantitative Analysis Module for OpenFinance.

Provides factor management, strategy development, backtesting,
and custom factor development capabilities.
"""

from openfinance.quant.factors import (
    FactorBase,
    FactorEngine,
    get_factor_engine,
    get_factor_registry,
)
from openfinance.quant.strategy.engine import StrategyEngine
from openfinance.quant.backtest.engine import BacktestEngine
from openfinance.quant.backtest.metrics import BacktestCalculator

__all__ = [
    "FactorBase",
    "FactorEngine",
    "get_factor_engine",
    "get_factor_registry",
    "StrategyEngine",
    "BacktestEngine",
    "BacktestCalculator",
]
