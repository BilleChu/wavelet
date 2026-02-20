"""
Quantitative Factor Framework.

This module provides a comprehensive framework for factor-based
quantitative analysis with enhanced features:

- FactorBase: Unified abstract base class for all factors
- UnifiedFactorRegistry: Central registry with singleton pattern
- FactorEngine: High-performance calculation engine
- Factor Analysis: Neutralization, Correlation, IC/IR
- Storage: Database persistence and caching

All factors are calculated from K-Line base data (OHLCV).
"""

from .base import (
    FactorBase,
    FactorType,
    FactorCategory,
    FactorMetadata,
    FactorResult,
    FactorConfig,
    FactorStatus,
    NormalizeMethod,
    NeutralizationType,
    ParameterDefinition,
    ValidationResult,
    create_factor,
)

from .registry import (
    FactorDefinition,
    UnifiedFactorRegistry,
    get_factor_registry,
    register_factor,
)

from .engine import (
    EngineConfig,
    FactorEngine,
    get_factor_engine,
)

from .data_source import (
    DataSourceConfig,
    KLineDataSource,
    DataCenterDataSource,
    MockDataSource,
    get_data_source,
)

from .analysis import (
    NeutralizationConfig,
    FactorNeutralizer,
    FactorCorrelationAnalyzer,
    FactorICAnalyzer,
    CorrelationResult,
    ICResult,
    IRResult,
    get_neutralizer,
    get_correlation_analyzer,
    get_ic_analyzer,
)

from . import indicators
from . import library

__all__ = [
    "FactorBase",
    "FactorType",
    "FactorCategory",
    "FactorMetadata",
    "FactorResult",
    "FactorConfig",
    "FactorStatus",
    "NormalizeMethod",
    "NeutralizationType",
    "ParameterDefinition",
    "ValidationResult",
    "create_factor",
    "FactorDefinition",
    "UnifiedFactorRegistry",
    "get_factor_registry",
    "register_factor",
    "EngineConfig",
    "FactorEngine",
    "get_factor_engine",
    "DataSourceConfig",
    "KLineDataSource",
    "DataCenterDataSource",
    "MockDataSource",
    "get_data_source",
    "NeutralizationConfig",
    "FactorNeutralizer",
    "FactorCorrelationAnalyzer",
    "FactorICAnalyzer",
    "CorrelationResult",
    "ICResult",
    "IRResult",
    "get_neutralizer",
    "get_correlation_analyzer",
    "get_ic_analyzer",
    "indicators",
    "library",
]

__version__ = "2.0.0"
