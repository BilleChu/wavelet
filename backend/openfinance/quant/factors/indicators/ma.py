"""
Moving Average (MA) Factor.

SMA/EMA are trend-following indicators that smooth out price data.

All calculations are based on K-Line close prices only.
"""

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


def calculate_sma(klines: list[ADSKLineModel], period: int = 20) -> float | None:
    """
    Calculate Simple Moving Average from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: SMA period
    
    Returns:
        SMA value or None
    """
    if len(klines) < period:
        return None
    
    closes = np.array([k.close for k in klines])
    return float(np.mean(closes[-period:]))


def calculate_ema(klines: list[ADSKLineModel], period: int = 20) -> float | None:
    """
    Calculate Exponential Moving Average from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: EMA period
    
    Returns:
        EMA value or None
    """
    if len(klines) < period:
        return None
    
    closes = np.array([k.close for k in klines])
    alpha = 2 / (period + 1)
    
    ema = np.mean(closes[:period])
    for i in range(period, len(closes)):
        ema = alpha * closes[i] + (1 - alpha) * ema
    
    return float(ema)


def sma(data: np.ndarray | list, period: int) -> np.ndarray:
    """
    Calculate SMA values for arrays.
    
    Args:
        data: Price data array
        period: Moving average period
    
    Returns:
        SMA values array (NaN for insufficient data)
    """
    data = np.asarray(data, dtype=float)
    result = np.full_like(data, np.nan, dtype=float)
    
    if len(data) < period:
        return result
    
    cumsum = np.cumsum(data)
    result[period-1:] = (cumsum[period-1:] - np.concatenate([[0], cumsum[:-period]])) / period
    
    return result


def ema(data: np.ndarray | list, period: int) -> np.ndarray:
    """
    Calculate EMA values for arrays.
    
    Args:
        data: Price data array
        period: EMA period
    
    Returns:
        EMA values array
    """
    data = np.asarray(data, dtype=float)
    result = np.full_like(data, np.nan, dtype=float)
    
    if len(data) < period:
        return result
    
    alpha = 2 / (period + 1)
    result[period-1] = np.mean(data[:period])
    
    for i in range(period, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
    
    return result


def wma(data: np.ndarray | list, period: int) -> np.ndarray:
    """
    Calculate WMA values for arrays.
    
    Args:
        data: Price data array
        period: WMA period
    
    Returns:
        WMA values array
    """
    data = np.asarray(data, dtype=float)
    result = np.full_like(data, np.nan, dtype=float)
    
    if len(data) < period:
        return result
    
    weights = np.arange(1, period + 1)
    weight_sum = weights.sum()
    
    for i in range(period - 1, len(data)):
        result[i] = np.sum(data[i-period+1:i+1] * weights) / weight_sum
    
    return result


@register_factor(is_builtin=True)
class SMAFactor(FactorBase):
    """
    Simple Moving Average Factor.
    
    SMA is a trend-following indicator that calculates the average
    price over a specified period.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_sma",
            name="SMA (Simple Moving Average)",
            description="Trend-following indicator using average price over period",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["trend", "moving_average", "lagging"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_sma(klines, period=period)
    
    def generate_signal(
        self,
        value: float,
        current_price: float,
    ) -> float:
        """
        Generate trading signal from SMA value.
        
        Args:
            value: SMA value
            current_price: Current close price
        
        Returns:
            Signal value (-1 to 1)
        """
        if current_price > value:
            return min(1.0, (current_price - value) / value * 10)
        else:
            return max(-1.0, (current_price - value) / value * 10)


@register_factor(is_builtin=True)
class EMAFactor(FactorBase):
    """
    Exponential Moving Average Factor.
    
    EMA gives more weight to recent prices, making it more responsive
    to new information compared to SMA.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_ema",
            name="EMA (Exponential Moving Average)",
            description="Weighted moving average giving more weight to recent prices",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["trend", "moving_average", "lagging"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_ema(klines, period=period)
    
    def generate_signal(
        self,
        value: float,
        current_price: float,
    ) -> float:
        """
        Generate trading signal from EMA value.
        
        Args:
            value: EMA value
            current_price: Current close price
        
        Returns:
            Signal value (-1 to 1)
        """
        if current_price > value:
            return min(1.0, (current_price - value) / value * 10)
        else:
            return max(-1.0, (current_price - value) / value * 10)
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate EMA with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        result = self.calculate(klines, **kwargs)
        
        if result and result.value is not None:
            current_price = klines[-1].close
            result.signal = self.generate_signal(result.value, current_price)
            result.confidence = abs(result.signal)
        
        return result
