"""
OpenFinance - Intelligent Financial Analysis Platform

A production-grade financial analysis platform powered by LLM and LangGraph.
"""

__version__ = "1.0.0"
__author__ = "OpenFinance Team"

from .base import MetaData, UserData, NLUData
from .intent import IntentType

__all__ = [
    "__version__",
    "__author__",
    "MetaData",
    "UserData",
    "NLUData",
    "IntentType",
]
