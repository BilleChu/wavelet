"""
Source Health - Health monitoring for data sources.

Provides health status tracking and connection testing.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field

from openfinance.datacenter.collector.source.types import SourceStatus
from openfinance.datacenter.collector.source.config import SourceConfig

logger = logging.getLogger(__name__)


class HealthCheckResult(BaseModel):
    """Result of a health check."""
    
    source_id: str
    healthy: bool
    checked_at: datetime = Field(default_factory=datetime.now)
    latency_ms: float | None = None
    error_message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "healthy": self.healthy,
            "checked_at": self.checked_at.isoformat(),
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "details": self.details,
        }


class SourceHealth(BaseModel):
    """Health status of a data source."""
    
    source_id: str
    status: SourceStatus = Field(default=SourceStatus.UNKNOWN)
    
    last_check: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    average_latency_ms: float = 0.0
    min_latency_ms: float | None = None
    max_latency_ms: float | None = None
    
    uptime_percentage: float = 0.0
    error_rate: float = 0.0
    
    error_message: str | None = None
    last_error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "average_latency_ms": self.average_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "uptime_percentage": self.uptime_percentage,
            "error_rate": self.error_rate,
            "error_message": self.error_message,
        }


class HealthChecker:
    """
    Health checker for data sources.
    
    Provides:
    - Connection testing
    - Health status tracking
    - Latency monitoring
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        success_threshold: int = 2,
        latency_window: int = 100,
    ):
        self._health: dict[str, SourceHealth] = {}
        self._latency_history: dict[str, list[float]] = {}
        
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._latency_window = latency_window
    
    async def check_health(
        self,
        config: SourceConfig,
    ) -> HealthCheckResult:
        """Perform health check on a data source."""
        start_time = time.time()
        
        try:
            result = await self._perform_check(config)
            
            latency = (time.time() - start_time) * 1000
            result.latency_ms = latency
            
            self._update_health(
                source_id=config.source_id,
                success=result.healthy,
                latency=latency,
                error_message=result.error_message,
            )
            
            return result
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            
            self._update_health(
                source_id=config.source_id,
                success=False,
                latency=latency,
                error_message=str(e),
            )
            
            return HealthCheckResult(
                source_id=config.source_id,
                healthy=False,
                latency_ms=latency,
                error_message=str(e),
            )
    
    async def _perform_check(
        self,
        config: SourceConfig,
    ) -> HealthCheckResult:
        """Perform the actual health check."""
        from openfinance.datacenter.collector.source.types import SourceType
        
        if config.source_type == SourceType.API:
            return await self._check_api(config)
        elif config.source_type == SourceType.DATABASE:
            return await self._check_database(config)
        elif config.source_type == SourceType.WEB_SOCKET:
            return await self._check_websocket(config)
        else:
            return HealthCheckResult(
                source_id=config.source_id,
                healthy=True,
                details={"message": f"Health check not implemented for {config.source_type}"},
            )
    
    async def _check_api(
        self,
        config: SourceConfig,
    ) -> HealthCheckResult:
        """Check API source health."""
        import aiohttp
        
        url = config.connection.base_url
        if not url:
            return HealthCheckResult(
                source_id=config.source_id,
                healthy=False,
                error_message="No base URL configured",
            )
        
        headers = {}
        if config.auth.bearer_token:
            headers["Authorization"] = f"Bearer {config.auth.bearer_token.get_secret_value()}"
        elif config.auth.api_key:
            headers["X-API-Key"] = config.auth.api_key.get_secret_value()
        
        headers.update(config.auth.custom_headers)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=config.connection.timeout),
                    ssl=config.connection.ssl_verify,
                ) as response:
                    if response.status < 500:
                        return HealthCheckResult(
                            source_id=config.source_id,
                            healthy=True,
                            details={"status_code": response.status},
                        )
                    else:
                        return HealthCheckResult(
                            source_id=config.source_id,
                            healthy=False,
                            error_message=f"HTTP {response.status}",
                            details={"status_code": response.status},
                        )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                source_id=config.source_id,
                healthy=False,
                error_message="Connection timeout",
            )
        except Exception as e:
            return HealthCheckResult(
                source_id=config.source_id,
                healthy=False,
                error_message=str(e),
            )
    
    async def _check_database(
        self,
        config: SourceConfig,
    ) -> HealthCheckResult:
        """Check database source health."""
        return HealthCheckResult(
            source_id=config.source_id,
            healthy=True,
            details={"message": "Database health check placeholder"},
        )
    
    async def _check_websocket(
        self,
        config: SourceConfig,
    ) -> HealthCheckResult:
        """Check WebSocket source health."""
        return HealthCheckResult(
            source_id=config.source_id,
            healthy=True,
            details={"message": "WebSocket health check placeholder"},
        )
    
    def _update_health(
        self,
        source_id: str,
        success: bool,
        latency: float,
        error_message: str | None = None,
    ) -> None:
        """Update health status for a source."""
        now = datetime.now()
        
        if source_id not in self._health:
            self._health[source_id] = SourceHealth(source_id=source_id)
            self._latency_history[source_id] = []
        
        health = self._health[source_id]
        health.last_check = now
        health.total_requests += 1
        
        self._latency_history[source_id].append(latency)
        if len(self._latency_history[source_id]) > self._latency_window:
            self._latency_history[source_id] = self._latency_history[source_id][-self._latency_window:]
        
        health.average_latency_ms = sum(self._latency_history[source_id]) / len(self._latency_history[source_id])
        health.min_latency_ms = min(self._latency_history[source_id])
        health.max_latency_ms = max(self._latency_history[source_id])
        
        if success:
            health.last_success = now
            health.successful_requests += 1
            health.consecutive_successes += 1
            health.consecutive_failures = 0
            health.error_message = None
            health.last_error = None
            
            if health.consecutive_successes >= self._success_threshold:
                health.status = SourceStatus.ACTIVE
        else:
            health.last_failure = now
            health.failed_requests += 1
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            health.error_message = error_message
            health.last_error = error_message
            
            if health.consecutive_failures >= self._failure_threshold:
                health.status = SourceStatus.ERROR
        
        if health.total_requests > 0:
            health.error_rate = health.failed_requests / health.total_requests
            health.uptime_percentage = (health.successful_requests / health.total_requests) * 100
    
    def get_health(self, source_id: str) -> SourceHealth | None:
        """Get health status for a source."""
        return self._health.get(source_id)
    
    def get_all_health(self) -> dict[str, SourceHealth]:
        """Get health status for all sources."""
        return self._health.copy()
    
    def reset_health(self, source_id: str) -> None:
        """Reset health status for a source."""
        if source_id in self._health:
            del self._health[source_id]
        if source_id in self._latency_history:
            del self._latency_history[source_id]


import asyncio
