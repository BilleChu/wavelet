"""
Compatibility layer for engine module.

This module re-exports all engines from the new location (services.storage)
to maintain backward compatibility with existing imports.

DEPRECATED: Import from 'openfinance.services.storage' instead.
"""

import warnings

from openfinance.services.storage import (
    EntityEngine,
    EntityCreateResult,
    EntitySearchResult,
    RelationEngine,
    RelationCreateResult,
    FactorEngine,
    StrategyEngine,
)

warnings.warn(
    "Importing from 'openfinance.engine' is deprecated. "
    "Use 'openfinance.services.storage' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "EntityEngine",
    "RelationEngine",
    "FactorEngine",
    "StrategyEngine",
]
