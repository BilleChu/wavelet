"""
Factor Analysis Module.

Provides factor analysis capabilities:
- Neutralization (industry, market cap)
- Correlation analysis
- IC/IR calculation
- Decay analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class NeutralizationConfig:
    """Configuration for factor neutralization."""
    
    industry_neutral: bool = True
    market_cap_neutral: bool = True
    industry_classification: str = "sw_l1"
    min_industry_stocks: int = 5


class FactorNeutralizer:
    """
    Factor neutralization processor.
    
    Supports:
    - Industry neutralization
    - Market cap neutralization
    - Combined neutralization
    """
    
    def __init__(self, config: NeutralizationConfig | None = None):
        self.config = config or NeutralizationConfig()
    
    def neutralize(
        self,
        factor_values: dict[str, float],
        industry_map: dict[str, str] | None = None,
        market_caps: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """
        Neutralize factor values.
        
        Args:
            factor_values: Raw factor values by stock code
            industry_map: Stock code to industry mapping
            market_caps: Stock code to market cap mapping
        
        Returns:
            Neutralized factor values
        """
        if not factor_values:
            return {}
        
        values = np.array(list(factor_values.values()))
        codes = list(factor_values.keys())
        
        neutralized = values.copy()
        
        if self.config.industry_neutral and industry_map:
            neutralized = self._industry_neutralize(
                neutralized, codes, industry_map
            )
        
        if self.config.market_cap_neutral and market_caps:
            neutralized = self._market_cap_neutralize(
                neutralized, codes, market_caps
            )
        
        return dict(zip(codes, neutralized))
    
    def _industry_neutralize(
        self,
        values: np.ndarray,
        codes: list[str],
        industry_map: dict[str, str],
    ) -> np.ndarray:
        """Apply industry neutralization."""
        industry_groups: dict[str, list[int]] = {}
        
        for i, code in enumerate(codes):
            industry = industry_map.get(code, "unknown")
            if industry not in industry_groups:
                industry_groups[industry] = []
            industry_groups[industry].append(i)
        
        result = values.copy()
        
        for industry, indices in industry_groups.items():
            if len(indices) >= self.config.min_industry_stocks:
                industry_values = values[indices]
                mean = np.nanmean(industry_values)
                result[indices] = industry_values - mean
        
        return result
    
    def _market_cap_neutralize(
        self,
        values: np.ndarray,
        codes: list[str],
        market_caps: dict[str, float],
    ) -> np.ndarray:
        """Apply market cap neutralization."""
        log_mcs = []
        valid_indices = []
        
        for i, code in enumerate(codes):
            mc = market_caps.get(code)
            if mc and mc > 0:
                log_mcs.append(np.log(mc))
                valid_indices.append(i)
        
        if len(valid_indices) < 10:
            return values
        
        log_mcs = np.array(log_mcs)
        valid_values = values[valid_indices]
        
        mask = ~(np.isnan(valid_values) | np.isnan(log_mcs))
        if np.sum(mask) < 10:
            return values
        
        slope, intercept, _, _, _ = stats.linregress(
            log_mcs[mask], valid_values[mask]
        )
        
        result = values.copy()
        for i, code in enumerate(codes):
            mc = market_caps.get(code)
            if mc and mc > 0:
                expected = slope * np.log(mc) + intercept
                result[i] = values[i] - expected
        
        return result


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""
    
    factor1: str
    factor2: str
    correlation: float
    p_value: float
    sample_size: int
    method: str = "pearson"


class FactorCorrelationAnalyzer:
    """
    Factor correlation analysis.
    
    Supports:
    - Pearson correlation
    - Spearman correlation
    - Rolling correlation
    - Correlation matrix
    """
    
    def calculate_correlation(
        self,
        factor1_values: dict[str, float],
        factor2_values: dict[str, float],
        method: str = "pearson",
    ) -> CorrelationResult:
        """
        Calculate correlation between two factors.
        
        Args:
            factor1_values: First factor values by stock code
            factor2_values: Second factor values by stock code
            method: Correlation method (pearson or spearman)
        
        Returns:
            CorrelationResult
        """
        common_codes = set(factor1_values.keys()) & set(factor2_values.keys())
        
        if len(common_codes) < 10:
            return CorrelationResult(
                factor1="",
                factor2="",
                correlation=0.0,
                p_value=1.0,
                sample_size=len(common_codes),
                method=method,
            )
        
        x = np.array([factor1_values[c] for c in common_codes])
        y = np.array([factor2_values[c] for c in common_codes])
        
        mask = ~(np.isnan(x) | np.isnan(y))
        x = x[mask]
        y = y[mask]
        
        if len(x) < 10:
            return CorrelationResult(
                factor1="",
                factor2="",
                correlation=0.0,
                p_value=1.0,
                sample_size=len(x),
                method=method,
            )
        
        if method == "spearman":
            corr, p_value = stats.spearmanr(x, y)
        else:
            corr, p_value = stats.pearsonr(x, y)
        
        return CorrelationResult(
            factor1="",
            factor2="",
            correlation=float(corr),
            p_value=float(p_value),
            sample_size=len(x),
            method=method,
        )
    
    def calculate_correlation_matrix(
        self,
        factor_values: dict[str, dict[str, float]],
        method: str = "pearson",
    ) -> dict[str, dict[str, float]]:
        """
        Calculate correlation matrix for multiple factors.
        
        Args:
            factor_values: Dict of factor_id -> {code: value}
            method: Correlation method
        
        Returns:
            Correlation matrix as nested dict
        """
        factor_ids = list(factor_values.keys())
        n = len(factor_ids)
        
        matrix = {fid: {} for fid in factor_ids}
        
        for i in range(n):
            for j in range(i, n):
                fid1, fid2 = factor_ids[i], factor_ids[j]
                
                if i == j:
                    matrix[fid1][fid2] = 1.0
                else:
                    result = self.calculate_correlation(
                        factor_values[fid1],
                        factor_values[fid2],
                        method,
                    )
                    matrix[fid1][fid2] = result.correlation
                    matrix[fid2][fid1] = result.correlation
        
        return matrix


@dataclass
class ICResult:
    """Information Coefficient result."""
    
    date: date
    ic: float
    rank_ic: float
    p_value: float
    sample_size: int


@dataclass
class IRResult:
    """Information Ratio result."""
    
    mean_ic: float
    ic_std: float
    ir: float
    ic_ir: float
    positive_ratio: float
    sample_size: int


class FactorICAnalyzer:
    """
    Factor IC/IR analysis.
    
    Supports:
    - IC (Information Coefficient)
    - Rank IC
    - IR (Information Ratio)
    - IC decay
    """
    
    def calculate_ic(
        self,
        factor_values: dict[str, float],
        forward_returns: dict[str, float],
        method: str = "spearman",
    ) -> ICResult:
        """
        Calculate IC for a single period.
        
        Args:
            factor_values: Factor values by stock code
            forward_returns: Forward returns by stock code
            method: IC method (pearson or spearman)
        
        Returns:
            ICResult
        """
        common_codes = set(factor_values.keys()) & set(forward_returns.keys())
        
        if len(common_codes) < 10:
            return ICResult(
                date=date.today(),
                ic=0.0,
                rank_ic=0.0,
                p_value=1.0,
                sample_size=len(common_codes),
            )
        
        x = np.array([factor_values[c] for c in common_codes])
        y = np.array([forward_returns[c] for c in common_codes])
        
        mask = ~(np.isnan(x) | np.isnan(y))
        x = x[mask]
        y = y[mask]
        
        if len(x) < 10:
            return ICResult(
                date=date.today(),
                ic=0.0,
                rank_ic=0.0,
                p_value=1.0,
                sample_size=len(x),
            )
        
        ic, p_value = stats.pearsonr(x, y)
        rank_ic, _ = stats.spearmanr(x, y)
        
        return ICResult(
            date=date.today(),
            ic=float(ic),
            rank_ic=float(rank_ic),
            p_value=float(p_value),
            sample_size=len(x),
        )
    
    def calculate_ir(
        self,
        ic_series: list[ICResult],
    ) -> IRResult:
        """
        Calculate IR from IC series.
        
        Args:
            ic_series: List of IC results over time
        
        Returns:
            IRResult
        """
        if not ic_series:
            return IRResult(
                mean_ic=0.0,
                ic_std=0.0,
                ir=0.0,
                ic_ir=0.0,
                positive_ratio=0.0,
                sample_size=0,
            )
        
        ics = [r.ic for r in ic_series if not np.isnan(r.ic)]
        rank_ics = [r.rank_ic for r in ic_series if not np.isnan(r.rank_ic)]
        
        if not ics:
            return IRResult(
                mean_ic=0.0,
                ic_std=0.0,
                ir=0.0,
                ic_ir=0.0,
                positive_ratio=0.0,
                sample_size=0,
            )
        
        mean_ic = np.mean(ics)
        ic_std = np.std(ics)
        
        ir = mean_ic / ic_std if ic_std > 0 else 0.0
        
        mean_rank_ic = np.mean(rank_ics) if rank_ics else 0.0
        rank_ic_std = np.std(rank_ics) if rank_ics else 1.0
        ic_ir = mean_rank_ic / rank_ic_std if rank_ic_std > 0 else 0.0
        
        positive_ratio = sum(1 for ic in ics if ic > 0) / len(ics)
        
        return IRResult(
            mean_ic=float(mean_ic),
            ic_std=float(ic_std),
            ir=float(ir),
            ic_ir=float(ic_ir),
            positive_ratio=float(positive_ratio),
            sample_size=len(ics),
        )
    
    def calculate_ic_decay(
        self,
        factor_values_series: list[dict[str, float]],
        forward_returns_series: list[dict[str, float]],
        max_periods: int = 20,
    ) -> list[tuple[int, float]]:
        """
        Calculate IC decay over holding periods.
        
        Args:
            factor_values_series: Factor values over time
            forward_returns_series: Forward returns over time
            max_periods: Maximum periods to analyze
        
        Returns:
            List of (period, ic) tuples
        """
        decay = []
        
        for period in range(1, max_periods + 1):
            if period <= len(forward_returns_series):
                ic_result = self.calculate_ic(
                    factor_values_series[0],
                    forward_returns_series[period - 1],
                )
                decay.append((period, ic_result.rank_ic))
        
        return decay


_neutralizer: FactorNeutralizer | None = None
_correlation_analyzer: FactorCorrelationAnalyzer | None = None
_ic_analyzer: FactorICAnalyzer | None = None


def get_neutralizer() -> FactorNeutralizer:
    """Get the global neutralizer instance."""
    global _neutralizer
    if _neutralizer is None:
        _neutralizer = FactorNeutralizer()
    return _neutralizer


def get_correlation_analyzer() -> FactorCorrelationAnalyzer:
    """Get the global correlation analyzer instance."""
    global _correlation_analyzer
    if _correlation_analyzer is None:
        _correlation_analyzer = FactorCorrelationAnalyzer()
    return _correlation_analyzer


def get_ic_analyzer() -> FactorICAnalyzer:
    """Get the global IC analyzer instance."""
    global _ic_analyzer
    if _ic_analyzer is None:
        _ic_analyzer = FactorICAnalyzer()
    return _ic_analyzer
