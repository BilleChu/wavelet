"""
Volume Strength Factor for Strong Stock Detection.

Analyzes volume patterns to identify strong stocks.
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


def calculate_volume_strength(
    klines: list[ADSKLineModel],
    period: int = 20,
) -> float | None:
    """
    Calculate volume strength.
    
    Compares recent volume to historical average.
    Higher volume on up days indicates accumulation.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: Lookback period
    
    Returns:
        Volume strength value or None
    """
    if len(klines) < period:
        return None
    
    recent_klines = klines[-period:]
    
    volumes = np.array([k.volume for k in recent_klines])
    closes = np.array([k.close for k in recent_klines])
    
    if len(volumes) < 2:
        return None
    
    avg_volume = np.mean(volumes)
    if avg_volume <= 0:
        return None
    
    price_changes = np.diff(closes)
    
    up_days = price_changes > 0
    down_days = price_changes < 0
    
    if len(volumes) > 1:
        up_volumes = volumes[1:][up_days]
        down_volumes = volumes[1:][down_days]
        
        avg_up_volume = np.mean(up_volumes) if len(up_volumes) > 0 else 0
        avg_down_volume = np.mean(down_volumes) if len(down_volumes) > 0 else 0
        
        if avg_down_volume > 0:
            volume_ratio = avg_up_volume / avg_down_volume
        else:
            volume_ratio = 2.0 if avg_up_volume > 0 else 1.0
        
        recent_avg = np.mean(volumes[-5:])
        volume_trend = recent_avg / avg_volume if avg_volume > 0 else 1.0
        
        up_days_count = np.sum(up_days)
        down_days_count = np.sum(down_days)
        trend_direction = 1.0 if up_days_count > down_days_count else -1.0
        
        accumulation_score = 0.0
        if trend_direction > 0:
            if volume_ratio > 1.0:
                accumulation_score = (volume_ratio - 1.0) * 50
            else:
                accumulation_score = (volume_ratio - 1.0) * 25
        else:
            if volume_ratio < 1.0:
                accumulation_score = (volume_ratio - 1.0) * 50
            else:
                accumulation_score = -(volume_ratio - 1.0) * 25
        
        volume_activity = (volume_trend - 1.0) * 20 * trend_direction
        
        strength = accumulation_score + volume_activity
        
        return float(strength)
    
    return None


@register_factor(is_builtin=True)
class VolumeStrengthFactor(FactorBase):
    """
    Volume Strength Factor.
    
    Analyzes volume patterns to identify accumulation.
    Higher values indicate stronger buying pressure.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_volume_strength",
            name="Volume Strength",
            description="Volume analysis for accumulation detection",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.FLOW,
            version="1.0.0",
            author="system",
            tags=["volume", "accumulation", "strength"],
            required_fields=["close", "volume"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """Calculate volume strength value."""
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_volume_strength(klines, period=period)
