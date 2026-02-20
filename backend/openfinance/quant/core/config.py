"""
Core configuration and constants for quantitative analysis module.
"""

from enum import Enum
from typing import Any


class Frequency(str, Enum):
    """Data frequency options."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INTRADAY = "intraday"
    TICK = "tick"


class PositionSide(str, Enum):
    """Position side options."""
    
    LONG = "long"
    SHORT = "short"


class OrderStatus(str, Enum):
    """Order status options."""
    
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class BacktestMode(str, Enum):
    """Backtest execution mode."""
    
    QUICK = "quick"  # Fast approximation
    FULL = "full"    # Detailed simulation
    PAPER = "paper"  # Real-time forward testing


# Default configuration values
DEFAULT_INITIAL_CAPITAL = 1_000_000.0
DEFAULT_COMMISSION_RATE = 0.0003  # 0.03%
DEFAULT_SLIPPAGE_RATE = 0.0001    # 0.01%
DEFAULT_BENCHMARK = "000300.SH"   # CSI 300

# Risk-free rate (annualized)
RISK_FREE_RATE = 0.03  # 3%

# Trading days per year
TRADING_DAYS_PER_YEAR = 252

# Performance calculation constants
VAR_CONFIDENCE_LEVELS = [0.95, 0.99]
ROLLING_WINDOW_DEFAULT = 252  # 1 year
MONTE_CARLO_SIMULATIONS = 1000
