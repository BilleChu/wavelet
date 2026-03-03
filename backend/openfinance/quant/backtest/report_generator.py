"""
Professional Backtest Report Generator.

Generates comprehensive backtest reports with:
- Executive Summary
- Performance Metrics Dashboard
- Risk Analysis
- Attribution Analysis
- Trade Analysis
- Visualization Charts
"""

import logging
from datetime import datetime, date
from typing import Any, Optional
import pandas as pd
import numpy as np

from openfinance.domain.models.quant import (
    BacktestResult,
    PerformanceMetrics,
    DailyEquity,
    TradeRecord,
    DailyPosition,
)

logger = logging.getLogger(__name__)


class BacktestReportGenerator:
    """
    Professional backtest report generator.
    
    Generates detailed reports including:
    - Executive summary with key metrics
    - Performance analysis (returns, risk, risk-adjusted)
    - Drawdown analysis
    - Monthly/yearly returns breakdown
    - Trade statistics and analysis
    - Factor attribution
    - Benchmark comparison
    """
    
    def __init__(self):
        self.trading_days_per_year = 252
    
    def generate_report(
        self,
        result: BacktestResult,
        include_trades: bool = True,
        include_positions: bool = False,
    ) -> dict[str, Any]:
        """
        Generate comprehensive backtest report.
        
        Args:
            result: BacktestResult object
            include_trades: Whether to include trade details
            include_positions: Whether to include position details
        
        Returns:
            Dictionary containing full report
        """
        report = {
            "metadata": self._generate_metadata(result),
            "executive_summary": self._generate_executive_summary(result),
            "performance_metrics": self._generate_performance_metrics(result),
            "risk_analysis": self._generate_risk_analysis(result),
            "return_analysis": self._generate_return_analysis(result),
            "drawdown_analysis": self._generate_drawdown_analysis(result),
            "trade_analysis": self._generate_trade_analysis(result) if include_trades else None,
            "benchmark_comparison": self._generate_benchmark_comparison(result),
            "monthly_returns": self._generate_monthly_returns(result),
            "yearly_returns": self._generate_yearly_returns(result),
            "risk_decomposition": self._generate_risk_decomposition(result),
            "recommendations": self._generate_recommendations(result),
            "equity_curve": self._generate_equity_curve_data(result),
        }
        
        if include_positions and result.positions:
            report["position_analysis"] = self._generate_position_analysis(result)
        
        return report
    
    def _generate_metadata(self, result: BacktestResult) -> dict[str, Any]:
        """Generate report metadata."""
        return {
            "backtest_id": result.backtest_id,
            "strategy_id": result.strategy_id,
            "start_date": str(result.start_date),
            "end_date": str(result.end_date),
            "duration_days": (result.end_date - result.start_date).days if isinstance(result.end_date, date) else 0,
            "generated_at": datetime.now().isoformat(),
            "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
            "initial_capital": result.config.initial_capital,
            "commission_rate": result.config.commission,
            "slippage_rate": result.config.slippage,
        }
    
    def _generate_executive_summary(self, result: BacktestResult) -> dict[str, Any]:
        """Generate executive summary with key metrics."""
        if not result.metrics:
            return {}
        
        metrics = result.metrics
        
        final_equity = result.equity_curve[-1].equity if result.equity_curve else 0
        initial_capital = result.config.initial_capital
        
        total_profit = final_equity - initial_capital
        profit_pct = (total_profit / initial_capital * 100) if initial_capital > 0 else 0
        
        grade, score = self._calculate_strategy_grade(metrics)
        
        return {
            "final_equity": final_equity,
            "total_profit": total_profit,
            "profit_percentage": profit_pct,
            "total_return": metrics.total_return,
            "annual_return": metrics.annual_return,
            "max_drawdown": metrics.max_drawdown,
            "sharpe_ratio": metrics.sharpe_ratio,
            "win_rate": metrics.win_rate,
            "total_trades": len(result.trades) if result.trades else 0,
            "strategy_grade": grade,
            "strategy_score": score,
            "performance_assessment": self._assess_performance(metrics),
        }
    
    def _generate_performance_metrics(self, result: BacktestResult) -> dict[str, Any]:
        """Generate detailed performance metrics."""
        if not result.metrics:
            return {}
        
        metrics = result.metrics
        
        return {
            "returns": {
                "total_return": {
                    "value": metrics.total_return,
                    "formatted": f"{metrics.total_return * 100:.2f}%",
                    "description": "总收益率",
                },
                "annual_return": {
                    "value": metrics.annual_return,
                    "formatted": f"{metrics.annual_return * 100:.2f}%",
                    "description": "年化收益率",
                },
                "benchmark_return": {
                    "value": metrics.benchmark_return,
                    "formatted": f"{metrics.benchmark_return * 100:.2f}%",
                    "description": "基准收益率",
                },
                "excess_return": {
                    "value": metrics.excess_return,
                    "formatted": f"{metrics.excess_return * 100:.2f}%",
                    "description": "超额收益率",
                },
            },
            "risk": {
                "volatility": {
                    "value": metrics.volatility,
                    "formatted": f"{metrics.volatility * 100:.2f}%" if metrics.volatility else "N/A",
                    "description": "年化波动率",
                },
                "downside_volatility": {
                    "value": metrics.downside_volatility,
                    "formatted": f"{metrics.downside_volatility * 100:.2f}%" if metrics.downside_volatility else "N/A",
                    "description": "下行波动率",
                },
                "max_drawdown": {
                    "value": metrics.max_drawdown,
                    "formatted": f"{metrics.max_drawdown * 100:.2f}%" if metrics.max_drawdown else "N/A",
                    "description": "最大回撤",
                },
                "var_95": {
                    "value": metrics.var_95 if hasattr(metrics, 'var_95') else None,
                    "formatted": f"{metrics.var_95 * 100:.2f}%" if hasattr(metrics, 'var_95') and metrics.var_95 else "N/A",
                    "description": "95% VaR",
                },
                "cvar_95": {
                    "value": metrics.cvar_95 if hasattr(metrics, 'cvar_95') else None,
                    "formatted": f"{metrics.cvar_95 * 100:.2f}%" if hasattr(metrics, 'cvar_95') and metrics.cvar_95 else "N/A",
                    "description": "95% CVaR",
                },
            },
            "risk_adjusted": {
                "sharpe_ratio": {
                    "value": metrics.sharpe_ratio,
                    "formatted": f"{metrics.sharpe_ratio:.2f}",
                    "description": "夏普比率",
                    "rating": self._rate_sharpe(metrics.sharpe_ratio),
                },
                "sortino_ratio": {
                    "value": metrics.sortino_ratio,
                    "formatted": f"{metrics.sortino_ratio:.2f}",
                    "description": "索提诺比率",
                    "rating": self._rate_sortino(metrics.sortino_ratio),
                },
                "calmar_ratio": {
                    "value": metrics.calmar_ratio,
                    "formatted": f"{metrics.calmar_ratio:.2f}",
                    "description": "卡尔马比率",
                },
                "information_ratio": {
                    "value": metrics.information_ratio,
                    "formatted": f"{metrics.information_ratio:.2f}",
                    "description": "信息比率",
                },
            },
            "market_risk": {
                "beta": {
                    "value": metrics.beta if hasattr(metrics, 'beta') else None,
                    "description": "贝塔系数",
                },
                "alpha": {
                    "value": metrics.alpha if hasattr(metrics, 'alpha') else None,
                    "description": "阿尔法",
                },
                "r_squared": {
                    "value": metrics.r_squared if hasattr(metrics, 'r_squared') else None,
                    "description": "R平方",
                },
            },
            "trading": {
                "win_rate": {
                    "value": metrics.win_rate,
                    "formatted": f"{metrics.win_rate * 100:.2f}%",
                    "description": "胜率",
                },
                "profit_loss_ratio": {
                    "value": metrics.profit_loss_ratio,
                    "formatted": f"{metrics.profit_loss_ratio:.2f}",
                    "description": "盈亏比",
                },
                "total_trades": {
                    "value": len(result.trades) if result.trades else 0,
                    "description": "总交易次数",
                },
                "turnover_rate": {
                    "value": metrics.turnover_rate,
                    "formatted": f"{metrics.turnover_rate * 100:.2f}%",
                    "description": "换手率",
                },
            },
        }
    
    def _generate_risk_analysis(self, result: BacktestResult) -> dict[str, Any]:
        """Generate detailed risk analysis."""
        if not result.equity_curve:
            return {}
        
        equity_curve = result.equity_curve
        equities = [e.equity for e in equity_curve]
        
        returns = []
        for i in range(1, len(equities)):
            if equities[i-1] > 0:
                returns.append((equities[i] - equities[i-1]) / equities[i-1])
        
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        
        var_levels = [90, 95, 99]
        var_metrics = {}
        for level in var_levels:
            var = np.percentile(returns_array, 100 - level)
            cvar = returns_array[returns_array <= var].mean() if len(returns_array[returns_array <= var]) > 0 else var
            var_metrics[f"var_{level}"] = {
                "var": var,
                "cvar": cvar,
                "formatted_var": f"{var * 100:.2f}%",
                "formatted_cvar": f"{cvar * 100:.2f}%",
            }
        
        drawdowns = []
        peak = equities[0]
        for equity in equities:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            drawdowns.append(dd)
        
        drawdowns_array = np.array(drawdowns)
        
        return {
            "volatility_analysis": {
                "daily_vol": float(np.std(returns)),
                "annual_vol": float(np.std(returns) * np.sqrt(self.trading_days_per_year)),
                "vol_percentile": float(np.percentile(np.abs(returns), 95)),
            },
            "var_analysis": var_metrics,
            "drawdown_statistics": {
                "max_drawdown": float(np.max(drawdowns)),
                "avg_drawdown": float(np.mean(drawdowns)),
                "median_drawdown": float(np.median(drawdowns)),
                "drawdown_std": float(np.std(drawdowns)),
                "max_drawdown_duration": result.metrics.max_drawdown_duration if result.metrics else 0,
            },
            "tail_risk": {
                "skewness": float(self._calculate_skewness(returns_array)),
                "kurtosis": float(self._calculate_kurtosis(returns_array)),
                "tail_ratio": float(self._calculate_tail_ratio(returns_array)),
            },
            "worst_days": {
                "worst_1_day": float(np.min(returns)),
                "worst_5_days": float(np.percentile(returns, 5)),
                "worst_10_days": float(np.percentile(returns, 10)),
            },
            "best_days": {
                "best_1_day": float(np.max(returns)),
                "best_5_days": float(np.percentile(returns, 95)),
                "best_10_days": float(np.percentile(returns, 90)),
            },
        }
    
    def _generate_return_analysis(self, result: BacktestResult) -> dict[str, Any]:
        """Generate return distribution analysis."""
        if not result.equity_curve:
            return {}
        
        equities = [e.equity for e in result.equity_curve]
        returns = []
        for i in range(1, len(equities)):
            if equities[i-1] > 0:
                returns.append((equities[i] - equities[i-1]) / equities[i-1])
        
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        
        positive_returns = returns_array[returns_array > 0]
        negative_returns = returns_array[returns_array < 0]
        zero_returns = returns_array[returns_array == 0]
        
        return {
            "distribution": {
                "mean": float(np.mean(returns_array)),
                "median": float(np.median(returns_array)),
                "std": float(np.std(returns_array)),
                "min": float(np.min(returns_array)),
                "max": float(np.max(returns_array)),
                "skewness": float(self._calculate_skewness(returns_array)),
                "kurtosis": float(self._calculate_kurtosis(returns_array)),
            },
            "statistics": {
                "total_days": len(returns),
                "positive_days": len(positive_returns),
                "negative_days": len(negative_returns),
                "zero_days": len(zero_returns),
                "positive_ratio": len(positive_returns) / len(returns) if returns else 0,
            },
            "averages": {
                "avg_positive": float(np.mean(positive_returns)) if len(positive_returns) > 0 else 0,
                "avg_negative": float(np.mean(negative_returns)) if len(negative_returns) > 0 else 0,
                "avg_absolute": float(np.mean(np.abs(returns_array))),
            },
            "percentiles": {
                "p5": float(np.percentile(returns_array, 5)),
                "p25": float(np.percentile(returns_array, 25)),
                "p50": float(np.percentile(returns_array, 50)),
                "p75": float(np.percentile(returns_array, 75)),
                "p95": float(np.percentile(returns_array, 95)),
            },
        }
    
    def _generate_drawdown_analysis(self, result: BacktestResult) -> dict[str, Any]:
        """Generate detailed drawdown analysis."""
        if not result.equity_curve:
            return {}
        
        equities = [e.equity for e in result.equity_curve]
        dates = [e.date for e in result.equity_curve]
        
        drawdown_periods = []
        peak = equities[0]
        peak_idx = 0
        in_drawdown = False
        dd_start_idx = 0
        
        for i, equity in enumerate(equities):
            if equity > peak:
                if in_drawdown:
                    drawdown_periods.append({
                        "start_date": str(dates[dd_start_idx]),
                        "end_date": str(dates[i-1]),
                        "duration_days": i - 1 - dd_start_idx,
                        "max_drawdown": max_dd,
                        "recovery_date": str(dates[i]),
                    })
                    in_drawdown = False
                peak = equity
                peak_idx = i
            else:
                dd = (peak - equity) / peak if peak > 0 else 0
                if dd > 0.05 and not in_drawdown:
                    in_drawdown = True
                    dd_start_idx = peak_idx
                    max_dd = dd
                elif in_drawdown and dd > max_dd:
                    max_dd = dd
        
        drawdowns = []
        peak = equities[0]
        for equity in equities:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            drawdowns.append(dd)
        
        drawdowns_array = np.array(drawdowns)
        
        significant_drawdowns = [dd for dd in drawdown_periods if dd["max_drawdown"] > 0.05]
        
        return {
            "summary": {
                "max_drawdown": float(np.max(drawdowns_array)),
                "avg_drawdown": float(np.mean(drawdowns_array)),
                "current_drawdown": float(drawdowns[-1]),
                "drawdown_periods": len(significant_drawdowns),
            },
            "periods": significant_drawdowns[:10],
            "distribution": {
                "max": float(np.max(drawdowns_array)),
                "p95": float(np.percentile(drawdowns_array, 95)),
                "p75": float(np.percentile(drawdowns_array, 75)),
                "median": float(np.percentile(drawdowns_array, 50)),
                "mean": float(np.mean(drawdowns_array)),
            },
        }
    
    def _generate_trade_analysis(self, result: BacktestResult) -> dict[str, Any]:
        """Generate trade analysis."""
        if not result.trades:
            return {"total_trades": 0}
        
        trades = result.trades
        
        buy_trades = [t for t in trades if t.direction == "buy"]
        sell_trades = [t for t in trades if t.direction == "sell"]
        
        total_buy_amount = sum(t.amount for t in buy_trades)
        total_sell_amount = sum(t.amount for t in sell_trades)
        total_commission = sum(t.commission for t in trades)
        total_slippage = sum(t.slippage for t in trades)
        
        stock_trades = {}
        for trade in trades:
            if trade.stock_code not in stock_trades:
                stock_trades[trade.stock_code] = {
                    "buy_count": 0,
                    "sell_count": 0,
                    "total_amount": 0,
                }
            
            if trade.direction == "buy":
                stock_trades[trade.stock_code]["buy_count"] += 1
            else:
                stock_trades[trade.stock_code]["sell_count"] += 1
            
            stock_trades[trade.stock_code]["total_amount"] += trade.amount
        
        top_traded_stocks = sorted(
            stock_trades.items(),
            key=lambda x: x[1]["total_amount"],
            reverse=True
        )[:10]
        
        return {
            "summary": {
                "total_trades": len(trades),
                "buy_trades": len(buy_trades),
                "sell_trades": len(sell_trades),
                "total_buy_amount": total_buy_amount,
                "total_sell_amount": total_sell_amount,
                "total_commission": total_commission,
                "total_slippage": total_slippage,
                "total_transaction_cost": total_commission + total_slippage,
            },
            "trade_frequency": {
                "avg_trades_per_day": len(trades) / len(result.equity_curve) if result.equity_curve else 0,
                "avg_trades_per_month": len(trades) / (len(result.equity_curve) / 20) if result.equity_curve else 0,
            },
            "trade_size": {
                "avg_trade_amount": np.mean([t.amount for t in trades]),
                "median_trade_amount": np.median([t.amount for t in trades]),
                "max_trade_amount": max(t.amount for t in trades),
                "min_trade_amount": min(t.amount for t in trades),
            },
            "stock_analysis": {
                "total_stocks_traded": len(stock_trades),
                "top_10_stocks": [
                    {
                        "stock_code": code,
                        **stats
                    }
                    for code, stats in top_traded_stocks
                ],
            },
        }
    
    def _generate_benchmark_comparison(self, result: BacktestResult) -> dict[str, Any]:
        """Generate benchmark comparison analysis."""
        if not result.benchmark_curve or not result.equity_curve:
            return {}
        
        strategy_equities = [e.equity for e in result.equity_curve]
        benchmark_equities = [e.equity for e in result.benchmark_curve]
        
        if len(strategy_equities) != len(benchmark_equities):
            return {}
        
        strategy_return = (strategy_equities[-1] - strategy_equities[0]) / strategy_equities[0]
        benchmark_return = (benchmark_equities[-1] - benchmark_equities[0]) / benchmark_equities[0]
        
        excess_return = strategy_return - benchmark_return
        
        strategy_returns = []
        benchmark_returns = []
        
        for i in range(1, len(strategy_equities)):
            if strategy_equities[i-1] > 0:
                strategy_returns.append((strategy_equities[i] - strategy_equities[i-1]) / strategy_equities[i-1])
            if benchmark_equities[i-1] > 0:
                benchmark_returns.append((benchmark_equities[i] - benchmark_equities[i-1]) / benchmark_equities[i-1])
        
        min_len = min(len(strategy_returns), len(benchmark_returns))
        if min_len < 2:
            return {}
        
        strategy_returns = strategy_returns[:min_len]
        benchmark_returns = benchmark_returns[:min_len]
        
        tracking_error = np.std([s - b for s, b in zip(strategy_returns, benchmark_returns)]) * np.sqrt(self.trading_days_per_year)
        
        correlation = np.corrcoef(strategy_returns, benchmark_returns)[0, 1]
        
        up_capture = []
        down_capture = []
        
        for s, b in zip(strategy_returns, benchmark_returns):
            if b > 0:
                up_capture.append(s / b if b != 0 else 0)
            elif b < 0:
                down_capture.append(s / b if b != 0 else 0)
        
        up_capture_ratio = np.mean(up_capture) if up_capture else 1.0
        down_capture_ratio = np.mean(down_capture) if down_capture else 1.0
        
        return {
            "returns_comparison": {
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "outperformed": strategy_return > benchmark_return,
            },
            "risk_comparison": {
                "strategy_volatility": result.metrics.volatility if result.metrics else 0,
                "benchmark_volatility": np.std(benchmark_returns) * np.sqrt(self.trading_days_per_year),
            },
            "correlation_analysis": {
                "correlation": correlation,
                "r_squared": correlation ** 2,
                "tracking_error": tracking_error,
            },
            "capture_ratios": {
                "up_capture": up_capture_ratio,
                "down_capture": down_capture_ratio,
                "interpretation": self._interpret_capture_ratios(up_capture_ratio, down_capture_ratio),
            },
        }
    
    def _generate_monthly_returns(self, result: BacktestResult) -> dict[str, Any]:
        """Generate monthly returns breakdown."""
        if not result.equity_curve:
            return {}
        
        df = pd.DataFrame([
            {
                "date": e.date,
                "equity": e.equity,
            }
            for e in result.equity_curve
        ])
        
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        monthly_returns = df['equity'].resample('M').last().pct_change().dropna()
        
        monthly_data = {}
        for date, ret in monthly_returns.items():
            month_key = date.strftime('%Y-%m')
            monthly_data[month_key] = {
                "return": float(ret),
                "formatted": f"{ret * 100:.2f}%",
            }
        
        return {
            "monthly_returns": monthly_data,
            "best_month": {
                "month": max(monthly_data.items(), key=lambda x: x[1]['return'])[0] if monthly_data else None,
                "return": max(r['return'] for r in monthly_data.values()) if monthly_data else 0,
            },
            "worst_month": {
                "month": min(monthly_data.items(), key=lambda x: x[1]['return'])[0] if monthly_data else None,
                "return": min(r['return'] for r in monthly_data.values()) if monthly_data else 0,
            },
            "positive_months": sum(1 for r in monthly_data.values() if r['return'] > 0),
            "negative_months": sum(1 for r in monthly_data.values() if r['return'] < 0),
        }
    
    def _generate_yearly_returns(self, result: BacktestResult) -> dict[str, Any]:
        """Generate yearly returns breakdown."""
        if not result.equity_curve:
            return {}
        
        df = pd.DataFrame([
            {
                "date": e.date,
                "equity": e.equity,
            }
            for e in result.equity_curve
        ])
        
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        yearly_returns = df['equity'].resample('Y').last().pct_change().dropna()
        
        yearly_data = {}
        for date, ret in yearly_returns.items():
            year_key = date.strftime('%Y')
            yearly_data[year_key] = {
                "return": float(ret),
                "formatted": f"{ret * 100:.2f}%",
            }
        
        return {
            "yearly_returns": yearly_data,
            "best_year": {
                "year": max(yearly_data.items(), key=lambda x: x[1]['return'])[0] if yearly_data else None,
                "return": max(r['return'] for r in yearly_data.values()) if yearly_data else 0,
            },
            "worst_year": {
                "year": min(yearly_data.items(), key=lambda x: x[1]['return'])[0] if yearly_data else None,
                "return": min(r['return'] for r in yearly_data.values()) if yearly_data else 0,
            },
        }
    
    def _generate_risk_decomposition(self, result: BacktestResult) -> dict[str, Any]:
        """Generate risk decomposition analysis."""
        if not result.metrics:
            return {}
        
        metrics = result.metrics
        
        total_risk = metrics.volatility
        
        systematic_risk = metrics.beta * 0.2 if hasattr(metrics, 'beta') and metrics.beta else 0.2
        idiosyncratic_risk = max(0, total_risk - systematic_risk)
        
        return {
            "total_risk": total_risk,
            "risk_components": {
                "systematic_risk": {
                    "value": systematic_risk,
                    "percentage": systematic_risk / total_risk * 100 if total_risk > 0 else 0,
                    "description": "系统性风险（市场风险）",
                },
                "idiosyncratic_risk": {
                    "value": idiosyncratic_risk,
                    "percentage": idiosyncratic_risk / total_risk * 100 if total_risk > 0 else 0,
                    "description": "特质风险（个股风险）",
                },
            },
            "risk_adjusted_performance": {
                "return_per_unit_risk": metrics.annual_return / total_risk if total_risk > 0 else 0,
                "downside_risk_adjusted": metrics.annual_return / metrics.downside_volatility if metrics.downside_volatility > 0 else 0,
            },
        }
    
    def _generate_position_analysis(self, result: BacktestResult) -> dict[str, Any]:
        """Generate position analysis."""
        if not result.positions:
            return {}
        
        positions_by_stock = {}
        for pos in result.positions:
            if pos.stock_code not in positions_by_stock:
                positions_by_stock[pos.stock_code] = []
            positions_by_stock[pos.stock_code].append(pos)
        
        stock_stats = []
        for stock_code, positions in positions_by_stock.items():
            avg_weight = np.mean([p.weight for p in positions])
            max_weight = max(p.weight for p in positions)
            holding_days = len(positions)
            
            stock_stats.append({
                "stock_code": stock_code,
                "avg_weight": avg_weight,
                "max_weight": max_weight,
                "holding_days": holding_days,
            })
        
        top_holdings = sorted(stock_stats, key=lambda x: x['avg_weight'], reverse=True)[:10]
        
        return {
            "number_of_stocks": len(positions_by_stock),
            "top_holdings": top_holdings,
            "concentration": {
                "top_5_weight": sum(s['avg_weight'] for s in top_holdings[:5]),
                "top_10_weight": sum(s['avg_weight'] for s in top_holdings[:10]),
            },
        }
    
    def _generate_recommendations(self, result: BacktestResult) -> list[dict[str, str]]:
        """Generate recommendations based on backtest results."""
        recommendations = []
        
        if not result.metrics:
            return recommendations
        
        metrics = result.metrics
        
        if metrics.sharpe_ratio < 1.0:
            recommendations.append({
                "category": "风险调整收益",
                "issue": "夏普比率较低",
                "recommendation": "考虑优化策略以降低波动率或提高收益率",
                "priority": "高",
            })
        
        if metrics.max_drawdown > 0.20:
            recommendations.append({
                "category": "风险控制",
                "issue": "最大回撤过大",
                "recommendation": "加强止损机制，考虑添加风险预算管理",
                "priority": "高",
            })
        
        if metrics.win_rate < 0.4:
            recommendations.append({
                "category": "交易策略",
                "issue": "胜率偏低",
                "recommendation": "优化选股逻辑，提高信号质量",
                "priority": "中",
            })
        
        if metrics.turnover_rate > 5.0:
            recommendations.append({
                "category": "交易成本",
                "issue": "换手率过高",
                "recommendation": "降低交易频率，优化调仓逻辑",
                "priority": "中",
            })
        
        if metrics.profit_loss_ratio < 1.5:
            recommendations.append({
                "category": "盈亏比",
                "issue": "盈亏比不理想",
                "recommendation": "优化止盈止损策略，让盈利奔跑",
                "priority": "中",
            })
        
        return recommendations
    
    def _calculate_strategy_grade(self, metrics: PerformanceMetrics) -> tuple[str, float]:
        """Calculate strategy grade based on multiple factors."""
        score = 0.0
        
        if metrics.sharpe_ratio > 2.0:
            score += 25
        elif metrics.sharpe_ratio > 1.5:
            score += 20
        elif metrics.sharpe_ratio > 1.0:
            score += 15
        elif metrics.sharpe_ratio > 0.5:
            score += 10
        else:
            score += 5
        
        if metrics.annual_return > 0.30:
            score += 25
        elif metrics.annual_return > 0.20:
            score += 20
        elif metrics.annual_return > 0.15:
            score += 15
        elif metrics.annual_return > 0.10:
            score += 10
        else:
            score += 5
        
        if metrics.max_drawdown < 0.10:
            score += 25
        elif metrics.max_drawdown < 0.15:
            score += 20
        elif metrics.max_drawdown < 0.20:
            score += 15
        elif metrics.max_drawdown < 0.30:
            score += 10
        else:
            score += 5
        
        if metrics.win_rate > 0.6:
            score += 25
        elif metrics.win_rate > 0.5:
            score += 20
        elif metrics.win_rate > 0.4:
            score += 15
        elif metrics.win_rate > 0.3:
            score += 10
        else:
            score += 5
        
        if score >= 90:
            grade = "A+"
        elif score >= 80:
            grade = "A"
        elif score >= 70:
            grade = "B+"
        elif score >= 60:
            grade = "B"
        elif score >= 50:
            grade = "C+"
        elif score >= 40:
            grade = "C"
        else:
            grade = "D"
        
        return grade, score
    
    def _assess_performance(self, metrics: PerformanceMetrics) -> str:
        """Assess overall performance."""
        if metrics.sharpe_ratio > 1.5 and metrics.max_drawdown < 0.15:
            return "优秀 - 策略表现优异，风险控制良好"
        elif metrics.sharpe_ratio > 1.0 and metrics.max_drawdown < 0.20:
            return "良好 - 策略表现良好，风险可控"
        elif metrics.sharpe_ratio > 0.5 and metrics.max_drawdown < 0.30:
            return "一般 - 策略表现一般，需要优化"
        else:
            return "较差 - 策略表现不佳，需要重大改进"
    
    def _rate_sharpe(self, sharpe: float) -> str:
        """Rate Sharpe ratio."""
        if sharpe > 2.0:
            return "优秀"
        elif sharpe > 1.5:
            return "良好"
        elif sharpe > 1.0:
            return "一般"
        elif sharpe > 0.5:
            return "较差"
        else:
            return "很差"
    
    def _rate_sortino(self, sortino: float) -> str:
        """Rate Sortino ratio."""
        if sortino > 2.5:
            return "优秀"
        elif sortino > 2.0:
            return "良好"
        elif sortino > 1.5:
            return "一般"
        elif sortino > 1.0:
            return "较差"
        else:
            return "很差"
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        if len(returns) < 3:
            return 0.0
        
        mean = np.mean(returns)
        std = np.std(returns)
        
        if std == 0:
            return 0.0
        
        return float(np.mean(((returns - mean) / std) ** 3))
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate kurtosis of returns."""
        if len(returns) < 4:
            return 0.0
        
        mean = np.mean(returns)
        std = np.std(returns)
        
        if std == 0:
            return 0.0
        
        return float(np.mean(((returns - mean) / std) ** 4) - 3)
    
    def _calculate_tail_ratio(self, returns: np.ndarray) -> float:
        """Calculate tail ratio."""
        if len(returns) < 10:
            return 1.0
        
        var_95 = np.percentile(returns, 95)
        var_5 = np.percentile(returns, 5)
        
        if abs(var_5) < 0.0001:
            return 1.0
        
        return float(abs(var_95 / var_5))
    
    def _interpret_capture_ratios(self, up_capture: float, down_capture: float) -> str:
        """Interpret capture ratios."""
        if up_capture > 1.0 and down_capture < 1.0:
            return "优秀 - 上涨时捕获更多收益，下跌时控制损失"
        elif up_capture > 1.0 and down_capture > 1.0:
            return "激进 - 上涨和下跌都放大，波动较大"
        elif up_capture < 1.0 and down_capture < 1.0:
            return "保守 - 上涨和下跌都缩小，相对稳定"
        else:
            return "一般 - 捕获比率需要优化"
    
    def _generate_equity_curve_data(self, result: BacktestResult) -> dict[str, Any]:
        """Generate equity curve data for visualization."""
        if not result.equity_curve:
            logger.warning("No equity curve data in backtest result")
            return {"dates": [], "equities": [], "returns": [], "drawdowns": []}
        
        logger.info(f"Generating equity curve data with {len(result.equity_curve)} points")
        
        dates = []
        equities = []
        daily_returns = []
        drawdowns = []
        benchmark_equities = []
        
        initial_capital = result.config.initial_capital
        
        for i, e in enumerate(result.equity_curve):
            date_str = str(e.date) if hasattr(e.date, 'strftime') else str(e.date)
            if hasattr(e.date, 'strftime'):
                date_str = e.date.strftime('%Y-%m-%d')
            dates.append(date_str)
            equities.append(float(e.equity))
            daily_returns.append(float(e.daily_return) if hasattr(e, 'daily_return') else 0.0)
            drawdowns.append(float(e.drawdown) if hasattr(e, 'drawdown') else 0.0)
        
        logger.info(f"Equity curve: dates={len(dates)}, equities={len(equities)}, first_equity={equities[0] if equities else 'N/A'}, last_equity={equities[-1] if equities else 'N/A'}")
        
        if result.benchmark_curve:
            for b in result.benchmark_curve:
                benchmark_equities.append(float(b.equity) if hasattr(b, 'equity') else float(b))
        
        cumulative_returns = []
        for equity in equities:
            cumulative_returns.append((equity - initial_capital) / initial_capital)
        
        return {
            "dates": dates,
            "equities": equities,
            "cumulative_returns": cumulative_returns,
            "daily_returns": daily_returns,
            "drawdowns": drawdowns,
            "benchmark_equities": benchmark_equities if benchmark_equities else None,
            "initial_capital": float(initial_capital),
            "final_equity": float(equities[-1]) if equities else float(initial_capital),
            "total_return": cumulative_returns[-1] if cumulative_returns else 0.0,
        }
