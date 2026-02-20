"""
Quantitative Analysis Models for OpenFinance.

Defines data structures for factor management, strategy development,
backtesting, and custom factor development.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class FactorType(str, enum.Enum):
    """Factor type enumeration."""

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"
    CUSTOM = "custom"


class FactorCategory(str, enum.Enum):
    """Factor category enumeration."""

    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VALUE = "value"
    QUALITY = "quality"
    GROWTH = "growth"
    SENTIMENT = "sentiment"
    FLOW = "flow"
    LIQUIDITY = "liquidity"
    LEVERAGE = "leverage"
    CUSTOM = "custom"


class StrategyType(str, enum.Enum):
    """Strategy type enumeration."""

    SINGLE_FACTOR = "single_factor"
    MULTI_FACTOR = "multi_factor"
    COMBO = "combo"


class WeightMethod(str, enum.Enum):
    """Portfolio weight method."""

    EQUAL = "equal"
    MARKET_CAP = "market_cap"
    RISK_PARITY = "risk_parity"
    MIN_VARIANCE = "min_variance"
    CUSTOM = "custom"


class OptimizeMethod(str, enum.Enum):
    """Optimization method."""

    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    GENETIC = "genetic"
    BAYESIAN = "bayesian"


class BacktestStatus(str, enum.Enum):
    """Backtest status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FactorStatus(str, enum.Enum):
    """Factor status."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class NormalizeMethod(str, enum.Enum):
    """Normalization methods for factor values."""

    NONE = "none"
    ZSCORE = "zscore"
    MINMAX = "minmax"
    RANK = "rank"
    PERCENTILE = "percentile"
    ROBUST = "robust"


class NeutralizationType(str, enum.Enum):
    """Neutralization types for factor values."""

    NONE = "none"
    INDUSTRY = "industry"
    MARKET_CAP = "market_cap"
    BOTH = "both"


class Factor(BaseModel):
    """Factor definition."""

    factor_id: str = Field(
        default_factory=lambda: f"factor_{uuid.uuid4().hex[:12]}",
        description="Unique factor ID",
    )
    name: str = Field(..., description="Factor name")
    code: str = Field(..., description="Factor code (unique identifier)")
    description: str = Field(default="", description="Factor description")
    factor_type: FactorType = Field(..., description="Factor type")
    category: FactorCategory = Field(..., description="Factor category")
    formula: str | None = Field(default=None, description="Factor formula/expression")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Factor parameters",
    )
    default_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Default parameter values",
    )
    lookback_period: int = Field(default=20, description="Lookback period in days")
    frequency: str = Field(default="daily", description="Calculation frequency")
    status: FactorStatus = Field(default=FactorStatus.DRAFT, description="Factor status")
    version: int = Field(default=1, description="Factor version")
    tags: list[str] = Field(default_factory=list, description="Factor tags")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )
    created_by: str | None = Field(default=None, description="Creator ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class FactorVersion(BaseModel):
    """Factor version history."""

    version_id: str = Field(
        default_factory=lambda: f"ver_{uuid.uuid4().hex[:8]}",
        description="Version ID",
    )
    factor_id: str = Field(..., description="Factor ID")
    version: int = Field(..., description="Version number")
    formula: str | None = Field(default=None, description="Formula at this version")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters at this version",
    )
    change_log: str = Field(default="", description="Change description")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    created_by: str | None = Field(default=None, description="Creator ID")


class FactorValue(BaseModel):
    """Calculated factor value."""

    factor_id: str = Field(..., description="Factor ID")
    stock_code: str = Field(..., description="Stock code")
    trade_date: datetime = Field(..., description="Trade date")
    value: float | None = Field(..., description="Factor value")
    rank: int | None = Field(default=None, description="Rank among all stocks")
    percentile: float | None = Field(default=None, description="Percentile rank")
    zscore: float | None = Field(default=None, description="Z-score normalized value")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class FactorCalculationRequest(BaseModel):
    """Request for factor calculation."""

    factor_id: str | None = Field(default=None, description="Factor ID (for existing)")
    factor_code: str | None = Field(default=None, description="Factor code")
    formula: str | None = Field(default=None, description="Custom formula")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Calculation parameters",
    )
    stock_codes: list[str] = Field(
        default_factory=list,
        description="Target stock codes (empty for all)",
    )
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    normalize: bool = Field(default=True, description="Whether to normalize")


class FactorCalculationResult(BaseModel):
    """Result of factor calculation."""

    calculation_id: str = Field(
        default_factory=lambda: f"calc_{uuid.uuid4().hex[:8]}",
        description="Calculation ID",
    )
    factor_id: str = Field(..., description="Factor ID")
    status: str = Field(default="completed", description="Calculation status")
    values: list[FactorValue] = Field(
        default_factory=list,
        description="Calculated values",
    )
    statistics: dict[str, float] = Field(
        default_factory=dict,
        description="Factor statistics (mean, std, skew, kurtosis)",
    )
    coverage: float = Field(default=0.0, description="Data coverage ratio")
    duration_ms: float = Field(..., description="Calculation duration")


class Strategy(BaseModel):
    """Strategy definition."""

    strategy_id: str = Field(
        default_factory=lambda: f"strat_{uuid.uuid4().hex[:12]}",
        description="Unique strategy ID",
    )
    name: str = Field(..., description="Strategy name")
    code: str = Field(..., description="Strategy code (unique identifier)")
    description: str = Field(default="", description="Strategy description")
    strategy_type: StrategyType = Field(..., description="Strategy type")
    factors: list[str] = Field(
        default_factory=list,
        description="Factor IDs used in strategy",
    )
    factor_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Factor weights",
    )
    weight_method: WeightMethod = Field(
        default=WeightMethod.EQUAL,
        description="Weight method",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy parameters",
    )
    rebalance_freq: str = Field(default="monthly", description="Rebalance frequency")
    max_positions: int = Field(default=50, description="Maximum positions")
    position_size: float = Field(default=0.02, description="Default position size")
    stop_loss: float | None = Field(default=None, description="Stop loss percentage")
    take_profit: float | None = Field(default=None, description="Take profit percentage")
    status: FactorStatus = Field(default=FactorStatus.DRAFT, description="Strategy status")
    version: int = Field(default=1, description="Strategy version")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )
    created_by: str | None = Field(default=None, description="Creator ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class StrategyParameter(BaseModel):
    """Strategy parameter definition."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (int, float, str, bool)")
    default: Any = Field(..., description="Default value")
    min: float | None = Field(default=None, description="Minimum value")
    max: float | None = Field(default=None, description="Maximum value")
    options: list[Any] | None = Field(default=None, description="Valid options")
    description: str = Field(default="", description="Parameter description")


