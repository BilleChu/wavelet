"""
Source Module - Unified data source management.

Provides:
- Source types and enums
- Source configuration models
- Source registry for CRUD operations
- Health monitoring

Usage:
    from openfinance.datacenter.collector.source import (
        SourceRegistry, SourceConfig, SourceType, SourceStatus,
        get_source_registry,
    )
    
    # Get registry
    registry = get_source_registry()
    
    # Load from config file
    registry.load_from_file("config/sources.yaml")
    
    # Get source
    source = registry.get_source("eastmoney")
    
    # Check health
    health = await registry.check_health("eastmoney")
"""

from openfinance.datacenter.collector.source.types import (
    SourceType,
    SourceStatus,
    AuthType,
)
from openfinance.datacenter.collector.source.config import (
    SourceConfig,
    CollectionRule,
    ConnectionConfig,
    AuthConfig,
    RateLimitConfig,
    RetryConfig,
)
from openfinance.datacenter.collector.source.registry import (
    SourceRegistry,
    get_source_registry,
)
from openfinance.datacenter.collector.source.health import (
    HealthChecker,
    SourceHealth,
    HealthCheckResult,
)

__all__ = [
    "SourceType",
    "SourceStatus",
    "AuthType",
    "SourceConfig",
    "CollectionRule",
    "ConnectionConfig",
    "AuthConfig",
    "RateLimitConfig",
    "RetryConfig",
    "SourceRegistry",
    "get_source_registry",
    "HealthChecker",
    "SourceHealth",
    "HealthCheckResult",
]
