"""
MCP Service Architecture for Data Service Center.

Provides microservice governance including service registration,
discovery, load balancing, and circuit breaking.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Status of a service instance."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


class MCPServerConfig(BaseModel):
    """Configuration for MCP server."""

    service_name: str = Field(..., description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    enable_registry: bool = Field(default=True, description="Enable service registry")
    registry_url: str | None = Field(default=None, description="Registry URL")
    
    enable_circuit_breaker: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_threshold: int = Field(default=5, description="Failure threshold")
    circuit_breaker_timeout_seconds: int = Field(default=30, description="Recovery timeout")
    
    enable_rate_limit: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=100, description="Rate limit per minute")
    
    enable_auth: bool = Field(default=True, description="Enable authentication")
    auth_type: str = Field(default="jwt", description="Authentication type")
    
    health_check_interval_seconds: int = Field(default=30, description="Health check interval")
    request_timeout_seconds: float = Field(default=30.0, description="Request timeout")


class ServiceEndpoint(BaseModel):
    """Endpoint definition for a service."""

    path: str = Field(..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    description: str = Field(..., description="Endpoint description")
    requires_auth: bool = Field(default=True, description="Requires authentication")
    rate_limit: int | None = Field(default=None, description="Custom rate limit")


class ServiceMetadata(BaseModel):
    """Metadata for a service instance."""

    service_id: str = Field(..., description="Unique service ID")
    service_name: str = Field(..., description="Service name")
    service_version: str = Field(..., description="Service version")
    host: str = Field(..., description="Service host")
    port: int = Field(..., description="Service port")
    status: ServiceStatus = Field(default=ServiceStatus.UNKNOWN, description="Service status")
    endpoints: list[ServiceEndpoint] = Field(default_factory=list, description="Service endpoints")
    tags: list[str] = Field(default_factory=list, description="Service tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    registered_at: datetime = Field(
        default_factory=datetime.now,
        description="Registration time",
    )
    last_heartbeat: datetime = Field(
        default_factory=datetime.now,
        description="Last heartbeat time",
    )


class ServiceRequest(BaseModel):
    """Request to a service."""

    request_id: str = Field(..., description="Request ID")
    service_name: str = Field(..., description="Target service name")
    endpoint: str = Field(..., description="Endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    params: dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    body: dict[str, Any] | None = Field(default=None, description="Request body")
    timeout_seconds: float | None = Field(default=None, description="Request timeout")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ServiceResponse(BaseModel):
    """Response from a service."""

    request_id: str = Field(..., description="Corresponding request ID")
    status_code: int = Field(..., description="HTTP status code")
    headers: dict[str, str] = Field(default_factory=dict, description="Response headers")
    body: dict[str, Any] | None = Field(default=None, description="Response body")
    error: str | None = Field(default=None, description="Error message")
    duration_ms: float = Field(..., description="Response duration in ms")
    from_cache: bool = Field(default=False, description="Whether from cache")


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current state."""
        return self._state

    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            
            if self._state == CircuitBreakerState.OPEN:
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.recovery_timeout_seconds:
                        self._state = CircuitBreakerState.HALF_OPEN
                        return True
                return False
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                return True

        return False

    async def record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            self._failure_count = 0
            self._state = CircuitBreakerState.CLOSED

    async def record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitBreakerState.OPEN


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate_per_minute: int = 100) -> None:
        self.rate_per_minute = rate_per_minute
        self._tokens = rate_per_minute
        self._last_refill = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a token."""
        async with self._lock:
            self._refill_tokens()
            
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * (self.rate_per_minute / 60.0)
        self._tokens = min(self.rate_per_minute, self._tokens + tokens_to_add)
        self._last_refill = now


class MCPService(ABC):
    """Abstract base class for MCP services.

    Provides:
    - Service lifecycle management
    - Health checking
    - Request handling
    - Circuit breaking
    - Rate limiting
    """

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._metadata: ServiceMetadata | None = None
        self._circuit_breaker = (
            CircuitBreaker(
                failure_threshold=config.circuit_breaker_threshold,
                recovery_timeout_seconds=config.circuit_breaker_timeout_seconds,
            ) if config.enable_circuit_breaker else None
        )
        self._rate_limiter = (
            RateLimiter(rate_per_minute=config.rate_limit_per_minute)
            if config.enable_rate_limit else None
        )
        self._handlers: dict[str, Callable] = {}
        self._running = False

    @property
    def metadata(self) -> ServiceMetadata | None:
        """Get service metadata."""
        return self._metadata

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    async def start(self) -> None:
        """Start the service."""
        self._metadata = ServiceMetadata(
            service_id=f"{self.config.service_name}_{self.config.port}",
            service_name=self.config.service_name,
            service_version=self.config.service_version,
            host=self.config.host,
            port=self.config.port,
            status=ServiceStatus.STARTING,
            endpoints=self._get_endpoints(),
        )

        await self._initialize()
        self._running = True
        self._metadata.status = ServiceStatus.HEALTHY
        logger.info(f"Started MCP service: {self.config.service_name}")

    async def stop(self) -> None:
        """Stop the service."""
        self._running = False
        if self._metadata:
            self._metadata.status = ServiceStatus.STOPPING
        await self._cleanup()
        if self._metadata:
            self._metadata.status = ServiceStatus.UNHEALTHY
        logger.info(f"Stopped MCP service: {self.config.service_name}")

    async def handle_request(self, request: ServiceRequest) -> ServiceResponse:
        """Handle an incoming request."""
        start_time = time.time()

        if self._rate_limiter and not await self._rate_limiter.acquire():
            return ServiceResponse(
                request_id=request.request_id,
                status_code=429,
                error="Rate limit exceeded",
                duration_ms=(time.time() - start_time) * 1000,
            )

        if self._circuit_breaker and not await self._circuit_breaker.can_execute():
            return ServiceResponse(
                request_id=request.request_id,
                status_code=503,
                error="Service unavailable (circuit breaker open)",
                duration_ms=(time.time() - start_time) * 1000,
            )

        try:
            handler = self._handlers.get(request.endpoint)
            if not handler:
                return ServiceResponse(
                    request_id=request.request_id,
                    status_code=404,
                    error=f"Endpoint not found: {request.endpoint}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            result = await handler(request)
            
            if self._circuit_breaker:
                await self._circuit_breaker.record_success()

            return ServiceResponse(
                request_id=request.request_id,
                status_code=200,
                body=result,
                duration_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            if self._circuit_breaker:
                await self._circuit_breaker.record_failure()

            logger.exception(f"Request handling failed: {request.request_id}")
            return ServiceResponse(
                request_id=request.request_id,
                status_code=500,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    def register_handler(
        self,
        endpoint: str,
        handler: Callable,
    ) -> None:
        """Register a request handler for an endpoint."""
        self._handlers[endpoint] = handler

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        return {
            "service_name": self.config.service_name,
            "status": self._metadata.status.value if self._metadata else "unknown",
            "is_running": self._running,
            "circuit_breaker_state": (
                self._circuit_breaker.state.value
                if self._circuit_breaker else None
            ),
            "checked_at": datetime.now().isoformat(),
        }

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize service resources."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Cleanup service resources."""
        pass

    @abstractmethod
    def _get_endpoints(self) -> list[ServiceEndpoint]:
        """Get service endpoints."""
        pass
