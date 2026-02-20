"""
Technical Indicators Package.

All indicators are calculated from K-Line base data (OHLCV) only.
Each indicator exports:
- calculate_xxx(klines, ...): Calculate from K-Line data
- xxx(array, ...): Calculate from numpy arrays
- XXXFactor: Factor class for registry integration
"""

from .ma import sma, ema, wma, calculate_sma, calculate_ema, SMAFactor, EMAFactor
from .macd import macd, calculate_macd, MACDFactor, MACDValues
from .boll import boll, calculate_boll, BOLLFactor, BOLLValues
from .atr import atr, calculate_atr, true_range, ATRFactor, ATRValues
from .cci import cci, calculate_cci, CCIFactor, CCIValues
from .wr import wr, calculate_wr, WRFactor, WRValues
from .obv import obv, calculate_obv, OBVFactor, OBVValues
from .rsi import calculate_rsi, RSIFactor
from .kdj import calculate_kdj, kdj, KDJFactor, KDJValues

import importlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_custom_factors_loaded = False

def load_custom_factors():
    """Load all custom factors from the custom directory."""
    global _custom_factors_loaded
    
    if _custom_factors_loaded:
        return
    
    custom_dir = Path(__file__).parent / "custom"
    if not custom_dir.exists():
        custom_dir.mkdir(parents=True, exist_ok=True)
        _custom_factors_loaded = True
        return
    
    for factor_file in custom_dir.glob("*.py"):
        if factor_file.name.startswith("_"):
            continue
        
        module_name = factor_file.stem
        try:
            full_module_name = f"openfinance.quant.factors.indicators.custom.{module_name}"
            importlib.import_module(full_module_name)
            logger.info(f"Loaded custom factor: {module_name}")
        except Exception as e:
            logger.warning(f"Failed to load custom factor {module_name}: {e}")
    
    _custom_factors_loaded = True

load_custom_factors()

__all__ = [
    "sma", "ema", "wma", "calculate_sma", "calculate_ema", "SMAFactor", "EMAFactor",
    "macd", "calculate_macd", "MACDFactor", "MACDValues",
    "boll", "calculate_boll", "BOLLFactor", "BOLLValues",
    "atr", "calculate_atr", "true_range", "ATRFactor", "ATRValues",
    "cci", "calculate_cci", "CCIFactor", "CCIValues",
    "wr", "calculate_wr", "WRFactor", "WRValues",
    "obv", "calculate_obv", "OBVFactor", "OBVValues",
    "calculate_rsi", "RSIFactor",
    "calculate_kdj", "kdj", "KDJFactor", "KDJValues",
    "load_custom_factors",
]
