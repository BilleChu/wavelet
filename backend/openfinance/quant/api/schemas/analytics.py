"""
Enhanced schemas for quantitative analysis API.

Provides comprehensive data models for factors, strategies, backtesting,
and advanced analytics with professional-grade metrics.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Performance Metrics Schemas
# ============================================================================

class ReturnsMetrics(BaseModel):
    """Return-related performance metrics."""
    
    total_return: float = Field(..., description="Total return over the period")
    annualized_return: float = Field(..., description="Annualized return (CAGR)")
    excess_return: float = Field(default=0.0, description="Excess return vs benchmark")
    active_return: float = Field(default=0.0, description="Active return (portfolio - benchmark)")
    cumulative_return: float = Field(..., description="Cumulative return")
    cagr: float = Field(..., description="Compound Annual Growth Rate")


class RiskMetrics(BaseModel):
    """Risk-related performance metrics."""
    
    volatility: float = Field(..., description="Annualized volatility")
    downside_deviation: float = Field(default=0.0, description="Downside deviation")
    var_95: float = Field(default=0.0, description="95% Value at Risk")
    cvar_95: float = Field(default=0.0, description="95% Conditional VaR")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    avg_drawdown: float = Field(default=0.0, description="Average drawdown")
    ulcer_index: float = Field(default=0.0, description="Ulcer Index")


class RiskAdjustedMetrics(BaseModel):
    """Risk-adjusted return metrics."""
    
    sharpe_ratio: float = Field(..., description="Sharpe Ratio")
    sortino_ratio: float = Field(default=0.0, description="Sortino Ratio")
    calmar_ratio: float = Field(default=0.0, description="Calmar Ratio")
    information_ratio: float = Field(default=0.0, description="Information Ratio")
    omega_ratio: float = Field(default=0.0, description="Omega Ratio")


class MarketRiskMetrics(BaseModel):
    """Market risk metrics."""
    
    beta: float = Field(default=1.0, description="Beta vs benchmark")
    alpha: float = Field(default=0.0, description="Alpha (Jensen's Alpha)")
    tracking_error: float = Field(default=0.0, description="Tracking Error")
    r_squared: float = Field(default=0.0, description="R-squared")


class TradingMetrics(BaseModel):
    """Trading statistics."""
    
    win_rate: float = Field(default=0.0, description="Win Rate")
    profit_loss_ratio: float = Field(default=0.0, description="Profit/Loss Ratio")
    avg_win: float = Field(default=0.0, description="Average Win")
    avg_loss: float = Field(default=0.0, description="Average Loss")
    expectancy: float = Field(default=0.0, description="Trade Expectancy")
    turnover_rate: float = Field(default=0.0, description="Turnover Rate")
    avg_holding_period: int = Field(default=0, description="Average Holding Period (days)")


class AdvancedMetrics(BaseModel):
    """Advanced statistical metrics."""
    
    tail_ratio: float = Field(default=0.0, description="Tail Ratio")
    skewness: float = Field(default=0.0, description="Skewness")
    kurtosis: float = Field(default=0.0, description="Kurtosis")


class PerformanceMetrics(BaseModel):
    """Comprehensive performance metrics combining all categories."""
    
    returns: ReturnsMetrics
    risk: RiskMetrics
    risk_adjusted: RiskAdjustedMetrics
    market_risk: MarketRiskMetrics
    trading: TradingMetrics
    advanced: AdvancedMetrics
    
    # Summary metrics for quick view
    summary: dict[str, float] = Field(default_factory=dict)


# ============================================================================
# Attribution Analysis Schemas
# ============================================================================

class BrinsonAttribution(BaseModel):
    """Brinson attribution decomposition."""
    
    allocation_effect: float = Field(..., description="Allocation effect")
    selection_effect: float = Field(..., description="Selection effect")
    interaction_effect: float = Field(..., description="Interaction effect")
    total_active_return: float = Field(..., description="Total active return")


class FactorAttribution(BaseModel):
    """Factor-based attribution."""
    
    size: float = Field(default=0.0, description="Size factor contribution")
    value: float = Field(default=0.0, description="Value factor contribution")
    momentum: float = Field(default=0.0, description="Momentum factor contribution")
    quality: float = Field(default=0.0, description="Quality factor contribution")
    volatility: float = Field(default=0.0, description="Volatility factor contribution")
    liquidity: float = Field(default=0.0, description="Liquidity factor contribution")
    other: float = Field(default=0.0, description="Other factors contribution")


class SectorAttributionItem(BaseModel):
    """Sector attribution for one sector."""
    
    sector: str = Field(..., description="Sector name")
    allocation_effect: float = Field(..., description="Allocation effect")
    selection_effect: float = Field(..., description="Selection effect")
    total_effect: float = Field(..., description="Total effect")


class AttributionResult(BaseModel):
    """Complete attribution analysis result."""
    
    brinson: BrinsonAttribution
    factor: FactorAttribution
    sector: list[SectorAttributionItem] = Field(default_factory=list)


# ============================================================================
# Risk Analysis Schemas
# ============================================================================

class StressTestScenario(BaseModel):
    """Stress test scenario configuration."""
    
    name: str = Field(..., description="Scenario name")
    description: str = Field(default="", description="Scenario description")
    date_range: tuple[datetime, datetime] = Field(..., description="Historical period")
    benchmark_return: float = Field(..., description="Benchmark return during period")


class StressTestResult(BaseModel):
    """Stress test result."""
    
    scenario: str = Field(..., description="Scenario name")
    portfolio_return: float = Field(..., description="Portfolio return during stress period")
    benchmark_return: float = Field(..., description="Benchmark return")
    relative_performance: float = Field(..., description="Relative performance")
    max_drawdown: float = Field(..., description="Max drawdown during period")
    recovery_time: int = Field(default=0, description="Recovery time in days")


class SensitivityAnalysisRequest(BaseModel):
    """Request for sensitivity analysis."""
    
    strategy_id: str = Field(..., description="Strategy ID")
    parameter_name: str = Field(..., description="Parameter to analyze")
    parameter_range: list[float] = Field(..., description="Range of parameter values")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")


class SensitivityAnalysisResult(BaseModel):
    """Sensitivity analysis result."""
    
    parameter_name: str = Field(..., description="Parameter analyzed")
    results: list[dict[str, Any]] = Field(..., description="Results for each parameter value")
    optimal_value: float = Field(..., description="Optimal parameter value")
    sensitivity_score: float = Field(..., description="How sensitive strategy is to this parameter")


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation configuration."""
    
    num_simulations: int = Field(default=1000, description="Number of simulations")
    confidence_level: float = Field(default=0.95, description="Confidence level")
    method: str = Field(default="bootstrap", description="Simulation method")


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation result."""
    
    expected_return: float = Field(..., description="Expected annualized return")
    return_std: float = Field(..., description="Standard deviation of returns")
    var_95: float = Field(..., description="95% VaR from simulation")
    cvar_95: float = Field(..., description="95% CVaR from simulation")
    probability_of_loss: float = Field(..., description="Probability of negative return")
    confidence_intervals: dict[str, tuple[float, float]] = Field(
        default_factory=dict, 
        description="Confidence intervals for metrics"
    )


# ============================================================================
# Rolling Analysis Schemas
# ============================================================================

class RollingMetricsRequest(BaseModel):
    """Request for rolling window analysis."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    window: int = Field(default=252, description="Rolling window size (days)")
    step: int = Field(default=21, description="Rolling step (days)")


