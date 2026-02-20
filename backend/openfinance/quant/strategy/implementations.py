"""
Multi-Factor Strategy Implementations.

This module provides concrete strategy implementations that combine multiple factors.
"""

from datetime import datetime
from typing import Any, Optional

import pandas as pd

from openfinance.datacenter.ads import ADSKLineModel
from openfinance.quant.factors.indicators.rsi import RSIFactor
from openfinance.quant.factors.indicators.kdj import KDJFactor
from openfinance.quant.factors import FactorConfig
from .base import (
    BaseStrategy,
    StrategyMetadata,
    StrategySignal,
    StrategyConfig,
    StrategyType,
    SignalType,
    WeightMethod,
    RebalanceFrequency,
)
from .registry import register_strategy


@register_strategy(is_builtin=True)
class RSIKDJMomentumStrategy(BaseStrategy):
    """
    RSI + KDJ Momentum Strategy.
    
    Combines RSI and KDJ indicators to generate trading signals:
    - RSI for momentum confirmation
    - KDJ for entry/exit timing
    
    Signal Logic:
    - Strong Buy: RSI oversold (<30) + KDJ K crosses above D
    - Buy: RSI < 40 + KDJ in oversold zone
    - Strong Sell: RSI overbought (>70) + KDJ K crosses below D
    - Sell: RSI > 60 + KDJ in overbought zone
    """
    
    def __init__(
        self,
        strategy_id: str = "strategy_rsi_kdj_momentum",
        name: str = "RSI + KDJ Momentum Strategy",
        code: str = "rsi_kdj_momentum",
        description: str = "Combines RSI and KDJ for momentum-based trading signals",
        factors: Optional[list[str]] = None,
        factor_weights: Optional[dict[str, float]] = None,
        weight_method: str = WeightMethod.EQUAL_WEIGHT,
        rebalance_freq: str = RebalanceFrequency.MONTHLY,
        max_positions: int = 100,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        parameters: Optional[dict[str, Any]] = None,
        rsi_period: int = 14,
        kdj_n: int = 9,
        kdj_m1: int = 3,
        kdj_m2: int = 3,
    ) -> None:
        super().__init__(
            strategy_id=strategy_id,
            name=name,
            code=code,
            description=description,
            strategy_type=StrategyType.MULTI_FACTOR,
            factors=factors or ["factor_rsi", "factor_kdj"],
            factor_weights=factor_weights or {"factor_rsi": 0.5, "factor_kdj": 0.5},
            weight_method=weight_method,
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            stop_loss=stop_loss,
            take_profit=take_profit,
            parameters=parameters,
        )
        
        rsi_config = FactorConfig(lookback_period=rsi_period)
        self._rsi_factor = RSIFactor(config=rsi_config)
        
        kdj_config = FactorConfig(lookback_period=kdj_n)
        self._kdj_factor = KDJFactor(config=kdj_config)
        
        self._kdj_m1 = kdj_m1
        self._kdj_m2 = kdj_m2
    
    def generate_signals(
        self,
        data: dict[str, pd.DataFrame],
        factor_values: Optional[dict[str, pd.DataFrame]] = None,
        date: Optional[datetime] = None,
    ) -> dict[str, float]:
        """Generate trading signals for all stocks."""
        signals = {}
        
        for code, df in data.items():
            if len(df) < 30:
                continue
            
            klines = self._convert_to_klines(df)
            signal = self._generate_signal_for_stock(code, klines)
            if signal:
                signals[code] = signal.strength
        
        return signals
    
    def calculate_portfolio_weights(
        self,
        signals: dict[str, float],
        prices: pd.DataFrame,
        covariance_matrix: Optional[pd.DataFrame] = None,
    ) -> dict[str, float]:
        """Calculate equal weights for top signals."""
        if not signals:
            return {}
        
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_signals = sorted_signals[:self.max_positions]
        
        n = len(top_signals)
        if n == 0:
            return {}
        
        return {code: 1.0 / n for code, _ in top_signals}
    
    def _convert_to_klines(self, df: pd.DataFrame) -> list:
        """Convert DataFrame to kline format."""
        return [type('ADSKLineModel', (), {
            'trade_date': row.get('trade_date', row.get('date')),
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': row.get('close'),
            'volume': row.get('volume'),
        })() for _, row in df.iterrows()]
    
    def _generate_signal_for_stock(
        self,
        code: str,
        klines: list,
    ) -> StrategySignal | None:
        """Generate signal for a single stock."""
        if len(klines) < 30:
            return None
        
        rsi_result = self._rsi_factor.calculate(klines)
        kdj_result = self._kdj_factor.calculate_full(
            klines,
            m1=self._kdj_m1,
            m2=self._kdj_m2,
        )
        
        if not rsi_result or rsi_result.value is None:
            return None
        
        if not kdj_result or not kdj_result.is_valid:
            return None
        
        rsi_value = rsi_result.value
        k_value = kdj_result.k
        d_value = kdj_result.d
        j_value = kdj_result.j
        
        signal_value, confidence = self._calculate_combined_signal(
            rsi_value, k_value, d_value, j_value
        )
        
        signal_type = self._classify_signal(signal_value)
        
        return StrategySignal(
            stock_code=code,
            signal_type=signal_type,
            strength=signal_value,
            metadata={
                "rsi": rsi_value,
                "kdj_k": k_value,
                "kdj_d": d_value,
                "kdj_j": j_value,
                "confidence": confidence,
            },
        )
    
    def _calculate_combined_signal(
        self,
        rsi: float,
        k: float,
        d: float,
        j: float,
    ) -> tuple[float, float]:
        """Calculate combined signal from RSI and KDJ."""
        rsi_signal = self._rsi_signal(rsi)
        kdj_signal = self._kdj_signal(k, d, j)
        
        rsi_weight = self.factor_weights.get("factor_rsi", 0.5)
        kdj_weight = self.factor_weights.get("factor_kdj", 0.5)
        
        combined = rsi_signal * rsi_weight + kdj_signal * kdj_weight
        
        rsi_conf = self._rsi_confidence(rsi)
        kdj_conf = self._kdj_confidence(k, d, j)
        confidence = (rsi_conf + kdj_conf) / 2
        
        if abs(rsi_signal) > 0.5 and abs(kdj_signal) > 0.5:
            if rsi_signal * kdj_signal > 0:
                combined *= 1.2
                confidence = min(confidence * 1.2, 1.0)
        
        return combined, confidence
    
    def _rsi_signal(self, rsi: float) -> float:
        """Convert RSI value to signal (-1 to 1)."""
        if rsi >= 70:
            return -1.0
        elif rsi >= 60:
            return -0.5
        elif rsi <= 30:
            return 1.0
        elif rsi <= 40:
            return 0.5
        else:
            return (50 - rsi) / 50
    
    def _kdj_signal(self, k: float, d: float, j: float) -> float:
        """Convert KDJ values to signal (-1 to 1)."""
        signal = 0.0
        
        if k > d:
            if k < 20:
                signal = 1.0
            elif k < 50:
                signal = 0.5
        elif k < d:
            if k > 80:
                signal = -1.0
            elif k > 50:
                signal = -0.5
        
        if j > 100:
            signal = min(signal, -0.8)
        elif j < 0:
            signal = max(signal, 0.8)
        
        return signal
    
    def _rsi_confidence(self, rsi: float) -> float:
        """Calculate confidence based on RSI extremity."""
        if rsi >= 70 or rsi <= 30:
            return 0.9
        elif rsi >= 60 or rsi <= 40:
            return 0.7
        else:
            return 0.5
    
    def _kdj_confidence(self, k: float, d: float, j: float) -> float:
        """Calculate confidence based on KDJ values."""
        if (k >= 80 and d >= 80) or (k <= 20 and d <= 20):
            return 0.9
        elif k >= 70 or k <= 30:
            return 0.7
        elif j > 100 or j < 0:
            return 0.8
        else:
            return 0.5
    
    def _classify_signal(self, signal_value: float) -> str:
        """Classify signal value into signal type."""
        if signal_value >= 0.7:
            return SignalType.STRONG_BUY
        elif signal_value >= 0.3:
            return SignalType.BUY
        elif signal_value <= -0.7:
            return SignalType.STRONG_SELL
        elif signal_value <= -0.3:
            return SignalType.SELL
        else:
            return SignalType.HOLD


