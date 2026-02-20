"""
Comprehensive risk analysis module.

Provides advanced risk metrics and analysis tools:
- Value at Risk (VaR) - Historical, Parametric, Monte Carlo
- Conditional VaR (Expected Shortfall)
- Stress Testing - Historical scenarios
- Scenario Analysis - Custom scenarios
- Rolling risk metrics
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from scipy import stats

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """
    Professional risk analysis toolkit.
    
    Implements comprehensive risk measurement and analysis:
    - VaR (Historical, Parametric, Monte Carlo)
    - CVaR / Expected Shortfall
    - Stress testing with historical scenarios
    - Scenario analysis
    - Rolling risk metrics
    """
    
    def __init__(self, confidence_levels: list[float] = [0.95, 0.99]):
        """
        Initialize risk analyzer.
        
        Args:
            confidence_levels: List of confidence levels for VaR/CVaR
        """
        self.confidence_levels = confidence_levels
    
    def calculate_var(
        self,
        returns: pd.Series,
        method: str = "historical",
        confidence_level: float = 0.95,
        horizon: int = 1,
    ) -> float:
        """
        Calculate Value at Risk.
        
        Args:
            returns: Series of returns
            method: 'historical', 'parametric', or 'monte_carlo'
            confidence_level: Confidence level (e.g., 0.95 for 95%)
            horizon: Time horizon in days
        
        Returns:
            VaR as a positive number representing potential loss
        """
        if method == "historical":
            return self._var_historical(returns, confidence_level, horizon)
        elif method == "parametric":
            return self._var_parametric(returns, confidence_level, horizon)
        elif method == "monte_carlo":
            return self._var_monte_carlo(returns, confidence_level, horizon)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
    
    def _var_historical(
        self,
        returns: pd.Series,
        confidence_level: float,
        horizon: int,
    ) -> float:
        """Calculate historical VaR using empirical distribution."""
        # Scale to horizon
        scaled_returns = returns * np.sqrt(horizon)
        
        # Historical percentile
        alpha = 1 - confidence_level
        var = -np.percentile(scaled_returns, alpha * 100)
        
        return float(var)
    
    def _var_parametric(
        self,
        returns: pd.Series,
        confidence_level: float,
        horizon: int,
    ) -> float:
        """Calculate parametric VaR assuming normal distribution."""
        mean = returns.mean()
        std = returns.std()
        
        # Z-score for confidence level
        z_score = stats.norm.ppf(confidence_level)
        
        # VaR formula
        var = -(mean * horizon + std * z_score * np.sqrt(horizon))
        
        return float(var)
    
    def _var_monte_carlo(
        self,
        returns: pd.Series,
        confidence_level: float,
        horizon: int,
        n_simulations: int = 10000,
    ) -> float:
        """Calculate Monte Carlo VaR."""
        mean = returns.mean()
        std = returns.std()
        
        # Simulate returns
        simulated_returns = np.random.normal(mean, std, n_simulations)
        
        # Scale to horizon
        cumulative_returns = np.cumprod(1 + simulated_returns) ** (1 / np.sqrt(horizon)) - 1
        
        # Find percentile
        alpha = 1 - confidence_level
        var = -np.percentile(cumulative_returns, alpha * 100)
        
        return float(var)
    
    def calculate_cvar(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        horizon: int = 1,
    ) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).
        
        Args:
            returns: Series of returns
            confidence_level: Confidence level
            horizon: Time horizon in days
        
        Returns:
            CVaR as expected loss given that loss exceeds VaR
        """
        # First calculate VaR
        var = self.calculate_var(returns, "historical", confidence_level, horizon)
        
        # Find returns worse than VaR
        threshold = -var
        tail_returns = returns[returns <= threshold]
        
        if len(tail_returns) == 0:
            return var
        
        # Average of tail losses
        cvar = -tail_returns.mean()
        
        return float(cvar)
    
    def stress_test(
        self,
        equity_curve: pd.Series,
        scenarios: list[dict],
    ) -> list[dict]:
        """
        Perform stress testing with historical scenarios.
        
        Args:
            equity_curve: Portfolio equity curve
            scenarios: List of scenario definitions with:
                - name: Scenario name
                - start_date: Start date
                - end_date: End date
                - description: Optional description
        
        Returns:
            List of stress test results
        """
        results = []
        
        for scenario in scenarios:
            try:
                # Extract period data
                mask = (equity_curve.index >= scenario['start_date']) & \
                       (equity_curve.index <= scenario['end_date'])
                
                period_equity = equity_curve[mask]
                
                if len(period_equity) < 2:
                    continue
                
                # Calculate metrics
                period_returns = period_equity.pct_change().dropna()
                
                # Portfolio performance
                portfolio_return = (period_equity.iloc[-1] / period_equity.iloc[0]) - 1
                
                # Maximum drawdown during period
                running_max = period_equity.cummax()
                drawdown = (period_equity - running_max) / running_max
                max_dd = float(drawdown.min())
                
                # Recovery time (days to recover from max drawdown)
                recovery_time = self._calculate_recovery_time(period_equity)
                
                results.append({
                    'scenario': scenario['name'],
                    'portfolio_return': float(portfolio_return),
                    'max_drawdown': float(max_dd),
                    'recovery_time': recovery_time,
                    'start_date': str(scenario['start_date']),
                    'end_date': str(scenario['end_date']),
                    'description': scenario.get('description', ''),
                })
                
            except Exception as e:
                logger.warning(f"Failed to process scenario {scenario['name']}: {e}")
                continue
        
        return results
    
    def _calculate_recovery_time(self, equity_curve: pd.Series) -> int:
        """Calculate days to recover from maximum drawdown."""
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        
        # Find when max drawdown occurred
        max_dd_idx = drawdown.idxmin()
        
        if max_dd_idx is None or pd.isna(max_dd_idx):
            return 0
        
        # Find peak before drawdown
        peak_idx = running_max[:max_dd_idx].idxmax()
        
        # Find recovery point (when equity exceeds previous peak)
        peak_value = running_max[peak_idx]
        recovery_mask = equity_curve[max_dd_idx:] >= peak_value
        
        if recovery_mask.any():
            recovery_idx = recovery_mask[recovery_mask].index[0]
            recovery_days = (recovery_idx - max_dd_idx).days
            return int(recovery_days)
        else:
            # Not yet recovered
            return 0
    
    def calculate_rolling_risk_metrics(
        self,
        equity_curve: pd.Series,
        window: int = 252,
        step: int = 21,
    ) -> pd.DataFrame:
        """
        Calculate rolling risk metrics.
        
        Args:
            equity_curve: Portfolio equity curve
            window: Rolling window size in days
            step: Step size for rolling calculation
        
        Returns:
            DataFrame with rolling metrics over time
        """
        returns = equity_curve.pct_change().dropna()
        
        results = []
        
        for i in range(window, len(returns), step):
            window_returns = returns.iloc[i-window:i]
            
            if len(window_returns) < window:
                continue
            
            # Calculate metrics for this window
            volatility = window_returns.std() * np.sqrt(252)
            sharpe = (window_returns.mean() * 252 - 0.03) / volatility if volatility > 0 else 0
            
            # VaR
            var_95 = -np.percentile(window_returns, 5)
            
            # Skewness
            skewness = stats.skew(window_returns)
            
            # Kurtosis
            kurtosis = stats.kurtosis(window_returns)
            
            results.append({
                'date': returns.index[i],
                'volatility': volatility,
                'sharpe': sharpe,
                'var_95': var_95,
                'skewness': skewness,
                'kurtosis': kurtosis,
            })
        
        return pd.DataFrame(results).set_index('date')
    
    def scenario_analysis(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
    ) -> dict:
        """
        Perform general scenario analysis.
        
        Args:
            equity_curve: Portfolio equity curve
            benchmark_curve: Optional benchmark for comparison
        
        Returns:
            Dictionary with scenario analysis results
        """
        returns = equity_curve.pct_change().dropna()
        
        analysis = {
            'worst_day': {
                'date': str(returns.idxmin()),
                'return': float(returns.min()),
            },
            'best_day': {
                'date': str(returns.idxmax()),
                'return': float(returns.max()),
            },
            'worst_week': self._find_worst_period(returns, days=5),
            'worst_month': self._find_worst_period(returns, days=21),
            'worst_quarter': self._find_worst_period(returns, days=63),
        }
        
        if benchmark_curve is not None:
            benchmark_returns = benchmark_curve.pct_change().dropna()
            aligned_returns = returns.reindex(benchmark_returns.index)
            
            # Worst relative day
            active_returns = aligned_returns - benchmark_returns
            analysis['worst_relative_day'] = {
                'date': str(active_returns.idxmin()),
                'active_return': float(active_returns.min()),
            }
        
        return analysis
    
    def _find_worst_period(
        self,
        returns: pd.Series,
        days: int,
    ) -> dict:
        """Find worst N-day period."""
        worst_return = float('inf')
        worst_start = None
        worst_end = None
        
        for i in range(len(returns) - days):
            period_return = returns.iloc[i:i+days].sum()
            if period_return < worst_return:
                worst_return = period_return
                worst_start = returns.index[i]
                worst_end = returns.index[i+days]
        
        return {
            'start_date': str(worst_start) if worst_start else None,
            'end_date': str(worst_end) if worst_end else None,
            'return': float(worst_return) if worst_return != float('inf') else None,
        }


# Predefined historical stress test scenarios for Chinese market
CHINA_STRESS_SCENARIOS = [
    {
        'name': '2015 Stock Market Crash',
        'start_date': '2015-06-15',
        'end_date': '2015-08-26',
        'description': 'Chinese stock market crash and government intervention',
    },
    {
        'name': '2016 Circuit Breaker',
        'start_date': '2016-01-04',
        'end_date': '2016-01-07',
        'description': 'Circuit breaker mechanism triggered multiple times',
    },
    {
        'name': '2018 Trade War',
        'start_date': '2018-03-22',
        'end_date': '2018-12-24',
        'description': 'US-China trade war escalation',
    },
    {
        'name': '2020 COVID-19 Crash',
        'start_date': '2020-01-23',
        'end_date': '2020-03-23',
        'description': 'COVID-19 pandemic market crash',
    },
    {
        'name': '2022 Real Estate Crisis',
        'start_date': '2022-01-01',
        'end_date': '2022-10-31',
        'description': 'Chinese real estate sector crisis',
    },
]
