"""
Predefined Hook Handlers for OpenFinance Skills.

Provides common hook implementations for security, validation, and logging.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from openfinance.agents.hooks.base import (
    HookContext,
    HookEvent,
    HookInput,
    HookOutput,
    PermissionDecision,
)

logger = logging.getLogger(__name__)


class PermissionHook:
    """Hook for checking tool permissions.

    Example:
        permission_hook = PermissionHook()
        permission_hook.deny("execute_command", pattern="rm -rf")
        permission_hook.allow("read_file")
    """

    def __init__(self) -> None:
        self._allowed: set[str] = set()
        self._denied: set[str] = set()
        self._denied_patterns: dict[str, list[str]] = defaultdict(list)
        self._ask_patterns: dict[str, list[str]] = defaultdict(list)

    def allow(self, tool_name: str) -> None:
        """Allow a tool."""
        self._allowed.add(tool_name)

    def deny(self, tool_name: str, pattern: str | None = None) -> None:
        """Deny a tool, optionally with a pattern."""
        self._denied.add(tool_name)
        if pattern:
            self._denied_patterns[tool_name].append(pattern)

    def ask(self, tool_name: str, pattern: str) -> None:
        """Require user confirmation for a pattern."""
        self._ask_patterns[tool_name].append(pattern)

    async def __call__(
        self,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Check permissions."""
        tool_name = input_data.tool_name
        if not tool_name:
            return HookOutput()

        if tool_name in self._denied:
            return HookOutput(
                permission_decision=PermissionDecision.DENY,
                permission_decision_reason=f"Tool '{tool_name}' is denied",
            )

        for pattern in self._denied_patterns.get(tool_name, []):
            if self._matches_pattern(input_data, pattern):
                return HookOutput(
                    permission_decision=PermissionDecision.DENY,
                    permission_decision_reason=f"Pattern '{pattern}' is denied for '{tool_name}'",
                )

        for pattern in self._ask_patterns.get(tool_name, []):
            if self._matches_pattern(input_data, pattern):
                return HookOutput(
                    permission_decision=PermissionDecision.ASK,
                    permission_decision_reason=f"Pattern '{pattern}' requires confirmation for '{tool_name}'",
                )

        if self._allowed and tool_name not in self._allowed:
            return HookOutput(
                permission_decision=PermissionDecision.DENY,
                permission_decision_reason=f"Tool '{tool_name}' is not in allowed list",
            )

        return HookOutput(
            permission_decision=PermissionDecision.ALLOW,
        )

    def _matches_pattern(self, input_data: HookInput, pattern: str) -> bool:
        """Check if input matches a pattern."""
        if not input_data.tool_input:
            return False

        for value in input_data.tool_input.values():
            if isinstance(value, str) and pattern in value:
                return True
            if isinstance(value, dict):
                for v in value.values():
                    if isinstance(v, str) and pattern in v:
                        return True

        return False