class OptimizationConfig(BaseModel):
    """Parameter optimization configuration."""

    method: OptimizeMethod = Field(
        default=OptimizeMethod.GRID_SEARCH,
        description="Optimization method",
    )
    parameters: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Parameters to optimize with ranges",
    )
    objective: str = Field(
        default="sharpe_ratio",
        description="Optimization objective",
    )
    max_iterations: int = Field(default=100, description="Maximum iterations")
    n_jobs: int = Field(default=1, description="Parallel jobs")
    seed: int | None = Field(default=None, description="Random seed")


class OptimizationResult(BaseModel):
    """Parameter optimization result."""

    optimization_id: str = Field(
        default_factory=lambda: f"opt_{uuid.uuid4().hex[:8]}",
        description="Optimization ID",
    )
    strategy_id: str = Field(..., description="Strategy ID")
    method: OptimizeMethod = Field(..., description="Optimization method")
    best_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Best parameters found",
    )
    best_score: float = Field(..., description="Best objective score")
    all_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="All optimization results",
    )
    duration_ms: float = Field(..., description="Optimization duration")
    converged: bool = Field(default=True, description="Whether optimization converged")


class BacktestConfig(BaseModel):
    """Backtest configuration."""

    backtest_id: str = Field(
        default_factory=lambda: f"bt_{uuid.uuid4().hex[:8]}",
        description="Backtest ID",
    )
    strategy_id: str = Field(..., description="Strategy ID")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    initial_capital: float = Field(default=1_000_000.0, description="Initial capital")
    commission: float = Field(default=0.0003, description="Commission rate")
    slippage: float = Field(default=0.0001, description="Slippage rate")
    benchmark: str = Field(default="000300", description="Benchmark index code")
    risk_free_rate: float = Field(default=0.03, description="Risk-free rate (annual)")
    position_limit: float = Field(default=1.0, description="Max position ratio")
    allow_short: bool = Field(default=False, description="Allow short selling")
    reinvest_dividend: bool = Field(default=True, description="Reinvest dividends")


