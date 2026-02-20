"""
Attribution Analyzer for Quantitative Analysis.

Provides performance attribution analysis capabilities.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from openfinance.domain.models.quant import (
    AttributionResult,
    BacktestResult,
    DailyEquity,
)

logger = logging.getLogger(__name__)


class AttributionAnalyzer:
    """Analyzer for performance attribution.

    Provides:
    - Factor attribution
    - Sector attribution
    - Style attribution
    - Selection vs timing analysis
    """

    def __init__(self) -> None:
        pass

    def analyze(
        self,
        backtest_result: BacktestResult,
        factor_data: dict[str, pd.DataFrame] | None = None,
        sector_data: pd.DataFrame | None = None,
        style_data: pd.DataFrame | None = None,
    ) -> AttributionResult:
        """Perform attribution analysis.

        Args:
            backtest_result: Backtest result to analyze.
            factor_data: Factor returns by factor ID.
            sector_data: Sector returns data.
            style_data: Style returns data.

        Returns:
            AttributionResult with attribution breakdown.
        """
        factor_attribution = {}
        sector_attribution = {}
        style_attribution = {}

        if factor_data:
            factor_attribution = self._factor_attribution(
                backtest_result,
                factor_data,
            )

        if sector_data:
            sector_attribution = self._sector_attribution(
                backtest_result,
                sector_data,
            )

        if style_data:
            style_attribution = self._style_attribution(
                backtest_result,
                style_data,
            )

        selection_return = self._calc_selection_return(backtest_result)
        timing_return = self._calc_timing_return(backtest_result)
        interaction_return = self._calc_interaction_return(backtest_result)

        return AttributionResult(
            backtest_id=backtest_result.backtest_id,
            factor_attribution=factor_attribution,
            sector_attribution=sector_attribution,
            style_attribution=style_attribution,
            selection_return=selection_return,
            timing_return=timing_return,
            interaction_return=interaction_return,
        )

    def _factor_attribution(
        self,
        backtest_result: BacktestResult,
        factor_data: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        """Calculate factor attribution."""
        attribution = {}

        if not backtest_result.equity_curve:
            return attribution

        portfolio_returns = self._calculate_returns(backtest_result.equity_curve)

        for factor_id, factor_df in factor_data.items():
            if "daily_return" in factor_df.columns:
                factor_returns = factor_df["daily_return"].values

                min_len = min(len(portfolio_returns), len(factor_returns))
                if min_len > 0:
                    covariance = np.cov(
                        portfolio_returns[:min_len],
                        factor_returns[:min_len],
                    )[0, 1]
                    variance = np.var(factor_returns[:min_len])

                    if variance > 0:
                        beta = covariance / variance
                        factor_contribution = beta * np.mean(factor_returns[:min_len])
                        attribution[factor_id] = factor_contribution

        return attribution

    def _sector_attribution(
        self,
        backtest_result: BacktestResult,
        sector_data: pd.DataFrame,
    ) -> dict[str, float]:
        """Calculate sector attribution."""
        attribution = {}

        if sector_data.empty or not backtest_result.positions:
            return attribution

        sectors = sector_data["sector"].unique() if "sector" in sector_data.columns else []

        for sector in sectors:
            sector_positions = [
                p for p in backtest_result.positions
                if self._get_stock_sector(p.stock_code, sector_data) == sector
            ]

            if sector_positions:
                sector_return = sum(
                    p.daily_return * p.weight
                    for p in sector_positions
                    if p.daily_return is not None
                )
                attribution[sector] = sector_return

        return attribution

    def _style_attribution(
        self,
        backtest_result: BacktestResult,
        style_data: pd.DataFrame,
    ) -> dict[str, float]:
        """Calculate style attribution using regression-based approach."""
        attribution = {}

        if not backtest_result.equity_curve:
            return attribution

        portfolio_returns = self._calculate_returns(backtest_result.equity_curve)
        
        if not portfolio_returns:
            return attribution

        styles = ["momentum", "value", "quality", "size", "volatility"]

        if style_data.empty:
            return {style: 0.0 for style in styles}

        for style in styles:
            if style in style_data.columns:
                style_returns = style_data[style].values
                
                min_len = min(len(portfolio_returns), len(style_returns))
                if min_len > 1:
                    covariance = np.cov(
                        portfolio_returns[:min_len],
                        style_returns[:min_len],
                    )[0, 1]
                    variance = np.var(style_returns[:min_len])
                    
                    if variance > 0:
                        beta = covariance / variance
                        attribution[style] = beta * np.mean(style_returns[:min_len])
                    else:
                        attribution[style] = 0.0
                else:
                    attribution[style] = 0.0
            else:
                attribution[style] = 0.0

        return attribution

    def _calc_selection_return(self, backtest_result: BacktestResult) -> float:
        """Calculate selection return component."""
        if not backtest_result.metrics:
            return 0.0

        return backtest_result.metrics.alpha or 0.0

    def _calc_timing_return(self, backtest_result: BacktestResult) -> float:
        """Calculate timing return component."""
        if not backtest_result.equity_curve or not backtest_result.benchmark_curve:
            return 0.0

        equity_returns = self._calculate_returns(backtest_result.equity_curve)
        benchmark_returns = self._calculate_returns(backtest_result.benchmark_curve)
        
        if not equity_returns or not benchmark_returns:
            return 0.0
        
        min_len = min(len(equity_returns), len(benchmark_returns))
        if min_len < 2:
            return 0.0
        
        equity_arr = np.array(equity_returns[:min_len])
        benchmark_arr = np.array(benchmark_returns[:min_len])
        
        timing_score = np.mean(equity_arr * np.sign(benchmark_arr))
        
        return float(timing_score)

    def _calc_interaction_return(self, backtest_result: BacktestResult) -> float:
        """Calculate interaction return component."""
        selection_return = self._calc_selection_return(backtest_result)
        timing_return = self._calc_timing_return(backtest_result)
        
        interaction = selection_return * timing_return * 0.5
        
        return float(interaction)

    def _calculate_returns(self, equity_curve: list[DailyEquity]) -> list[float]:
        """Calculate daily returns from equity curve."""
        if len(equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1].equity
            curr = equity_curve[i].equity
            if prev > 0:
                returns.append((curr - prev) / prev)
            else:
                returns.append(0.0)

        return returns

    def _get_stock_sector(
        self,
        stock_code: str,
        sector_data: pd.DataFrame,
    ) -> str:
        """Get sector for a stock."""
        if sector_data.empty:
            return "unknown"

        stock_data = sector_data[sector_data["stock_code"] == stock_code]
        if not stock_data.empty and "sector" in stock_data.columns:
            return stock_data["sector"].iloc[0]

        return "unknown"

    def brinson_attribution(
        self,
        portfolio_weights: dict[str, float],
        benchmark_weights: dict[str, float],
        portfolio_returns: dict[str, float],
        benchmark_returns: dict[str, float],
    ) -> dict[str, float]:
        """Perform Brinson attribution analysis.

        Returns:
            Dictionary with allocation, selection, and interaction effects.
        """
        all_assets = set(portfolio_weights.keys()) | set(benchmark_weights.keys())

        allocation_effect = 0.0
        selection_effect = 0.0
        interaction_effect = 0.0

        benchmark_total_return = sum(
            benchmark_weights.get(a, 0) * benchmark_returns.get(a, 0)
            for a in all_assets
        )

        for asset in all_assets:
            pw = portfolio_weights.get(asset, 0)
            bw = benchmark_weights.get(asset, 0)
            pr = portfolio_returns.get(asset, 0)
            br = benchmark_returns.get(asset, 0)

            allocation_effect += (pw - bw) * br

            selection_effect += bw * (pr - br)

            interaction_effect += (pw - bw) * (pr - br)

        return {
            "allocation_effect": allocation_effect,
            "selection_effect": selection_effect,
            "interaction_effect": interaction_effect,
            "total_active_return": allocation_effect + selection_effect + interaction_effect,
        }
