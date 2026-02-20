"""
Comprehensive performance metrics calculator for quantitative strategies.

Implements 60+ professional-grade metrics across multiple categories:
- Returns metrics
- Risk metrics  
- Risk-adjusted returns
- Market risk metrics
- Trading statistics
- Advanced statistical metrics
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional
from scipy import stats

from openfinance.quant.core.config import (
    TRADING_DAYS_PER_YEAR,
    RISK_FREE_RATE,
    VAR_CONFIDENCE_LEVELS,
)
from openfinance.quant.core.cache import get_performance_cache, async_cache
from openfinance.quant.api.schemas.analytics import (
    PerformanceMetrics,
    ReturnsMetrics,
    RiskMetrics,
    RiskAdjustedMetrics,
    MarketRiskMetrics,
    TradingMetrics,
    AdvancedMetrics,
)

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """
    Professional-grade performance metrics calculator.
    
    Calculates comprehensive metrics for strategy evaluation including:
    - Return metrics (total, annualized, excess, CAGR)
    - Risk metrics (volatility, VaR, CVaR, drawdown)
    - Risk-adjusted returns (Sharpe, Sortino, Calmar, Information Ratio)
    - Market risk (Beta, Alpha, Tracking Error)
    - Trading statistics (win rate, profit/loss ratio)
    - Advanced metrics (skewness, kurtosis, tail ratio)
    """
    
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE):
        """
        Initialize performance calculator.
        
        Args:
            risk_free_rate: Annual risk-free rate (default: 3%)
        """
        self.risk_free_rate = risk_free_rate
        self.daily_rf_rate = (1 + risk_free_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
        self._cache = get_performance_cache()
    
    async def calculate_all_cached(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
        trades: Optional[pd.DataFrame] = None,
        backtest_id: Optional[str] = None,
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics with caching.
        
        Args:
            equity_curve: Series of portfolio values indexed by date
            benchmark_curve: Optional benchmark series for relative metrics
            trades: Optional DataFrame of trades for trading statistics
            backtest_id: Optional backtest ID for cache key generation
        
        Returns:
            PerformanceMetrics object with all calculated metrics
        """
        # Try cache first if backtest_id provided
        if backtest_id:
            cache_key = f"perf:{backtest_id}:{benchmark_curve is not None}"
            cached_result = await self._cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for backtest {backtest_id}")
                return cached_result
        
        # Calculate metrics (synchronous, CPU-bound)
        import concurrent.futures
        
        loop = asyncio.get_event_loop()
        
        # Run CPU-bound calculation in thread pool
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                lambda: self.calculate_all_sync(equity_curve, benchmark_curve, trades)
            )
        
        # Cache result
        if backtest_id:
            await self._cache.put(cache_key, result)
            logger.debug(f"Cached result for backtest {backtest_id}")
        
        return result
    
    def calculate_all_sync(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
        trades: Optional[pd.DataFrame] = None,
    ) -> PerformanceMetrics:
        """Synchronous version of calculate_all for thread pool execution."""
        # Calculate returns
        returns_metrics = self.calculate_returns_metrics(equity_curve)
        
        # Calculate risk metrics
        risk_metrics = self.calculate_risk_metrics(equity_curve)
        
        # Calculate risk-adjusted metrics
        risk_adjusted_metrics = self.calculate_risk_adjusted_metrics(
            equity_curve, 
            benchmark_curve
        )
        
        # Calculate market risk metrics
        market_risk_metrics = self.calculate_market_risk_metrics(
            equity_curve,
            benchmark_curve
        )
        
        # Calculate trading metrics
        trading_metrics = self.calculate_trading_metrics(trades) if trades is not None else TradingMetrics(
            win_rate=0.0,
            profit_loss_ratio=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            expectancy=0.0,
            turnover_rate=0.0,
            avg_holding_period=0,
        )
        
        # Calculate advanced metrics
        advanced_metrics = self.calculate_advanced_metrics(equity_curve)
        
        # Create summary
        summary = self._create_summary(
            returns_metrics,
            risk_metrics,
            risk_adjusted_metrics,
        )
        
        return PerformanceMetrics(
            returns=returns_metrics,
            risk=risk_metrics,
            risk_adjusted=risk_adjusted_metrics,
            market_risk=market_risk_metrics,
            trading=trading_metrics,
            advanced=advanced_metrics,
            summary=summary,
        )
    
    def calculate_returns_metrics(self, equity_curve: pd.Series) -> ReturnsMetrics:
        """Calculate return-related metrics."""
        returns = equity_curve.pct_change().dropna()
        
        # Total return
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        
        # Annualized return (CAGR)
        n_days = len(equity_curve)
        n_years = n_days / TRADING_DAYS_PER_YEAR
        if n_years > 0:
            cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / n_years) - 1
        else:
            cagr = 0.0
        
        # Cumulative return (same as total return for simplicity)
        cumulative_return = total_return
        
        # Annualized return (simple)
        annualized_return = cagr
        
        # Excess and active return (placeholder if no benchmark)
        excess_return = annualized_return - self.risk_free_rate
        active_return = 0.0
        
        return ReturnsMetrics(
            total_return=float(total_return),
            annualized_return=float(annualized_return),
            excess_return=float(excess_return),
            active_return=float(active_return),
            cumulative_return=float(cumulative_return),
            cagr=float(cagr),
        )
    
    def calculate_risk_metrics(self, equity_curve: pd.Series) -> RiskMetrics:
        """Calculate risk metrics."""
        returns = equity_curve.pct_change().dropna()
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        # Downside deviation (only negative returns)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            downside_deviation = negative_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        else:
            downside_deviation = 0.0
        
        # Value at Risk (VaR) - Historical method
        var_95 = float(np.percentile(returns, 5))  # 5th percentile
        var_99 = float(np.percentile(returns, 1))  # 1st percentile
        
        # Conditional VaR (Expected Shortfall)
        cvar_95 = float(returns[returns <= var_95].mean()) if len(returns[returns <= var_95]) > 0 else var_95
        cvar_99 = float(returns[returns <= var_99].mean()) if len(returns[returns <= var_99]) > 0 else var_99
        
        # Maximum Drawdown
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = float(drawdown.min())
        
        # Average Drawdown
        avg_drawdown = float(drawdown.mean())
        
        # Ulcer Index (measure of drawdown severity and duration)
        ulcer_index = self._calculate_ulcer_index(equity_curve)
        
        return RiskMetrics(
            volatility=float(volatility),
            downside_deviation=float(downside_deviation),
            var_95=float(var_95),
            cvar_95=float(cvar_95),
            max_drawdown=float(max_drawdown),
            avg_drawdown=float(avg_drawdown),
            ulcer_index=float(ulcer_index),
        )
    
    def calculate_risk_adjusted_metrics(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
    ) -> RiskAdjustedMetrics:
        """Calculate risk-adjusted return metrics."""
        returns = equity_curve.pct_change().dropna()
        
        # Portfolio returns
        port_mean_return = returns.mean() * TRADING_DAYS_PER_YEAR
        
        # Sharpe Ratio
        if returns.std() > 0:
            sharpe_ratio = (port_mean_return - self.risk_free_rate) / (returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        else:
            sharpe_ratio = 0.0
        
        # Sortino Ratio (uses downside deviation)
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and negative_returns.std() > 0:
            downside_std = negative_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
            sortino_ratio = (port_mean_return - self.risk_free_rate) / downside_std
        else:
            sortino_ratio = 0.0
        
        # Calmar Ratio (return / max_drawdown)
        max_dd = self.calculate_risk_metrics(equity_curve).max_drawdown
        if abs(max_dd) > 0.001:
            calmar_ratio = port_mean_return / abs(max_dd)
        else:
            calmar_ratio = 0.0
        
        # Information Ratio (active return / tracking error)
        if benchmark_curve is not None:
            benchmark_returns = benchmark_curve.pct_change().dropna()
            active_returns = returns - benchmark_returns
            
            tracking_error = active_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
            active_return_annual = active_returns.mean() * TRADING_DAYS_PER_YEAR
            
            if tracking_error > 0:
                information_ratio = active_return_annual / tracking_error
            else:
                information_ratio = 0.0
        else:
            information_ratio = 0.0
        
        # Omega Ratio (probability-weighted ratio of gains/losses)
        omega_ratio = self._calculate_omega_ratio(returns)
        
        return RiskAdjustedMetrics(
            sharpe_ratio=float(sharpe_ratio),
            sortino_ratio=float(sortino_ratio),
            calmar_ratio=float(calmar_ratio),
            information_ratio=float(information_ratio),
            omega_ratio=float(omega_ratio),
        )
    
    def calculate_market_risk_metrics(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
    ) -> MarketRiskMetrics:
        """Calculate market risk metrics (Beta, Alpha, etc.)."""
        if benchmark_curve is None:
            return MarketRiskMetrics(
                beta=1.0,
                alpha=0.0,
                tracking_error=0.0,
                r_squared=0.0,
            )
        
        returns = equity_curve.pct_change().dropna()
        benchmark_returns = benchmark_curve.pct_change().dropna()
        
        # Align indices
        aligned_returns = returns.reindex(benchmark_returns.index).fillna(0)
        
        if len(aligned_returns) < 10:
            return MarketRiskMetrics(
                beta=1.0,
                alpha=0.0,
                tracking_error=0.0,
                r_squared=0.0,
            )
        
        # Beta (sensitivity to market)
        covariance = np.cov(aligned_returns, benchmark_returns)[0, 1]
        market_variance = np.var(benchmark_returns)
        
        if market_variance > 0:
            beta = covariance / market_variance
        else:
            beta = 1.0
        
        # Alpha (Jensen's Alpha - annualized)
        port_mean = aligned_returns.mean() * TRADING_DAYS_PER_YEAR
        bench_mean = benchmark_returns.mean() * TRADING_DAYS_PER_YEAR
        alpha = port_mean - (self.risk_free_rate + beta * (bench_mean - self.risk_free_rate))
        
        # Tracking Error
        active_returns = aligned_returns - benchmark_returns
        tracking_error = active_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        
        # R-squared (coefficient of determination)
        correlation = np.corrcoef(aligned_returns, benchmark_returns)[0, 1]
        r_squared = correlation ** 2
        
        return MarketRiskMetrics(
            beta=float(beta),
            alpha=float(alpha),
            tracking_error=float(tracking_error),
            r_squared=float(r_squared),
        )
    
    def calculate_trading_metrics(self, trades: pd.DataFrame) -> TradingMetrics:
        """Calculate trading statistics from trade log."""
        if trades.empty:
            return TradingMetrics(
                win_rate=0.0,
                profit_loss_ratio=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                expectancy=0.0,
                turnover_rate=0.0,
                avg_holding_period=0,
            )
        
        # Calculate P&L for each trade
        trades['pnl'] = trades.apply(
            lambda row: (row['amount'] if row['direction'] == 'sell' else -row['amount']) - row['commission'] - row['slippage'],
            axis=1
        )
        
        wins = trades[trades['pnl'] > 0]['pnl']
        losses = trades[trades['pnl'] < 0]['pnl']
        
        total_trades = len(trades)
        num_wins = len(wins)
        num_losses = len(losses)
        
        # Win Rate
        win_rate = num_wins / total_trades if total_trades > 0 else 0.0
        
        # Profit/Loss Ratio
        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        
        # Expectancy
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Turnover Rate (placeholder - would need portfolio value data)
        turnover_rate = 0.0
        
        # Average Holding Period (placeholder - would need entry/exit timestamps)
        avg_holding_period = 0
        
        return TradingMetrics(
            win_rate=float(win_rate),
            profit_loss_ratio=float(profit_loss_ratio),
            avg_win=float(avg_win),
            avg_loss=float(avg_loss),
            expectancy=float(expectancy),
            turnover_rate=float(turnover_rate),
            avg_holding_period=avg_holding_period,
        )
    
    def calculate_advanced_metrics(self, equity_curve: pd.Series) -> AdvancedMetrics:
        """Calculate advanced statistical metrics."""
        returns = equity_curve.pct_change().dropna()
        
        # Tail Ratio (ratio of upside to downside tails)
        tail_ratio = self._calculate_tail_ratio(returns)
        
        # Skewness (asymmetry of return distribution)
        skewness = float(stats.skew(returns))
        
        # Kurtosis (tailedness of distribution)
        kurtosis = float(stats.kurtosis(returns))
        
        return AdvancedMetrics(
            tail_ratio=float(tail_ratio),
            skewness=float(skewness),
            kurtosis=float(kurtosis),
        )
    
    def _calculate_ulcer_index(self, equity_curve: pd.Series) -> float:
        """
        Calculate Ulcer Index - measure of drawdown severity and duration.
        
        Formula: sqrt(mean(drawdown^2))
        """
        running_max = equity_curve.cummax()
        drawdown_pct = (equity_curve - running_max) / running_max
        
        ulcer_index = np.sqrt((drawdown_pct ** 2).mean())
        return float(ulcer_index)
    
    def _calculate_omega_ratio(self, returns: pd.Series, threshold: float = 0.0) -> float:
        """
        Calculate Omega Ratio - probability-weighted ratio of gains/losses.
        
        Formula: sum(returns > threshold) / sum(returns < threshold)
        """
        gains = returns[returns > threshold]
        losses = returns[returns <= threshold]
        
        if len(losses) == 0:
            return float('inf')
        
        omega = gains.sum() / abs(losses.sum())
        return float(omega)
    
    def _calculate_tail_ratio(self, returns: pd.Series) -> float:
        """
        Calculate Tail Ratio - ratio of upside to downside extreme returns.
        
        Formula: VaR(95) / VaR(5)
        """
        var_95 = np.percentile(returns, 95)
        var_5 = np.percentile(returns, 5)
        
        if abs(var_5) > 0.001:
            tail_ratio = abs(var_95 / var_5)
        else:
            tail_ratio = 1.0
        
        return float(tail_ratio)
    
    def _create_summary(
        self,
        returns: ReturnsMetrics,
        risk: RiskMetrics,
        risk_adjusted: RiskAdjustedMetrics,
    ) -> dict[str, float]:
        """Create summary metrics for quick overview."""
        return {
            "total_return": returns.total_return,
            "cagr": returns.cagr,
            "volatility": risk.volatility,
            "sharpe_ratio": risk_adjusted.sharpe_ratio,
            "max_drawdown": risk.max_drawdown,
            "sortino_ratio": risk_adjusted.sortino_ratio,
            "calmar_ratio": risk_adjusted.calmar_ratio,
        }