class TradeRecord(BaseModel):
    """Trade record."""

    trade_id: str = Field(
        default_factory=lambda: f"trade_{uuid.uuid4().hex[:8]}",
        description="Trade ID",
    )
    backtest_id: str = Field(..., description="Backtest ID")
    stock_code: str = Field(..., description="Stock code")
    trade_date: datetime = Field(..., description="Trade date")
    direction: str = Field(..., description="Trade direction (buy/sell)")
    quantity: int = Field(..., description="Trade quantity")
    price: float = Field(..., description="Trade price")
    amount: float = Field(..., description="Trade amount")
    commission: float = Field(default=0.0, description="Commission")
    slippage: float = Field(default=0.0, description="Slippage cost")
    pnl: float | None = Field(default=None, description="Realized PnL")
    signal: str | None = Field(default=None, description="Trade signal")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class DailyPosition(BaseModel):
    """Daily position record."""

    date: datetime = Field(..., description="Date")
    stock_code: str = Field(..., description="Stock code")
    quantity: int = Field(..., description="Position quantity")
    market_value: float = Field(..., description="Market value")
    weight: float = Field(..., description="Portfolio weight")
    daily_return: float | None = Field(default=None, description="Daily return")
    pnl: float | None = Field(default=None, description="Daily PnL")


class DailyEquity(BaseModel):
    """Daily equity curve."""

    date: datetime = Field(..., description="Date")
    equity: float = Field(..., description="Total equity")
    cash: float = Field(..., description="Cash balance")
    position_value: float = Field(..., description="Position market value")
    daily_return: float = Field(default=0.0, description="Daily return")
    cumulative_return: float = Field(default=0.0, description="Cumulative return")
    drawdown: float = Field(default=0.0, description="Drawdown")


class PerformanceMetrics(BaseModel):
    """Performance metrics."""

    total_return: float = Field(default=0.0, description="Total return")
    annual_return: float = Field(default=0.0, description="Annualized return")
    benchmark_return: float = Field(default=0.0, description="Benchmark return")
    excess_return: float = Field(default=0.0, description="Excess return over benchmark")

    volatility: float = Field(default=0.0, description="Annualized volatility")
    downside_volatility: float = Field(default=0.0, description="Downside volatility")

    sharpe_ratio: float = Field(default=0.0, description="Sharpe ratio")
    sortino_ratio: float = Field(default=0.0, description="Sortino ratio")
    calmar_ratio: float = Field(default=0.0, description="Calmar ratio")
    information_ratio: float = Field(default=0.0, description="Information ratio")
    treynor_ratio: float | None = Field(default=None, description="Treynor ratio")

    max_drawdown: float = Field(default=0.0, description="Maximum drawdown")
    max_drawdown_duration: int = Field(default=0, description="Max drawdown duration (days)")
    recovery_days: int | None = Field(default=None, description="Recovery days")

    win_rate: float = Field(default=0.0, description="Win rate")
    profit_loss_ratio: float = Field(default=0.0, description="Profit/Loss ratio")
    avg_profit: float = Field(default=0.0, description="Average profit")
    avg_loss: float = Field(default=0.0, description="Average loss")
    max_consecutive_wins: int = Field(default=0, description="Max consecutive wins")
    max_consecutive_losses: int = Field(default=0, description="Max consecutive losses")

    alpha: float | None = Field(default=None, description="Jensen's Alpha")
    beta: float | None = Field(default=None, description="Beta")
    r_squared: float | None = Field(default=None, description="R-squared")

    var_95: float | None = Field(default=None, description="VaR 95%")
    cvar_95: float | None = Field(default=None, description="CVaR 95%")

    total_trades: int = Field(default=0, description="Total trades")
    total_commission: float = Field(default=0.0, description="Total commission")
    total_slippage: float = Field(default=0.0, description="Total slippage")
    turnover_rate: float = Field(default=0.0, description="Turnover rate")