@register_strategy(is_builtin=True)
class FlexibleMultiFactorStrategy(BaseStrategy):
    """
    Flexible Multi-Factor Strategy.
    
    Supports dynamic factor configuration at runtime.
    Factors can be added/removed and weights adjusted.
    """
    
    def __init__(
        self,
        strategy_id: str = "strategy_flexible_multi_factor",
        name: str = "Flexible Multi-Factor Strategy",
        code: str = "flexible_multi_factor",
        description: str = "Configurable multi-factor strategy with dynamic factor selection",
        factors: Optional[list[str]] = None,
        factor_weights: Optional[dict[str, float]] = None,
        weight_method: str = WeightMethod.EQUAL_WEIGHT,
        rebalance_freq: str = RebalanceFrequency.MONTHLY,
        max_positions: int = 100,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        parameters: Optional[dict[str, Any]] = None,
        factor_instances: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            strategy_id=strategy_id,
            name=name,
            code=code,
            description=description,
            strategy_type=StrategyType.MULTI_FACTOR,
            factors=factors or [],
            factor_weights=factor_weights or {},
            weight_method=weight_method,
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            stop_loss=stop_loss,
            take_profit=take_profit,
            parameters=parameters,
        )
        self._factor_instances = factor_instances or {}
    
    def generate_signals(
        self,
        data: dict[str, pd.DataFrame],
        factor_values: Optional[dict[str, pd.DataFrame]] = None,
        date: Optional[datetime] = None,
    ) -> dict[str, float]:
        """Generate signals using all configured factors."""
        if not self._factor_instances:
            return {}
        
        signals = {}
        
        for code, df in data.items():
            if len(df) < 30:
                continue
            
            klines = self._convert_to_klines(df)
            signal = self._generate_signal_for_stock(code, klines)
            if signal:
                signals[code] = signal.strength
        
        return signals
    
    def calculate_portfolio_weights(
        self,
        signals: dict[str, float],
        prices: pd.DataFrame,
        covariance_matrix: Optional[pd.DataFrame] = None,
    ) -> dict[str, float]:
        """Calculate equal weights for top signals."""
        if not signals:
            return {}
        
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        top_signals = sorted_signals[:self.max_positions]
        
        n = len(top_signals)
        if n == 0:
            return {}
        
        return {code: 1.0 / n for code, _ in top_signals}
    
    def _convert_to_klines(self, df: pd.DataFrame) -> list:
        """Convert DataFrame to kline format."""
        return [type('ADSKLineModel', (), {
            'trade_date': row.get('trade_date', row.get('date')),
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': row.get('close'),
            'volume': row.get('volume'),
        })() for _, row in df.iterrows()]
    
    def add_factor(
        self,
        factor_id: str,
        factor_instance: Any,
        weight: float = 1.0,
    ) -> None:
        """Add a factor to the strategy."""
        self._factor_instances[factor_id] = factor_instance
        if factor_id not in self.factors:
            self.factors.append(factor_id)
        self.factor_weights[factor_id] = weight
    
    def remove_factor(self, factor_id: str) -> bool:
        """Remove a factor from the strategy."""
        if factor_id in self._factor_instances:
            del self._factor_instances[factor_id]
            if factor_id in self.factors:
                self.factors.remove(factor_id)
            if factor_id in self.factor_weights:
                del self.factor_weights[factor_id]
            return True
        return False
    
    def set_factor_weight(self, factor_id: str, weight: float) -> None:
        """Set weight for a factor."""
        self.factor_weights[factor_id] = weight
    
    def normalize_weights(self) -> None:
        """Normalize all factor weights to sum to 1."""
        total = sum(self.factor_weights.values())
        if total > 0:
            for fid in self.factor_weights:
                self.factor_weights[fid] /= total
    
    def _generate_signal_for_stock(
        self,
        code: str,
        klines: list,
    ) -> StrategySignal | None:
        """Generate signal for a single stock."""
        if len(klines) < 30:
            return None
        
        factor_values_dict: dict[str, float | None] = {}
        factor_signals_dict: dict[str, float] = {}
        
        for factor_id, factor in self._factor_instances.items():
            result = factor.calculate(klines)
            if result and result.value is not None:
                factor_values_dict[factor_id] = result.value
                if hasattr(factor, 'generate_signal'):
                    factor_signals_dict[factor_id] = factor.generate_signal(result.value)
                else:
                    factor_signals_dict[factor_id] = 0.0
            else:
                factor_values_dict[factor_id] = None
                factor_signals_dict[factor_id] = 0.0
        
        if not any(v is not None for v in factor_values_dict.values()):
            return None
        
        combined_signal = self._combine_signals(factor_signals_dict)
        confidence = self._calculate_confidence(factor_values_dict, factor_signals_dict)
        
        return StrategySignal(
            stock_code=code,
            signal_type=self._classify_signal(combined_signal),
            strength=combined_signal,
            metadata={
                "confidence": confidence,
                "factor_values": factor_values_dict,
                "factor_signals": factor_signals_dict,
            },
        )
    
    def _combine_signals(self, factor_signals: dict[str, float]) -> float:
        """Combine factor signals using weights."""
        if not self.factor_weights:
            weights = {fid: 1.0 / len(factor_signals) for fid in factor_signals}
        else:
            total = sum(self.factor_weights.values())
            weights = {fid: w / total for fid, w in self.factor_weights.items()}
        
        combined = 0.0
        for factor_id, signal in factor_signals.items():
            weight = weights.get(factor_id, 0.0)
            combined += signal * weight
        
        return max(-1.0, min(1.0, combined))
    
    def _calculate_confidence(
        self,
        factor_values: dict[str, float | None],
        factor_signals: dict[str, float],
    ) -> float:
        """Calculate overall confidence."""
        valid_count = sum(1 for v in factor_values.values() if v is not None)
        total_count = len(factor_values)
        
        if total_count == 0:
            return 0.0
        
        coverage = valid_count / total_count
        
        signal_strength = sum(abs(s) for s in factor_signals.values()) / len(factor_signals)
        
        return (coverage * 0.4 + signal_strength * 0.6)
    
    def _classify_signal(self, signal_value: float) -> str:
        """Classify signal value into signal type."""
        if signal_value >= 0.7:
            return SignalType.STRONG_BUY
        elif signal_value >= 0.3:
            return SignalType.BUY
        elif signal_value <= -0.7:
            return SignalType.STRONG_SELL
        elif signal_value <= -0.3:
            return SignalType.SELL
        else:
            return SignalType.HOLD
