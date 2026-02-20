"""
Global logging configuration for OpenFinance.

Features:
- Dynamic log level control via environment variable or config
- Structured JSON logging with timestamps
- File rotation with size limit (100MB)
- Date-based file organization
- 30-day retention policy
- Module-specific log files
"""

import json
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
RETENTION_DAYS = 30
DEFAULT_LOG_LEVEL = os.getenv("OPENFINANCE_LOG_LEVEL", "INFO")

_current_log_level = DEFAULT_LOG_LEVEL.upper()


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "context") and record.context:
            log_data["context"] = record.context

        if hasattr(record, "extra_data") and record.extra_data:
            log_data["extra"] = record.extra_data

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        base_msg = f"[{timestamp}] {color}{record.levelname:8}{self.RESET} | {record.name:30} | {record.getMessage()}"
        
        if hasattr(record, "context") and record.context:
            base_msg += f" | context={json.dumps(record.context, ensure_ascii=False)}"
        
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
        
        return base_msg


class ModuleFileHandler:
    """Manages file handlers for different modules."""

    _handlers: dict[str, RotatingFileHandler] = {}

    @classmethod
    def get_handler(cls, module_name: str) -> RotatingFileHandler:
        if module_name in cls._handlers:
            return cls._handlers[module_name]

        cls._ensure_logs_dir()
        cls._cleanup_old_logs()

        safe_name = module_name.replace(".", "_").replace("/", "_")
        log_file = LOGS_DIR / f"{safe_name}.log"

        handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_FILE_SIZE,
            backupCount=10,
            encoding="utf-8",
        )
        handler.setFormatter(StructuredFormatter())

        cls._handlers[module_name] = handler
        return handler

    @classmethod
    def _ensure_logs_dir(cls) -> None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        date_dir = LOGS_DIR / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(exist_ok=True)

    @classmethod
    def _cleanup_old_logs(cls) -> None:
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)

        for item in LOGS_DIR.iterdir():
            if item.is_dir():
                try:
                    dir_date = datetime.strptime(item.name, "%Y-%m-%d")
                    if dir_date < cutoff_date:
                        for file in item.iterdir():
                            file.unlink()
                        item.rmdir()
                except ValueError:
                    pass


class ContextFilter(logging.Filter):
    """Filter that adds context to log records."""

    def __init__(self, context: dict[str, Any] | None = None):
        super().__init__()
        self._context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "context"):
            record.context = {}
        record.context.update(self._context)
        return True


class LogContext:
    """Context manager for adding context to logs."""

    _current_context: dict[str, Any] = {}

    def __init__(self, **kwargs: Any):
        self._new_context = kwargs
        self._old_context: dict[str, Any] = {}

    def __enter__(self) -> "LogContext":
        self._old_context = self._current_context.copy()
        self._current_context.update(self._new_context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        LogContext._current_context = self._old_context

    @classmethod
    def get_context(cls) -> dict[str, Any]:
        return cls._current_context.copy()


class OpenFinanceLogger(logging.Logger):
    """Custom logger with structured logging support."""

    def _log_with_context(
        self,
        level: int,
        msg: str,
        args: tuple,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        extra = kwargs.get("extra", {})
        extra["context"] = {**LogContext.get_context(), **(context or {})}
        kwargs["extra"] = extra
        super()._log(level, msg, args, **kwargs)

    def info_with_context(self, msg: str, context: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        self._log_with_context(logging.INFO, msg, args, context, **kwargs)

    def error_with_context(self, msg: str, context: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        self._log_with_context(logging.ERROR, msg, args, context, **kwargs)

    def warning_with_context(self, msg: str, context: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        self._log_with_context(logging.WARNING, msg, args, context, **kwargs)

    def debug_with_context(self, msg: str, context: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        self._log_with_context(logging.DEBUG, msg, args, context, **kwargs)


logging.setLoggerClass(OpenFinanceLogger)


def setup_logging(
    level: str | None = None,
    enable_file: bool = True,
    enable_console: bool = True,
    module_name: str = "openfinance",
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file: Enable file logging
        enable_console: Enable console logging
        module_name: Module name for file logging
    """
    global _current_log_level

    if level:
        _current_log_level = level.upper()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, _current_log_level, logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(HumanFormatter())
        console_handler.setLevel(getattr(logging, _current_log_level, logging.INFO))
        root_logger.addHandler(console_handler)

    if enable_file:
        file_handler = ModuleFileHandler.get_handler(module_name)
        file_handler.setLevel(getattr(logging, _current_log_level, logging.INFO))
        root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> OpenFinanceLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        OpenFinanceLogger instance
    """
    return logging.getLogger(name)  # type: ignore


def set_log_level(level: str) -> None:
    """
    Dynamically set the log level.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    global _current_log_level
    _current_log_level = level.upper()

    logging.getLogger().setLevel(getattr(logging, _current_log_level, logging.INFO))

    for handler in logging.getLogger().handlers:
        handler.setLevel(getattr(logging, _current_log_level, logging.INFO))


def get_log_level() -> str:
    """
    Get the current log level.

    Returns:
        Current log level string
    """
    return _current_log_level


@contextmanager
def log_context(**kwargs: Any):
    """
    Context manager for adding context to logs.

    Usage:
        with log_context(user_id="123", request_id="abc"):
            logger.info("Processing request")
    """
    with LogContext(**kwargs):
        yield


def log_function_call(
    logger: OpenFinanceLogger,
    func_name: str,
    args: dict[str, Any] | None = None,
    result: Any = None,
    error: Exception | None = None,
    duration_ms: float | None = None,
) -> None:
    """
    Log a function call with structured context.

    Args:
        logger: Logger instance
        func_name: Function name
        args: Function arguments
        result: Function result
        error: Exception if any
        duration_ms: Execution duration in milliseconds
    """
    context = {
        "function": func_name,
    }

    if args:
        context["args"] = args
    if result is not None:
        context["result"] = str(result)[:500]
    if duration_ms is not None:
        context["duration_ms"] = round(duration_ms, 2)

    if error:
        logger.error_with_context(
            f"Function {func_name} failed: {error}",
            context=context,
        )
    else:
        logger.info_with_context(
            f"Function {func_name} completed",
            context=context,
        )
