"""
Average True Range (ATR) Factor.

ATR is a volatility indicator that measures market volatility.
True Range = max(High-Low, abs(High-PrevClose), abs(Low-PrevClose))
ATR = SMA(True Range, period)

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


def calculate_atr(
    klines: list[ADSKLineModel],
    period: int = 14,
) -> float | None:
    """
    Calculate Average True Range from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: ATR period
    
    Returns:
        ATR value or None
    """
    if len(klines) < period + 1:
        return None
    
    true_ranges = []
    
    for i in range(1, len(klines)):
        high = klines[i].high
        low = klines[i].low
        prev_close = klines[i - 1].close
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return None
    
    return float(np.mean(true_ranges[-period:]))


def atr(
    high: np.ndarray | list,
    low: np.ndarray | list,
    close: np.ndarray | list,
    period: int = 14,
) -> np.ndarray:
    """
    Calculate ATR values for arrays.
    
    Args:
        high: High price array
        low: Low price array
        close: Close price array
        period: ATR period (default 14)
    
    Returns:
        ATR values array
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    
    result = np.full_like(close, np.nan, dtype=float)
    
    if len(close) < period + 1:
        return result
    
    true_ranges = np.zeros(len(close))
    true_ranges[0] = high[0] - low[0]
    
    for i in range(1, len(close)):
        true_ranges[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    
    for i in range(period, len(close)):
        result[i] = np.mean(true_ranges[i - period + 1:i + 1])
    
    return result


def true_range(
    high: np.ndarray | list,
    low: np.ndarray | list,
    close: np.ndarray | list,
) -> np.ndarray:
    """
    Calculate True Range values for arrays.
    
    Args:
        high: High price array
        low: Low price array
        close: Close price array
    
    Returns:
        True Range values array
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    
    result = np.zeros(len(close))
    result[0] = high[0] - low[0]
    
    for i in range(1, len(close)):
        result[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    
    return result


@dataclass
class ATRValues:
    """ATR values container."""
    atr: float | None = None
    tr: float | None = None
    atr_percent: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return self.atr is not None


@register_factor(is_builtin=True)
class ATRFactor(FactorBase):
    """
    Average True Range (ATR) Factor.
    
    ATR measures market volatility:
    - Higher ATR: Higher volatility
    - Lower ATR: Lower volatility
    
    Common uses:
    - Stop-loss placement
    - Position sizing
    - Trend confirmation
    
    Calculation uses K-Line high, low, and close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_atr",
            name="ATR (Average True Range)",
            description="Volatility indicator measuring the average range of price movement",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.VOLATILITY,
            version="1.0.0",
            author="system",
            tags=["volatility", "risk", "stop_loss"],
            required_fields=["high", "low", "close"],
            lookback_period=14,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate ATR value.
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            ATR value or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        return calculate_atr(klines, period=period)
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> ATRValues | None:
        """
        Calculate full ATR values.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            ATRValues or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        
        atr_value = calculate_atr(klines, period=period)
        
        if atr_value is None:
            return None
        
        latest = klines[-1]
        prev = klines[-2] if len(klines) > 1 else None
        
        tr = max(
            latest.high - latest.low,
            abs(latest.high - prev.close) if prev else latest.high - latest.low,
            abs(latest.low - prev.close) if prev else latest.high - latest.low,
        )
        
        atr_percent = atr_value / latest.close if latest.close > 0 else None
        
        return ATRValues(
            atr=atr_value,
            tr=tr,
            atr_percent=atr_percent,
        )
    
    def generate_signal(
        self,
        atr_value: float,
        current_price: float,
        avg_atr: float | None = None,
    ) -> float:
        """
        Generate trading signal from ATR.
        
        Note: ATR is primarily used for risk management,
        not for directional signals.
        
        Args:
            atr_value: Current ATR value
            current_price: Current close price
            avg_atr: Average ATR for comparison (optional)
        
        Returns:
            Signal value (0 for ATR, use for volatility assessment)
        """
        return 0.0
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate ATR with trading context.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with ATR context
        """
        atr_values = self.calculate_full(klines, **kwargs)
        
        if atr_values is None or not atr_values.is_valid:
            return None
        
        latest = klines[-1]
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=atr_values.atr,
            signal=0.0,
            confidence=0.0,
            metadata={
                "atr": atr_values.atr,
                "true_range": atr_values.tr,
                "atr_percent": atr_values.atr_percent,
                "stop_loss_long": latest.close - 2 * atr_values.atr,
                "stop_loss_short": latest.close + 2 * atr_values.atr,
            },
        )
