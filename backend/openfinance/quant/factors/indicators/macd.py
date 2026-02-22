"""
MACD (Moving Average Convergence Divergence) Factor.

MACD is a trend-following momentum indicator.
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(MACD Line, 9)
Histogram = MACD Line - Signal Line

All calculations are based on K-Line close prices only.
"""

from dataclasses import dataclass
from typing import Any, Tuple

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


def calculate_macd(
    klines: list[ADSKLineModel],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[float | None, float | None, float | None]:
    """
    Calculate MACD values from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
    
    Returns:
        Tuple of (MACD line, Signal line, Histogram) or (None, None, None)
    """
    if len(klines) < slow + signal:
        return None, None, None
    
    closes = np.array([k.close for k in klines])
    
    ema_fast = _calculate_ema_array(closes, fast)
    ema_slow = _calculate_ema_array(closes, slow)
    
    macd_line = ema_fast - ema_slow
    
    valid_idx = np.where(~np.isnan(macd_line))[0]
    if len(valid_idx) == 0:
        return None, None, None
    
    first_valid = valid_idx[0]
    if len(closes) - first_valid < signal:
        return None, None, None
    
    signal_line = _calculate_ema_array(macd_line[first_valid:], signal)
    signal_line_full = np.full_like(closes, np.nan)
    signal_line_full[first_valid:] = signal_line
    
    histogram = macd_line - signal_line_full
    
    macd_val = float(macd_line[-1]) if not np.isnan(macd_line[-1]) else None
    signal_val = float(signal_line_full[-1]) if not np.isnan(signal_line_full[-1]) else None
    hist_val = float(histogram[-1]) if not np.isnan(histogram[-1]) else None
    
    return macd_val, signal_val, hist_val


def _calculate_ema_array(data: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate EMA for an array.
    
    Args:
        data: Price data array
        period: EMA period
    
    Returns:
        EMA values array
    """
    result = np.full_like(data, np.nan, dtype=float)
    
    if len(data) < period:
        return result
    
    alpha = 2 / (period + 1)
    result[period-1] = np.mean(data[:period])
    
    for i in range(period, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
    
    return result


def macd(
    close: np.ndarray | list,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate MACD values for arrays.
    
    Args:
        close: Close price array
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)
    
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    close = np.asarray(close, dtype=float)
    
    ema_fast = _calculate_ema_array(close, fast)
    ema_slow = _calculate_ema_array(close, slow)
    
    macd_line = ema_fast - ema_slow
    
    valid_start = np.where(~np.isnan(macd_line))[0]
    if len(valid_start) == 0:
        return (
            np.full_like(close, np.nan),
            np.full_like(close, np.nan),
            np.full_like(close, np.nan),
        )
    
    first_valid = valid_start[0]
    signal_line = np.full_like(close, np.nan)
    
    if len(close) - first_valid >= signal:
        signal_values = _calculate_ema_array(macd_line[first_valid:], signal)
        signal_line[first_valid:] = signal_values
    
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


@dataclass
class MACDValues:
    """MACD values container."""
    macd: float | None = None
    signal: float | None = None
    histogram: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return all(v is not None for v in [self.macd, self.signal, self.histogram])


@register_factor(is_builtin=True)
class MACDFactor(FactorBase):
    """
    MACD (Moving Average Convergence Divergence) Factor.
    
    MACD shows the relationship between two moving averages of price:
    - MACD > 0: Bullish momentum
    - MACD < 0: Bearish momentum
    - MACD crossing above Signal: Buy signal
    - MACD crossing below Signal: Sell signal
    
    Calculation uses only K-Line close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_macd",
            name="MACD (Moving Average Convergence Divergence)",
            description="Trend-following momentum indicator showing relationship between moving averages",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["momentum", "trend", "oscillator"],
            required_fields=["close"],
            lookback_period=35,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate MACD line value (primary value).
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            MACD line value or None
        """
        fast = kwargs.get("fast", 12)
        slow = kwargs.get("slow", 26)
        signal = kwargs.get("signal", 9)
        
        macd_val, _, _ = calculate_macd(klines, fast=fast, slow=slow, signal=signal)
        return macd_val
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> MACDValues | None:
        """
        Calculate full MACD values (MACD, Signal, Histogram).
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            MACDValues or None
        """
        fast = kwargs.get("fast", 12)
        slow = kwargs.get("slow", 26)
        signal = kwargs.get("signal", 9)
        
        macd_val, signal_val, hist_val = calculate_macd(klines, fast=fast, slow=slow, signal=signal)
        
        if macd_val is None:
            return None
        
        return MACDValues(macd=macd_val, signal=signal_val, histogram=hist_val)
    
    def generate_signal(
        self,
        macd_value: float,
        signal_value: float,
        histogram: float,
    ) -> float:
        """
        Generate trading signal from MACD values.
        
        Args:
            macd_value: MACD line value
            signal_value: Signal line value
            histogram: Histogram value
        
        Returns:
            Signal value (-1 to 1)
        """
        if histogram > 0:
            return min(1.0, histogram / abs(macd_value) if macd_value != 0 else 0)
        else:
            return max(-1.0, histogram / abs(macd_value) if macd_value != 0 else 0)
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate MACD with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        macd_values = self.calculate_full(klines, **kwargs)
        
        if macd_values is None or not macd_values.is_valid:
            return None
        
        latest = klines[-1]
        signal = self.generate_signal(
            macd_values.macd,
            macd_values.signal,
            macd_values.histogram,
        )
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=macd_values.macd,
            signal=signal,
            confidence=abs(signal),
            metadata={
                "macd": macd_values.macd,
                "signal": macd_values.signal,
                "histogram": macd_values.histogram,
            },
        )
