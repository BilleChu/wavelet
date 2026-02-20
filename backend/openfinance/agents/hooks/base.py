"""
Hook Base Classes for OpenFinance Skills.

Provides the foundation for the hook system.
Inspired by Claude Agent SDK hooks.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HookEvent(str, Enum):
    """Hook event types."""

    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    PRE_COMPACT = "PreCompact"
    STOP = "Stop"
    ERROR = "Error"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"


class PermissionDecision(str, Enum):
    """Permission decision for tool use."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class HookInput(BaseModel):
    """Input for a hook handler."""

    hook_event_name: str = Field(..., description="Hook event name")
    tool_name: str | None = Field(default=None, description="Tool name if applicable")
    tool_input: dict[str, Any] | None = Field(
        default=None,
        description="Tool input arguments",
    )
    tool_use_id: str | None = Field(default=None, description="Tool use ID")
    tool_result: str | None = Field(default=None, description="Tool result")
    prompt: str | None = Field(default=None, description="User prompt")
    error: str | None = Field(default=None, description="Error message")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )


class HookOutput(BaseModel):
    """Output from a hook handler."""

    permission_decision: PermissionDecision | None = Field(
        default=None,
        description="Permission decision",
    )
    permission_decision_reason: str | None = Field(
        default=None,
        description="Reason for decision",
    )
    modified_input: dict[str, Any] | None = Field(
        default=None,
        description="Modified tool input",
    )
    modified_result: str | None = Field(
        default=None,
        description="Modified tool result",
    )
    modified_prompt: str | None = Field(
        default=None,
        description="Modified user prompt",
    )
    additional_output: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional output",
    )
    continue_: bool = Field(default=True, description="Whether to continue")
    stop_reason: str | None = Field(default=None, description="Reason for stopping")


class HookMatcher(BaseModel):
    """Matcher for routing hooks to specific tools."""

    matcher: str = Field(..., description="Tool name pattern to match")
    hooks: list[str] = Field(
        default_factory=list,
        description="Hook handler names",
    )
    priority: int = Field(default=0, description="Matcher priority")
    enabled: bool = Field(default=True, description="Whether matcher is enabled")

    def matches(self, tool_name: str) -> bool:
        """Check if this matcher matches a tool name."""
        if not self.enabled:
            return False

        if self.matcher == "*":
            return True

        if self.matcher == tool_name:
            return True

        if self.matcher.endswith("*"):
            prefix = self.matcher[:-1]
            return tool_name.startswith(prefix)

        return False


