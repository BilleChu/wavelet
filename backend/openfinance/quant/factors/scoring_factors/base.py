"""
Configuration-driven scoring factors for Wavelet analysis.

This module provides a base class and loader for scoring factors
that are defined in YAML configuration files.

Features:
- Load factor definitions from YAML files
- Dynamic score calculation based on formulas
- Support for value maps and optimal ranges
- Integration with the factor registry
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import yaml

from openfinance.datacenter.models.analytical import ADSKLineModel
from openfinance.quant.factors.base import (
    FactorBase,
    FactorMetadata,
    FactorResult,
    FactorConfig,
    FactorType,
    FactorCategory,
)
from openfinance.quant.factors.registry import register_factor

logger = logging.getLogger(__name__)


@dataclass
class IndicatorDefinition:
    """Definition of an indicator used in scoring factors."""
    name: str
    code: str
    weight: float
    data_source: str = ""
    optimal_range: tuple[float, float] | None = None
    score_formula: str | None = None
    value_map: dict[str, float] | None = None
    unit: str = ""
    description: str = ""


@dataclass
class ScoringFactorConfig:
    """Configuration for a scoring factor."""
    factor_id: str
    name: str
    display_name: str
    description: str
    factor_type: str
    category: str
    version: str = "1.0.0"
    author: str = "system"
    tags: list[str] = field(default_factory=list)
    indicators: dict[str, IndicatorDefinition] = field(default_factory=dict)
    output_range: tuple[float, float] = (0, 100)
    calculation_method: str = "weighted_average"
    event_scoring: dict[str, Any] | None = None


class FormulaEvaluator:
    """Safe formula evaluator for score calculations."""
    
    SAFE_FUNCTIONS = {
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'sqrt': lambda x: x ** 0.5,
        'pow': pow,
    }
    
    SAFE_NAMES = {
        'value': None,
        'price': None,
        'ma20': None,
        'ma_vol': None,
        'vol': None,
        'adv': None,
        'dec': None,
        'highs': None,
        'lows': None,
        'ind_ret': None,
        'mkt_ret': None,
        'r5': None,
        'r20': None,
        'expected': None,
        'current': None,
        'True': True,
        'False': False,
        'None': None,
    }
    
    @classmethod
    def evaluate(cls, formula: str, variables: dict[str, Any]) -> float:
        """
        Safely evaluate a formula with given variables.
        
        Args:
            formula: Formula string (e.g., "min(100, max(0, value * 25))")
            variables: Dictionary of variable values
        
        Returns:
            Calculated value
        """
        try:
            namespace = {**cls.SAFE_FUNCTIONS, **cls.SAFE_NAMES, **variables}
            result = eval(formula, {"__builtins__": {}}, namespace)
            return float(result) if result is not None else 50.0
        except Exception as e:
            logger.debug(f"Formula evaluation failed: {formula}, error: {e}")
            return 50.0


class ScoringFactorBase(FactorBase):
    """
    Base class for configuration-driven scoring factors.
    
    These factors calculate scores based on multiple indicators
    defined in YAML configuration files.
    """
    
    def __init__(
        self,
        config: ScoringFactorConfig | None = None,
        config_path: str | None = None,
        **kwargs,
    ):
        if config:
            self._scoring_config = config
            metadata = FactorMetadata(
                factor_id=config.factor_id,
                name=config.name,
                description=config.description,
                factor_type=FactorType(config.factor_type),
                category=FactorCategory(config.category),
                version=config.version,
                author=config.author,
                tags=config.tags,
            )
            super().__init__(metadata=metadata, **kwargs)
        elif config_path:
            self._scoring_config = self._load_config(config_path)
            super().__init__(
                factor_id=self._scoring_config.factor_id,
                name=self._scoring_config.name,
                description=self._scoring_config.description,
                factor_type=self._scoring_config.factor_type,
                category=self._scoring_config.category,
                **kwargs,
            )
        else:
            super().__init__(**kwargs)
            self._scoring_config = None
        
        self._indicator_values: dict[str, Any] = {}
        self._indicator_scores: dict[str, float] = {}
    
    def _load_config(self, config_path: str) -> ScoringFactorConfig:
        """Load factor configuration from YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        indicators = {}
        for code, ind_data in data.get('indicators', {}).items():
            indicators[code] = IndicatorDefinition(
                name=ind_data.get('name', code),
                code=code,
                weight=ind_data.get('weight', 1.0),
                data_source=ind_data.get('data_source', ''),
                optimal_range=tuple(ind_data['optimal_range']) if ind_data.get('optimal_range') else None,
                score_formula=ind_data.get('score_formula'),
                value_map=ind_data.get('value_map'),
                unit=ind_data.get('unit', ''),
                description=ind_data.get('description', ''),
            )
        
        output_range = data.get('output', {}).get('range', [0, 100])
        
        return ScoringFactorConfig(
            factor_id=data['factor_id'],
            name=data['name'],
            display_name=data.get('display_name', data['name']),
            description=data.get('description', ''),
            factor_type=data.get('factor_type', 'custom'),
            category=data.get('category', 'custom'),
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'system'),
            tags=data.get('tags', []),
            indicators=indicators,
            output_range=tuple(output_range),
            calculation_method=data.get('calculation', {}).get('method', 'weighted_average'),
            event_scoring=data.get('event_scoring'),
        )
    
    @property
    def scoring_config(self) -> ScoringFactorConfig | None:
        return self._scoring_config
    
    def get_indicator_definitions(self) -> dict[str, IndicatorDefinition]:
        """Get indicator definitions for this factor."""
        if self._scoring_config:
            return self._scoring_config.indicators
        return {}
    
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **params: Any,
    ) -> float | None:
        """
        Scoring factors don't use K-Line data directly.
        Use calculate_from_indicators instead.
        """
        indicator_values = params.get('indicator_values', {})
        return self.calculate_from_indicators(indicator_values)
    
    def calculate_from_indicators(
        self,
        indicator_values: dict[str, Any],
    ) -> float | None:
        """
        Calculate factor score from indicator values.
        
        Args:
            indicator_values: Dictionary of indicator code -> value
        
        Returns:
            Factor score (0-100)
        """
        if not self._scoring_config:
            return 50.0
        
        self._indicator_values = indicator_values
        self._indicator_scores = {}
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for code, indicator in self._scoring_config.indicators.items():
            value = indicator_values.get(code)
            score = self._calculate_indicator_score(indicator, value)
            
            weighted_sum += score * indicator.weight
            total_weight += indicator.weight
            self._indicator_scores[code] = score
        
        if total_weight > 0:
            score = weighted_sum / total_weight
            min_val, max_val = self._scoring_config.output_range
            return max(min_val, min(max_val, score))
        
        return 50.0
    
    def _calculate_indicator_score(
        self,
        indicator: IndicatorDefinition,
        value: Any,
    ) -> float:
        """
        Calculate score for a single indicator.
        
        Args:
            indicator: Indicator definition
            value: Indicator value
        
        Returns:
            Score (0-100)
        """
        if value is None:
            return 50.0
        
        try:
            if indicator.score_formula:
                if isinstance(value, dict):
                    return FormulaEvaluator.evaluate(indicator.score_formula, value)
                else:
                    return FormulaEvaluator.evaluate(indicator.score_formula, {'value': value})
            
            if indicator.value_map and isinstance(value, str):
                return indicator.value_map.get(value, 50.0)
            
            if indicator.optimal_range:
                low, high = indicator.optimal_range
                if low <= value <= high:
                    return 100.0
                else:
                    deviation = min(abs(value - low), abs(value - high))
                    return max(0, 100 - deviation * 10)
            
            return 50.0
        except Exception as e:
            logger.debug(f"Failed to calculate indicator score: {e}")
            return 50.0
    
    def get_indicator_scores(self) -> dict[str, float]:
        """Get scores for each indicator."""
        return self._indicator_scores.copy()
    
    def get_factor_details(self) -> dict[str, Any]:
        """Get detailed factor information including indicator scores."""
        return {
            'factor_id': self.factor_id,
            'name': self.name,
            'score': getattr(self, '_last_score', 50.0),
            'indicators': {
                code: {
                    'name': ind.name,
                    'weight': ind.weight,
                    'value': self._indicator_values.get(code),
                    'score': self._indicator_scores.get(code, 50.0),
                }
                for code, ind in self.get_indicator_definitions().items()
            },
        }


