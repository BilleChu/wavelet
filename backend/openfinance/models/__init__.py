"""
Compatibility layer for models module.

This module re-exports all models from the new location (domain.models)
to maintain backward compatibility with existing imports.

DEPRECATED: Import from 'openfinance.domain.models' instead.
"""

import warnings

from openfinance.domain.models import *

warnings.warn(
    "Importing from 'openfinance.models' is deprecated. "
    "Use 'openfinance.domain.models' instead.",
    DeprecationWarning,
    stacklevel=2
)
