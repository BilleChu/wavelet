"""
Trend Strength Factor for Strong Stock Detection.

Combines price and volume to measure trend strength.
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


def calculate_trend_strength(
    klines: list[ADSKLineModel],
    period: int = 20,
) -> float | None:
    """
    Calculate trend strength.
    
    Combines price trend consistency and volume confirmation.
    Uses directional movement concepts.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: Lookback period
    
    Returns:
        Trend strength value (0-100) or None
    """
    if len(klines) < period:
        return None
    
    recent_klines = klines[-period:]
    
    highs = np.array([k.high for k in recent_klines])
    lows = np.array([k.low for k in recent_klines])
    closes = np.array([k.close for k in recent_klines])
    volumes = np.array([k.volume for k in recent_klines])
    
    if len(closes) < 2:
        return None
    
    up_moves = np.diff(highs)
    down_moves = -np.diff(lows)
    
    plus_dm = np.where((up_moves > down_moves) & (up_moves > 0), up_moves, 0)
    minus_dm = np.where((down_moves > up_moves) & (down_moves > 0), down_moves, 0)
    
    true_ranges = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )
    
    atr = np.mean(true_ranges[-min(14, len(true_ranges)):])
    
    if atr <= 0:
        return None
    
    plus_di = 100 * np.sum(plus_dm[-min(14, len(plus_dm)):]) / (atr * min(14, len(plus_dm)))
    minus_di = 100 * np.sum(minus_dm[-min(14, len(minus_dm)):]) / (atr * min(14, len(minus_dm)))
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
    
    trend_direction = 1.0 if plus_di > minus_di else -1.0
    
    price_trend = 0.0
    if closes[-1] > closes[0]:
        price_trend = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0
    else:
        price_trend = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0
    
    avg_volume = np.mean(volumes)
    recent_volume = np.mean(volumes[-5:])
    volume_trend = recent_volume / avg_volume if avg_volume > 0 else 1.0
    
    directional_strength = dx * trend_direction * 0.4
    
    price_strength = price_trend * 0.4
    
    volume_factor = 0.0
    if trend_direction > 0:
        volume_factor = (volume_trend - 1.0) * 20
    else:
        volume_factor = -(volume_trend - 1.0) * 20
    
    trend_strength = directional_strength + price_strength + volume_factor
    
    return float(trend_strength)


@register_factor(is_builtin=True)
class TrendStrengthFactor(FactorBase):
    """
    Trend Strength Factor.
    
    Measures the strength of price trend using directional movement.
    Higher values indicate stronger and more sustainable trends.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_trend_strength",
            name="Trend Strength",
            description="Trend strength using directional movement index",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.TECH_TREND,
            version="1.0.0",
            author="system",
            tags=["trend", "strength", "directional_movement"],
            required_fields=["high", "low", "close", "volume"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """Calculate trend strength value."""
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_trend_strength(klines, period=period)
