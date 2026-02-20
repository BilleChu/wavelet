"""
OBV (On-Balance Volume) Factor.

OBV is a momentum indicator that uses volume flow to predict price changes.
OBV = Previous OBV + Volume (if Close > Previous Close)
OBV = Previous OBV - Volume (if Close < Previous Close)
OBV = Previous OBV (if Close = Previous Close)

Calculations use K-Line close prices and volume.
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


def calculate_obv(
    klines: list[ADSKLineModel],
) -> float | None:
    """
    Calculate OBV from K-Line data.
    
    Args:
        klines: K-Line data (sorted by date, oldest first)
    
    Returns:
        OBV value or None
    """
    if len(klines) < 2:
        return None
    
    obv = 0.0
    
    for i in range(1, len(klines)):
        if klines[i].close > klines[i - 1].close:
            obv += klines[i].volume
        elif klines[i].close < klines[i - 1].close:
            obv -= klines[i].volume
    
    return float(obv)


def obv(
    close: np.ndarray | list,
    volume: np.ndarray | list,
) -> np.ndarray:
    """
    Calculate OBV values for arrays.
    
    Args:
        close: Close price array
        volume: Volume array
    
    Returns:
        OBV values array
    """
    close = np.asarray(close, dtype=float)
    volume = np.asarray(volume, dtype=float)
    
    result = np.zeros(len(close), dtype=float)
    
    if len(close) < 2:
        return result
    
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            result[i] = result[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            result[i] = result[i - 1] - volume[i]
        else:
            result[i] = result[i - 1]
    
    return result


@dataclass
class OBVValues:
    """OBV values container."""
    obv: float | None = None
    obv_ma: float | None = None
    obv_trend: float | None = None
    
    @property
    def is_valid(self) -> bool:
        return self.obv is not None


@register_factor(is_builtin=True)
class OBVFactor(FactorBase):
    """
    On-Balance Volume (OBV) Factor.
    
    OBV measures buying and selling pressure:
    - Rising OBV: Accumulation (buying pressure)
    - Falling OBV: Distribution (selling pressure)
    - Divergence: Potential price reversal
    
    Calculation uses K-Line close prices and volume.
    """
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_obv",
            name="OBV (On-Balance Volume)",
            description="Momentum indicator using volume flow to predict price changes",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.FLOW,
            version="1.0.0",
            author="system",
            tags=["volume", "momentum", "accumulation"],
            required_fields=["close", "volume"],
            lookback_period=20,
        )
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> float | None:
        """
        Calculate OBV value.
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **kwargs: Additional parameters
        
        Returns:
            OBV value or None
        """
        return calculate_obv(klines)
    
    def calculate_full(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> OBVValues | None:
        """
        Calculate full OBV values.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            OBVValues or None
        """
        obv_value = calculate_obv(klines)
        
        if obv_value is None:
            return None
        
        obv_values = []
        running_obv = 0.0
        
        for i in range(1, len(klines)):
            if klines[i].close > klines[i - 1].close:
                running_obv += klines[i].volume
            elif klines[i].close < klines[i - 1].close:
                running_obv -= klines[i].volume
            obv_values.append(running_obv)
        
        ma_period = kwargs.get("ma_period", self._config.lookback_period)
        obv_ma = np.mean(obv_values[-ma_period:]) if len(obv_values) >= ma_period else None
        
        obv_trend = None
        if len(obv_values) >= 5:
            recent = obv_values[-5:]
            obv_trend = (recent[-1] - recent[0]) / abs(recent[0]) if recent[0] != 0 else 0
        
        return OBVValues(
            obv=obv_value,
            obv_ma=obv_ma,
            obv_trend=obv_trend,
        )
    
    def generate_signal(
        self,
        obv_value: float,
        obv_ma: float | None = None,
        obv_trend: float | None = None,
    ) -> float:
        """
        Generate trading signal from OBV.
        
        Args:
            obv_value: OBV value
            obv_ma: OBV moving average
            obv_trend: OBV trend
        
        Returns:
            Signal value (-1 to 1)
        """
        if obv_trend is not None:
            if obv_trend > 0.1:
                return min(1.0, obv_trend * 5)
            elif obv_trend < -0.1:
                return max(-1.0, obv_trend * 5)
        
        if obv_ma is not None and obv_ma != 0:
            deviation = (obv_value - obv_ma) / abs(obv_ma)
            return max(-1.0, min(1.0, deviation))
        
        return 0.0
    
    def calculate_with_signal(
        self,
        klines: list[ADSKLineModel],
        **kwargs: Any,
    ) -> FactorResult | None:
        """
        Calculate OBV with trading signal.
        
        Args:
            klines: K-Line data
            **kwargs: Additional parameters
        
        Returns:
            FactorResult with signal
        """
        obv_values = self.calculate_full(klines, **kwargs)
        
        if obv_values is None or not obv_values.is_valid:
            return None
        
        latest = klines[-1]
        signal = self.generate_signal(
            obv_values.obv,
            obv_values.obv_ma,
            obv_values.obv_trend,
        )
        
        return FactorResult(
            factor_id=self._metadata.factor_id,
            code=latest.code,
            trade_date=latest.trade_date,
            value=obv_values.obv,
            signal=signal,
            confidence=abs(signal),
            metadata={
                "obv": obv_values.obv,
                "obv_ma": obv_values.obv_ma,
                "obv_trend": obv_values.obv_trend,
            },
        )