class RollingMetricsResult(BaseModel):
    """Rolling window analysis result."""
    
    metric_name: str = Field(..., description="Metric being analyzed")
    dates: list[datetime] = Field(..., description="Time series dates")
    values: list[float] = Field(..., description="Metric values")
    mean: float = Field(..., description="Mean of rolling metric")
    std: float = Field(..., description="Std of rolling metric")
    min: float = Field(..., description="Minimum value")
    max: float = Field(..., description="Maximum value")


# ============================================================================
# Backtest Comparison Schemas
# ============================================================================

class BacktestComparisonRequest(BaseModel):
    """Request to compare multiple backtests."""
    
    backtest_ids: list[str] = Field(..., description="List of backtest IDs to compare")
    metrics: list[str] = Field(
        default=["sharpe", "total_return", "max_drawdown"],
        description="Metrics to compare"
    )


class BacktestComparisonResult(BaseModel):
    """Result of backtest comparison."""
    
    comparison_table: list[dict[str, Any]] = Field(..., description="Comparison table")
    ranking: list[tuple[str, int]] = Field(..., description="Ranked backtests")
    best_by_metric: dict[str, str] = Field(..., description="Best backtest for each metric")


# ============================================================================
# Report Generation Schemas
# ============================================================================

class ReportConfig(BaseModel):
    """Report generation configuration."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    report_type: str = Field(default="full", description="Type: factsheet, full, risk")
    format: str = Field(default="html", description="Output format: html, pdf")
    include_sections: list[str] = Field(
        default=["overview", "performance", "risk", "attribution"],
        description="Sections to include"
    )


class ReportResponse(BaseModel):
    """Report generation response."""
    
    report_id: str = Field(..., description="Generated report ID")
    url: str = Field(..., description="URL to access report")
    format: str = Field(..., description="Report format")
    generated_at: datetime = Field(..., description="Generation timestamp")
    file_size_kb: int = Field(default=0, description="File size in KB")