class BacktestResult(BaseModel):
    """Backtest result."""

    backtest_id: str = Field(..., description="Backtest ID")
    strategy_id: str = Field(..., description="Strategy ID")
    config: BacktestConfig = Field(..., description="Backtest configuration")
    status: BacktestStatus = Field(default=BacktestStatus.COMPLETED, description="Status")

    equity_curve: list[DailyEquity] = Field(
        default_factory=list,
        description="Daily equity curve",
    )
    positions: list[DailyPosition] = Field(
        default_factory=list,
        description="Position history",
    )
    trades: list[TradeRecord] = Field(
        default_factory=list,
        description="Trade records",
    )
    metrics: PerformanceMetrics = Field(
        default_factory=PerformanceMetrics,
        description="Performance metrics",
    )

    benchmark_curve: list[DailyEquity] = Field(
        default_factory=list,
        description="Benchmark equity curve",
    )

    start_date: datetime = Field(..., description="Actual start date")
    end_date: datetime = Field(..., description="Actual end date")
    duration_ms: float = Field(..., description="Backtest duration")

    error: str | None = Field(default=None, description="Error message if failed")


class SensitivityAnalysisResult(BaseModel):
    """Parameter sensitivity analysis result."""

    analysis_id: str = Field(
        default_factory=lambda: f"sens_{uuid.uuid4().hex[:8]}",
        description="Analysis ID",
    )
    strategy_id: str = Field(..., description="Strategy ID")
    parameter: str = Field(..., description="Parameter name")
    values: list[Any] = Field(
        default_factory=list,
        description="Tested values",
    )
    metrics: list[PerformanceMetrics] = Field(
        default_factory=list,
        description="Metrics for each value",
    )
    optimal_value: Any = Field(..., description="Optimal parameter value")
    sensitivity_score: float = Field(
        default=0.0,
        description="Sensitivity score (higher = more sensitive)",
    )


class AttributionResult(BaseModel):
    """Performance attribution result."""

    attribution_id: str = Field(
        default_factory=lambda: f"attr_{uuid.uuid4().hex[:8]}",
        description="Attribution ID",
    )
    backtest_id: str = Field(..., description="Backtest ID")

    factor_attribution: dict[str, float] = Field(
        default_factory=dict,
        description="Return attribution by factor",
    )
    sector_attribution: dict[str, float] = Field(
        default_factory=dict,
        description="Return attribution by sector",
    )
    style_attribution: dict[str, float] = Field(
        default_factory=dict,
        description="Return attribution by style",
    )

    selection_return: float = Field(default=0.0, description="Selection return")
    interaction_return: float = Field(default=0.0, description="Interaction return")
    timing_return: float = Field(default=0.0, description="Timing return")


class CustomFactor(BaseModel):
    """Custom factor definition."""

    custom_id: str = Field(
        default_factory=lambda: f"custom_{uuid.uuid4().hex[:12]}",
        description="Custom factor ID",
    )
    name: str = Field(..., description="Factor name")
    code: str = Field(..., description="Factor code")
    description: str = Field(default="", description="Factor description")
    python_code: str = Field(..., description="Python implementation code")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Factor parameters",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Required data fields",
    )
    is_validated: bool = Field(default=False, description="Whether code is validated")
    validation_errors: list[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    test_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Test results",
    )
    status: FactorStatus = Field(default=FactorStatus.DRAFT, description="Factor status")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp",
    )
    created_by: str | None = Field(default=None, description="Creator ID")


