"""
Strategy Module for Quantitative Analysis.

Provides strategy development and optimization capabilities.
"""

from openfinance.quant.strategy.engine import StrategyEngine
from openfinance.quant.strategy.builder import StrategyBuilder
from openfinance.quant.strategy.optimizer import StrategyOptimizer

from .base import (
    BaseStrategy,
    StrategyMetadata,
    StrategyConfig,
    StrategySignal,
    StrategyResult,
    StrategyType,
    SignalType,
    WeightMethod,
    RebalanceFrequency,
)
from .registry import (
    StrategyRegistry,
    StrategyInfo,
    get_strategy_registry,
    register_strategy,
)
from .implementations import (
    RSIKDJMomentumStrategy,
    FlexibleMultiFactorStrategy,
)

import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_custom_strategies_loaded = False

def load_custom_strategies():
    """Load all custom strategies from the custom directory."""
    global _custom_strategies_loaded
    
    if _custom_strategies_loaded:
        return
    
    custom_dir = Path(__file__).parent / "custom"
    if not custom_dir.exists():
        custom_dir.mkdir(parents=True, exist_ok=True)
        _custom_strategies_loaded = True
        return
    
    for strategy_file in custom_dir.glob("*.py"):
        if strategy_file.name.startswith("_"):
            continue
        
        module_name = strategy_file.stem
        try:
            full_module_name = f"openfinance.quant.strategy.custom.{module_name}"
            importlib.import_module(full_module_name)
            logger.info(f"Loaded custom strategy: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to load custom strategy {module_name}: {e}")
    
    _custom_strategies_loaded = True

load_custom_strategies()

__all__ = [
    "StrategyEngine",
    "StrategyBuilder",
    "StrategyOptimizer",
    "StrategyBase",
    "StrategyMetadata",
    "StrategyConfig",
    "StrategySignal",
    "StrategyResult",
    "StrategyType",
    "SignalType",
    "WeightMethod",
    "RebalanceFrequency",
    "StrategyRegistry",
    "StrategyInfo",
    "get_strategy_registry",
    "register_strategy",
    "RSIKDJMomentumStrategy",
    "FlexibleMultiFactorStrategy",
    "load_custom_strategies",
]
