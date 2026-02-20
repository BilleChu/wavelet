"""
Base strategy module for OpenFinance quantitative system.

Defines the abstract base class and interfaces for all strategy implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class StrategyType:
    """Strategy type constants."""
    SINGLE_FACTOR = "single_factor"
    MULTI_FACTOR = "multi_factor"
    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"


class WeightMethod:
    """Portfolio weighting method constants."""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MEAN_VARIANCE = "mean_variance"
    BLACK_LITTERMAN = "black_litterman"
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"
    CUSTOM = "custom"


class RebalanceFrequency:
    """Rebalancing frequency constants."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class SignalType:
    """Signal type constants."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class StrategyMetadata:
    """Strategy metadata."""
    strategy_id: str
    name: str
    description: str = ""
    strategy_type: str = StrategyType.SINGLE_FACTOR
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    factor_ids: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=list)
    min_data_points: int = 30


@dataclass
class StrategyConfig:
    """Strategy configuration."""
    max_positions: int = 50
    position_size: float = 0.02
    stop_loss: float | None = None
    take_profit: float | None = None
    rebalance_freq: str = RebalanceFrequency.MONTHLY
    weight_method: str = WeightMethod.EQUAL_WEIGHT
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategySignal:
    """Trading signal."""
    stock_code: str
    signal_type: str
    strength: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    """Strategy execution result."""
    strategy_id: str
    signals: list[StrategySignal]
    weights: dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    All strategy implementations must inherit from this class
    and implement the required methods.
    
    Attributes:
        strategy_id: Unique identifier for the strategy
        name: Human-readable strategy name
        code: Strategy code/symbol
        description: Strategy description
        strategy_type: Type of strategy
        factors: List of factor IDs used by strategy
        factor_weights: Dictionary of factor weights
        weight_method: Method for calculating portfolio weights
        rebalance_freq: How often to rebalance
        max_positions: Maximum number of positions
        stop_loss: Stop loss threshold (optional)
        take_profit: Take profit threshold (optional)
        parameters: Strategy-specific parameters
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        strategy_id: str,
        name: str,
        code: str,
        description: str = "",
        strategy_type: str = StrategyType.SINGLE_FACTOR,
        factors: Optional[list[str]] = None,
        factor_weights: Optional[dict[str, float]] = None,
        weight_method: str = WeightMethod.EQUAL_WEIGHT,
        rebalance_freq: str = RebalanceFrequency.MONTHLY,
        max_positions: int = 100,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        parameters: Optional[dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.strategy_id = strategy_id
        self.name = name
        self.code = code
        self.description = description
        self.strategy_type = strategy_type
        self.factors = factors or []
        self.factor_weights = factor_weights or {}
        self.weight_method = weight_method
        self.rebalance_freq = rebalance_freq
        self.max_positions = max_positions
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.parameters = parameters or {}
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
        self.metadata = StrategyMetadata(
            strategy_id=self.strategy_id,
            name=self.name,
            description=self.description,
            strategy_type=self.strategy_type,
            factor_ids=self.factors,
        )
        
        self._validate()
    
    @abstractmethod
    def generate_signals(
        self,
        data: dict[str, pd.DataFrame],
        factor_values: Optional[dict[str, pd.DataFrame]] = None,
        date: Optional[datetime] = None,
    ) -> dict[str, float]:
        """
        Generate trading signals for current date.
        
        Args:
            data: Dictionary of DataFrames with market data
                  Keys are stock codes, values are OHLCV data
            factor_values: Dictionary of factor values by stock
            date: Current trading date
        
        Returns:
            Dictionary mapping stock_code to signal strength (-1 to 1)
            where:
              -1.0 = strong sell
              -0.5 = weak sell
               0.0 = neutral
              +0.5 = weak buy
              +1.0 = strong buy
        """
        pass
    
    @abstractmethod
    def calculate_portfolio_weights(
        self,
        signals: dict[str, float],
        prices: pd.DataFrame,
        covariance_matrix: Optional[pd.DataFrame] = None,
    ) -> dict[str, float]:
        """
        Calculate optimal portfolio weights based on signals.
        
        Args:
            signals: Trading signals from generate_signals()
            prices: Current prices DataFrame
            covariance_matrix: Asset return covariance matrix
        
        Returns:
            Dictionary mapping stock_code to target weight (0 to 1)
        """
        pass
    
    def _validate(self) -> None:
        """Validate strategy configuration."""
        if not self.strategy_id:
            raise ValueError("strategy_id is required")
        if not self.name:
            raise ValueError("name is required")
        if not self.code:
            raise ValueError("code is required")
        if self.max_positions < 1:
            raise ValueError("max_positions must be >= 1")
        
        # Validate factor weights sum to 1 (if provided)
        if self.factor_weights:
            total_weight = sum(self.factor_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(
                    f"Factor weights sum to {total_weight}, not 1.0. "
                    "Weights will be normalized."
                )
    
    def get_signal_names(self) -> list[str]:
        """Get names of signals used by this strategy."""
        return [f"signal_{factor}" for factor in self.factors]
    
    def get_description(self) -> str:
        """Get strategy description with parameters."""
        desc = f"{self.description}\n\n"
        desc += f"Type: {self.strategy_type}\n"
        desc += f"Factors: {', '.join(self.factors)}\n"
        desc += f"Weight Method: {self.weight_method}\n"
        desc += f"Rebalance: {self.rebalance_freq}\n"
        desc += f"Max Positions: {self.max_positions}\n"
        
        if self.parameters:
            desc += "\nParameters:\n"
            for key, value in self.parameters.items():
                desc += f"  - {key}: {value}\n"
        
        return desc
    
    def to_dict(self) -> dict[str, Any]:
        """Convert strategy to dictionary representation."""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "factors": self.factors,
            "factor_weights": self.factor_weights,
            "weight_method": self.weight_method,
            "rebalance_freq": self.rebalance_freq,
            "max_positions": self.max_positions,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(strategy_id='{self.strategy_id}', name='{self.name}')"


class SignalGenerator:
    """
    Helper class for generating and processing trading signals.
    
    Provides common signal processing utilities used by strategies.
    """
    
    @staticmethod
    def normalize_signals(
        signals: dict[str, float],
        method: str = "zscore",
    ) -> dict[str, float]:
        """
        Normalize signals to standard range.
        
        Args:
            signals: Raw signals
            method: Normalization method ('zscore', 'minmax', 'rank')
        
        Returns:
            Normalized signals
        """
        import numpy as np
        
        values = list(signals.values())
        
        if method == "zscore":
            mean = np.mean(values)
            std = np.std(values)
            if std > 0:
                return {k: (v - mean) / std for k, v in signals.items()}
            return {k: 0.0 for k in signals.keys()}
        
        elif method == "minmax":
            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val
            if range_val > 0:
                return {k: (v - min_val) / range_val for k, v in signals.items()}
            return {k: 0.5 for k in signals.keys()}
        
        elif method == "rank":
            sorted_keys = sorted(signals.keys(), key=lambda k: signals[k])
            n = len(sorted_keys)
            return {k: i / (n - 1) if n > 1 else 0.5 for i, k in enumerate(sorted_keys)}
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
    
    @staticmethod
    def apply_threshold(
        signals: dict[str, float],
        buy_threshold: float = 0.5,
        sell_threshold: float = -0.5,
    ) -> dict[str, float]:
        """
        Apply thresholds to filter weak signals.
        
        Args:
            signals: Input signals
            buy_threshold: Minimum signal for buy
            sell_threshold: Maximum signal for sell
        
        Returns:
            Filtered signals (0 for neutral stocks)
        """
        filtered = {}
        for stock, signal in signals.items():
            if signal > buy_threshold:
                filtered[stock] = 1.0
            elif signal < sell_threshold:
                filtered[stock] = -1.0
            else:
                filtered[stock] = 0.0
        return filtered


class PortfolioConstraints:
    """
    Container for portfolio construction constraints.
    
    Attributes:
        max_position: Maximum weight for single position
        min_position: Minimum weight for selected position
        max_sector: Maximum weight for single sector
        max_turnover: Maximum turnover rate
        long_only: Whether long-only constraint applies
    """
    
    def __init__(
        self,
        max_position: float = 0.10,
        min_position: float = 0.01,
        max_sector: Optional[float] = None,
        max_turnover: Optional[float] = None,
        long_only: bool = True,
    ):
        self.max_position = max_position
        self.min_position = min_position
        self.max_sector = max_sector
        self.max_turnover = max_turnover
        self.long_only = long_only
    
    def apply_constraints(
        self,
        target_weights: dict[str, float],
        current_weights: Optional[dict[str, float]] = None,
        sectors: Optional[dict[str, str]] = None,
    ) -> dict[str, float]:
        """
        Apply constraints to target weights.
        
        Args:
            target_weights: Raw target weights
            current_weights: Current portfolio weights
            sectors: Stock to sector mapping
        
        Returns:
            Constrained weights
        """
        constrained = target_weights.copy()
        
        # Apply max position constraint
        for stock in constrained:
            constrained[stock] = min(constrained[stock], self.max_position)
            if self.long_only:
                constrained[stock] = max(constrained[stock], 0.0)
            else:
                constrained[stock] = max(constrained[stock], -self.max_position)
        
        # Apply sector constraint if provided
        if self.max_sector and sectors:
            sector_weights: dict[str, float] = {}
            for stock, weight in constrained.items():
                sector = sectors.get(stock, "unknown")
                sector_weights[sector] = sector_weights.get(sector, 0.0) + weight
            
            # Reduce overweighted sectors
            for sector, total_weight in sector_weights.items():
                if total_weight > self.max_sector:
                    reduction_factor = self.max_sector / total_weight
                    for stock, weight in constrained.items():
                        if sectors.get(stock) == sector:
                            constrained[stock] *= reduction_factor
        
        # Normalize to sum to 1
        total = sum(abs(w) for w in constrained.values())
        if total > 0:
            constrained = {k: v / total for k, v in constrained.items()}
        
        return constrained
