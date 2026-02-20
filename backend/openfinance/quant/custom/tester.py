"""
Factor Tester for Quantitative Analysis.

Provides testing and performance evaluation for factors.
"""

import logging
import time
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from openfinance.domain.models.quant import (
    FactorTestRequest,
    FactorTestResult,
    FactorValue,
)

logger = logging.getLogger(__name__)


class FactorTester:
    """Tester for factor performance.

    Provides:
    - IC (Information Coefficient) calculation
    - Rank IC calculation
    - Turnover analysis
    - Coverage analysis
    - Monotonicity test
    - Quantile return analysis
    """

    def __init__(self) -> None:
        pass

    def test(
        self,
        request: FactorTestRequest,
        factor_values: list[FactorValue],
        forward_returns: pd.DataFrame | None = None,
    ) -> FactorTestResult:
        """Test factor performance.

        Args:
            request: Test request with parameters.
            factor_values: Calculated factor values.
            forward_returns: Forward returns data for IC calculation.

        Returns:
            FactorTestResult with performance metrics.
        """
        start_time = time.time()
        test_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        ic_mean = None
        ic_std = None
        ic_ir = None
        ic_positive_ratio = None
        rank_ic_mean = None
        rank_ic_std = None
        turnover_mean = None
        coverage_mean = None
        monotonicity = None
        quantile_returns = None

        if forward_returns is not None and not forward_returns.empty:
            ic_results = self._calculate_ic(factor_values, forward_returns)
            ic_mean = ic_results.get("ic_mean")
            ic_std = ic_results.get("ic_std")
            ic_ir = ic_results.get("ic_ir")
            ic_positive_ratio = ic_results.get("ic_positive_ratio")
            rank_ic_mean = ic_results.get("rank_ic_mean")
            rank_ic_std = ic_results.get("rank_ic_std")

        coverage_mean = self._calculate_coverage(factor_values)

        if "turnover" in request.test_metrics:
            turnover_mean = self._estimate_turnover(factor_values)

        if forward_returns is not None:
            quantile_results = self._quantile_analysis(factor_values, forward_returns)
            monotonicity = quantile_results.get("monotonicity")
            quantile_returns = quantile_results.get("quantile_returns")

        duration_ms = (time.time() - start_time) * 1000

        return FactorTestResult(
            test_id=test_id,
            factor_id=request.factor_id,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ic_ir=ic_ir,
            ic_positive_ratio=ic_positive_ratio,
            rank_ic_mean=rank_ic_mean,
            rank_ic_std=rank_ic_std,
            turnover_mean=turnover_mean,
            coverage_mean=coverage_mean,
            monotonicity=monotonicity,
            quantile_returns=quantile_returns,
            duration_ms=duration_ms,
        )

    def _calculate_ic(
        self,
        factor_values: list[FactorValue],
        forward_returns: pd.DataFrame,
    ) -> dict[str, float]:
        """Calculate Information Coefficient."""
        results = {
            "ic_mean": 0.0,
            "ic_std": 0.0,
            "ic_ir": 0.0,
            "ic_positive_ratio": 0.0,
            "rank_ic_mean": 0.0,
            "rank_ic_std": 0.0,
        }

        if not factor_values or forward_returns.empty:
            return results

        factor_df = pd.DataFrame([
            {
                "stock_code": v.stock_code,
                "trade_date": v.trade_date,
                "factor_value": v.value,
            }
            for v in factor_values
            if v.value is not None
        ])

        if factor_df.empty:
            return results

        ic_values = []
        rank_ic_values = []

        for date in factor_df["trade_date"].unique():
            date_factors = factor_df[factor_df["trade_date"] == date]
            date_returns = forward_returns[forward_returns["trade_date"] == date]

            if date_returns.empty:
                continue

            merged = pd.merge(
                date_factors,
                date_returns[["stock_code", "forward_return"]],
                on="stock_code",
                how="inner",
            )

            if len(merged) < 5:
                continue

            ic = merged["factor_value"].corr(merged["forward_return"])
            if not np.isnan(ic):
                ic_values.append(ic)

            rank_ic = merged["factor_value"].rank().corr(
                merged["forward_return"].rank()
            )
            if not np.isnan(rank_ic):
                rank_ic_values.append(rank_ic)

        if ic_values:
            results["ic_mean"] = float(np.mean(ic_values))
            results["ic_std"] = float(np.std(ic_values))
            results["ic_ir"] = results["ic_mean"] / results["ic_std"] if results["ic_std"] > 0 else 0.0
            results["ic_positive_ratio"] = float(sum(1 for ic in ic_values if ic > 0) / len(ic_values))

        if rank_ic_values:
            results["rank_ic_mean"] = float(np.mean(rank_ic_values))
            results["rank_ic_std"] = float(np.std(rank_ic_values))

        return results

    def _calculate_coverage(self, factor_values: list[FactorValue]) -> float:
        """Calculate factor coverage."""
        if not factor_values:
            return 0.0

        valid_count = sum(1 for v in factor_values if v.value is not None)
        return valid_count / len(factor_values)

    def _estimate_turnover(self, factor_values: list[FactorValue]) -> float:
        """Estimate factor turnover."""
        if len(factor_values) < 2:
            return 0.0

        by_date: dict[str, list[FactorValue]] = {}
        for v in factor_values:
            date_str = v.trade_date.strftime("%Y-%m-%d") if isinstance(v.trade_date, datetime) else str(v.trade_date)
            if date_str not in by_date:
                by_date[date_str] = []
            by_date[date_str].append(v)

        dates = sorted(by_date.keys())
        if len(dates) < 2:
            return 0.0

        turnovers = []
        for i in range(1, len(dates)):
            prev_values = {v.stock_code: v.value for v in by_date[dates[i - 1]] if v.value is not None}
            curr_values = {v.stock_code: v.value for v in by_date[dates[i]] if v.value is not None}

            if not prev_values or not curr_values:
                continue

            prev_ranks = pd.Series(prev_values).rank()
            curr_ranks = pd.Series(curr_values).rank()

            common_stocks = set(prev_ranks.index) & set(curr_ranks.index)
            if len(common_stocks) < 5:
                continue

            prev_top = set(prev_ranks.nlargest(10).index)
            curr_top = set(curr_ranks.nlargest(10).index)

            turnover = len(prev_top.symmetric_difference(curr_top)) / 20
            turnovers.append(turnover)

        return float(np.mean(turnovers)) if turnovers else 0.0

    def _quantile_analysis(
        self,
        factor_values: list[FactorValue],
        forward_returns: pd.DataFrame,
        n_quantiles: int = 5,
    ) -> dict[str, Any]:
        """Perform quantile analysis."""
        results = {
            "monotonicity": 0.0,
            "quantile_returns": [],
        }

        if not factor_values or forward_returns.empty:
            return results

        factor_df = pd.DataFrame([
            {
                "stock_code": v.stock_code,
                "trade_date": v.trade_date,
                "factor_value": v.value,
            }
            for v in factor_values
            if v.value is not None
        ])

        if factor_df.empty:
            return results

        merged = pd.merge(
            factor_df,
            forward_returns[["stock_code", "trade_date", "forward_return"]],
            on=["stock_code", "trade_date"],
            how="inner",
        )

        if merged.empty:
            return results

        merged["quantile"] = pd.qcut(
            merged["factor_value"],
            n_quantiles,
            labels=False,
            duplicates="drop",
        )

        quantile_returns = merged.groupby("quantile")["forward_return"].mean().tolist()
        results["quantile_returns"] = quantile_returns

        if len(quantile_returns) >= 2:
            monotonic_count = 0
            for i in range(1, len(quantile_returns)):
                if quantile_returns[i] > quantile_returns[i - 1]:
                    monotonic_count += 1

            results["monotonicity"] = monotonic_count / (len(quantile_returns) - 1)

        return results

    def calculate_factor_correlation(
        self,
        factor_values_1: list[FactorValue],
        factor_values_2: list[FactorValue],
    ) -> float:
        """Calculate correlation between two factors."""
        values_1 = {v.stock_code: v.value for v in factor_values_1 if v.value is not None}
        values_2 = {v.stock_code: v.value for v in factor_values_2 if v.value is not None}

        common_stocks = set(values_1.keys()) & set(values_2.keys())

        if len(common_stocks) < 5:
            return 0.0

        x = [values_1[s] for s in common_stocks]
        y = [values_2[s] for s in common_stocks]

        return float(np.corrcoef(x, y)[0, 1])

    def calculate_mutual_information(
        self,
        factor_values: list[FactorValue],
        forward_returns: pd.DataFrame,
        n_bins: int = 10,
    ) -> float:
        """Calculate mutual information between factor and returns."""
        if not factor_values or forward_returns.empty:
            return 0.0

        factor_df = pd.DataFrame([
            {"stock_code": v.stock_code, "trade_date": v.trade_date, "factor_value": v.value}
            for v in factor_values
            if v.value is not None
        ])

        merged = pd.merge(
            factor_df,
            forward_returns[["stock_code", "trade_date", "forward_return"]],
            on=["stock_code", "trade_date"],
            how="inner",
        )

        if merged.empty:
            return 0.0

        factor_binned = pd.cut(merged["factor_value"], bins=n_bins, labels=False)
        return_binned = pd.cut(merged["forward_return"], bins=n_bins, labels=False)

        contingency = pd.crosstab(factor_binned, return_binned)

        contingency_np = contingency.values
        total = contingency_np.sum()
        if total == 0:
            return 0.0

        p_xy = contingency_np / total
        p_x = contingency_np.sum(axis=1, keepdims=True) / total
        p_y = contingency_np.sum(axis=0, keepdims=True) / total

        p_xy_safe = np.where(p_xy == 0, 1e-10, p_xy)
        p_x_safe = np.where(p_x == 0, 1e-10, p_x)
        p_y_safe = np.where(p_y == 0, 1e-10, p_y)

        mi = np.sum(p_xy * np.log(p_xy_safe / (p_x_safe * p_y_safe)))

        return float(mi)
