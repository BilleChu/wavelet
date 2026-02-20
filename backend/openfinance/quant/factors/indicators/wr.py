"""
Williams %R (W%R) Factor.

Williams %R is a momentum indicator measuring overbought/oversold levels.
%R = (Highest High - Close) / (Highest High - Lowest Low) * (-100)

Calculations use K-Line high, low, and close prices.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from openfinance.datacenter.ads import ADSKLineModel
from ..base import (
    FactorBase,
    FactorMetadata,
    FactorResult,
    FactorConfig,
    FactorType,
    FactorCategory,
)
from ..registry import register_factor


def calculate_wr(
    klines: list[ADSKLineModel],
    period: int = 14,
) -> float | None:
    """
    Calculate Williams %R from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: Lookback period
    
    Returns:
        Williams %R value or None
    """
    if len(klines) < period:
        return None
    
    window = klines[-period:]
    highest_high = max(k.high for k in window)
    lowest_low = min(k.low for k in window)
    close = klines[-1].close
    
    if highest_high == lowest_low:
        return -50.0
    
    wr = (highest_high - close) / (highest_high - lowest_low) * (-100)
    
    return float(wr)


def wr(
    high: np.ndarray | list,
    low: np.ndarray | list,
    close: np.ndarray | list,
    period: int = 14,
) -> np.ndarray:
    """
    Calculate Williams %R values for arrays.
    
    Args:
        high: High price array
        low: Low price array
        close: Close price array
        period: Lookback period (default 14)
    
    Returns:
        Williams %R values array
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    
    result = np.full_like(close, np.nan, dtype=float)
    
    if len(close) < period:
        return result
    
    for i in range(period - 1, len(close)):
        highest_high = np.max(high[i - period + 1:i + 1])
        lowest_low = np.min(low[i - period + 1:i + 1])
        
        if highest_high == lowest_low:
            result[i] = -50.0
        else:
            result[i] = (highest_high - close[i]) / (highest_high - lowest_low) * (-100)
    
    return result


@dataclass
class WRValues:
    """Williams %R values container."""
    wr: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return self.wr is not None
    
    @property
    def is_overbought(self) -> bool:
        """Check if overbought (%R > -20)."""
        return self.wr is not None and self.wr > -20
    
    @property
    def is_oversold(self) -> bool:
        """Check if oversold (%R < -80)."""
        return self.wr is not None and self.wr < -80


@register_factor(is_builtin=True)
class WRFactor(FactorBase):
    """
    Williams %R Factor.
    
    Williams %R is a momentum indicator:
    - %R > -20: Overbought zone
    - %R < -80: Oversold zone
    - Range: 0 to -100
    
    Calculation uses K-Line high, low, and close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_wr",
            name="Williams %R",
            description="Momentum indicator measuring overbought and oversold levels",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["momentum", "oscillator", "overbought_oversold"],
            required_fields=["high", "low", "close"],
            lookback_period=14,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate Williams %R value.
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            Williams %R value or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_wr(klines, period=period)
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> WRValues | None:
        """
        Calculate full Williams %R values.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            WRValues or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        
        wr_value = calculate_wr(klines, period=period)
        
        if wr_value is None:
            return None
        
        return WRValues(wr=wr_value)
    
    def generate_signal(self, wr_value: float) -> float:
        """
        Generate trading signal from Williams %R.
        
        Args:
            wr_value: Williams %R value
        
        Returns:
            Signal value (-1 to 1)
        """
        if wr_value > -20:
            return -1.0
        elif wr_value < -80:
            return 1.0
        elif wr_value > -50:
            return -(wr_value + 50) / 30
        else:
            return -(wr_value + 50) / 30
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate Williams %R with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        wr_values = self.calculate_full(klines, **kwargs)
        
        if wr_values is None or not wr_values.is_valid:
            return None
        
        latest = klines[-1]
        signal = self.generate_signal(wr_values.wr)
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=wr_values.wr,
            signal=signal,
            confidence=abs(signal),
            metadata={
                "wr": wr_values.wr,
                "overbought": wr_values.is_overbought,
                "oversold": wr_values.is_oversold,
            },
        )
