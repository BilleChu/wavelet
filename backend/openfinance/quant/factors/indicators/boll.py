"""
Bollinger Bands (BOLL) Factor.

Bollinger Bands are volatility bands placed above and below a moving average.
Middle Band = SMA(20)
Upper Band = Middle Band + 2 * StdDev(20)
Lower Band = Middle Band - 2 * StdDev(20)

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


def calculate_boll(
    klines: list[ADSKLineModel],
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[float | None, float | None, float | None]:
    """
    Calculate Bollinger Bands from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        period: SMA period
        std_dev: Standard deviation multiplier
    
    Returns:
        Tuple of (Upper Band, Middle Band, Lower Band) or (None, None, None)
    """
    if len(klines) < period:
        return None, None, None
    
    closes = np.array([k.close for k in klines])
    
    middle = np.mean(closes[-period:])
    std = np.std(closes[-period:], ddof=1)
    
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    
    return float(upper), float(middle), float(lower)


def boll(
    close: np.ndarray | list,
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate Bollinger Bands for arrays.
    
    Args:
        close: Close price array
        period: SMA period (default 20)
        std_dev: Standard deviation multiplier (default 2.0)
    
    Returns:
        Tuple of (Upper Band, Middle Band, Lower Band)
    """
    close = np.asarray(close, dtype=float)
    
    middle = np.full_like(close, np.nan, dtype=float)
    upper = np.full_like(close, np.nan, dtype=float)
    lower = np.full_like(close, np.nan, dtype=float)
    
    if len(close) < period:
        return upper, middle, lower
    
    for i in range(period - 1, len(close)):
        window = close[i - period + 1:i + 1]
        middle[i] = np.mean(window)
        std = np.std(window, ddof=1)
        upper[i] = middle[i] + std_dev * std
        lower[i] = middle[i] - std_dev * std
    
    return upper, middle, lower


@dataclass
class BOLLValues:
    """Bollinger Bands values container."""
    upper: float | None = None
    middle: float | None = None
    lower: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return all(v is not None for v in [self.upper, self.middle, self.lower])
    
    @property
    def bandwidth(self) -> float | None:
        """Calculate bandwidth (relative width)."""
        if not self.is_valid or self.middle == 0:
            return None
        return (self.upper - self.lower) / self.middle
    
    @property
    def percent_b(self) -> float | None:
        """Calculate %B (position within bands)."""
        if not self.is_valid or self.upper == self.lower:
            return None
        return None


@register_factor(is_builtin=True)
class BOLLFactor(FactorBase):
    """
    Bollinger Bands Factor.
    
    Bollinger Bands measure volatility and relative price levels:
    - Price near Upper Band: Potentially overbought
    - Price near Lower Band: Potentially oversold
    - Band Width: Volatility indicator
    - Squeeze: Low volatility, potential breakout
    
    Calculation uses only K-Line close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_boll",
            name="Bollinger Bands (BOLL)",
            description="Volatility indicator showing price relative to moving average and standard deviation",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.VOLATILITY,
            version="1.0.0",
            author="system",
            tags=["volatility", "trend", "overbought_oversold"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate Middle Band value (primary value).
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            Middle Band value or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        std_dev = kwargs.get("std_dev", 2.0)
        
        _, middle, _ = calculate_boll(klines, period=period, std_dev=std_dev)
        return middle
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> BOLLValues | None:
        """
        Calculate full Bollinger Bands values.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            BOLLValues or None
        """
        period = kwargs.get("period", self._config.lookback_period)
        std_dev = kwargs.get("std_dev", 2.0)
        
        upper, middle, lower = calculate_boll(klines, period=period, std_dev=std_dev)
        
        if middle is None:
            return None
        
        return BOLLValues(upper=upper, middle=middle, lower=lower)
    
    def generate_signal(
        self,
        current_price: float,
        upper: float,
        middle: float,
        lower: float,
    ) -> float:
        """
        Generate trading signal from Bollinger Bands.
        
        Args:
            current_price: Current close price
            upper: Upper band
            middle: Middle band
            lower: Lower band
        
        Returns:
            Signal value (-1 to 1)
        """
        if upper == lower:
            return 0.0
        
        percent_b = (current_price - lower) / (upper - lower)
        
        if percent_b > 1:
            return -1.0
        elif percent_b < 0:
            return 1.0
        elif percent_b > 0.8:
            return -0.5
        elif percent_b < 0.2:
            return 0.5
        else:
            return 0.0
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate Bollinger Bands with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        boll_values = self.calculate_full(klines, **kwargs)
        
        if boll_values is None or not boll_values.is_valid:
            return None
        
        latest = klines[-1]
        signal = self.generate_signal(
            latest.close,
            boll_values.upper,
            boll_values.middle,
            boll_values.lower,
        )
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=boll_values.middle,
            signal=signal,
            confidence=abs(signal),
            metadata={
                "upper": boll_values.upper,
                "middle": boll_values.middle,
                "lower": boll_values.lower,
                "bandwidth": boll_values.bandwidth,
            },
        )
