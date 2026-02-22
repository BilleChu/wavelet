"""
KDJ (Stochastic Oscillator) Factor.

KDJ is a momentum indicator comparing closing price to price range.
K = %K line (fast)
D = %D line (slow, SMA of K)
J = 3K - 2D

Calculations use K-Line high, low, and close prices.
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


def calculate_kdj(
    klines: list[ADSKLineModel],
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> Tuple[float | None, float | None, float | None]:
    """
    Calculate KDJ values from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
        n: RSV period
        m1: K smoothing period
        m2: D smoothing period
    
    Returns:
        Tuple of (K, D, J) or (None, None, None)
    """
    if len(klines) < n:
        return None, None, None
    
    rsv_values = []
    
    for i in range(n - 1, len(klines)):
        window = klines[i - n + 1:i + 1]
        high_n = max(k.high for k in window)
        low_n = min(k.low for k in window)
        
        if high_n == low_n:
            rsv = 50.0
        else:
            rsv = (klines[i].close - low_n) / (high_n - low_n) * 100
        
        rsv_values.append(rsv)
    
    if len(rsv_values) < max(m1, m2):
        return None, None, None
    
    k_values = []
    k = 50.0
    
    for rsv in rsv_values:
        k = (2 / 3) * k + (1 / 3) * rsv
        k_values.append(k)
    
    d_values = []
    d = 50.0
    
    for k_val in k_values:
        d = (2 / 3) * d + (1 / 3) * k_val
        d_values.append(d)
    
    k_final = k_values[-1] if k_values else None
    d_final = d_values[-1] if d_values else None
    j_final = 3 * k_final - 2 * d_final if k_final and d_final else None
    
    return float(k_final), float(d_final), float(j_final)


def kdj(
    high: np.ndarray | list,
    low: np.ndarray | list,
    close: np.ndarray | list,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate KDJ values for arrays.
    
    Args:
        high: High price array
        low: Low price array
        close: Close price array
        n: RSV period (default 9)
        m1: K smoothing period (default 3)
        m2: D smoothing period (default 3)
    
    Returns:
        Tuple of (K, D, J) arrays
    """
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    
    k = np.full_like(close, np.nan, dtype=float)
    d = np.full_like(close, np.nan, dtype=float)
    j = np.full_like(close, np.nan, dtype=float)
    
    if len(close) < n:
        return k, d, j
    
    rsv = np.full_like(close, np.nan, dtype=float)
    
    for i in range(n - 1, len(close)):
        high_n = np.max(high[i - n + 1:i + 1])
        low_n = np.min(low[i - n + 1:i + 1])
        
        if high_n == low_n:
            rsv[i] = 50.0
        else:
            rsv[i] = (close[i] - low_n) / (high_n - low_n) * 100
    
    k[n - 1] = 50.0
    d[n - 1] = 50.0
    
    for i in range(n, len(close)):
        k[i] = (2 / 3) * k[i - 1] + (1 / 3) * rsv[i]
        d[i] = (2 / 3) * d[i - 1] + (1 / 3) * k[i]
        j[i] = 3 * k[i] - 2 * d[i]
    
    return k, d, j


@dataclass
class KDJValues:
    """KDJ values container."""
    k: float | None = None
    d: float | None = None
    j: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return all(v is not None for v in [self.k, self.d, self.j])
    
    @property
    def is_overbought(self) -> bool:
        """Check if overbought (K > 80)."""
        return self.k is not None and self.k > 80
    
    @property
    def is_oversold(self) -> bool:
        """Check if oversold (K < 20)."""
        return self.k is not None and self.k < 20


@register_factor(is_builtin=True)
class KDJFactor(FactorBase):
    """
    KDJ (Stochastic Oscillator) Factor.
    
    KDJ is a momentum indicator:
    - K > 80: Overbought zone
    - K < 20: Oversold zone
    - K crossing above D: Buy signal
    - K crossing below D: Sell signal
    - J > 100 or J < 0: Extreme conditions
    
    Calculation uses K-Line high, low, and close prices.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_kdj",
            name="KDJ (Stochastic Oscillator)",
            description="Momentum indicator comparing closing price to price range over period",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            version="1.0.0",
            author="system",
            tags=["momentum", "oscillator", "overbought_oversold"],
            required_fields=["high", "low", "close"],
            lookback_period=9,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate K value (primary value).
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            K value or None
        """
        n = kwargs.get("n", self._config.lookback_period)
        m1 = kwargs.get("m1", 3)
        m2 = kwargs.get("m2", 3)
        
        k, _, _ = calculate_kdj(klines, n=n, m1=m1, m2=m2)
        return k
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> KDJValues | None:
        """
        Calculate full KDJ values.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            KDJValues or None
        """
        n = kwargs.get("n", self._config.lookback_period)
        m1 = kwargs.get("m1", 3)
        m2 = kwargs.get("m2", 3)
        
        k, d, j = calculate_kdj(klines, n=n, m1=m1, m2=m2)
        
        if k is None:
            return None
        
        return KDJValues(k=k, d=d, j=j)
    
    def generate_signal(
        self,
        k: float,
        d: float,
        j: float,
    ) -> float:
        """
        Generate trading signal from KDJ values.
        
        Args:
            k: K value
            d: D value
            j: J value
        
        Returns:
            Signal value (-1 to 1)
        """
        if k > 80:
            return -1.0
        elif k < 20:
            return 1.0
        elif k > d:
            return min(0.5, (k - d) / 20)
        elif k < d:
            return max(-0.5, (k - d) / 20)
        else:
            return 0.0
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate KDJ with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        kdj_values = self.calculate_full(klines, **kwargs)
        
        if kdj_values is None or not kdj_values.is_valid:
            return None
        
        latest = klines[-1]
        signal = self.generate_signal(kdj_values.k, kdj_values.d, kdj_values.j)
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=kdj_values.k,
            signal=signal,
            confidence=abs(signal),
            metadata={
                "k": kdj_values.k,
                "d": kdj_values.d,
                "j": kdj_values.j,
                "overbought": kdj_values.is_overbought,
                "oversold": kdj_values.is_oversold,
            },
        )
