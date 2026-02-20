"""
RSI (Relative Strength Index) Factor.

RSI measures the speed and magnitude of recent price changes.
RSI = 100 - 100 / (1 + RS)
RS = Average Gain / Average Loss

All calculations are based on K-Line close prices only.
"""

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


def calculate_rsi(klines: list[ADSKLineModel], period: int = 14) -> float | None:
    """
    Calculate RSI value from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: RSI period
    
    Returns:
        RSI value (0-100) or None
    """
    if len(klines) < period + 1:
        return None
    
    closes = np.array([k.close for k in klines])
    deltas = np.diff(closes)
    
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi)


@register_factor(is_builtin=True)
class RSIFactor(FactorBase):
    """
    RSI (Relative Strength Index) Factor.
    
    RSI oscillates between 0 and 100:
    - RSI > 70: Overbought condition
    - RSI < 30: Oversold condition
    
    Calculation uses only K-Line close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_rsi",
            name="RSI (Relative Strength Index)",
            description="Measures the speed and magnitude of recent price changes",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["momentum", "oscillator", "overbought", "oversold"],
            required_fields=["close"],
            lookback_period=15,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate RSI value.
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters (period can override config)
        
        Returns:
            RSI value (0-100) or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_rsi(klines, period=period)
    
    def generate_signal(
        self,
        value: float,
        overbought: float = 70.0,
        oversold: float = 30.0,
    ) -> float:
        """
        Generate trading signal from RSI value.
        
        Args:
            value: RSI value
            overbought: Overbought threshold
            oversold: Oversold threshold
        
        Returns:
            Signal value (-1 to 1)
        """
        if value >= overbought:
            return -1.0
        elif value <= oversold:
            return 1.0
        elif value >= 50:
            return (value - 50) / (overbought - 50) * -0.5
        else:
            return (50 - value) / (50 - oversold) * 0.5
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        overbought: float = 70.0,
        oversold: float = 30.0,
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate RSI with trading signal.
        
        Args:
            klines: K-Line data
            overbought: Overbought threshold
            oversold: Oversold threshold
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        result = self.calculate(klines, **kwargs)
        
        if result and result.value is not None:
            result.signal = self.generate_signal(
                result.value,
                overbought=overbought,
                oversold=oversold,
            )
            result.confidence = abs(result.signal)
            result.metadata["overbought"] = overbought
            result.metadata["oversold"] = oversold
        
        return result
