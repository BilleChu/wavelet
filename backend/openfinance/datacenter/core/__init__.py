"""
Core Abstraction Layer for Datacenter.

This module provides unified abstractions for:
- Type conversion utilities
- Stock code utilities
- HTTP client abstraction
- Field mapping registry
- Data source registry
- Unified configuration
- Configuration-driven collector framework

The goal is to eliminate code duplication and provide a clean,
extensible foundation for all data collection and processing.
"""

from .converters import (
    ValueConverter,
    DateConverter,
    PercentageConverter,
    safe_float,
    safe_int,
    safe_str,
    safe_decimal,
)
from .code_utils import (
    CodeUtils,
    Exchange,
    CodeFormat,
    normalize_code,
    format_code,
    validate_code,
)
from .http_client import (
    HttpClient,
    HttpRequest,
    HttpResponse,
    RetryPolicy,
    RateLimitPolicy,
    HttpClientError,
)
from .field_mapping import (
    FieldMappingRegistry,
    FieldMapping,
    FieldMappingRule,
    FieldType,
    apply_field_mapping,
)
from .source_registry import (
    SourceRegistry,
    SourceCapabilities,
    SourceConfig,
    SourceStatus,
    SourceHealth,
    get_source_registry,
)
from .config import (
    DatacenterConfig,
    SourceSettings,
    CollectionSettings,
    StorageSettings,
    CacheSettings,
    LoggingSettings,
    load_config,
    get_config,
    create_default_config,
)
from .collector_config import (
    ConfigDrivenCollector,
    CollectorConfig,
    RequestConfig,
    AuthConfig,
    ResponseParserConfig,
    RequestType,
    AuthType,
)
from .exceptions import (
    DatacenterError,
    NetworkError,
    ValidationError,
    TransformationError,
    StorageError,
    ConfigurationError,
    ExternalServiceError,
    ErrorSeverity,
    ErrorCategory,
    handle_errors,
    HealthChecker,
    HealthStatus,
    get_health_checker,
    register_health_check,
    get_error_statistics,
)

__all__ = [
    "ValueConverter",
    "DateConverter",
    "PercentageConverter",
    "safe_float",
    "safe_int",
    "safe_str",
    "safe_decimal",
    "CodeUtils",
    "Exchange",
    "CodeFormat",
    "normalize_code",
    "format_code",
    "validate_code",
    "HttpClient",
    "HttpRequest",
    "HttpResponse",
    "RetryPolicy",
    "RateLimitPolicy",
    "HttpClientError",
    "FieldMappingRegistry",
    "FieldMapping",
    "FieldMappingRule",
    "FieldType",
    "apply_field_mapping",
    "SourceRegistry",
    "SourceCapabilities",
    "SourceConfig",
    "SourceStatus",
    "SourceHealth",
    "get_source_registry",
    "DatacenterConfig",
    "SourceSettings",
    "CollectionSettings",
    "StorageSettings",
    "CacheSettings",
    "LoggingSettings",
    "load_config",
    "get_config",
    "create_default_config",
    "ConfigDrivenCollector",
    "CollectorConfig",
    "RequestConfig",
    "AuthConfig",
    "ResponseParserConfig",
    "RequestType",
    "AuthType",
    "DatacenterError",
    "NetworkError",
    "ValidationError",
    "TransformationError",
    "StorageError",
    "ConfigurationError",
    "ExternalServiceError",
    "ErrorSeverity",
    "ErrorCategory",
    "handle_errors",
    "HealthChecker",
    "HealthStatus",
    "get_health_checker",
    "register_health_check",
    "get_error_statistics",
]
