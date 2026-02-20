"""
Skill Error Handler for OpenFinance.

Provides error handling, retry strategies, and recovery mechanisms.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of skill errors."""

    TIMEOUT = "timeout"
    VALIDATION = "validation"
    EXECUTION = "execution"
    RESOURCE = "resource"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


class RetryStrategy(str, Enum):
    """Retry strategies."""

    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class SkillError(BaseModel):
    """Error information for skill execution."""

    error_id: str = Field(..., description="Error ID")
    skill_id: str = Field(..., description="Skill ID")
    error_type: ErrorType = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    exception_type: str | None = Field(default=None, description="Exception class")
    traceback: str | None = Field(default=None, description="Stack trace")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Error context",
    )


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    max_retries: int = Field(default=3, description="Maximum retry attempts")
    strategy: RetryStrategy = Field(
        default=RetryStrategy.EXPONENTIAL,
        description="Retry strategy",
    )
    base_delay_seconds: float = Field(default=1.0, description="Base delay")
    max_delay_seconds: float = Field(default=60.0, description="Maximum delay")
    retryable_errors: list[ErrorType] = Field(
        default=[ErrorType.TIMEOUT, ErrorType.EXECUTION, ErrorType.RESOURCE],
        description="Error types that can be retried",
    )


class RecoveryAction(BaseModel):
    """Recovery action for error handling."""

    action_type: str = Field(..., description="Action type")
    skill_id: str | None = Field(default=None, description="Fallback skill")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class SkillErrorHandler:
    """Handles errors in skill execution.

    Provides:
    - Error classification
    - Retry strategies
    - Recovery actions
    - Error logging and tracking
    """

    DEFAULT_RECOVERY_ACTIONS: dict[ErrorType, RecoveryAction] = {
        ErrorType.TIMEOUT: RecoveryAction(
            action_type="retry",
            params={"strategy": RetryStrategy.EXPONENTIAL},
        ),
        ErrorType.EXECUTION: RecoveryAction(
            action_type="retry",
            params={"strategy": RetryStrategy.LINEAR, "max_retries": 2},
        ),
        ErrorType.RESOURCE: RecoveryAction(
            action_type="wait_and_retry",
            params={"wait_seconds": 5},
        ),
        ErrorType.VALIDATION: RecoveryAction(
            action_type="fail",
            params={},
        ),
        ErrorType.DEPENDENCY: RecoveryAction(
            action_type="skip",
            params={},
        ),
    }

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.retry_config = retry_config or RetryConfig()
        self._errors: list[SkillError] = []
        self._recovery_actions = dict(self.DEFAULT_RECOVERY_ACTIONS)
        self._custom_handlers: dict[ErrorType, Callable] = {}

    def classify_error(self, exception: Exception) -> ErrorType:
        """Classify an exception into error type."""
        exception_name = type(exception).__name__.lower()

        if "timeout" in exception_name:
            return ErrorType.TIMEOUT
        if "validation" in exception_name or "value" in exception_name:
            return ErrorType.VALIDATION
        if "resource" in exception_name or "memory" in exception_name:
            return ErrorType.RESOURCE
        if "dependency" in exception_name or "import" in exception_name:
            return ErrorType.DEPENDENCY

        return ErrorType.EXECUTION

    def should_retry(
        self,
        error: SkillError,
        attempt: int,
    ) -> bool:
        """Determine if error should be retried."""
        if attempt >= self.retry_config.max_retries:
            return False

        return error.error_type in self.retry_config.retryable_errors

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before retry."""
        strategy = self.retry_config.strategy

        if strategy == RetryStrategy.NONE:
            return 0

        if strategy == RetryStrategy.IMMEDIATE:
            return 0

        if strategy == RetryStrategy.LINEAR:
            delay = self.retry_config.base_delay_seconds * attempt

        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = self.retry_config.base_delay_seconds * (2 ** (attempt - 1))

        else:
            delay = self.retry_config.base_delay_seconds

        return min(delay, self.retry_config.max_delay_seconds)

    async def handle_error(
        self,
        error: SkillError,
        attempt: int = 1,
    ) -> RecoveryAction:
        """Handle an error and determine recovery action."""
        self._errors.append(error)

        logger.error(
            f"Skill error: {error.skill_id} - {error.error_type}: {error.message}"
        )

        if self.should_retry(error, attempt):
            return RecoveryAction(
                action_type="retry",
                params={
                    "delay": self.calculate_delay(attempt),
                    "attempt": attempt + 1,
                },
            )

        custom_handler = self._custom_handlers.get(error.error_type)
        if custom_handler:
            try:
                result = custom_handler(error)
                if asyncio.iscoroutine(result):
                    result = await result
                if isinstance(result, RecoveryAction):
                    return result
            except Exception as e:
                logger.exception(f"Custom error handler failed: {e}")

        return self._recovery_actions.get(
            error.error_type,
            RecoveryAction(action_type="fail"),
        )

    def register_custom_handler(
        self,
        error_type: ErrorType,
        handler: Callable,
    ) -> None:
        """Register a custom error handler."""
        self._custom_handlers[error_type] = handler

    def set_recovery_action(
        self,
        error_type: ErrorType,
        action: RecoveryAction,
    ) -> None:
        """Set recovery action for an error type."""
        self._recovery_actions[error_type] = action

    def create_error(
        self,
        skill_id: str,
        exception: Exception,
        context: dict[str, Any] | None = None,
    ) -> SkillError:
        """Create a SkillError from an exception."""
        import traceback

        return SkillError(
            error_id=f"err_{skill_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            skill_id=skill_id,
            error_type=self.classify_error(exception),
            message=str(exception),
            exception_type=type(exception).__name__,
            traceback="".join(traceback.format_exception(type(exception), exception, exception.__traceback__)),
            context=context or {},
        )

    def get_errors(
        self,
        skill_id: str | None = None,
        error_type: ErrorType | None = None,
        limit: int = 100,
    ) -> list[SkillError]:
        """Get recorded errors."""
        errors = self._errors

        if skill_id:
            errors = [e for e in errors if e.skill_id == skill_id]
        if error_type:
            errors = [e for e in errors if e.error_type == error_type]

        return errors[-limit:]

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        type_counts: dict[ErrorType, int] = {}
        skill_counts: dict[str, int] = {}

        for error in self._errors:
            type_counts[error.error_type] = type_counts.get(error.error_type, 0) + 1
            skill_counts[error.skill_id] = skill_counts.get(error.skill_id, 0) + 1

        return {
            "total_errors": len(self._errors),
            "by_type": {t.value: c for t, c in type_counts.items()},
            "by_skill": skill_counts,
        }

    def clear_errors(self) -> None:
        """Clear recorded errors."""
        self._errors.clear()


async def execute_with_retry(
    func: Callable,
    skill_id: str,
    handler: SkillErrorHandler,
    max_retries: int = 3,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic."""
    attempt = 1

    while True:
        try:
            result = func(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        except Exception as e:
            error = handler.create_error(skill_id, e, kwargs)
            
            if not handler.should_retry(error, attempt):
                raise

            if attempt >= max_retries:
                raise

            delay = handler.calculate_delay(attempt)
            logger.warning(
                f"Retrying {skill_id} after error (attempt {attempt}/{max_retries}): {e}"
            )
            await asyncio.sleep(delay)
            attempt += 1
