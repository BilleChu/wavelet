"""
Factor Expression Engine.

Provides a DSL (Domain Specific Language) for defining and calculating
quantitative factors from OHLCV data. All factors are derived from
raw market data only.
"""

import ast
import logging
import operator
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Protocol

import numpy as np
import pandas as pd

from openfinance.datacenter.ads import ADSKLineModel

logger = logging.getLogger(__name__)


class ExpressionType(str, Enum):
    """Types of factor expressions."""
    SIMPLE = "simple"
    COMPOUND = "compound"
    CONDITIONAL = "conditional"
    CUSTOM = "custom"


@dataclass
class ExpressionContext:
    """Context for expression evaluation."""
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    amount: np.ndarray | None = None
    pre_close: np.ndarray | None = None
    
    vwap: np.ndarray | None = None
    returns: np.ndarray | None = None
    log_returns: np.ndarray | None = None
    
    trade_date: date | None = None
    code: str | None = None
    
    def get_field(self, name: str) -> np.ndarray | None:
        """Get field by name."""
        return getattr(self, name, None)


@dataclass
class ParsedExpression:
    """Parsed factor expression."""
    raw: str
    ast_tree: ast.AST | None = None
    dependencies: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    is_valid: bool = False
    error: str | None = None


class FunctionRegistry:
    """Registry for factor calculation functions."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._functions = {}
            cls._instance._register_builtin_functions()
        return cls._instance
    
    def _register_builtin_functions(self) -> None:
        """Register built-in calculation functions."""
        self._functions = {
            'sma': self._sma,
            'ema': self._ema,
            'wma': self._wma,
            'std': self._std,
            'var': self._var,
            'max': self._rolling_max,
            'min': self._rolling_min,
            'sum': self._rolling_sum,
            'prod': self._rolling_prod,
            'count': self._rolling_count,
            'rank': self._rank,
            'delta': self._delta,
            'pct_change': self._pct_change,
            'diff': self._diff,
            'shift': self._shift,
            'cumsum': self._cumsum,
            'cumprod': self._cumprod,
            'cummax': self._cummax,
            'cummin': self._cummin,
            'rsi': self._rsi,
            'macd': self._macd,
            'kdj': self._kdj,
            'boll': self._boll,
            'atr': self._atr,
            'obv': self._obv,
            'cci': self._cci,
            'wr': self._wr,
            'ad': self._ad,
            'mfi': self._mfi,
            'roc': self._roc,
            'momentum': self._momentum,
            'volatility': self._volatility,
            'skewness': self._skewness,
            'kurtosis': self._kurtosis,
            'zscore': self._zscore,
            'normalize': self._normalize,
            'winsorize': self._winsorize,
            'quantile': self._quantile,
            'corr': self._corr,
            'cov': self._cov,
            'beta': self._beta,
            'alpha': self._alpha,
            'sharpe': self._sharpe,
            'sortino': self._sortino,
            'max_drawdown': self._max_drawdown,
            'calmar': self._calmar,
            'if': self._if_else,
            'abs': np.abs,
            'sqrt': np.sqrt,
            'log': np.log,
            'log10': np.log10,
            'exp': np.exp,
            'power': np.power,
            'sign': np.sign,
            'floor': np.floor,
            'ceil': np.ceil,
            'round': np.round,
            'clip': np.clip,
            'where': np.where,
            'isnan': np.isnan,
            'isinf': np.isinf,
            'nan_to_num': np.nan_to_num,
        }
    
    def register(self, name: str, func: Callable) -> None:
        """Register a custom function."""
        self._functions[name.lower()] = func
    
    def get(self, name: str) -> Callable | None:
        """Get function by name."""
        return self._functions.get(name.lower())
    
    def list_functions(self) -> list[str]:
        """List all registered functions."""
        return list(self._functions.keys())
    
    @staticmethod
    def _sma(data: np.ndarray, period: int) -> np.ndarray:
        """Simple Moving Average."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        cumsum = np.cumsum(data)
        result[period-1:] = (cumsum[period-1:] - np.concatenate([[0], cumsum[:-period]])) / period
        return result
    
    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """Exponential Moving Average."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        alpha = 2 / (period + 1)
        result[period-1] = np.mean(data[:period])
        for i in range(period, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        return result
    
    @staticmethod
    def _wma(data: np.ndarray, period: int) -> np.ndarray:
        """Weighted Moving Average."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        weights = np.arange(1, period + 1)
        for i in range(period - 1, len(data)):
            result[i] = np.sum(data[i-period+1:i+1] * weights) / weights.sum()
        return result
    
    @staticmethod
    def _std(data: np.ndarray, period: int, ddof: int = 1) -> np.ndarray:
        """Rolling Standard Deviation."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = np.std(data[i-period+1:i+1], ddof=ddof)
        return result
    
    @staticmethod
    def _var(data: np.ndarray, period: int, ddof: int = 1) -> np.ndarray:
        """Rolling Variance."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = np.var(data[i-period+1:i+1], ddof=ddof)
        return result
    
    @staticmethod
    def _rolling_max(data: np.ndarray, period: int) -> np.ndarray:
        """Rolling Maximum."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = np.max(data[i-period+1:i+1])
        return result
    
    @staticmethod
    def _rolling_min(data: np.ndarray, period: int) -> np.ndarray:
        """Rolling Minimum."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = np.min(data[i-period+1:i+1])
        return result
    
    @staticmethod
    def _rolling_sum(data: np.ndarray, period: int) -> np.ndarray:
        """Rolling Sum."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        cumsum = np.cumsum(data)
        result[period-1:] = cumsum[period-1:] - np.concatenate([[0], cumsum[:-period]])
        return result
    
    @staticmethod
    def _rolling_prod(data: np.ndarray, period: int) -> np.ndarray:
        """Rolling Product."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = np.prod(data[i-period+1:i+1])
        return result
    
    @staticmethod
    def _rolling_count(data: np.ndarray, period: int) -> np.ndarray:
        """Rolling Count of non-NaN values."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        for i in range(period - 1, len(data)):
            result[i] = np.sum(~np.isnan(data[i-period+1:i+1]))
        return result
    
    @staticmethod
    def _rank(data: np.ndarray) -> np.ndarray:
        """Rank values (percentile)."""
        valid_mask = ~np.isnan(data)
        result = np.full_like(data, np.nan, dtype=float)
        if not np.any(valid_mask):
            return result
        valid_data = data[valid_mask]
        ranks = np.argsort(np.argsort(valid_data)) / (len(valid_data) - 1)
        result[valid_mask] = ranks
        return result
    
    @staticmethod
    def _delta(data: np.ndarray, period: int = 1) -> np.ndarray:
        """Difference from N periods ago."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) <= period:
            return result
        result[period:] = data[period:] - data[:-period]
        return result
    
    @staticmethod
    def _pct_change(data: np.ndarray, period: int = 1) -> np.ndarray:
        """Percentage change from N periods ago."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) <= period:
            return result
        result[period:] = (data[period:] - data[:-period]) / data[:-period]
        return result
    
    @staticmethod
    def _diff(data: np.ndarray, n: int = 1) -> np.ndarray:
        """First discrete difference."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) <= n:
            return result
        result[n:] = np.diff(data, n=n)
        return result
    
    @staticmethod
    def _shift(data: np.ndarray, periods: int) -> np.ndarray:
        """Shift data by N periods."""
        result = np.full_like(data, np.nan, dtype=float)
        if periods > 0:
            if len(data) > periods:
                result[periods:] = data[:-periods]
        elif periods < 0:
            if len(data) > abs(periods):
                result[:periods] = data[-periods:]
        else:
            result[:] = data
        return result
    
    @staticmethod
    def _cumsum(data: np.ndarray) -> np.ndarray:
        """Cumulative sum."""
        result = np.full_like(data, np.nan, dtype=float)
        valid_mask = ~np.isnan(data)
        if not np.any(valid_mask):
            return result
        cumsum = np.cumsum(data[valid_mask])
        result[valid_mask] = cumsum
        return result
    
    @staticmethod
    def _cumprod(data: np.ndarray) -> np.ndarray:
        """Cumulative product."""
        result = np.full_like(data, np.nan, dtype=float)
        valid_mask = ~np.isnan(data)
        if not np.any(valid_mask):
            return result
        cumprod = np.cumprod(data[valid_mask])
        result[valid_mask] = cumprod
        return result
    
    @staticmethod
    def _cummax(data: np.ndarray) -> np.ndarray:
        """Cumulative maximum."""
        result = np.full_like(data, np.nan, dtype=float)
        valid_mask = ~np.isnan(data)
        if not np.any(valid_mask):
            return result
        cummax = np.maximum.accumulate(data[valid_mask])
        result[valid_mask] = cummax
        return result
    
    @staticmethod
    def _cummin(data: np.ndarray) -> np.ndarray:
        """Cumulative minimum."""
        result = np.full_like(data, np.nan, dtype=float)
        valid_mask = ~np.isnan(data)
        if not np.any(valid_mask):
            return result
        cummin = np.minimum.accumulate(data[valid_mask])
        result[valid_mask] = cummin
        return result
    
    @staticmethod
    def _rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) < period + 1:
            return result
        
        delta = np.diff(close)
        gains = np.where(delta > 0, delta, 0)
        losses = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.zeros(len(delta))
        avg_loss = np.zeros(len(delta))
        
        avg_gain[period-1] = np.mean(gains[:period])
        avg_loss[period-1] = np.mean(losses[:period])
        
        for i in range(period, len(delta)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i]) / period
        
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 0)
        rsi_values = 100 - (100 / (1 + rs))
        
        result[period:] = rsi_values[period-1:]
        return result
    
    @staticmethod
    def _macd(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """MACD indicator."""
        ema_fast = FunctionRegistry._ema(close, fast)
        ema_slow = FunctionRegistry._ema(close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = FunctionRegistry._ema(macd_line[~np.isnan(macd_line)], signal)
        
        result_signal = np.full_like(close, np.nan, dtype=float)
        valid_start = np.where(~np.isnan(macd_line))[0]
        if len(valid_start) > signal - 1:
            result_signal[valid_start[signal-1]:] = signal_line
        
        hist = macd_line - result_signal
        return macd_line, result_signal, hist
    
    @staticmethod
    def _kdj(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
             n: int = 9, m1: int = 3, m2: int = 3) -> tuple:
        """KDJ indicator."""
        k = np.full_like(close, np.nan, dtype=float)
        d = np.full_like(close, np.nan, dtype=float)
        j = np.full_like(close, np.nan, dtype=float)
        
        if len(close) < n:
            return k, d, j
        
        lowest_low = np.zeros(len(close))
        highest_high = np.zeros(len(close))
        
        for i in range(n - 1, len(close)):
            lowest_low[i] = np.min(low[i-n+1:i+1])
            highest_high[i] = np.max(high[i-n+1:i+1])
        
        rsv = np.where(highest_high != lowest_low,
                       (close - lowest_low) / (highest_high - lowest_low) * 100,
                       50)
        
        alpha1, alpha2 = 1 / m1, 1 / m2
        k[n-1] = 50
        d[n-1] = 50
        
        for i in range(n, len(close)):
            k[i] = alpha1 * rsv[i] + (1 - alpha1) * k[i-1]
            d[i] = alpha2 * k[i] + (1 - alpha2) * d[i-1]
        
        j = 3 * k - 2 * d
        return k, d, j
    
    @staticmethod
    def _boll(close: np.ndarray, period: int = 20, std_dev: float = 2.0) -> tuple:
        """Bollinger Bands."""
        middle = FunctionRegistry._sma(close, period)
        std = FunctionRegistry._std(close, period)
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower
    
    @staticmethod
    def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) < period + 1:
            return result
        
        prev_close = np.concatenate([[np.nan], close[:-1]])
        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - prev_close),
                np.abs(low - prev_close)
            )
        )
        
        result[period] = np.mean(tr[1:period+1])
        for i in range(period + 1, len(close)):
            result[i] = (result[i-1] * (period - 1) + tr[i]) / period
        
        return result
    
    @staticmethod
    def _obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """On-Balance Volume."""
        result = np.zeros_like(close, dtype=float)
        if len(close) < 2:
            return result
        
        direction = np.sign(np.diff(close))
        direction = np.concatenate([[0], direction])
        result = np.cumsum(direction * volume)
        return result
    
    @staticmethod
    def _cci(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 20) -> np.ndarray:
        """Commodity Channel Index."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) < period:
            return result
        
        tp = (high + low + close) / 3
        sma_tp = FunctionRegistry._sma(tp, period)
        
        for i in range(period - 1, len(close)):
            mean_dev = np.mean(np.abs(tp[i-period+1:i+1] - sma_tp[i]))
            if mean_dev != 0:
                result[i] = (tp[i] - sma_tp[i]) / (0.015 * mean_dev)
        
        return result
    
    @staticmethod
    def _wr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
        """Williams %R."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) < period:
            return result
        
        for i in range(period - 1, len(close)):
            highest = np.max(high[i-period+1:i+1])
            lowest = np.min(low[i-period+1:i+1])
            if highest != lowest:
                result[i] = (highest - close[i]) / (highest - lowest) * -100
        
        return result
    
    @staticmethod
    def _ad(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
        """Accumulation/Distribution Line."""
        result = np.zeros_like(close, dtype=float)
        if len(close) < 1:
            return result
        
        for i in range(len(close)):
            if high[i] != low[i]:
                clv = ((close[i] - low[i]) - (high[i] - close[i])) / (high[i] - low[i])
            else:
                clv = 0
            result[i] = result[i-1] + clv * volume[i] if i > 0 else clv * volume[i]
        
        return result
    
    @staticmethod
    def _mfi(high: np.ndarray, low: np.ndarray, close: np.ndarray, 
             volume: np.ndarray, period: int = 14) -> np.ndarray:
        """Money Flow Index."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) < period + 1:
            return result
        
        tp = (high + low + close) / 3
        mf = tp * volume
        
        positive_mf = np.zeros_like(close)
        negative_mf = np.zeros_like(close)
        
        for i in range(1, len(close)):
            if tp[i] > tp[i-1]:
                positive_mf[i] = mf[i]
            elif tp[i] < tp[i-1]:
                negative_mf[i] = mf[i]
        
        for i in range(period, len(close)):
            pos_sum = np.sum(positive_mf[i-period+1:i+1])
            neg_sum = np.sum(negative_mf[i-period+1:i+1])
            if pos_sum + neg_sum != 0:
                result[i] = 100 * pos_sum / (pos_sum + neg_sum)
        
        return result
    
    @staticmethod
    def _roc(close: np.ndarray, period: int = 12) -> np.ndarray:
        """Rate of Change."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) <= period:
            return result
        result[period:] = (close[period:] - close[:-period]) / close[:-period] * 100
        return result
    
    @staticmethod
    def _momentum(close: np.ndarray, period: int = 10) -> np.ndarray:
        """Momentum indicator."""
        result = np.full_like(close, np.nan, dtype=float)
        if len(close) <= period:
            return result
        result[period:] = close[period:] - close[:-period]
        return result
    
    @staticmethod
    def _volatility(close: np.ndarray, period: int = 20, annualize: bool = True) -> np.ndarray:
        """Historical Volatility."""
        returns = np.full_like(close, np.nan, dtype=float)
        returns[1:] = np.diff(close) / close[:-1]
        
        result = FunctionRegistry._std(returns, period)
        if annualize:
            result = result * np.sqrt(252)
        return result
    
    @staticmethod
    def _skewness(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling Skewness."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            window = window[~np.isnan(window)]
            if len(window) >= 3:
                mean = np.mean(window)
                std = np.std(window)
                if std > 0:
                    result[i] = np.mean(((window - mean) / std) ** 3)
        
        return result
    
    @staticmethod
    def _kurtosis(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling Kurtosis."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            window = window[~np.isnan(window)]
            if len(window) >= 4:
                mean = np.mean(window)
                std = np.std(window)
                if std > 0:
                    result[i] = np.mean(((window - mean) / std) ** 4) - 3
        
        return result
    
    @staticmethod
    def _zscore(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling Z-Score."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            mean = np.mean(window)
            std = np.std(window)
            if std > 0:
                result[i] = (data[i] - mean) / std
        
        return result
    
    @staticmethod
    def _normalize(data: np.ndarray, period: int = 20) -> np.ndarray:
        """Normalize to 0-1 range."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            min_val = np.min(window)
            max_val = np.max(window)
            if max_val != min_val:
                result[i] = (data[i] - min_val) / (max_val - min_val)
        
        return result
    
    @staticmethod
    def _winsorize(data: np.ndarray, lower: float = 0.01, upper: float = 0.99) -> np.ndarray:
        """Winsorize data."""
        result = data.copy()
        valid_mask = ~np.isnan(data)
        if not np.any(valid_mask):
            return result
        
        valid_data = data[valid_mask]
        lower_bound = np.quantile(valid_data, lower)
        upper_bound = np.quantile(valid_data, upper)
        
        result = np.clip(result, lower_bound, upper_bound)
        return result
    
    @staticmethod
    def _quantile(data: np.ndarray, q: float, period: int = 20) -> np.ndarray:
        """Rolling Quantile."""
        result = np.full_like(data, np.nan, dtype=float)
        if len(data) < period:
            return result
        
        for i in range(period - 1, len(data)):
            window = data[i-period+1:i+1]
            window = window[~np.isnan(window)]
            if len(window) > 0:
                result[i] = np.quantile(window, q)
        
        return result
    
    @staticmethod
    def _corr(x: np.ndarray, y: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling Correlation."""
        result = np.full_like(x, np.nan, dtype=float)
        if len(x) < period:
            return result
        
        for i in range(period - 1, len(x)):
            x_window = x[i-period+1:i+1]
            y_window = y[i-period+1:i+1]
            valid_mask = ~np.isnan(x_window) & ~np.isnan(y_window)
            if np.sum(valid_mask) >= 2:
                result[i] = np.corrcoef(x_window[valid_mask], y_window[valid_mask])[0, 1]
        
        return result
    
    @staticmethod
    def _cov(x: np.ndarray, y: np.ndarray, period: int = 20) -> np.ndarray:
        """Rolling Covariance."""
        result = np.full_like(x, np.nan, dtype=float)
        if len(x) < period:
            return result
        
        for i in range(period - 1, len(x)):
            x_window = x[i-period+1:i+1]
            y_window = y[i-period+1:i+1]
            valid_mask = ~np.isnan(x_window) & ~np.isnan(y_window)
            if np.sum(valid_mask) >= 2:
                result[i] = np.cov(x_window[valid_mask], y_window[valid_mask])[0, 1]
        
        return result
    
    @staticmethod
    def _beta(stock_returns: np.ndarray, market_returns: np.ndarray, period: int = 60) -> np.ndarray:
        """Rolling Beta."""
        result = np.full_like(stock_returns, np.nan, dtype=float)
        if len(stock_returns) < period:
            return result
        
        for i in range(period - 1, len(stock_returns)):
            stock_window = stock_returns[i-period+1:i+1]
            market_window = market_returns[i-period+1:i+1]
            valid_mask = ~np.isnan(stock_window) & ~np.isnan(market_window)
            if np.sum(valid_mask) >= 2:
                cov = np.cov(stock_window[valid_mask], market_window[valid_mask])[0, 1]
                var = np.var(market_window[valid_mask])
                if var > 0:
                    result[i] = cov / var
        
        return result
    
    @staticmethod
    def _alpha(stock_returns: np.ndarray, market_returns: np.ndarray, 
               risk_free: float = 0.0, period: int = 60) -> np.ndarray:
        """Rolling Jensen's Alpha."""
        beta = FunctionRegistry._beta(stock_returns, market_returns, period)
        mean_stock = FunctionRegistry._sma(stock_returns, period)
        mean_market = FunctionRegistry._sma(market_returns, period)
        
        result = mean_stock - (risk_free + beta * (mean_market - risk_free))
        return result
    
    @staticmethod
    def _sharpe(returns: np.ndarray, risk_free: float = 0.0, period: int = 60) -> np.ndarray:
        """Rolling Sharpe Ratio."""
        mean_ret = FunctionRegistry._sma(returns, period)
        std_ret = FunctionRegistry._std(returns, period)
        
        result = np.full_like(returns, np.nan, dtype=float)
        valid_mask = ~np.isnan(mean_ret) & ~np.isnan(std_ret) & (std_ret > 0)
        result[valid_mask] = (mean_ret[valid_mask] - risk_free) / std_ret[valid_mask]
        return result
    
    @staticmethod
    def _sortino(returns: np.ndarray, risk_free: float = 0.0, period: int = 60) -> np.ndarray:
        """Rolling Sortino Ratio."""
        result = np.full_like(returns, np.nan, dtype=float)
        if len(returns) < period:
            return result
        
        for i in range(period - 1, len(returns)):
            window = returns[i-period+1:i+1]
            valid_mask = ~np.isnan(window)
            if np.sum(valid_mask) >= 2:
                valid_returns = window[valid_mask]
                mean_ret = np.mean(valid_returns)
                downside = valid_returns[valid_returns < 0]
                if len(downside) > 0:
                    downside_std = np.sqrt(np.mean(downside ** 2))
                    if downside_std > 0:
                        result[i] = (mean_ret - risk_free) / downside_std
        
        return result
    
    @staticmethod
    def _max_drawdown(equity: np.ndarray, period: int = 60) -> np.ndarray:
        """Rolling Maximum Drawdown."""
        result = np.full_like(equity, np.nan, dtype=float)
        if len(equity) < period:
            return result
        
        for i in range(period - 1, len(equity)):
            window = equity[i-period+1:i+1]
            valid_mask = ~np.isnan(window)
            if np.sum(valid_mask) >= 2:
                valid_equity = window[valid_mask]
                cummax = np.maximum.accumulate(valid_equity)
                drawdown = (cummax - valid_equity) / cummax
                result[i] = np.max(drawdown)
        
        return result
    
    @staticmethod
    def _calmar(returns: np.ndarray, equity: np.ndarray, period: int = 60) -> np.ndarray:
        """Rolling Calmar Ratio."""
        annual_return = FunctionRegistry._sma(returns, period) * 252
        max_dd = FunctionRegistry._max_drawdown(equity, period)
        
        result = np.full_like(returns, np.nan, dtype=float)
        valid_mask = ~np.isnan(annual_return) & ~np.isnan(max_dd) & (max_dd > 0)
        result[valid_mask] = annual_return[valid_mask] / max_dd[valid_mask]
        return result
    
    @staticmethod
    def _if_else(condition: np.ndarray, true_val: np.ndarray, false_val: np.ndarray) -> np.ndarray:
        """Conditional selection."""
        return np.where(condition, true_val, false_val)


class ExpressionParser:
    """Parser for factor expressions."""
    
    ALLOWED_NAMES = {
        'open', 'high', 'low', 'close', 'volume', 'amount', 'pre_close',
        'vwap', 'returns', 'log_returns',
        'true', 'false', 'True', 'False', 'None',
        'and', 'or', 'not', 'in', 'is',
    }
    
    def __init__(self):
        self._function_registry = FunctionRegistry()
    
    def parse(self, expression: str) -> ParsedExpression:
        """Parse a factor expression."""
        result = ParsedExpression(raw=expression)
        
        try:
            tree = ast.parse(expression, mode='eval')
            result.ast_tree = tree
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    name = node.id
                    if name in self._function_registry.list_functions():
                        if name not in result.functions:
                            result.functions.append(name)
                    elif name not in self.ALLOWED_NAMES:
                        result.dependencies.append(name)
            
            result.is_valid = True
            
        except SyntaxError as e:
            result.error = f"Syntax error: {e}"
        except Exception as e:
            result.error = f"Parse error: {e}"
        
        return result
    
    def validate(self, expression: str) -> tuple[bool, str]:
        """Validate an expression."""
        parsed = self.parse(expression)
        
        if not parsed.is_valid:
            return False, parsed.error or "Invalid expression"
        
        for dep in parsed.dependencies:
            if dep not in self.ALLOWED_NAMES:
                return False, f"Unknown variable: {dep}"
        
        return True, "Valid"


class ExpressionEvaluator:
    """Evaluator for factor expressions."""
    
    def __init__(self):
        self._function_registry = FunctionRegistry()
        self._parser = ExpressionParser()
    
    def evaluate(
        self,
        expression: str,
        context: ExpressionContext,
        parameters: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """
        Evaluate a factor expression.
        
        Args:
            expression: Factor expression string
            context: Evaluation context with OHLCV data
            parameters: Additional parameters
        
        Returns:
            Calculated factor values as numpy array
        """
        parsed = self._parser.parse(expression)
        if not parsed.is_valid:
            raise ValueError(f"Invalid expression: {parsed.error}")
        
        local_vars = {
            'open': context.open,
            'high': context.high,
            'low': context.low,
            'close': context.close,
            'volume': context.volume,
            'amount': context.amount,
            'pre_close': context.pre_close,
            'vwap': context.vwap,
            'returns': context.returns,
            'log_returns': context.log_returns,
            'np': np,
            'nan': np.nan,
            'inf': np.inf,
            'True': True,
            'False': False,
            'None': None,
        }
        
        for func_name in self._function_registry.list_functions():
            local_vars[func_name] = self._function_registry.get(func_name)
        
        if parameters:
            local_vars.update(parameters)
        
        result = eval(expression, {"__builtins__": {}}, local_vars)
        
        if isinstance(result, (int, float)):
            result = np.full(len(context.close), result, dtype=float)
        
        return np.asarray(result, dtype=float)


class FactorExpressionEngine:
    """
    Main engine for factor expression management.
    
    Provides a complete solution for:
    - Expression parsing and validation
    - Dynamic function registration
    - Factor calculation from OHLCV data
    - Real-time factor updates
    """
    
    def __init__(self):
        self._parser = ExpressionParser()
        self._evaluator = ExpressionEvaluator()
        self._function_registry = FunctionRegistry()
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function."""
        self._function_registry.register(name, func)
    
    def parse(self, expression: str) -> ParsedExpression:
        """Parse a factor expression."""
        return self._parser.parse(expression)
    
    def validate(self, expression: str) -> tuple[bool, str]:
        """Validate a factor expression."""
        return self._parser.validate(expression)
    
    def calculate(
        self,
        expression: str,
        klines: list[ADSKLineModel],
        parameters: dict[str, Any] | None = None,
    ) -> np.ndarray:
        """
        Calculate factor values from K-Line data.
        
        Args:
            expression: Factor expression
            klines: List of K-Line data
            parameters: Additional parameters
        
        Returns:
            Factor values as numpy array
        """
        if not klines:
            raise ValueError("No K-Line data provided")
        
        open_arr = np.array([k.open for k in klines], dtype=float)
        high_arr = np.array([k.high for k in klines], dtype=float)
        low_arr = np.array([k.low for k in klines], dtype=float)
        close_arr = np.array([k.close for k in klines], dtype=float)
        volume_arr = np.array([k.volume for k in klines], dtype=float)
        
        amount_arr = None
        pre_close_arr = None
        if hasattr(klines[0], 'amount'):
            amount_arr = np.array([k.amount for k in klines], dtype=float)
        if hasattr(klines[0], 'pre_close'):
            pre_close_arr = np.array([k.pre_close for k in klines], dtype=float)
        
        vwap_arr = np.where(volume_arr > 0, amount_arr / volume_arr, close_arr) if amount_arr is not None else None
        returns_arr = np.concatenate([[np.nan], np.diff(close_arr) / close_arr[:-1]])
        log_returns_arr = np.concatenate([[np.nan], np.log(close_arr[1:] / close_arr[:-1])])
        
        context = ExpressionContext(
            open=open_arr,
            high=high_arr,
            low=low_arr,
            close=close_arr,
            volume=volume_arr,
            amount=amount_arr,
            pre_close=pre_close_arr,
            vwap=vwap_arr,
            returns=returns_arr,
            log_returns=log_returns_arr,
            trade_date=klines[-1].trade_date if klines else None,
            code=klines[-1].code if klines else None,
        )
        
        return self._evaluator.evaluate(expression, context, parameters)
    
    def list_functions(self) -> list[str]:
        """List all available functions."""
        return self._function_registry.list_functions()
    
    def get_function_info(self, name: str) -> dict[str, Any]:
        """Get information about a function."""
        func = self._function_registry.get(name)
        if func is None:
            return {}
        
        return {
            'name': name,
            'docstring': func.__doc__ or '',
            'signature': str(func.__code__.co_varnames) if hasattr(func, '__code__') else '',
        }


_engine_instance: FactorExpressionEngine | None = None


def get_expression_engine() -> FactorExpressionEngine:
    """Get the global expression engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = FactorExpressionEngine()
    return _engine_instance