class HookContext(BaseModel):
    """Context for hook execution."""

    session_id: str = Field(..., description="Session ID")
    user_id: str | None = Field(default=None, description="User ID")
    trace_id: str | None = Field(default=None, description="Trace ID")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Execution timestamp",
    )
    execution_count: int = Field(default=0, description="Number of executions")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class HookRegistry:
    """Registry for managing hooks.

    Example:
        registry = HookRegistry()

        @registry.register("PreToolUse")
        async def check_dangerous_tools(input: HookInput) -> HookOutput:
            if input.tool_name == "execute_command":
                if "rm -rf" in input.tool_input.get("command", ""):
                    return HookOutput(
                        permission_decision=PermissionDecision.DENY,
                        permission_decision_reason="Dangerous command blocked",
                    )
            return HookOutput()
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable]] = {}
        self._matchers: list[HookMatcher] = []
        self._contexts: dict[str, HookContext] = {}

    def register(
        self,
        event: str | HookEvent,
        matcher: str | None = None,
    ) -> Callable:
        """Decorator to register a hook handler.

        Args:
            event: The hook event name.
            matcher: Optional tool name matcher.

        Returns:
            Decorator function.
        """
        event_name = event.value if isinstance(event, HookEvent) else event

        def decorator(func: Callable) -> Callable:
            if event_name not in self._hooks:
                self._hooks[event_name] = []
            self._hooks[event_name].append(func)

            if matcher:
                self._matchers.append(HookMatcher(
                    matcher=matcher,
                    hooks=[func.__name__],
                ))

            logger.debug(f"Registered hook: {event_name} -> {func.__name__}")
            return func

        return decorator

    def add_hook(
        self,
        event: str | HookEvent,
        handler: Callable,
        matcher: str | None = None,
    ) -> None:
        """Add a hook handler directly.

        Args:
            event: The hook event name.
            handler: The hook handler function.
            matcher: Optional tool name matcher.
        """
        event_name = event.value if isinstance(event, HookEvent) else event

        if event_name not in self._hooks:
            self._hooks[event_name] = []
        self._hooks[event_name].append(handler)

        if matcher:
            self._matchers.append(HookMatcher(
                matcher=matcher,
                hooks=[handler.__name__],
            ))

    def remove_hook(
        self,
        event: str | HookEvent,
        handler: Callable,
    ) -> bool:
        """Remove a hook handler.

        Args:
            event: The hook event name.
            handler: The hook handler to remove.

        Returns:
            True if removed, False if not found.
        """
        event_name = event.value if isinstance(event, HookEvent) else event

        if event_name in self._hooks:
            try:
                self._hooks[event_name].remove(handler)
                return True
            except ValueError:
                pass
        return False

    def get_hooks(
        self,
        event: str | HookEvent,
        tool_name: str | None = None,
    ) -> list[Callable]:
        """Get hooks for an event.

        Args:
            event: The hook event name.
            tool_name: Optional tool name for matching.

        Returns:
            List of matching hook handlers.
        """
        event_name = event.value if isinstance(event, HookEvent) else event

        hooks = self._hooks.get(event_name, [])

        if tool_name:
            matched_hooks = []
            for matcher in self._matchers:
                if matcher.matches(tool_name):
                    for hook_name in matcher.hooks:
                        for hook in hooks:
                            if hook.__name__ == hook_name:
                                matched_hooks.append(hook)
            return matched_hooks

        return hooks

    async def execute(
        self,
        event: str | HookEvent,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Execute hooks for an event.

        Args:
            event: The hook event name.
            input_data: The hook input data.
            context: Optional execution context.

        Returns:
            Combined hook output.
        """
        event_name = event.value if isinstance(event, HookEvent) else event

        hooks = self.get_hooks(event_name, input_data.tool_name)

        result = HookOutput()

        for hook in hooks:
            try:
                output = hook(input_data, context)
                if asyncio.iscoroutine(output):
                    output = await output

                if isinstance(output, HookOutput):
                    result = self._merge_outputs(result, output)

                    if not result.continue_:
                        break

            except Exception as e:
                logger.exception(f"Hook execution failed: {hook.__name__}")
                result.additional_output["error"] = str(e)

        return result

    def _merge_outputs(
        self,
        base: HookOutput,
        override: HookOutput,
    ) -> HookOutput:
        """Merge two hook outputs."""
        return HookOutput(
            permission_decision=override.permission_decision or base.permission_decision,
            permission_decision_reason=override.permission_decision_reason or base.permission_decision_reason,
            modified_input=override.modified_input or base.modified_input,
            modified_result=override.modified_result or base.modified_result,
            modified_prompt=override.modified_prompt or base.modified_prompt,
            additional_output={**base.additional_output, **override.additional_output},
            continue_=override.continue_ if override.continue_ is not None else base.continue_,
            stop_reason=override.stop_reason or base.stop_reason,
        )

    def clear(self, event: str | HookEvent | None = None) -> None:
        """Clear hooks.

        Args:
            event: Optional event to clear. If None, clears all.
        """
        if event:
            event_name = event.value if isinstance(event, HookEvent) else event
            self._hooks.pop(event_name, None)
        else:
            self._hooks.clear()
            self._matchers.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        return {
            "events": {
                event: len(hooks)
                for event, hooks in self._hooks.items()
            },
            "matchers": len(self._matchers),
            "total_hooks": sum(len(h) for h in self._hooks.values()),
        }


_default_registry = HookRegistry()


def get_hook_registry() -> HookRegistry:
    """Get the default hook registry."""
    return _default_registry


def hook(
    event: str | HookEvent,
    matcher: str | None = None,
) -> Callable:
    """Decorator to register a hook with the default registry.

    Example:
        @hook(HookEvent.PRE_TOOL_USE, matcher="execute_command")
        async def check_command(input: HookInput) -> HookOutput:
            if "rm -rf" in input.tool_input.get("command", ""):
                return HookOutput(
                    permission_decision=PermissionDecision.DENY,
                )
            return HookOutput()
    """
    return _default_registry.register(event, matcher)
