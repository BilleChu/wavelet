"""
Performance Metrics Calculator for Quantitative Analysis.

Provides comprehensive performance metrics calculation.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np

from openfinance.models.quant import (
    DailyEquity,
    PerformanceMetrics,
    BacktestConfig,
)

logger = logging.getLogger(__name__)


class BacktestCalculator:
    """Calculator for performance metrics for backtesting.

    Provides:
    - Return metrics (total, annual, excess)
    - Risk metrics (volatility, drawdown, VaR)
    - Risk-adjusted metrics (Sharpe, Sortino, Calmar)
    - Trade statistics (win rate, profit/loss ratio)
    """

    def __init__(self) -> None:
        self._trading_days_per_year = 252

    def calculate(
        self,
        equity_curve: list[DailyEquity],
        benchmark_curve: list[DailyEquity] | None,
        config: BacktestConfig,
    ) -> PerformanceMetrics:
        """Calculate all performance metrics.

        Args:
            equity_curve: Daily equity values.
            benchmark_curve: Benchmark equity values.
            config: Backtest configuration.

        Returns:
            PerformanceMetrics with all calculated values.
        """
        if not equity_curve:
            return PerformanceMetrics()

        returns = self._calculate_returns(equity_curve)
        benchmark_returns = self._calculate_returns(benchmark_curve) if benchmark_curve else []

        total_return = self._calc_total_return(equity_curve)
        annual_return = self._calc_annual_return(returns)
        volatility = self._calc_annual_volatility(returns)
        downside_volatility = self._calc_downside_volatility(returns, config.risk_free_rate)

        benchmark_return = 0.0
        if benchmark_curve:
            benchmark_return = self._calc_total_return(benchmark_curve)

        excess_return = annual_return - benchmark_return

        sharpe_ratio = self._calc_sharpe_ratio(returns, config.risk_free_rate)
        sortino_ratio = self._calc_sortino_ratio(returns, config.risk_free_rate)
        max_drawdown = self._calc_max_drawdown(equity_curve)
        calmar_ratio = self._calc_calmar_ratio(annual_return, max_drawdown)

        information_ratio = 0.0
        if benchmark_returns:
            information_ratio = self._calc_information_ratio(returns, benchmark_returns)

        max_drawdown_duration = self._calc_max_drawdown_duration(equity_curve)
        recovery_days = self._calc_recovery_days(equity_curve)

        win_rate, profit_loss_ratio, avg_profit, avg_loss, max_wins, max_losses = \
            self._calc_trade_statistics(equity_curve)

        alpha, beta, r_squared = self._calc_regression_metrics(
            returns,
            benchmark_returns,
            config.risk_free_rate,
        )

        var_95 = self._calc_var(returns, 0.95)
        cvar_95 = self._calc_cvar(returns, 0.95)

        total_trades = self._estimate_trade_count(equity_curve)
        turnover_rate = self._estimate_turnover(equity_curve)

        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            volatility=volatility,
            downside_volatility=downside_volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            information_ratio=information_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            recovery_days=recovery_days,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            max_consecutive_wins=max_wins,
            max_consecutive_losses=max_losses,
            alpha=alpha,
            beta=beta,
            r_squared=r_squared,
            var_95=var_95,
            cvar_95=cvar_95,
            total_trades=total_trades,
            turnover_rate=turnover_rate,
        )

    def _calculate_returns(self, equity_curve: list[DailyEquity]) -> list[float]:
        """Calculate daily returns from equity curve."""
        if len(equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i - 1].equity
            curr_equity = equity_curve[i].equity
            if prev_equity > 0:
                returns.append((curr_equity - prev_equity) / prev_equity)
            else:
                returns.append(0.0)

        return returns

    def _calc_total_return(self, equity_curve: list[DailyEquity]) -> float:
        """Calculate total return."""
        if not equity_curve:
            return 0.0
        initial = equity_curve[0].equity
        final = equity_curve[-1].equity
        return (final - initial) / initial if initial > 0 else 0.0

    def _calc_annual_return(self, returns: list[float]) -> float:
        """Calculate annualized return."""
        if not returns:
            return 0.0

        cumulative = 1.0
        for r in returns:
            cumulative *= (1 + r)

        n_years = len(returns) / self._trading_days_per_year
        if n_years <= 0:
            return 0.0

        return (cumulative ** (1 / n_years) - 1)

    def _calc_annual_volatility(self, returns: list[float]) -> float:
        """Calculate annualized volatility."""
        if len(returns) < 2:
            return 0.0

        return float(np.std(returns) * np.sqrt(self._trading_days_per_year))

    def _calc_downside_volatility(
        self,
        returns: list[float],
        risk_free_rate: float,
    ) -> float:
        """Calculate downside volatility."""
        if len(returns) < 2:
            return 0.0

        daily_rf = risk_free_rate / self._trading_days_per_year
        downside_returns = [r for r in returns if r < daily_rf]

        if not downside_returns:
            return 0.0

        return float(np.std(downside_returns) * np.sqrt(self._trading_days_per_year))

    def _calc_sharpe_ratio(
        self,
        returns: list[float],
        risk_free_rate: float,
    ) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0

        excess_returns = [r - risk_free_rate / self._trading_days_per_year for r in returns]
        mean_excess = np.mean(excess_returns)
        std_returns = np.std(returns)

        if std_returns == 0:
            return 0.0

        return float(mean_excess / std_returns * np.sqrt(self._trading_days_per_year))

    def _calc_sortino_ratio(
        self,
        returns: list[float],
        risk_free_rate: float,
    ) -> float:
        """Calculate Sortino ratio."""
        if len(returns) < 2:
            return 0.0

        excess_returns = [r - risk_free_rate / self._trading_days_per_year for r in returns]
        mean_excess = np.mean(excess_returns)
        downside_vol = self._calc_downside_volatility(returns, risk_free_rate)

        if downside_vol == 0:
            return 0.0

        return float(mean_excess * self._trading_days_per_year / downside_vol)

    def _calc_max_drawdown(self, equity_curve: list[DailyEquity]) -> float:
        """Calculate maximum drawdown."""
        if not equity_curve:
            return 0.0

        peak = equity_curve[0].equity
        max_dd = 0.0

        for eq in equity_curve:
            if eq.equity > peak:
                peak = eq.equity

            dd = (peak - eq.equity) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        return max_dd

    def _calc_calmar_ratio(
        self,
        annual_return: float,
        max_drawdown: float,
    ) -> float:
        """Calculate Calmar ratio."""
        if max_drawdown == 0:
            return 0.0
        return annual_return / max_drawdown

    def _calc_information_ratio(
        self,
        returns: list[float],
        benchmark_returns: list[float],
    ) -> float:
        """Calculate information ratio."""
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return 0.0

        min_len = min(len(returns), len(benchmark_returns))
        excess = [returns[i] - benchmark_returns[i] for i in range(min_len)]

        mean_excess = np.mean(excess)
        std_excess = np.std(excess)

        if std_excess == 0:
            return 0.0

        return float(mean_excess / std_excess * np.sqrt(self._trading_days_per_year))

    def _calc_max_drawdown_duration(
        self,
        equity_curve: list[DailyEquity],
    ) -> int:
        """Calculate maximum drawdown duration in days."""
        if not equity_curve:
            return 0

        peak = equity_curve[0].equity
        peak_idx = 0
        max_duration = 0

        for i, eq in enumerate(equity_curve):
            if eq.equity >= peak:
                peak = eq.equity
                peak_idx = i
            else:
                duration = i - peak_idx
                max_duration = max(max_duration, duration)

        return max_duration

    def _calc_recovery_days(self, equity_curve: list[DailyEquity]) -> int | None:
        """Calculate recovery days from max drawdown."""
        if not equity_curve:
            return None

        peak = equity_curve[0].equity
        peak_idx = 0
        trough_idx = 0
        trough = peak

        for i, eq in enumerate(equity_curve):
            if eq.equity > peak:
                peak = eq.equity
                peak_idx = i
                trough = peak
                trough_idx = i
            elif eq.equity < trough:
                trough = eq.equity
                trough_idx = i

        for i in range(trough_idx, len(equity_curve)):
            if equity_curve[i].equity >= peak:
                return i - trough_idx

        return None

    def _calc_trade_statistics(
        self,
        equity_curve: list[DailyEquity],
    ) -> tuple[float, float, float, float, int, int]:
        """Calculate trade statistics."""
        if len(equity_curve) < 2:
            return 0.0, 0.0, 0.0, 0.0, 0, 0

        returns = self._calculate_returns(equity_curve)

        profits = [r for r in returns if r > 0]
        losses = [r for r in returns if r < 0]

        win_rate = len(profits) / len(returns) if returns else 0.0
        avg_profit = np.mean(profits) if profits else 0.0
        avg_loss = abs(np.mean(losses)) if losses else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for r in returns:
            if r > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif r < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return win_rate, profit_loss_ratio, avg_profit, avg_loss, max_wins, max_losses

    def _calc_regression_metrics(
        self,
        returns: list[float],
        benchmark_returns: list[float],
        risk_free_rate: float,
    ) -> tuple[float | None, float | None, float | None]:
        """Calculate alpha, beta, and R-squared."""
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return None, None, None

        min_len = min(len(returns), len(benchmark_returns))
        y = np.array(returns[:min_len])
        x = np.array(benchmark_returns[:min_len])

        if len(x) < 2:
            return None, None, None

        covariance = np.cov(x, y)[0, 1]
        variance = np.var(x)

        if variance == 0:
            return None, None, None

        beta = covariance / variance

        daily_rf = risk_free_rate / self._trading_days_per_year
        alpha = np.mean(y) - beta * np.mean(x) - daily_rf
        alpha = alpha * self._trading_days_per_year

        y_pred = beta * x
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return float(alpha), float(beta), float(r_squared)

    def _calc_var(self, returns: list[float], confidence: float) -> float:
        """Calculate Value at Risk."""
        if len(returns) < 2:
            return 0.0

        return float(np.percentile(returns, (1 - confidence) * 100))

    def _calc_cvar(self, returns: list[float], confidence: float) -> float:
        """Calculate Conditional Value at Risk."""
        if len(returns) < 2:
            return 0.0

        var = self._calc_var(returns, confidence)
        tail_returns = [r for r in returns if r <= var]

        return float(np.mean(tail_returns)) if tail_returns else var

    def _estimate_trade_count(self, equity_curve: list[DailyEquity]) -> int:
        """Estimate number of trades."""
        if len(equity_curve) < 2:
            return 0

        trades = 0
        for i in range(1, len(equity_curve)):
            if equity_curve[i].position_value != equity_curve[i - 1].position_value:
                trades += 1

        return trades // 2

    def _estimate_turnover(self, equity_curve: list[DailyEquity]) -> float:
        """Estimate portfolio turnover rate."""
        if len(equity_curve) < 2:
            return 0.0

        total_turnover = 0.0
        for eq in equity_curve:
            total_turnover += abs(eq.position_value)

        avg_equity = np.mean([eq.equity for eq in equity_curve])

        return total_turnover / (2 * avg_equity) if avg_equity > 0 else 0.0
