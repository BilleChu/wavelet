"""
Backtest Engine for Quantitative Analysis.

Provides comprehensive backtesting capabilities with realistic
simulation of trading conditions.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from openfinance.domain.models.quant import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus,
    Strategy,
    TradeRecord,
    DailyEquity,
    DailyPosition,
    PerformanceMetrics,
    FactorValue,
)
from openfinance.quant.strategy.engine import StrategyEngine
from openfinance.quant.backtest.metrics import BacktestCalculator

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtest engine for strategy evaluation.

    Provides:
    - Historical data backtesting
    - Trade simulation with realistic costs
    - Performance metrics calculation
    - Benchmark comparison
    """

    def __init__(self) -> None:
        self._strategy_engine = StrategyEngine()
        self._performance_calc = BacktestCalculator()
        self._backtest_results: dict[str, BacktestResult] = {}

    async def run(
        self,
        strategy: Strategy,
        config: BacktestConfig,
        price_data: pd.DataFrame,
        factor_values: dict[str, list[FactorValue]] | None = None,
        benchmark_data: pd.DataFrame | None = None,
    ) -> BacktestResult:
        """Run backtest for a strategy.

        Args:
            strategy: Strategy to backtest.
            config: Backtest configuration.
            price_data: Historical price data.
            factor_values: Pre-calculated factor values.
            benchmark_data: Benchmark price data.

        Returns:
            BacktestResult with performance metrics.
        """
        start_time = time.time()

        try:
            price_data = self._prepare_price_data(price_data, config)

            dates = sorted(price_data["trade_date"].unique())

            equity_curve: list[DailyEquity] = []
            positions: list[DailyPosition] = []
            trades: list[TradeRecord] = []

            cash = config.initial_capital
            current_positions: dict[str, dict[str, Any]] = {}

            rebalance_dates = self._get_rebalance_dates(
                dates,
                strategy.rebalance_freq,
            )

            for i, date in enumerate(dates):
                daily_data = price_data[price_data["trade_date"] == date]

                if date in rebalance_dates:
                    signals = self._generate_signals(
                        strategy,
                        daily_data,
                        factor_values,
                        date,
                    )

                    weights = self._strategy_engine.calculate_weights(
                        strategy,
                        signals,
                        daily_data,
                    )

                    trades_today = self._rebalance_portfolio(
                        current_positions,
                        weights,
                        daily_data,
                        cash,
                        config,
                        date,
                    )
                    trades.extend(trades_today)

                    for trade in trades_today:
                        if trade.direction == "buy":
                            cash -= trade.amount + trade.commission + trade.slippage
                        else:
                            cash += trade.amount - trade.commission - trade.slippage

                    current_positions = self._update_positions(
                        current_positions,
                        trades_today,
                        daily_data,
                    )

                position_value = sum(
                    pos["quantity"] * pos["price"]
                    for pos in current_positions.values()
                )
                total_equity = cash + position_value

                daily_return = 0.0
                if equity_curve:
                    prev_equity = equity_curve[-1].equity
                    daily_return = (total_equity - prev_equity) / prev_equity if prev_equity > 0 else 0

                cumulative_return = (total_equity / config.initial_capital - 1)

                drawdown = 0.0
                if equity_curve:
                    peak = max(e.equity for e in equity_curve)
                    drawdown = (peak - total_equity) / peak if peak > 0 else 0

                equity_curve.append(DailyEquity(
                    date=date,
                    equity=total_equity,
                    cash=cash,
                    position_value=position_value,
                    daily_return=daily_return,
                    cumulative_return=cumulative_return,
                    drawdown=drawdown,
                ))

                for stock_code, pos in current_positions.items():
                    stock_price = self._get_stock_price(daily_data, stock_code)
                    if stock_price:
                        positions.append(DailyPosition(
                            date=date,
                            stock_code=stock_code,
                            quantity=pos["quantity"],
                            market_value=pos["quantity"] * stock_price,
                            weight=pos["quantity"] * stock_price / total_equity if total_equity > 0 else 0,
                        ))

            benchmark_curve = self._calculate_benchmark_curve(
                benchmark_data,
                config,
                dates,
            )

            metrics = self._performance_calc.calculate(
                equity_curve,
                benchmark_curve,
                config,
            )

            duration_ms = (time.time() - start_time) * 1000

            result = BacktestResult(
                backtest_id=config.backtest_id,
                strategy_id=strategy.strategy_id,
                config=config,
                status=BacktestStatus.COMPLETED,
                equity_curve=equity_curve,
                positions=positions,
                trades=trades,
                metrics=metrics,
                benchmark_curve=benchmark_curve,
                start_date=config.start_date,
                end_date=config.end_date,
                duration_ms=duration_ms,
            )

            self._backtest_results[config.backtest_id] = result

            return result

        except Exception as e:
            logger.exception(f"Backtest failed: {strategy.strategy_id}")
            return BacktestResult(
                backtest_id=config.backtest_id,
                strategy_id=strategy.strategy_id,
                config=config,
                status=BacktestStatus.FAILED,
                start_date=config.start_date,
                end_date=config.end_date,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    def _prepare_price_data(
        self,
        price_data: pd.DataFrame,
        config: BacktestConfig,
    ) -> pd.DataFrame:
        """Prepare and filter price data."""
        df = price_data.copy()

        if "trade_date" not in df.columns:
            raise ValueError("price_data must have 'trade_date' column")

        df = df[
            (df["trade_date"] >= config.start_date) &
            (df["trade_date"] <= config.end_date)
        ]

        return df

    def _get_rebalance_dates(
        self,
        dates: list,
        frequency: str,
    ) -> set:
        """Get rebalance dates based on frequency."""
        rebalance_dates = set()

        if frequency == "daily":
            return set(dates)

        dates_dt = [d if isinstance(d, datetime) else pd.to_datetime(d) for d in dates]

        if frequency == "weekly":
            week_start = None
            for d in dates_dt:
                if week_start is None or d.isocalendar()[1] != week_start:
                    week_start = d.isocalendar()[1]
                    rebalance_dates.add(d)

        elif frequency == "monthly":
            month_start = None
            for d in dates_dt:
                if month_start is None or d.month != month_start:
                    month_start = d.month
                    rebalance_dates.add(d)

        elif frequency == "quarterly":
            quarter_start = None
            for d in dates_dt:
                quarter = (d.month - 1) // 3 + 1
                if quarter_start is None or quarter != quarter_start:
                    quarter_start = quarter
                    rebalance_dates.add(d)

        return rebalance_dates

    def _generate_signals(
        self,
        strategy: Strategy,
        daily_data: pd.DataFrame,
        factor_values: dict[str, list[FactorValue]] | None,
        date: datetime,
    ) -> dict[str, float]:
        """Generate trading signals."""
        signals = {}

        if factor_values:
            signals = self._strategy_engine.generate_signals(
                strategy,
                factor_values,
                date,
            )
        else:
            for _, row in daily_data.iterrows():
                stock_code = row.get("stock_code", "")
                if "momentum_20" in row:
                    signals[stock_code] = row["momentum_20"]
                elif "close" in row and len(daily_data) > 20:
                    signals[stock_code] = np.random.randn()

        return signals

    def _rebalance_portfolio(
        self,
        current_positions: dict[str, dict[str, Any]],
        target_weights: dict[str, float],
        daily_data: pd.DataFrame,
        cash: float,
        config: BacktestConfig,
        date: datetime,
    ) -> list[TradeRecord]:
        """Rebalance portfolio to target weights."""
        trades = []

        total_equity = cash + sum(
            pos["quantity"] * pos["price"]
            for pos in current_positions.values()
        )

        for stock_code in list(current_positions.keys()):
            if stock_code not in target_weights:
                pos = current_positions[stock_code]
                price = self._get_stock_price(daily_data, stock_code)

                if price and price > 0:
                    quantity = pos["quantity"]
                    amount = quantity * price
                    commission = amount * config.commission
                    slippage = amount * config.slippage

                    trades.append(TradeRecord(
                        backtest_id=config.backtest_id,
                        stock_code=stock_code,
                        trade_date=date,
                        direction="sell",
                        quantity=quantity,
                        price=price,
                        amount=amount,
                        commission=commission,
                        slippage=slippage,
                    ))

        for stock_code, weight in target_weights.items():
            target_value = total_equity * weight
            price = self._get_stock_price(daily_data, stock_code)

            if not price or price <= 0:
                continue

            current_qty = current_positions.get(stock_code, {}).get("quantity", 0)
            current_value = current_qty * price

            trade_value = target_value - current_value

            if abs(trade_value) > total_equity * 0.001:
                quantity = int(trade_value / price / 100) * 100

                if quantity != 0:
                    direction = "buy" if quantity > 0 else "sell"
                    quantity = abs(quantity)
                    amount = quantity * price
                    commission = amount * config.commission
                    slippage = amount * config.slippage

                    trades.append(TradeRecord(
                        backtest_id=config.backtest_id,
                        stock_code=stock_code,
                        trade_date=date,
                        direction=direction,
                        quantity=quantity,
                        price=price,
                        amount=amount,
                        commission=commission,
                        slippage=slippage,
                    ))

        return trades

    def _update_positions(
        self,
        current_positions: dict[str, dict[str, Any]],
        trades: list[TradeRecord],
        daily_data: pd.DataFrame,
    ) -> dict[str, dict[str, Any]]:
        """Update positions after trades."""
        positions = {
            k: v.copy()
            for k, v in current_positions.items()
        }

        for trade in trades:
            stock_code = trade.stock_code

            if stock_code not in positions:
                positions[stock_code] = {"quantity": 0, "price": trade.price}

            if trade.direction == "buy":
                positions[stock_code]["quantity"] += trade.quantity
            else:
                positions[stock_code]["quantity"] -= trade.quantity

            if positions[stock_code]["quantity"] <= 0:
                del positions[stock_code]

        for stock_code in positions:
            price = self._get_stock_price(daily_data, stock_code)
            if price:
                positions[stock_code]["price"] = price

        return positions

    def _get_stock_price(
        self,
        daily_data: pd.DataFrame,
        stock_code: str,
    ) -> float | None:
        """Get stock price from daily data."""
        stock_data = daily_data[daily_data["stock_code"] == stock_code]
        if not stock_data.empty:
            return float(stock_data["close"].iloc[-1])
        return None

    def _calculate_benchmark_curve(
        self,
        benchmark_data: pd.DataFrame | None,
        config: BacktestConfig,
        dates: list,
    ) -> list[DailyEquity]:
        """Calculate benchmark equity curve."""
        if benchmark_data is None or benchmark_data.empty:
            return []

        curve = []
        initial_value = config.initial_capital
        prev_value = initial_value

        for date in dates:
            bench_data = benchmark_data[benchmark_data["trade_date"] == date]
            if not bench_data.empty:
                daily_return = float(bench_data["daily_return"].iloc[-1])
                current_value = prev_value * (1 + daily_return)

                curve.append(DailyEquity(
                    date=date,
                    equity=current_value,
                    cash=current_value,
                    position_value=0,
                    daily_return=daily_return,
                    cumulative_return=(current_value / initial_value - 1),
                    drawdown=0,
                ))

                prev_value = current_value

        return curve

    def get_backtest_result(
        self,
        backtest_id: str,
    ) -> BacktestResult | None:
        """Get a stored backtest result."""
        return self._backtest_results.get(backtest_id)

    def list_backtests(self) -> list[BacktestResult]:
        """List all backtest results."""
        return list(self._backtest_results.values())

    def clear_backtests(self) -> None:
        """Clear all stored backtest results."""
        self._backtest_results.clear()
