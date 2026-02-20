"""
Attribution analysis module.

Implements comprehensive performance attribution methodologies:
- Brinson Attribution (Allocation, Selection, Interaction)
- Factor-based Attribution
- Sector Attribution
- Style Attribution
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


class AttributionAnalyzer:
    """
    Professional attribution analysis toolkit.
    
    Implements multiple attribution methodologies:
    - Brinson-Fachler attribution
    - Factor-based attribution
    - Sector attribution
    - Style attribution
    """
    
    def __init__(self):
        """Initialize attribution analyzer."""
        pass
    
    def brinson_attribution(
        self,
        portfolio_weights: pd.Series,
        benchmark_weights: pd.Series,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        sectors: Optional[pd.Series] = None,
    ) -> dict:
        """
        Perform Brinson-Fachler attribution analysis.
        
        Decomposes active return into:
        - Allocation Effect: Impact of sector weight decisions
        - Selection Effect: Impact of stock selection within sectors
        - Interaction Effect: Combined effect
        
        Args:
            portfolio_weights: Portfolio weights by sector/asset
            benchmark_weights: Benchmark weights by sector/asset
            portfolio_returns: Portfolio returns by sector/asset
            benchmark_returns: Benchmark returns by sector/asset
            sectors: Optional sector mapping for assets
        
        Returns:
            Dictionary with allocation, selection, interaction effects
        """
        # Ensure alignment
        all_assets = portfolio_weights.index.union(benchmark_weights.index)
        
        portfolio_weights = portfolio_weights.reindex(all_assets).fillna(0)
        benchmark_weights = benchmark_weights.reindex(all_assets).fillna(0)
        portfolio_returns = portfolio_returns.reindex(all_assets).fillna(0)
        benchmark_returns = benchmark_returns.reindex(all_assets).fillna(0)
        
        if sectors is not None:
            sectors = sectors.reindex(all_assets).fillna('Other')
        
        # Total active return
        total_portfolio_return = (portfolio_weights * portfolio_returns).sum()
        total_benchmark_return = (benchmark_weights * benchmark_returns).sum()
        total_active_return = total_portfolio_return - total_benchmark_return
        
        # If sectors provided, do sector-level attribution
        if sectors is not None:
            return self._brinson_by_sector(
                portfolio_weights,
                benchmark_weights,
                portfolio_returns,
                benchmark_returns,
                sectors,
                total_active_return,
            )
        else:
            # Asset-level attribution (simplified)
            return self._brinson_by_asset(
                portfolio_weights,
                benchmark_weights,
                portfolio_returns,
                benchmark_returns,
                total_active_return,
            )
    
    def _brinson_by_sector(
        self,
        wp: pd.Series,  # Portfolio weights
        wb: pd.Series,  # Benchmark weights
        rp: pd.Series,  # Portfolio returns
        rb: pd.Series,  # Benchmark returns
        sectors: pd.Series,
        total_active_return: float,
    ) -> dict:
        """Brinson attribution by sector."""
        unique_sectors = sectors.unique()
        
        sector_results = []
        total_allocation = 0.0
        total_selection = 0.0
        total_interaction = 0.0
        
        for sector in unique_sectors:
            mask = sectors == sector
            
            # Sector weights
            wp_sector = wp[mask].sum()
            wb_sector = wb[mask].sum()
            
            # Sector returns (weighted average)
            if wp[mask].sum() > 0:
                rp_sector = (wp[mask] * rp[mask]).sum() / wp[mask].sum()
            else:
                rp_sector = 0.0
            
            if wb[mask].sum() > 0:
                rb_sector = (wb[mask] * rb[mask]).sum() / wb[mask].sum()
            else:
                rb_sector = 0.0
            
            # Brinson-Fachler decomposition
            allocation = (wp_sector - wb_sector) * (rb_sector - sum(wb * rb))
            selection = wb_sector * (rp_sector - rb_sector)
            interaction = (wp_sector - wb_sector) * (rp_sector - rb_sector)
            
            sector_results.append({
                'sector': sector,
                'allocation_effect': float(allocation),
                'selection_effect': float(selection),
                'interaction_effect': float(interaction),
                'total_effect': float(allocation + selection + interaction),
                'portfolio_weight': float(wp_sector),
                'benchmark_weight': float(wb_sector),
                'portfolio_return': float(rp_sector),
                'benchmark_return': float(rb_sector),
            })
            
            total_allocation += allocation
            total_selection += selection
            total_interaction += interaction
        
        return {
            'brinson': {
                'allocation_effect': float(total_allocation),
                'selection_effect': float(total_selection),
                'interaction_effect': float(total_interaction),
                'total_active_return': float(total_active_return),
            },
            'sector': sector_results,
        }
    
    def _brinson_by_asset(
        self,
        wp: pd.Series,
        wb: pd.Series,
        rp: pd.Series,
        rb: pd.Series,
        total_active_return: float,
    ) -> dict:
        """Simplified Brinson attribution at asset level."""
        # BHB model (Brinson-Hood-Beebower)
        allocation = ((wp - wb) * rb).sum()
        selection = (wb * (rp - rb)).sum()
        interaction = ((wp - wb) * (rp - rb)).sum()
        
        return {
            'allocation_effect': float(allocation),
            'selection_effect': float(selection),
            'interaction_effect': float(interaction),
            'total_active_return': float(total_active_return),
        }
    
    def factor_attribution(
        self,
        portfolio_returns: pd.Series,
        factor_returns: pd.DataFrame,
    ) -> dict:
        """
        Perform factor-based attribution using regression.
        
        Decomposes returns into factor exposures:
        - Size (SMB: Small Minus Big)
        - Value (HML: High Minus Low)
        - Momentum (MOM)
        - Quality (QMJ: Quality Minus Junk)
        - Volatility (BAB: Betting Against Beta)
        - Liquidity (LIQ)
        
        Args:
            portfolio_returns: Portfolio return series
            factor_returns: DataFrame with factor returns as columns
        
        Returns:
            Dictionary with factor contributions
        """
        # Align data
        aligned_data = pd.concat([portfolio_returns, factor_returns], axis=1).dropna()
        
        if len(aligned_data) < 30:
            logger.warning("Insufficient data for factor attribution")
            return self._empty_factor_attribution()
        
        y = aligned_data.iloc[:, 0]  # Portfolio returns
        X = aligned_data.iloc[:, 1:]  # Factor returns
        
        # Add constant for intercept (alpha)
        X_with_const = pd.DataFrame(X)
        X_with_const['const'] = 1.0
        
        # OLS regression
        try:
            betas = np.linalg.lstsq(X_with_const.values, y.values, rcond=None)[0]
            
            # Extract factor loadings
            factor_names = list(factor_returns.columns)
            factor_betas = dict(zip(factor_names, betas[:-1]))
            alpha = betas[-1] * 252  # Annualized alpha
            
            # Calculate factor contributions
            factor_contributions = {}
            for i, factor_name in enumerate(factor_names):
                beta = betas[i]
                factor_mean_return = factor_returns[factor_name].mean() * 252
                contribution = beta * factor_mean_return
                factor_contributions[factor_name] = float(contribution)
            
            # Calculate residual
            predicted_returns = X_with_const.values @ betas
            residuals = y - predicted_returns
            residual_contribution = float(residuals.mean() * 252)
            
            return {
                'factor': factor_contributions,
                'alpha': float(alpha),
                'residual': residual_contribution,
                'r_squared': float(self._calculate_r_squared(y, predicted_returns)),
            }
            
        except Exception as e:
            logger.error(f"Factor attribution failed: {e}")
            return self._empty_factor_attribution()
    
    def _empty_factor_attribution(self) -> dict:
        """Return empty factor attribution structure."""
        return {
            'factor': {
                'size': 0.0,
                'value': 0.0,
                'momentum': 0.0,
                'quality': 0.0,
                'volatility': 0.0,
                'liquidity': 0.0,
                'other': 0.0,
            },
            'alpha': 0.0,
            'residual': 0.0,
            'r_squared': 0.0,
        }
    
    def _calculate_r_squared(self, actual: pd.Series, predicted: np.ndarray) -> float:
        """Calculate R-squared (coefficient of determination)."""
        ss_res = np.sum((actual - predicted) ** 2)
        ss_tot = np.sum((actual - actual.mean()) ** 2)
        
        if ss_tot == 0:
            return 0.0
        
        return 1 - (ss_res / ss_tot)
    
    def style_attribution(
        self,
        portfolio_returns: pd.Series,
        style_indices: dict[str, pd.Series],
    ) -> dict:
        """
        Perform style attribution using returns-based style analysis.
        
        Determines exposure to different investment styles:
        - Growth vs Value
        - Large Cap vs Small Cap
        - High Dividend vs Low Dividend
        
        Args:
            portfolio_returns: Portfolio return series
            style_indices: Dictionary of style index returns
        
        Returns:
            Dictionary with style exposures
        """
        # Convert to DataFrame
        style_df = pd.DataFrame(style_indices)
        
        # Align data
        aligned_data = pd.concat([portfolio_returns, style_df], axis=1).dropna()
        
        if len(aligned_data) < 60:
            logger.warning("Insufficient data for style attribution")
            return {'styles': {}, 'r_squared': 0.0}
        
        y = aligned_data.iloc[:, 0]
        X = aligned_data.iloc[:, 1:]
        
        # Constrained regression (non-negative coefficients that sum to 1)
        # Using simple OLS as approximation
        X_with_const = pd.DataFrame(X)
        
        try:
            betas = np.linalg.lstsq(X_with_const.values, y.values, rcond=None)[0]
            
            # Normalize to sum to 1 (approximation)
            positive_betas = np.maximum(betas, 0)
            if positive_betas.sum() > 0:
                normalized_betas = positive_betas / positive_betas.sum()
            else:
                normalized_betas = positive_betas
            
            style_exposures = dict(zip(style_indices.keys(), normalized_betas))
            
            # Calculate R-squared
            predicted = X_with_const.values @ betas
            r_squared = self._calculate_r_squared(y, predicted)
            
            return {
                'styles': style_exposures,
                'r_squared': float(r_squared),
            }
            
        except Exception as e:
            logger.error(f"Style attribution failed: {e}")
            return {'styles': {}, 'r_squared': 0.0}
