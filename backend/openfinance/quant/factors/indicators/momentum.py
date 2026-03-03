"""
Momentum Factor for Strong Stock Detection.

Calculates price momentum over multiple timeframes.
"""

from typing import Any
import numpy as np

from openfinance.datacenter.models.analytical import ADSKLineModel
from ..base import (
    FactorBase,
    FactorMetadata,
    FactorType,
    FactorCategory,
)
from ..registry import register_factor


def calculate_momentum(klines: list[ADSKLineModel], period: int = 20) -> float | None:
    """
    Calculate price momentum.
    
    Momentum = (Current Price - Price N days ago) / Price N days ago * 100
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: Lookback period
    
    Returns:
        Momentum percentage or None
    """
    if len(klines) < period + 1:
        return None
    
    closes = np.array([k.close for k in klines])
    current_price = closes[-1]
    past_price = closes[-period - 1]
    
    if past_price <= 0:
        return None
    
    momentum = (current_price - past_price) / past_price * 100
    return float(momentum)


@register_factor(is_builtin=True)
class MomentumFactor(FactorBase):
    """
    Momentum Factor.
    
    Measures the rate of price change over a specific period.
    Higher momentum indicates stronger upward trend.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_momentum",
            name="Price Momentum",
            description="Price momentum over specified period",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["momentum", "trend", "strength"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """Calculate momentum value."""
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_momentum(klines, period=period)
