"""
Hooks Module for OpenFinance Agents.

Provides hook system for intercepting and modifying agent behavior.
"""

from openfinance.agents.hooks.base import (
    HookEvent,
    HookInput,
    HookOutput,
    HookMatcher,
    HookRegistry,
    HookContext,
    PermissionDecision,
    hook,
)

__all__ = [
    "HookEvent",
    "HookInput",
    "HookOutput",
    "HookMatcher",
    "HookRegistry",
    "HookContext",
    "PermissionDecision",
    "hook",
]
