"""
Relative Strength Factor for Strong Stock Detection.

Calculates relative strength compared to benchmark or market average.
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


def calculate_relative_strength(
    klines: list[ADSKLineModel],
    period: int = 20,
) -> float | None:
    """
    Calculate relative strength.
    
    Uses price performance relative to a baseline.
    RS = Stock Return / Average Market Return
    
    For simplicity, we calculate the strength of the trend
    using linear regression slope normalized by price.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: Lookback period
    
    Returns:
        Relative strength value or None
    """
    if len(klines) < period:
        return None
    
    closes = np.array([k.close for k in klines[-period:]])
    
    if len(closes) < 2:
        return None
    
    x = np.arange(len(closes))
    
    try:
        slope, _ = np.polyfit(x, closes, 1)
        
        avg_price = np.mean(closes)
        if avg_price <= 0:
            return None
        
        normalized_slope = (slope / avg_price) * 100
        
        r_squared = np.corrcoef(x, closes)[0, 1] ** 2
        
        strength = normalized_slope * r_squared
        
        return float(strength)
    except Exception:
        return None


@register_factor(is_builtin=True)
class RelativeStrengthFactor(FactorBase):
    """
    Relative Strength Factor.
    
    Measures the strength of price trend using linear regression.
    Higher values indicate stronger upward trend.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_relative_strength",
            name="Relative Strength",
            description="Trend strength using linear regression slope",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["relative_strength", "trend", "regression"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """Calculate relative strength value."""
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_relative_strength(klines, period=period)