def load_scoring_factors_from_config(config_dir: str) -> list[ScoringFactorBase]:
    """
    Load all scoring factors from configuration directory.
    
    Args:
        config_dir: Path to directory containing YAML config files
    
    Returns:
        List of ScoringFactorBase instances
    """
    factors = []
    config_path = Path(config_dir)
    
    if not config_path.exists():
        logger.warning(f"Config directory not found: {config_dir}")
        return factors
    
    for yaml_file in config_path.glob("*.yaml"):
        try:
            factor = ScoringFactorBase(config_path=str(yaml_file))
            factors.append(factor)
            logger.info(f"Loaded scoring factor: {factor.factor_id}")
        except Exception as e:
            logger.error(f"Failed to load factor from {yaml_file}: {e}")
    
    return factors


def register_scoring_factors(config_dir: str) -> int:
    """
    Register all scoring factors from configuration directory.
    
    Args:
        config_dir: Path to directory containing YAML config files
    
    Returns:
        Number of factors registered
    """
    from openfinance.quant.factors.registry import get_factor_registry
    
    registry = get_factor_registry()
    factors = load_scoring_factors_from_config(config_dir)
    
    count = 0
    for factor in factors:
        try:
            registry.register_class(factor.__class__, is_builtin=False)
            count += 1
        except Exception as e:
            logger.error(f"Failed to register factor {factor.factor_id}: {e}")
    
    return count