class ValidationHook:
    """Hook for validating tool inputs.

    Example:
        validation_hook = ValidationHook()
        validation_hook.add_rule("read_file", "path", required=True, pattern=r"^/safe/")
        validation_hook.add_rule("calculate", "expression", max_length=100)
    """

    def __init__(self) -> None:
        self._rules: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    def add_rule(
        self,
        tool_name: str,
        param_name: str,
        required: bool = False,
        pattern: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        allowed_values: list[Any] | None = None,
    ) -> None:
        """Add a validation rule."""
        self._rules[tool_name][param_name] = {
            "required": required,
            "pattern": pattern,
            "min_value": min_value,
            "max_value": max_value,
            "min_length": min_length,
            "max_length": max_length,
            "allowed_values": allowed_values,
        }

    async def __call__(
        self,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Validate input."""
        tool_name = input_data.tool_name
        if not tool_name or not input_data.tool_input:
            return HookOutput()

        rules = self._rules.get(tool_name, {})
        errors = []
        modified_input = dict(input_data.tool_input)

        for param_name, rule in rules.items():
            value = input_data.tool_input.get(param_name)

            if rule.get("required") and value is None:
                errors.append(f"Parameter '{param_name}' is required")
                continue

            if value is None:
                continue

            if rule.get("pattern"):
                if not re.match(rule["pattern"], str(value)):
                    errors.append(f"Parameter '{param_name}' does not match pattern")

            if rule.get("min_value") is not None:
                if isinstance(value, (int, float)) and value < rule["min_value"]:
                    errors.append(f"Parameter '{param_name}' is below minimum")

            if rule.get("max_value") is not None:
                if isinstance(value, (int, float)) and value > rule["max_value"]:
                    errors.append(f"Parameter '{param_name}' exceeds maximum")

            if rule.get("min_length") is not None:
                if isinstance(value, str) and len(value) < rule["min_length"]:
                    errors.append(f"Parameter '{param_name}' is too short")

            if rule.get("max_length") is not None:
                if isinstance(value, str) and len(value) > rule["max_length"]:
                    errors.append(f"Parameter '{param_name}' is too long")

            if rule.get("allowed_values"):
                if value not in rule["allowed_values"]:
                    errors.append(f"Parameter '{param_name}' has invalid value")

        if errors:
            return HookOutput(
                permission_decision=PermissionDecision.DENY,
                permission_decision_reason="; ".join(errors),
            )

        return HookOutput(modified_input=modified_input)


class LoggingHook:
    """Hook for logging tool usage.

    Example:
        logging_hook = LoggingHook(level="INFO", include_input=True)
    """

    def __init__(
        self,
        level: str = "INFO",
        include_input: bool = False,
        include_output: bool = False,
        log_file: str | None = None,
    ) -> None:
        self.level = level.upper()
        self.include_input = include_input
        self.include_output = include_output
        self.log_file = log_file
        self._log_count = 0

    async def __call__(
        self,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Log tool usage."""
        self._log_count += 1

        log_data = {
            "event": input_data.hook_event_name,
            "tool": input_data.tool_name,
            "timestamp": datetime.now().isoformat(),
            "count": self._log_count,
        }

        if context:
            log_data["session_id"] = context.session_id
            log_data["user_id"] = context.user_id

        if self.include_input and input_data.tool_input:
            log_data["input"] = input_data.tool_input

        if self.include_output and input_data.tool_result:
            log_data["result"] = input_data.tool_result[:500]

        log_msg = f"[Hook] {log_data}"

        if self.level == "DEBUG":
            logger.debug(log_msg)
        elif self.level == "WARNING":
            logger.warning(log_msg)
        elif self.level == "ERROR":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

        return HookOutput()


class RateLimitHook:
    """Hook for rate limiting tool usage.

    Example:
        rate_limit = RateLimitHook(max_calls=10, window_seconds=60)
        rate_limit.set_limit("execute_command", max_calls=5, window_seconds=60)
    """

    def __init__(
        self,
        max_calls: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self.default_max_calls = max_calls
        self.default_window = timedelta(seconds=window_seconds)
        self._limits: dict[str, tuple[int, timedelta]] = {}
        self._calls: dict[str, list[datetime]] = defaultdict(list)

    def set_limit(
        self,
        tool_name: str,
        max_calls: int,
        window_seconds: int,
    ) -> None:
        """Set rate limit for a tool."""
        self._limits[tool_name] = (max_calls, timedelta(seconds=window_seconds))

    async def __call__(
        self,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Check rate limit."""
        tool_name = input_data.tool_name
        if not tool_name:
            return HookOutput()

        max_calls, window = self._limits.get(
            tool_name,
            (self.default_max_calls, self.default_window),
        )

        now = datetime.now()
        cutoff = now - window

        self._calls[tool_name] = [
            ts for ts in self._calls[tool_name]
            if ts > cutoff
        ]

        if len(self._calls[tool_name]) >= max_calls:
            return HookOutput(
                permission_decision=PermissionDecision.DENY,
                permission_decision_reason=f"Rate limit exceeded for '{tool_name}' ({max_calls} calls per {window.seconds}s)",
            )

        self._calls[tool_name].append(now)
        return HookOutput()

    def reset(self, tool_name: str | None = None) -> None:
        """Reset rate limit counters."""
        if tool_name:
            self._calls.pop(tool_name, None)
        else:
            self._calls.clear()


class TimeoutHook:
    """Hook for enforcing timeouts."""

    def __init__(self, default_timeout: float = 30.0) -> None:
        self.default_timeout = default_timeout
        self._timeouts: dict[str, float] = {}

    def set_timeout(self, tool_name: str, timeout: float) -> None:
        """Set timeout for a tool."""
        self._timeouts[tool_name] = timeout

    async def __call__(
        self,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Add timeout to input."""
        tool_name = input_data.tool_name
        if not tool_name or not input_data.tool_input:
            return HookOutput()

        timeout = self._timeouts.get(tool_name, self.default_timeout)

        modified_input = dict(input_data.tool_input)
        if "timeout" not in modified_input:
            modified_input["timeout"] = timeout

        return HookOutput(modified_input=modified_input)


class SanitizationHook:
    """Hook for sanitizing input/output."""

    def __init__(self) -> None:
        self._sensitive_patterns = [
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"api_key\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
            r"token\s*=\s*['\"][^'\"]+['\"]",
        ]
        self._replacement = "[REDACTED]"

    def add_pattern(self, pattern: str) -> None:
        """Add a sensitive pattern."""
        self._sensitive_patterns.append(pattern)

    async def __call__(
        self,
        input_data: HookInput,
        context: HookContext | None = None,
    ) -> HookOutput:
        """Sanitize input/output."""
        if input_data.tool_input:
            modified_input = self._sanitize_dict(input_data.tool_input)
            return HookOutput(modified_input=modified_input)

        if input_data.tool_result:
            modified_result = self._sanitize_string(input_data.tool_result)
            return HookOutput(modified_result=modified_result)

        return HookOutput()

    def _sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                result[key] = self._sanitize_dict(value)
            else:
                result[key] = value
        return result

    def _sanitize_string(self, text: str) -> str:
        """Sanitize a string."""
        result = text
        for pattern in self._sensitive_patterns:
            result = re.sub(pattern, self._replacement, result, flags=re.IGNORECASE)
        return result


def create_default_hooks() -> dict[str, list[Any]]:
    """Create default hooks for common use cases.

    Returns:
        Dictionary mapping event names to hook lists.
    """
    permission_hook = PermissionHook()
    permission_hook.deny("execute_command", pattern="rm -rf")
    permission_hook.deny("execute_command", pattern="sudo")
    permission_hook.deny("write_file", pattern="/etc/")

    validation_hook = ValidationHook()
    validation_hook.add_rule("read_file", "path", required=True)
    validation_hook.add_rule("write_file", "path", required=True)
    validation_hook.add_rule("write_file", "content", required=True)
    validation_hook.add_rule("execute_command", "command", required=True, max_length=1000)

    logging_hook = LoggingHook(level="INFO", include_input=False)

    rate_limit_hook = RateLimitHook(max_calls=100, window_seconds=60)
    rate_limit_hook.set_limit("execute_command", max_calls=10, window_seconds=60)
    rate_limit_hook.set_limit("web_search", max_calls=30, window_seconds=60)

    return {
        HookEvent.PRE_TOOL_USE.value: [
            permission_hook,
            validation_hook,
            rate_limit_hook,
        ],
        HookEvent.POST_TOOL_USE.value: [
            logging_hook,
        ],
        HookEvent.USER_PROMPT_SUBMIT.value: [
            logging_hook,
        ],
    }
