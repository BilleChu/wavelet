"""
Scoring Factors Package.

Configuration-driven scoring factors for market analysis.

Features:
- Load factor definitions from YAML files
- Dynamic score calculation based on formulas
- Support for value maps and optimal ranges
- Integration with the factor registry

Usage:
    from openfinance.quant.factors.scoring_factors import (
        ScoringFactorBase,
        load_scoring_factors_from_config,
        register_scoring_factors,
    )
    
    # Load factors from config directory
    factors = load_scoring_factors_from_config('./config')
    
    # Register factors with the registry
    register_scoring_factors('./config')
"""

from .base import (
    IndicatorDefinition,
    ScoringFactorConfig,
    ScoringFactorBase,
    FormulaEvaluator,
    load_scoring_factors_from_config,
    register_scoring_factors,
)

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent / "config"

_scoring_factors_loaded = False

def load_all_scoring_factors():
    """Load all scoring factors from the config directory."""
    global _scoring_factors_loaded
    
    if _scoring_factors_loaded:
        return
    
    if CONFIG_DIR.exists():
        count = register_scoring_factors(str(CONFIG_DIR))
        logger.info(f"Loaded {count} scoring factors from config")
    
    _scoring_factors_loaded = True

load_all_scoring_factors()

__all__ = [
    "IndicatorDefinition",
    "ScoringFactorConfig",
    "ScoringFactorBase",
    "FormulaEvaluator",
    "load_scoring_factors_from_config",
    "register_scoring_factors",
    "load_all_scoring_factors",
]
