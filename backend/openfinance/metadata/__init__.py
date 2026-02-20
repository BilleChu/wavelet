"""
Compatibility layer for metadata module.

This module re-exports all metadata components from the new location (domain.metadata)
to maintain backward compatibility with existing imports.

DEPRECATED: Import from 'openfinance.domain.metadata' instead.
"""

import warnings

from openfinance.domain.metadata import *

warnings.warn(
    "Importing from 'openfinance.metadata' is deprecated. "
    "Use 'openfinance.domain.metadata' instead.",
    DeprecationWarning,
    stacklevel=2
)
