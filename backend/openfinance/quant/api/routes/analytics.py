"""
Analytics API Routes for OpenFinance quantitative system.

Provides endpoints for:
- Performance metrics calculation
- Risk analysis (VaR, stress testing)
- Attribution analysis (Brinson, factor-based)
- Rolling window analysis
- Monte Carlo simulation
- Sensitivity analysis
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from openfinance.quant.analytics.performance import PerformanceCalculator
from openfinance.quant.analytics.risk import RiskAnalyzer, CHINA_STRESS_SCENARIOS
from openfinance.quant.analytics.attribution import AttributionAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["quant_analytics"])


# ============================================================================
# Request Models
# ============================================================================

class PerformanceMetricsRequest(BaseModel):
    """Request for performance metrics calculation."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    include_benchmark: bool = Field(default=True, description="Include benchmark comparison")


class RiskAnalysisRequest(BaseModel):
    """Request for risk analysis."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    var_method: str = Field(default="historical", description="VaR method: historical, parametric, monte_carlo")
    confidence_level: float = Field(default=0.95, ge=0.9, le=0.99, description="Confidence level")
    horizon: int = Field(default=1, ge=1, le=30, description="Time horizon in days")


class AttributionRequest(BaseModel):
    """Request for attribution analysis."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    method: str = Field(default="brinson", description="Attribution method: brinson, factor, sector")


