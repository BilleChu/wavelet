"""
Data Source Adapter Interface.

Provides standardized interface for data source integration,
enabling pluggable data access with consistent behavior.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar, AsyncIterator

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AdapterCapability(str, Enum):
    """Capabilities that a data source adapter can support."""
    
    REALTIME = "realtime"
    HISTORICAL = "historical"
    INCREMENTAL = "incremental"
    BATCH = "batch"
    STREAMING = "streaming"
    SEARCH = "search"
    FILTER = "filter"
    AGGREGATION = "aggregation"
    SUBSCRIPTION = "subscription"


class AdapterStatus(str, Enum):
    """Status of a data source adapter."""
    
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    DEGRADED = "degraded"
    ERROR = "error"
    DISABLED = "disabled"


class AdapterConfig(BaseModel):
    """Configuration for a data source adapter."""
    
    adapter_id: str = Field(..., description="Unique adapter identifier")
    adapter_name: str = Field(..., description="Human-readable adapter name")
    source_type: str = Field(..., description="Data source type")
    
    base_url: str | None = Field(default=None, description="Base URL for API")
    api_key: str | None = Field(default=None, description="API key for authentication")
    timeout_seconds: float = Field(default=30.0, description="Request timeout")
    
    rate_limit_per_second: float = Field(default=10.0, description="Rate limit")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: float = Field(default=1.0, description="Retry delay")
    
    batch_size: int = Field(default=100, description="Batch size for pagination")
    max_concurrent_requests: int = Field(default=5, description="Max concurrent requests")
    
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL")
    
    capabilities: list[AdapterCapability] = Field(
        default_factory=list,
        description="Supported capabilities"
    )
    
    extra_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional adapter-specific configuration"
    )


@dataclass
class AdapterMetrics:
    """Metrics for adapter monitoring."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_records_fetched: int = 0
    total_bytes_transferred: int = 0
    avg_latency_ms: float = 0.0
    last_request_time: datetime | None = None
    last_error: str | None = None
    last_error_time: datetime | None = None
    
    def record_success(self, records: int, latency_ms: float, bytes_count: int = 0) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        self.total_records_fetched += records
        self.total_bytes_transferred += bytes_count
        self.last_request_time = datetime.now()
        
        if self.total_requests > 0:
            self.avg_latency_ms = (
                (self.avg_latency_ms * (self.total_requests - 1) + latency_ms)
                / self.total_requests
            )
    
    def record_failure(self, error: str) -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.last_error = error
        self.last_error_time = datetime.now()
        self.last_request_time = datetime.now()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "total_records_fetched": self.total_records_fetched,
            "total_bytes_transferred": self.total_bytes_transferred,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


