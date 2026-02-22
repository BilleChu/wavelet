"""
CCI (Commodity Channel Index) Factor.

CCI measures the current price level relative to an average price level.
CCI = (TP - SMA(TP)) / (0.015 * MD(TP))
TP = (High + Low + Close) / 3

Calculations use K-Line high, low, and close prices.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np

from openfinance.datacenter.models.analytical import ADSKLineModel
from ..base import (
    FactorBase,
    FactorMetadata,
    FactorResult,
    FactorConfig,
    FactorType,
    FactorCategory,
)
from ..registry import register_factor


def calculate_cci(
    klines: list[ADSKLineModel],
    period: int = 20,
) -> float | None:
    """
    Calculate CCI from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: CCI period
    
    Returns:
        CCI value or None
    """
    if len(klines) < period:
        return None
    
    tp_values = [(k.high + k.low + k.close) / 3 for k in klines]
    
    tp_window = tp_values[-period:]
    sma_tp = np.mean(tp_window)
    
    mean_deviation = np.mean([abs(tp - sma_tp) for tp in tp_window])
    
    if mean_deviation == 0:
        return 0.0
    
    current_tp = tp_values[-1]
    cci = (current_tp - sma_tp) / (0.015 * mean_deviation)
    
    return float(cci)


def cci(
    high: np.ndarray | list,
    low: np.ndarray | list,
    close: np.ndarray | list,
    period: int = 20,
) -> np.ndarray:
    """
    Calculate CCI values for arrays.
    
    Args:
        high: High price array
        low: Low price array
        close: Close price array
        period: CCI period (default 20)
    
    Returns:
        CCI values array
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    
    result = np.full_like(close, np.nan, dtype=float)
    
    if len(close) < period:
        return result
    
    tp = (high + low + close) / 3
    
    for i in range(period - 1, len(close)):
        tp_window = tp[i - period + 1:i + 1]
        sma_tp = np.mean(tp_window)
        mean_dev = np.mean(np.abs(tp_window - sma_tp))
        
        if mean_dev == 0:
            result[i] = 0.0
        else:
            result[i] = (tp[i] - sma_tp) / (0.015 * mean_dev)
    
    return result


@dataclass
class CCIValues:
    """CCI values container."""
    cci: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return self.cci is not None
    
    @property
    def is_overbought(self) -> bool:
        """Check if overbought (CCI > 100)."""
        return self.cci is not None and self.cci > 100
    
    @property
    def is_oversold(self) -> bool:
        """Check if oversold (CCI < -100)."""
        return self.cci is not None and self.cci < -100


@register_factor(is_builtin=True)
class CCIFactor(FactorBase):
    """
    CCI (Commodity Channel Index) Factor.
    
    CCI identifies cyclical trends:
    - CCI > 100: Overbought / Strong uptrend
    - CCI < -100: Oversold / Strong downtrend
    - CCI between -100 and 100: Normal trading range
    
    Calculation uses K-Line high, low, and close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_cci",
            name="CCI (Commodity Channel Index)",
            description="Momentum oscillator measuring price level relative to moving average",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["momentum", "oscillator", "overbought_oversold"],
            required_fields=["high", "low", "close"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate CCI value.
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            CCI value or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_cci(klines, period=period)
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> CCIValues | None:
        """
        Calculate full CCI values.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            CCIValues or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        
        cci_value = calculate_cci(klines, period=period)
        
        if cci_value is None:
            return None
        
        return CCIValues(cci=cci_value)
    
    def generate_signal(self, cci_value: float) -> float:
        """
        Generate trading signal from CCI.
        
        Args:
            cci_value: CCI value
        
        Returns:
            Signal value (-1 to 1)
        """
        if cci_value > 100:
            return -1.0
        elif cci_value < -100:
            return 1.0
        elif cci_value > 0:
            return -cci_value / 200
        else:
            return -cci_value / 200
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate CCI with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        cci_values = self.calculate_full(klines, **kwargs)
        
        if cci_values is None or not cci_values.is_valid:
            return None
        
        latest = klines[-1]
        signal = self.generate_signal(cci_values.cci)
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=cci_values.cci,
            signal=signal,
            confidence=abs(signal),
            metadata={
                "cci": cci_values.cci,
                "overbought": cci_values.is_overbought,
                "oversold": cci_values.is_oversold,
            },
        )