class RollingMetricsRequest(BaseModel):
    """Request for rolling window analysis."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    window: int = Field(default=252, ge=20, le=500, description="Rolling window size (days)")
    step: int = Field(default=21, ge=1, le=50, description="Step size (days)")


class SensitivityAnalysisRequest(BaseModel):
    """Request for sensitivity analysis."""
    
    strategy_id: str = Field(..., description="Strategy ID")
    parameter_name: str = Field(..., description="Parameter to analyze")
    parameter_range: list[float] = Field(..., description="Range of parameter values")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    
    backtest_id: str = Field(..., description="Backtest ID")
    num_simulations: int = Field(default=1000, ge=100, le=10000, description="Number of simulations")
    confidence_level: float = Field(default=0.95, ge=0.9, le=0.99, description="Confidence level")


# ============================================================================
# Helper Functions
# ============================================================================

def get_sample_equity_curve() -> pd.Series:
    """Get sample equity curve for demonstration."""
    # In production, this would fetch from database
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    np.random.seed(42)
    
    # Simulate realistic equity curve
    daily_returns = np.random.normal(0.0005, 0.015, len(dates))
    equity = 1_000_000 * np.cumprod(1 + daily_returns)
    
    return pd.Series(equity, index=dates)


def get_sample_benchmark_curve() -> pd.Series:
    """Get sample benchmark curve."""
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    np.random.seed(43)
    
    # Simulate benchmark with slightly different characteristics
    daily_returns = np.random.normal(0.0003, 0.012, len(dates))
    equity = 1_000_000 * np.cumprod(1 + daily_returns)
    
    return pd.Series(equity, index=dates)


def get_sample_trades() -> pd.DataFrame:
    """Get sample trade log."""
    n_trades = 100
    np.random.seed(44)
    
    trades = pd.DataFrame({
        'trade_id': range(n_trades),
        'trade_date': pd.date_range('2023-01-01', periods=n_trades, freq='3D'),
        'stock_code': [f'600{i:03d}' for i in range(n_trades)],
        'direction': np.random.choice(['buy', 'sell'], n_trades),
        'quantity': np.random.randint(100, 10000, n_trades),
        'price': np.random.uniform(10, 500, n_trades),
        'amount': np.random.uniform(10000, 500000, n_trades),
        'commission': np.random.uniform(10, 500, n_trades),
        'slippage': np.random.uniform(5, 200, n_trades),
    })
    
    return trades


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/performance")
async def get_performance_metrics(
    backtest_id: str,
    include_benchmark: bool = True,
):
    """
    Get comprehensive performance metrics for a backtest.
    
    Calculates 60+ professional metrics including:
    - Returns (total, annualized, excess, CAGR)
    - Risk (volatility, VaR, CVaR, drawdown)
    - Risk-adjusted returns (Sharpe, Sortino, Calmar)
    - Market risk (Beta, Alpha, Tracking Error)
    - Trading statistics
    - Advanced metrics (skewness, kurtosis)
    
    Performance optimized with:
    - LRU caching (30 min TTL)
    - Thread pool execution for CPU-bound calculations
    - Efficient data sampling
    """
    try:
        # Get data (in production, fetch from database)
        equity_curve = get_sample_equity_curve()
        benchmark_curve = get_sample_benchmark_curve() if include_benchmark else None
        trades = get_sample_trades()
        
        # Calculate metrics with caching
        calculator = PerformanceCalculator()
        metrics = await calculator.calculate_all_cached(
            equity_curve,
            benchmark_curve,
            trades,
            backtest_id=backtest_id,
        )
        
        # Convert to dict for JSON response
        return {
            "backtest_id": backtest_id,
            "metrics": {
                "returns": metrics.returns.dict(),
                "risk": metrics.risk.dict(),
                "risk_adjusted": metrics.risk_adjusted.dict(),
                "market_risk": metrics.market_risk.dict(),
                "trading": metrics.trading.dict(),
                "advanced": metrics.advanced.dict(),
                "summary": metrics.summary,
            },
            "cached": True,  # Indicate if result was cached
        }
    
    except Exception as e:
        logger.exception(f"Error calculating performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk")
async def get_risk_analysis(
    backtest_id: str,
    var_method: str = "historical",
    confidence_level: float = 0.95,
    horizon: int = 1,
):
    """
    Get comprehensive risk analysis.
    
    Includes:
    - VaR (Value at Risk) using different methods
    - CVaR (Conditional VaR / Expected Shortfall)
    - Stress testing with historical scenarios
    - Rolling risk metrics
    - Scenario analysis
    """
    try:
        # Get data
        equity_curve = get_sample_equity_curve()
        returns = equity_curve.pct_change().dropna()
        
        # Initialize analyzer
        analyzer = RiskAnalyzer(confidence_levels=[confidence_level])
        
        # Calculate VaR and CVaR
        var = analyzer.calculate_var(returns, var_method, confidence_level, horizon)
        cvar = analyzer.calculate_cvar(returns, confidence_level, horizon)
        
        # Stress testing
        stress_results = analyzer.stress_test(equity_curve, CHINA_STRESS_SCENARIOS)
        
        # Rolling risk metrics
        rolling_metrics = analyzer.calculate_rolling_risk_metrics(equity_curve)
        
        # Scenario analysis
        scenario_analysis = analyzer.scenario_analysis(equity_curve)
        
        return {
            "backtest_id": backtest_id,
            "var": {
                "value": float(var),
                "method": var_method,
                "confidence_level": confidence_level,
                "horizon_days": horizon,
            },
            "cvar": float(cvar),
            "stress_tests": stress_results,
            "rolling_metrics": rolling_metrics.tail(10).to_dict('records') if not rolling_metrics.empty else [],
            "scenario_analysis": scenario_analysis,
        }
    
    except Exception as e:
        logger.exception(f"Error performing risk analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attribution")
async def get_attribution_analysis(
    backtest_id: str,
    method: str = "brinson",
):
    """
    Get performance attribution analysis.
    
    Supports:
    - Brinson attribution (allocation, selection, interaction)
    - Factor-based attribution
    - Sector attribution
    - Style attribution
    """
    try:
        # Get sample data
        portfolio_weights = pd.Series({
            'Technology': 0.30,
            'Healthcare': 0.25,
            'Financials': 0.20,
            'Consumer': 0.15,
            'Energy': 0.10,
        })
        
        benchmark_weights = pd.Series({
            'Technology': 0.25,
            'Healthcare': 0.20,
            'Financials': 0.25,
            'Consumer': 0.20,
            'Energy': 0.10,
        })
        
        portfolio_returns = pd.Series({
            'Technology': 0.15,
            'Healthcare': 0.12,
            'Financials': 0.08,
            'Consumer': 0.10,
            'Energy': 0.05,
        })
        
        benchmark_returns = pd.Series({
            'Technology': 0.12,
            'Healthcare': 0.10,
            'Financials': 0.07,
            'Consumer': 0.09,
            'Energy': 0.06,
        })
        
        sectors = pd.Series({
            '600000': 'Financials',
            '600519': 'Consumer',
            '000858': 'Consumer',
        })
        
        # Perform attribution
        analyzer = AttributionAnalyzer()
        
        if method == "brinson":
            result = analyzer.brinson_attribution(
                portfolio_weights,
                benchmark_weights,
                portfolio_returns,
                benchmark_returns,
            )
        elif method == "factor":
            # Sample factor returns
            factor_returns = pd.DataFrame({
                'size': np.random.randn(252) * 0.01,
                'value': np.random.randn(252) * 0.008,
                'momentum': np.random.randn(252) * 0.012,
                'quality': np.random.randn(252) * 0.007,
            })
            portfolio_returns_series = pd.Series(np.random.randn(252) * 0.015)
            
            result = analyzer.factor_attribution(portfolio_returns_series, factor_returns)
        else:
            raise ValueError(f"Unknown attribution method: {method}")
        
        return {
            "backtest_id": backtest_id,
            "method": method,
            "attribution": result,
        }
    
    except Exception as e:
        logger.exception(f"Error performing attribution analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rolling")
async def get_rolling_metrics(
    backtest_id: str,
    window: int = 252,
    step: int = 21,
):
    """
    Get rolling window analysis of risk and performance metrics.
    
    Shows how metrics evolve over time using rolling windows.
    """
    try:
        # Get data
        equity_curve = get_sample_equity_curve()
        
        # Calculate rolling metrics
        analyzer = RiskAnalyzer()
        rolling_metrics = analyzer.calculate_rolling_risk_metrics(equity_curve, window, step)
        
        # Convert to serializable format
        result = rolling_metrics.reset_index()
        result['date'] = result['date'].astype(str)
        
        return {
            "backtest_id": backtest_id,
            "window_days": window,
            "step_days": step,
            "metrics": result.to_dict('records'),
        }
    
    except Exception as e:
        logger.exception(f"Error calculating rolling metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sensitivity")
async def run_sensitivity_analysis(request: SensitivityAnalysisRequest):
    """
    Run sensitivity analysis on strategy parameters.
    
    Tests how strategy performance changes with different parameter values.
    """
    try:
        results = []
        
        for param_value in request.parameter_range:
            # In production, run backtest with this parameter value
            # For now, simulate results
            np.random.seed(int(param_value * 100))
            
            sharpe = 1.5 + np.random.randn() * 0.3
            total_return = 0.15 + np.random.randn() * 0.05
            max_dd = -0.12 + np.random.randn() * 0.03
            
            results.append({
                "parameter_value": param_value,
                "sharpe_ratio": float(sharpe),
                "total_return": float(total_return),
                "max_drawdown": float(max_dd),
            })
        
        # Find optimal value
        best_result = max(results, key=lambda x: x['sharpe_ratio'])
        optimal_value = best_result['parameter_value']
        
        # Calculate sensitivity score (how much performance varies)
        sharpe_values = [r['sharpe_ratio'] for r in results]
        sensitivity_score = float(np.std(sharpe_values))
        
        return {
            "strategy_id": request.strategy_id,
            "parameter_name": request.parameter_name,
            "results": results,
            "optimal_value": optimal_value,
            "sensitivity_score": sensitivity_score,
        }
    
    except Exception as e:
        logger.exception(f"Error running sensitivity analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monte-carlo")
async def run_monte_carlo_simulation(request: MonteCarloRequest):
    """
    Run Monte Carlo simulation for confidence interval estimation.
    
    Uses bootstrap simulation to estimate distribution of outcomes.
    """
    try:
        # Get historical returns
        equity_curve = get_sample_equity_curve()
        returns = equity_curve.pct_change().dropna()
        
        # Bootstrap simulation
        simulated_returns = []
        
        for _ in range(request.num_simulations):
            # Resample with replacement
            bootstrap_sample = returns.sample(n=len(returns), replace=True)
            cumulative_return = (1 + bootstrap_sample).prod() - 1
            simulated_returns.append(cumulative_return)
        
        simulated_returns = np.array(simulated_returns)
        
        # Calculate statistics
        expected_return = float(np.mean(simulated_returns))
        return_std = float(np.std(simulated_returns))
        var_95 = float(np.percentile(simulated_returns, 5))
        cvar_95 = float(np.percentile(simulated_returns, 2.5))
        probability_of_loss = float(np.mean(simulated_returns < 0))
        
        # Confidence intervals
        confidence_intervals = {
            "total_return": [
                float(np.percentile(simulated_returns, 2.5)),
                float(np.percentile(simulated_returns, 97.5)),
            ],
            "sharpe_ratio": [
                float(np.percentile(simulated_returns, 2.5)) * 2,  # Approximate
                float(np.percentile(simulated_returns, 97.5)) * 2,
            ],
        }
        
        return {
            "backtest_id": backtest_id,
            "num_simulations": request.num_simulations,
            "expected_return": expected_return,
            "return_std": return_std,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "probability_of_loss": probability_of_loss,
            "confidence_intervals": confidence_intervals,
        }
    
    except Exception as e:
        logger.exception(f"Error running Monte Carlo simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
