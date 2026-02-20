"""
Exception Handling and Monitoring Module.

This module provides comprehensive exception handling and monitoring
capabilities for the datacenter:
- Custom exception hierarchy
- Error handling decorators
- Monitoring and alerting system
- Health check endpoints
"""

import asyncio
import functools
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories."""
    NETWORK = "network"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    STORAGE = "storage"
    CONFIGURATION = "configuration"
    EXTERNAL = "external"
    INTERNAL = "internal"


class DatacenterError(Exception):
    """Base exception for datacenter errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: dict[str, Any] | None = None,
        recoverable: bool = True,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.recoverable = recoverable
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
        }


class NetworkError(DatacenterError):
    """Network-related errors."""
    
    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            details=details,
            **kwargs,
        )


class ValidationError(DatacenterError):
    """Data validation errors."""
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details,
            **kwargs,
        )


class TransformationError(DatacenterError):
    """Data transformation errors."""
    
    def __init__(
        self,
        message: str,
        source_field: str | None = None,
        target_field: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if source_field:
            details["source_field"] = source_field
        if target_field:
            details["target_field"] = target_field
        
        super().__init__(
            message=message,
            category=ErrorCategory.TRANSFORMATION,
            details=details,
            **kwargs,
        )


class StorageError(DatacenterError):
    """Storage-related errors."""
    
    def __init__(
        self,
        message: str,
        table: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if table:
            details["table"] = table
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs,
        )


class ConfigurationError(DatacenterError):
    """Configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            details=details,
            **kwargs,
        )


class ExternalServiceError(DatacenterError):
    """External service errors."""
    
    def __init__(
        self,
        message: str,
        service: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if service:
            details["service"] = service
        
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs,
        )


@dataclass
class ErrorContext:
    """Context for error handling."""
    operation: str
    component: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    success: bool = True
    error: DatacenterError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() * 1000


def handle_errors(
    default_return: Any = None,
    reraise: bool = False,
    log_errors: bool = True,
    alert_on_error: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for unified error handling.
    
    Args:
        default_return: Value to return on error
        reraise: Whether to reraise the exception
        log_errors: Whether to log errors
        alert_on_error: Whether to trigger alerts
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            context = ErrorContext(
                operation=func.__name__,
                component=func.__module__,
            )
            
            try:
                result = await func(*args, **kwargs)
                context.success = True
                return result
            
            except DatacenterError as e:
                context.success = False
                context.error = e
                _handle_error(e, log_errors, alert_on_error)
                if reraise:
                    raise
                return default_return
            
            except Exception as e:
                context.success = False
                wrapped = DatacenterError(
                    message=str(e),
                    category=ErrorCategory.INTERNAL,
                    severity=ErrorSeverity.HIGH,
                    details={"original_type": type(e).__name__},
                )
                context.error = wrapped
                _handle_error(wrapped, log_errors, alert_on_error)
                if reraise:
                    raise wrapped from e
                return default_return
            
            finally:
                context.end_time = datetime.now()
                _record_context(context)
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            context = ErrorContext(
                operation=func.__name__,
                component=func.__module__,
            )
            
            try:
                result = func(*args, **kwargs)
                context.success = True
                return result
            
            except DatacenterError as e:
                context.success = False
                context.error = e
                _handle_error(e, log_errors, alert_on_error)
                if reraise:
                    raise
                return default_return
            
            except Exception as e:
                context.success = False
                wrapped = DatacenterError(
                    message=str(e),
                    category=ErrorCategory.INTERNAL,
                    severity=ErrorSeverity.HIGH,
                    details={"original_type": type(e).__name__},
                )
                context.error = wrapped
                _handle_error(wrapped, log_errors, alert_on_error)
                if reraise:
                    raise wrapped from e
                return default_return
            
            finally:
                context.end_time = datetime.now()
                _record_context(context)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def _handle_error(
    error: DatacenterError,
    log_errors: bool,
    alert_on_error: bool,
) -> None:
    """Handle an error with logging and alerting."""
    if log_errors:
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(error.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"[{error.category.value}] {error.message}",
            extra={"error_details": error.details},
        )
    
    if alert_on_error and error.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
        _trigger_alert(error)


def _record_context(context: ErrorContext) -> None:
    """Record error context for monitoring."""
    global _error_contexts
    _error_contexts.append(context)
    
    if len(_error_contexts) > 1000:
        _error_contexts = _error_contexts[-500:]


def _trigger_alert(error: DatacenterError) -> None:
    """Trigger an alert for critical errors."""
    global _alert_handlers
    
    for handler in _alert_handlers:
        try:
            handler(error)
        except Exception as e:
            logger.error(f"Alert handler failed: {e}")


_error_contexts: list[ErrorContext] = []
_alert_handlers: list[Callable[[DatacenterError], None]] = []


def register_alert_handler(handler: Callable[[DatacenterError], None]) -> None:
    """Register an alert handler."""
    _alert_handlers.append(handler)


def get_error_statistics() -> dict[str, Any]:
    """Get error statistics."""
    total = len(_error_contexts)
    errors = [c for c in _error_contexts if not c.success]
    
    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    
    for ctx in errors:
        if ctx.error:
            cat = ctx.error.category.value
            sev = ctx.error.severity.value
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
    
    return {
        "total_operations": total,
        "total_errors": len(errors),
        "error_rate": len(errors) / total if total > 0 else 0,
        "by_category": by_category,
        "by_severity": by_severity,
    }


def clear_error_history() -> None:
    """Clear error history."""
    global _error_contexts
    _error_contexts = []


@dataclass
class HealthStatus:
    """Health status for a component."""
    component: str
    healthy: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Health checker for monitoring system status.
    
    Provides health check endpoints and status monitoring.
    """
    
    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], HealthStatus]] = {}
    
    def register_check(
        self,
        name: str,
        check_func: Callable[[], HealthStatus],
    ) -> None:
        """Register a health check."""
        self._checks[name] = check_func
    
    async def run_checks(self) -> dict[str, HealthStatus]:
        """Run all health checks."""
        results = {}
        
        for name, check_func in self._checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    status = await check_func()
                else:
                    status = check_func()
                results[name] = status
            except Exception as e:
                results[name] = HealthStatus(
                    component=name,
                    healthy=False,
                    message=f"Health check failed: {e}",
                )
        
        return results
    
    async def get_overall_health(self) -> HealthStatus:
        """Get overall system health."""
        checks = await self.run_checks()
        
        healthy = all(c.healthy for c in checks.values())
        
        issues = [name for name, status in checks.items() if not status.healthy]
        
        return HealthStatus(
            component="datacenter",
            healthy=healthy,
            message="All systems healthy" if healthy else f"Issues: {', '.join(issues)}",
            details={name: status.healthy for name, status in checks.items()},
        )


_global_health_checker = HealthChecker()


def get_health_checker() -> HealthChecker:
    """Get the global health checker."""
    return _global_health_checker


def register_health_check(
    name: str,
    check_func: Callable[[], HealthStatus],
) -> None:
    """Register a health check with the global checker."""
    _global_health_checker.register_check(name, check_func)
