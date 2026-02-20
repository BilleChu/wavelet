"""
Data Source Registry.

Provides unified data source management with capability declarations,
health monitoring, and client management.

Usage:
    from datacenter.core import SourceRegistry, SourceCapabilities
    
    registry = SourceRegistry()
    
    registry.register_source(
        source=DataSource.EASTMONEY,
        capabilities=SourceCapabilities(
            data_types=[DataType.STOCK_QUOTE, DataType.STOCK_KLINE],
            supports_realtime=True,
        ),
    )
    
    source = registry.get_source_for(DataType.STOCK_QUOTE)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..collector import DataType, DataFrequency


class SourceStatus(str, Enum):
    """Data source status."""
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class SourceCapabilities:
    """
    Data source capability declaration.
    
    Attributes:
        data_types: Supported data types
        frequencies: Supported data frequencies
        supports_realtime: Whether realtime data is supported
        supports_history: Whether historical data is supported
        max_history_days: Maximum history days available
        rate_limit_per_second: Rate limit (requests per second)
        requires_auth: Whether authentication is required
    """
    data_types: list[DataType] = field(default_factory=list)
    frequencies: list[DataFrequency] = field(default_factory=lambda: [DataFrequency.DAILY])
    supports_realtime: bool = False
    supports_history: bool = True
    max_history_days: int = 3650
    rate_limit_per_second: float = 10.0
    requires_auth: bool = False
    
    def supports(self, data_type: DataType, frequency: DataFrequency | None = None) -> bool:
        """Check if data type and frequency are supported."""
        if data_type not in self.data_types:
            return False
        if frequency and frequency not in self.frequencies:
            return False
        return True


@dataclass
class SourceConfig:
    """
    Data source configuration.
    
    Attributes:
        source_id: Unique source identifier
        name: Display name
        base_url: Base URL for API
        api_key: API key (if required)
        headers: Default headers
        timeout: Request timeout
        retry_count: Number of retries
    """
    source_id: str
    name: str
    base_url: str = ""
    api_key: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    retry_count: int = 3
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceHealth:
    """
    Data source health status.
    
    Attributes:
        source_id: Source identifier
        status: Current status
        last_check: Last health check time
        last_success: Last successful request time
        last_failure: Last failure time
        consecutive_failures: Number of consecutive failures
        total_requests: Total request count
        success_count: Successful request count
        error_count: Error count
        avg_response_time: Average response time in ms
    """
    source_id: str
    status: SourceStatus = SourceStatus.UNKNOWN
    last_check: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests
    
    def record_success(self, response_time_ms: float) -> None:
        """Record a successful request."""
        self.last_success = datetime.now()
        self.consecutive_failures = 0
        self.total_requests += 1
        self.success_count += 1
        self._update_avg_response_time(response_time_ms)
        self._update_status()
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self.last_failure = datetime.now()
        self.consecutive_failures += 1
        self.total_requests += 1
        self.error_count += 1
        self._update_status()
    
    def _update_avg_response_time(self, response_time_ms: float) -> None:
        """Update average response time."""
        if self.total_requests == 1:
            self.avg_response_time = response_time_ms
        else:
            self.avg_response_time = (
                (self.avg_response_time * (self.total_requests - 1) + response_time_ms)
                / self.total_requests
            )
    
    def _update_status(self) -> None:
        """Update status based on recent activity."""
        if self.consecutive_failures >= 5:
            self.status = SourceStatus.UNAVAILABLE
        elif self.consecutive_failures >= 2:
            self.status = SourceStatus.DEGRADED
        elif self.success_rate < 0.5:
            self.status = SourceStatus.DEGRADED
        else:
            self.status = SourceStatus.AVAILABLE


class SourceRegistry:
    """
    Central registry for data sources.
    
    Manages data source registration, capability queries,
    health monitoring, and client management.
    """
    
    def __init__(self) -> None:
        self._sources: dict[str, SourceConfig] = {}
        self._capabilities: dict[str, SourceCapabilities] = {}
        self._health: dict[str, SourceHealth] = {}
        self._clients: dict[str, Any] = {}
    
    def register(
        self,
        config: SourceConfig,
        capabilities: SourceCapabilities | None = None,
    ) -> None:
        """
        Register a data source.
        
        Args:
            config: Source configuration
            capabilities: Source capabilities
        """
        self._sources[config.source_id] = config
        if capabilities:
            self._capabilities[config.source_id] = capabilities
        self._health[config.source_id] = SourceHealth(source_id=config.source_id)
    
    def get_config(self, source_id: str) -> SourceConfig | None:
        """Get source configuration."""
        return self._sources.get(source_id)
    
    def get_capabilities(self, source_id: str) -> SourceCapabilities | None:
        """Get source capabilities."""
        return self._capabilities.get(source_id)
    
    def get_health(self, source_id: str) -> SourceHealth | None:
        """Get source health status."""
        return self._health.get(source_id)
    
    def get_source_for(
        self,
        data_type: DataType,
        frequency: DataFrequency | None = None,
        prefer_realtime: bool = False,
    ) -> str | None:
        """
        Find best source for data type and frequency.
        
        Args:
            data_type: Required data type
            frequency: Required frequency
            prefer_realtime: Prefer realtime-capable sources
            
        Returns:
            Source ID or None if not found
        """
        candidates: list[tuple[str, int]] = []
        
        for source_id, caps in self._capabilities.items():
            if not caps.supports(data_type, frequency):
                continue
            
            health = self._health.get(source_id)
            if health and health.status == SourceStatus.UNAVAILABLE:
                continue
            
            score = 0
            if prefer_realtime and caps.supports_realtime:
                score += 100
            if health:
                score += int(health.success_rate * 50)
                score -= health.consecutive_failures * 10
            
            candidates.append((source_id, score))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def list_sources(self) -> list[str]:
        """List all registered sources."""
        return list(self._sources.keys())
    
    def list_available_sources(self) -> list[str]:
        """List all available sources."""
        return [
            source_id
            for source_id, health in self._health.items()
            if health.status != SourceStatus.UNAVAILABLE
        ]
    
    def record_success(self, source_id: str, response_time_ms: float) -> None:
        """Record a successful request."""
        health = self._health.get(source_id)
        if health:
            health.record_success(response_time_ms)
    
    def record_failure(self, source_id: str) -> None:
        """Record a failed request."""
        health = self._health.get(source_id)
        if health:
            health.record_failure()
    
    def get_summary(self) -> dict[str, Any]:
        """Get registry summary."""
        return {
            "total_sources": len(self._sources),
            "available_sources": len(self.list_available_sources()),
            "sources": {
                source_id: {
                    "name": config.name,
                    "status": self._health.get(source_id, SourceHealth(source_id=source_id)).status.value,
                    "success_rate": self._health.get(source_id, SourceHealth(source_id=source_id)).success_rate,
                }
                for source_id, config in self._sources.items()
            },
        }


_global_registry: SourceRegistry | None = None


def get_source_registry() -> SourceRegistry:
    """Get the global source registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = SourceRegistry()
    return _global_registry


def init_source_registry() -> SourceRegistry:
    """Initialize and return a new source registry."""
    global _global_registry
    _global_registry = SourceRegistry()
    return _global_registry