class AdapterHealth(BaseModel):
    """Health status of an adapter."""
    
    adapter_id: str
    status: AdapterStatus
    is_healthy: bool
    message: str = ""
    last_check: datetime = Field(default_factory=datetime.now)
    response_time_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DataSourceAdapter(ABC, Generic[T]):
    """
    Abstract base class for data source adapters.
    
    Provides standardized interface for:
    - Data fetching (batch, streaming, realtime)
    - Connection management
    - Health monitoring
    - Rate limiting
    - Error handling
    
    Usage:
        class MyAdapter(DataSourceAdapter[MyData]):
            async def _fetch_batch(self, params: dict) -> list[MyData]:
                # Implementation
                pass
        
        adapter = MyAdapter(config)
        await adapter.initialize()
        data = await adapter.fetch_batch({"symbols": ["600000"]})
    """
    
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config
        self._status = AdapterStatus.INITIALIZING
        self._metrics = AdapterMetrics()
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._initialized = False
        self._last_rate_limit: datetime | None = None
        self._request_count = 0
    
    @property
    def adapter_id(self) -> str:
        return self.config.adapter_id
    
    @property
    def adapter_name(self) -> str:
        return self.config.adapter_name
    
    @property
    def status(self) -> AdapterStatus:
        return self._status
    
    @property
    def capabilities(self) -> list[AdapterCapability]:
        return self.config.capabilities
    
    def has_capability(self, capability: AdapterCapability) -> bool:
        return capability in self.capabilities
    
    async def initialize(self) -> None:
        """Initialize the adapter."""
        if self._initialized:
            return
        
        try:
            await self._initialize()
            self._status = AdapterStatus.READY
            self._initialized = True
            logger.info(f"Adapter {self.adapter_id} initialized successfully")
        except Exception as e:
            self._status = AdapterStatus.ERROR
            logger.error(f"Failed to initialize adapter {self.adapter_id}: {e}")
            raise
    
    async def close(self) -> None:
        """Close the adapter and release resources."""
        try:
            await self._close()
            self._initialized = False
            self._status = AdapterStatus.DISABLED
            logger.info(f"Adapter {self.adapter_id} closed")
        except Exception as e:
            logger.error(f"Error closing adapter {self.adapter_id}: {e}")
    
    async def health_check(self) -> AdapterHealth:
        """Perform health check on the adapter."""
        start_time = datetime.now()
        
        try:
            is_healthy = await self._health_check()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self._status = AdapterStatus.READY if is_healthy else AdapterStatus.DEGRADED
            
            return AdapterHealth(
                adapter_id=self.adapter_id,
                status=self._status,
                is_healthy=is_healthy,
                message="Healthy" if is_healthy else "Degraded",
                response_time_ms=response_time,
            )
        except Exception as e:
            self._status = AdapterStatus.ERROR
            return AdapterHealth(
                adapter_id=self.adapter_id,
                status=AdapterStatus.ERROR,
                is_healthy=False,
                message=str(e),
            )
    
    async def fetch_batch(self, params: dict[str, Any]) -> list[T]:
        """
        Fetch data in batch mode.
        
        Args:
            params: Query parameters including:
                - symbols: List of symbols to fetch
                - start_date: Start date for historical data
                - end_date: End date for historical data
                - limit: Maximum records to return
                - offset: Pagination offset
        
        Returns:
            List of data records
        """
        if not self.has_capability(AdapterCapability.BATCH):
            raise NotImplementedError(f"Adapter {self.adapter_id} does not support batch fetching")
        
        return await self._execute_with_monitoring(
            self._fetch_batch,
            params
        )
    
    async def fetch_streaming(
        self,
        params: dict[str, Any],
    ) -> AsyncIterator[list[T]]:
        """
        Fetch data in streaming mode.
        
        Yields batches of data as they become available.
        """
        if not self.has_capability(AdapterCapability.STREAMING):
            raise NotImplementedError(f"Adapter {self.adapter_id} does not support streaming")
        
        async for batch in self._fetch_streaming(params):
            yield batch
    
    async def fetch_realtime(self, params: dict[str, Any]) -> T:
        """Fetch realtime data."""
        if not self.has_capability(AdapterCapability.REALTIME):
            raise NotImplementedError(f"Adapter {self.adapter_id} does not support realtime")
        
        return await self._execute_with_monitoring(
            self._fetch_realtime,
            params
        )
    
    async def search(self, query: str, params: dict[str, Any] | None = None) -> list[T]:
        """Search for data matching query."""
        if not self.has_capability(AdapterCapability.SEARCH):
            raise NotImplementedError(f"Adapter {self.adapter_id} does not support search")
        
        return await self._execute_with_monitoring(
            self._search,
            query,
            params or {}
        )
    
    def get_metrics(self) -> dict[str, Any]:
        """Get adapter metrics."""
        return {
            "adapter_id": self.adapter_id,
            "status": self._status.value,
            "initialized": self._initialized,
            **self._metrics.to_dict(),
        }
    
    async def _execute_with_monitoring(
        self,
        func: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with monitoring and rate limiting."""
        async with self._semaphore:
            start_time = datetime.now()
            
            try:
                await self._apply_rate_limit()
                
                self._status = AdapterStatus.BUSY
                result = await func(*args, **kwargs)
                self._status = AdapterStatus.READY
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                records = len(result) if isinstance(result, list) else 1
                self._metrics.record_success(records, latency_ms)
                
                return result
                
            except Exception as e:
                self._metrics.record_failure(str(e))
                self._status = AdapterStatus.ERROR
                raise
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting."""
        if self._last_rate_limit:
            elapsed = (datetime.now() - self._last_rate_limit).total_seconds()
            min_interval = 1.0 / self.config.rate_limit_per_second
            
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        
        self._last_rate_limit = datetime.now()
    
    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize adapter resources."""
        pass
    
    @abstractmethod
    async def _close(self) -> None:
        """Close adapter resources."""
        pass
    
    @abstractmethod
    async def _health_check(self) -> bool:
        """Perform adapter-specific health check."""
        pass
    
    @abstractmethod
    async def _fetch_batch(self, params: dict[str, Any]) -> list[T]:
        """Implement batch data fetching."""
        pass
    
    async def _fetch_streaming(self, params: dict[str, Any]) -> AsyncIterator[list[T]]:
        """Implement streaming data fetching."""
        yield await self._fetch_batch(params)
    
    async def _fetch_realtime(self, params: dict[str, Any]) -> T:
        """Implement realtime data fetching."""
        raise NotImplementedError
    
    async def _search(self, query: str, params: dict[str, Any]) -> list[T]:
        """Implement search functionality."""
        raise NotImplementedError
