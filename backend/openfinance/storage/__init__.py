"""
Compatibility layer for storage module.

This module re-exports all storage components from the new location (domain.schemas)
to maintain backward compatibility with existing imports.

DEPRECATED: Import from 'openfinance.domain.schemas' instead.
"""

import warnings

from openfinance.domain.schemas.generic_model import (
    Base,
    GenericEntityModel,
    GenericRelationModel,
    GenericFactorModel,
    GenericStrategyModel,
)

warnings.warn(
    "Importing from 'openfinance.storage' is deprecated. "
    "Use 'openfinance.domain.schemas' instead.",
    DeprecationWarning,
    stacklevel=2
)