class FactorValidationRequest(BaseModel):
    """Request for factor code validation."""

    python_code: str = Field(..., description="Python code to validate")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to use",
    )
    test_data: dict[str, Any] | None = Field(
        default=None,
        description="Test data for validation",
    )


class FactorValidationResult(BaseModel):
    """Result of factor code validation."""

    is_valid: bool = Field(..., description="Whether code is valid")
    errors: list[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )
    syntax_valid: bool = Field(default=True, description="Syntax is valid")
    imports_valid: bool = Field(default=True, description="Imports are valid")
    logic_valid: bool = Field(default=True, description="Logic is valid")
    test_output: Any | None = Field(default=None, description="Test output")


class FactorTestRequest(BaseModel):
    """Request for factor performance test."""

    factor_id: str | None = Field(default=None, description="Factor ID")
    python_code: str | None = Field(default=None, description="Python code")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Test parameters",
    )
    stock_codes: list[str] = Field(
        default_factory=list,
        description="Test stock codes",
    )
    start_date: datetime = Field(..., description="Test start date")
    end_date: datetime = Field(..., description="Test end date")
    test_metrics: list[str] = Field(
        default_factory=lambda: ["ic", "ir", "turnover", "coverage"],
        description="Metrics to calculate",
    )


class FactorTestResult(BaseModel):
    """Result of factor performance test."""

    test_id: str = Field(
        default_factory=lambda: f"test_{uuid.uuid4().hex[:8]}",
        description="Test ID",
    )
    factor_id: str | None = Field(default=None, description="Factor ID")

    ic_mean: float | None = Field(default=None, description="Mean IC")
    ic_std: float | None = Field(default=None, description="IC standard deviation")
    ic_ir: float | None = Field(default=None, description="IC information ratio")
    ic_positive_ratio: float | None = Field(default=None, description="IC positive ratio")

    rank_ic_mean: float | None = Field(default=None, description="Mean rank IC")
    rank_ic_std: float | None = Field(default=None, description="Rank IC std")

    turnover_mean: float | None = Field(default=None, description="Mean turnover")
    coverage_mean: float | None = Field(default=None, description="Mean coverage")

    monotonicity: float | None = Field(default=None, description="Monotonicity score")
    quantile_returns: list[float] | None = Field(
        default=None,
        description="Returns by quantile",
    )

    duration_ms: float = Field(..., description="Test duration")
    error: str | None = Field(default=None, description="Error message")


class FactorListRequest(BaseModel):
    """Request for listing factors."""

    factor_type: FactorType | None = Field(default=None, description="Filter by type")
    category: FactorCategory | None = Field(default=None, description="Filter by category")
    status: FactorStatus | None = Field(default=None, description="Filter by status")
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    search: str | None = Field(default=None, description="Search in name/code")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")
    sort_by: str = Field(default="updated_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class FactorListResponse(BaseModel):
    """Response for factor list."""

    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    factors: list[Factor] = Field(..., description="Factor list")


class StrategyListRequest(BaseModel):
    """Request for listing strategies."""

    strategy_type: StrategyType | None = Field(default=None, description="Filter by type")
    status: FactorStatus | None = Field(default=None, description="Filter by status")
    search: str | None = Field(default=None, description="Search in name/code")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")
    sort_by: str = Field(default="updated_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")


class StrategyListResponse(BaseModel):
    """Response for strategy list."""

    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    strategies: list[Strategy] = Field(..., description="Strategy list")


class BacktestListRequest(BaseModel):
    """Request for listing backtests."""

    strategy_id: str | None = Field(default=None, description="Filter by strategy")
    status: BacktestStatus | None = Field(default=None, description="Filter by status")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Page size")


class BacktestListResponse(BaseModel):
    """Response for backtest list."""

    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    backtests: list[BacktestResult] = Field(..., description="Backtest list")
