"""
Common Utilities for OpenFinance.

Provides shared utility functions across the codebase.
"""

from openfinance.utils.stock_code import (
    normalize_stock_code,
    get_stock_exchange,
    format_stock_code_with_exchange,
    is_valid_stock_code,
)

from openfinance.utils.web_fetch import (
    web_fetch,
    web_fetch_simple,
    FetchMethod,
    FetchResult,
)

__all__ = [
    "normalize_stock_code",
    "get_stock_exchange",
    "format_stock_code_with_exchange",
    "is_valid_stock_code",
    "web_fetch",
    "web_fetch_simple",
    "FetchMethod",
    "FetchResult",
]