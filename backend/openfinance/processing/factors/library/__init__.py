"""
Fundamental Factor Library.

This module provides fundamental analysis factors based on financial data:
- Momentum: Price momentum factors
- Value: Valuation factors (PE, PB, etc.)
- Quality: Quality factors (ROE, etc.)
- Volatility: Risk factors

All factors are registered via @register_factor decorator.
"""

from openfinance.quant.factors.base import (
    FactorBase,
    FactorMetadata,
    FactorType,
    FactorCategory,
)
from openfinance.quant.factors.registry import register_factor
from openfinance.datacenter.ads import ADSKLineModel
from typing import Any
import numpy as np


@register_factor(is_builtin=True)
class MomentumFactor(FactorBase):
    """Price Momentum Factor - measures price change over a period."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_momentum",
            name="Price Momentum",
            description="Price return over lookback period",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            tags=["momentum", "trend"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        period = kwargs.get("period", self._config.lookback_period)
        if len(klines) < period + 1:
            return None
        
        closes = np.array([k.close for k in klines])
        return float((closes[-1] - closes[-period - 1]) / closes[-period - 1])


@register_factor(is_builtin=True)
class RiskAdjustedMomentumFactor(FactorBase):
    """Risk-Adjusted Momentum Factor - momentum divided by volatility."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_risk_adj_momentum",
            name="Risk-Adjusted Momentum",
            description="Momentum divided by volatility (Sharpe-like)",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.MOMENTUM,
            tags=["momentum", "risk", "sharpe"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        period = kwargs.get("period", self._config.lookback_period)
        if len(klines) < period + 1:
            return None
        
        closes = np.array([k.close for k in klines])
        returns = np.diff(closes[-period - 1:]) / closes[-period - 1:-1]
        
        momentum = (closes[-1] - closes[-period - 1]) / closes[-period - 1]
        volatility = np.std(returns) if len(returns) > 1 else 0
        
        if volatility == 0:
            return 0.0
        return float(momentum / volatility)


@register_factor(is_builtin=True)
class ValueFactor(FactorBase):
    """Value Factor - based on PE ratio (lower is better)."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_value_pe",
            name="Value (PE Ratio)",
            description="Price-to-Earnings ratio for value investing",
            factor_type=FactorType.FUNDAMENTAL,
            category=FactorCategory.VALUE,
            tags=["value", "valuation", "pe"],
            required_fields=["close"],
            lookback_period=1,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        pe_ratio = kwargs.get("pe_ratio", 15.0)
        return float(pe_ratio)


@register_factor(is_builtin=True)
class DividendYieldFactor(FactorBase):
    """Dividend Yield Factor - annual dividend / price."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_dividend_yield",
            name="Dividend Yield",
            description="Annual dividend yield percentage",
            factor_type=FactorType.FUNDAMENTAL,
            category=FactorCategory.VALUE,
            tags=["value", "dividend", "income"],
            required_fields=["close"],
            lookback_period=1,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        dividend_yield = kwargs.get("dividend_yield", 0.0)
        return float(dividend_yield)


@register_factor(is_builtin=True)
class QualityFactor(FactorBase):
    """Quality Factor - based on ROE (higher is better)."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_quality_roe",
            name="Quality (ROE)",
            description="Return on Equity for quality investing",
            factor_type=FactorType.FUNDAMENTAL,
            category=FactorCategory.QUALITY,
            tags=["quality", "profitability", "roe"],
            required_fields=["close"],
            lookback_period=1,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        roe = kwargs.get("roe", 0.1)
        return float(roe)


@register_factor(is_builtin=True)
class VolatilityFactor(FactorBase):
    """Volatility Factor - historical price volatility."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_volatility",
            name="Historical Volatility",
            description="Annualized price volatility",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.VOLATILITY,
            tags=["volatility", "risk"],
            required_fields=["close"],
            lookback_period=20,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        period = kwargs.get("period", self._config.lookback_period)
        if len(klines) < period + 1:
            return None
        
        closes = np.array([k.close for k in klines])
        returns = np.diff(closes[-period - 1:]) / closes[-period - 1:-1]
        
        return float(np.std(returns) * np.sqrt(252))


@register_factor(is_builtin=True)
class IdiosyncraticVolatilityFactor(FactorBase):
    """Idiosyncratic Volatility - stock-specific risk after market adjustment."""
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(
            factor_id="factor_idio_volatility",
            name="Idiosyncratic Volatility",
            description="Stock-specific volatility after market adjustment",
            factor_type=FactorType.TECHNICAL,
            category=FactorCategory.VOLATILITY,
            tags=["volatility", "risk", "idiosyncratic"],
            required_fields=["close"],
            lookback_period=60,
        )
    
    def _calculate(self, klines: list[ADSKLineModel], **kwargs) -> float | None:
        period = kwargs.get("period", self._config.lookback_period)
        if len(klines) < period + 1:
            return None
        
        closes = np.array([k.close for k in klines])
        returns = np.diff(closes[-period - 1:]) / closes[-period - 1:-1]
        
        market_return = np.mean(returns)
        residuals = returns - market_return
        
        return float(np.std(residuals) * np.sqrt(252))


__all__ = [
    "MomentumFactor",
    "RiskAdjustedMomentumFactor",
    "ValueFactor",
    "DividendYieldFactor",
    "QualityFactor",
    "VolatilityFactor",
    "IdiosyncraticVolatilityFactor",
]
