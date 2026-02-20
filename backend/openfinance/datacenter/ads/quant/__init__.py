"""
Quantitative Data Models.

Provides ADS models for quantitative analysis data:
- Factor data
- Trading signals
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from openfinance.datacenter.ads.base import (
    ADSModel,
    ADSModelWithCode,
    ADSModelWithDate,
    DataQuality,
)


class ADSFactorModel(ADSModelWithCode, ADSModelWithDate):
    """
    Factor data model.
    
    Standardized factor data structure for quantitative analysis.
    
    Field Naming Convention:
    - value: Raw factor value
    - value_normalized: Standardized value (z-score)
    - value_rank: Rank in universe
    - value_percentile: Percentile in universe
    """
    
    factor_id: str = Field(..., description="Factor identifier (must start with 'factor_')")
    factor_name: str | None = Field(None, description="Factor display name")
    factor_type: str = Field(..., description="Factor type: value/momentum/quality/volatility/etc")
    factor_category: str | None = Field(None, description="Factor category for grouping")
    
    value: float | None = Field(None, description="Raw factor value")
    value_normalized: float | None = Field(None, description="Standardized value (z-score)")
    value_rank: int | None = Field(None, description="Rank in universe")
    value_percentile: float | None = Field(None, description="Percentile (0-100)")
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Factor calculation parameters"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Required data fields for calculation"
    )
    
    neutralized: bool = Field(default=False, description="Whether neutralized")
    neutralization_method: str | None = Field(None, description="Neutralization method")
    
    calculated_at: datetime | None = Field(None, description="Calculation timestamp")
    
    @field_validator("factor_id")
    @classmethod
    def validate_factor_id(cls, v: str) -> str:
        if not v.startswith("factor_"):
            raise ValueError(f"Factor ID must start with 'factor_': {v}")
        return v
    
    @field_validator("factor_type")
    @classmethod
    def validate_factor_type(cls, v: str) -> str:
        valid_types = {
            "value", "momentum", "quality", "volatility",
            "growth", "size", "liquidity", "technical",
            "sentiment", "fundamental", "alternative"
        }
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid factor type: {v}")
        return v.lower()
    
    @property
    def is_top_decile(self) -> bool:
        """Check if factor is in top decile."""
        return self.value_percentile is not None and self.value_percentile >= 90
    
    @property
    def is_bottom_decile(self) -> bool:
        """Check if factor is in bottom decile."""
        return self.value_percentile is not None and self.value_percentile <= 10


class ADSSignalModel(ADSModelWithCode, ADSModelWithDate):
    """
    Trading signal data model.
    
    Standardized trading signal structure.
    """
    
    signal_id: str = Field(..., description="Unique signal identifier")
    strategy_id: str = Field(..., description="Strategy that generated this signal")
    
    signal_type: str = Field(..., description="Signal type: long/short/neutral")
    signal_strength: float = Field(
        ...,
        description="Signal strength [-1, 1]",
        ge=-1,
        le=1
    )
    
    target_weight: float | None = Field(None, description="Target portfolio weight")
    target_price: float | None = Field(None, description="Target price")
    stop_loss: float | None = Field(None, description="Stop loss price")
    take_profit: float | None = Field(None, description="Take profit price")
    
    factors: dict[str, float] = Field(
        default_factory=dict,
        description="Contributing factors and their values"
    )
    factor_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Factor weights used in signal generation"
    )
    
    confidence: float = Field(
        default=0.5,
        description="Signal confidence [0, 1]",
        ge=0,
        le=1
    )
    
    expected_return: float | None = Field(None, description="Expected return")
    expected_risk: float | None = Field(None, description="Expected risk/volatility")
    sharpe_ratio: float | None = Field(None, description="Expected Sharpe ratio")
    
    holding_period: int | None = Field(None, description="Expected holding period (days)")
    
    generated_at: datetime | None = Field(None, description="Signal generation time")
    expires_at: datetime | None = Field(None, description="Signal expiration time")
    
    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        valid_types = {"long", "short", "neutral", "buy", "sell", "hold"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid signal type: {v}")
        return v.lower()
    
    @property
    def is_long(self) -> bool:
        """Check if this is a long signal."""
        return self.signal_type in ("long", "buy")
    
    @property
    def is_short(self) -> bool:
        """Check if this is a short signal."""
        return self.signal_type in ("short", "sell")
    
    @property
    def is_actionable(self) -> bool:
        """Check if signal is actionable."""
        return (
            self.confidence >= 0.3
            and abs(self.signal_strength) >= 0.2
            and (self.expires_at is None or self.expires_at > datetime.now())
        )


class ADSBacktestResultModel(ADSModel):
    """
    Backtest result data model.
    
    Standardized backtest performance metrics.
    """
    
    backtest_id: str = Field(..., description="Backtest identifier")
    strategy_id: str = Field(..., description="Strategy identifier")
    
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    
    total_return: float | None = Field(None, description="Total return")
    annual_return: float | None = Field(None, description="Annualized return")
    benchmark_return: float | None = Field(None, description="Benchmark return")
    excess_return: float | None = Field(None, description="Excess return vs benchmark")
    
    volatility: float | None = Field(None, description="Annualized volatility")
    max_drawdown: float | None = Field(None, description="Maximum drawdown")
    sharpe_ratio: float | None = Field(None, description="Sharpe ratio")
    sortino_ratio: float | None = Field(None, description="Sortino ratio")
    calmar_ratio: float | None = Field(None, description="Calmar ratio")
    
    win_rate: float | None = Field(None, description="Win rate")
    profit_loss_ratio: float | None = Field(None, description="Profit/Loss ratio")
    
    turnover: float | None = Field(None, description="Annual turnover rate")
    transaction_costs: float | None = Field(None, description="Total transaction costs")
    
    trade_count: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Backtest parameters"
    )
    
    @property
    def is_profitable(self) -> bool | None:
        """Check if strategy was profitable."""
        if self.total_return is not None:
            return self.total_return > 0
        return None
    
    @property
    def beat_benchmark(self) -> bool | None:
        """Check if strategy beat benchmark."""
        if self.excess_return is not None:
            return self.excess_return > 0
        return None
