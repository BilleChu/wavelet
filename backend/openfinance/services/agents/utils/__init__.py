"""
Agent Utils Module.

Utility functions for agents.
"""

from openfinance.agents.utils.web_fetch import (
    web_fetch,
    web_fetch_simple,
    FetchMethod,
    FetchResult,
)

__all__ = [
    "web_fetch",
    "web_fetch_simple",
    "FetchMethod",
    "FetchResult",
]
