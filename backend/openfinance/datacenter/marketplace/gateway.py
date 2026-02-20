"""
Data Service Gateway.

Provides request routing, rate limiting, and load balancing
for the data service marketplace.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable

from .models import (
    DataRequest,
    DataResponse,
    DataServiceCategory,
    DataServiceDefinition,
    DataServiceStatus,
    DataServiceUsage,
    EndpointMethod,
    RateLimitConfig,
    ServiceHealth,
)
from .registry import DataServiceRegistry, get_service_registry

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed for the given key."""
        async with self._lock:
            now = time.time()
            requests = self._requests[key]
            
            requests[:] = [t for t in requests if now - t < 60]
            
            if len(requests) >= self.config.requests_per_minute:
                return False
            
            requests.append(now)
            return True

    async def wait_if_needed(self, key: str) -> float:
        """Wait if rate limited and return wait time."""
        if await self.is_allowed(key):
            return 0.0
        
        async with self._lock:
            requests = self._requests[key]
            if requests:
                oldest = min(requests)
                wait_time = 60 - (time.time() - oldest) + 0.1
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                return wait_time
        return 0.0


class DataGateway:
    """
    Data service gateway for routing and managing requests.

    Provides:
    - Request routing to appropriate services
    - Rate limiting
    - Request/response logging
    - Error handling
    - Response caching
    """

    def __init__(self, registry: DataServiceRegistry | None = None) -> None:
        self.registry = registry or get_service_registry()
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._cache: dict[str, tuple[Any, float]] = {}
        self._usage_records: list[DataServiceUsage] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the gateway."""
        if self._initialized:
            return

        await self.registry.initialize()
        
        for service in self.registry.list_services():
            self._rate_limiters[service.service_id] = RateLimiter(
                service.rate_limit
            )
        
        self._initialized = True
        logger.info("Data gateway initialized")

    async def route_request(self, request: DataRequest) -> DataResponse:
        """Route a request to the appropriate service."""
        start_time = time.time()
        
        service = self.registry.get_service(request.service_id)
        if not service:
            return DataResponse(
                request_id=request.request_id,
                success=False,
                error_code="SERVICE_NOT_FOUND",
                error_message=f"Service {request.service_id} not found",
            )
        
        if service.status != DataServiceStatus.ACTIVE:
            return DataResponse(
                request_id=request.request_id,
                success=False,
                error_code="SERVICE_UNAVAILABLE",
                error_message=f"Service {request.service_id} is {service.status}",
            )
        
        endpoint = self._find_endpoint(service, request.endpoint, request.method)
        if not endpoint:
            return DataResponse(
                request_id=request.request_id,
                success=False,
                error_code="ENDPOINT_NOT_FOUND",
                error_message=f"Endpoint {request.method} {request.endpoint} not found",
            )
        
        if endpoint.deprecated:
            logger.warning(
                f"Deprecated endpoint called: {request.endpoint}. "
                f"{endpoint.deprecation_message or ''}"
            )
        
        rate_limiter = self._rate_limiters.get(request.service_id)
        if rate_limiter:
            rate_key = f"{request.user_id or request.api_key or 'anonymous'}:{request.service_id}"
            if not await rate_limiter.is_allowed(rate_key):
                return DataResponse(
                    request_id=request.request_id,
                    success=False,
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_message="Rate limit exceeded. Please try again later.",
                )
        
        if endpoint.cache_ttl_seconds > 0:
            cache_key = self._get_cache_key(request)
            cached = self._cache.get(cache_key)
            if cached and time.time() - cached[1] < endpoint.cache_ttl_seconds:
                return DataResponse(
                    request_id=request.request_id,
                    success=True,
                    data=cached[0],
                    metadata={"cached": True},
                )
        
        handler = self.registry.get_handler(request.service_id, request.endpoint)
        if not handler:
            return DataResponse(
                request_id=request.request_id,
                success=False,
                error_code="NO_HANDLER",
                error_message=f"No handler registered for endpoint",
            )
        
        try:
            result = await handler(request.parameters)
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if endpoint.cache_ttl_seconds > 0:
                cache_key = self._get_cache_key(request)
                self._cache[cache_key] = (result, time.time())
            
            self.registry.update_health(
                request.service_id,
                success=True,
                response_time_ms=response_time_ms,
            )
            
            self._record_usage(request, response_time_ms, True)
            
            return DataResponse(
                request_id=request.request_id,
                success=True,
                data=result,
                metadata={
                    "response_time_ms": response_time_ms,
                    "service_id": request.service_id,
                },
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            self.registry.update_health(
                request.service_id,
                success=False,
                response_time_ms=response_time_ms,
            )
            
            self._record_usage(request, response_time_ms, False, str(e))
            
            logger.exception(f"Request failed: {e}")
            return DataResponse(
                request_id=request.request_id,
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=str(e),
            )

    def _find_endpoint(
        self,
        service: DataServiceDefinition,
        path: str,
        method: EndpointMethod,
    ) -> Any | None:
        """Find matching endpoint in service."""
        for endpoint in service.endpoints:
            if endpoint.method == method:
                endpoint_path = endpoint.path
                if "{" in endpoint_path:
                    pattern_parts = endpoint_path.split("/")
                    path_parts = path.split("/")
                    if len(pattern_parts) == len(path_parts):
                        match = True
                        for p1, p2 in zip(pattern_parts, path_parts):
                            if not (p1.startswith("{") or p1 == p2):
                                match = False
                                break
                        if match:
                            return endpoint
                elif endpoint_path == path:
                    return endpoint
        return None

    def _get_cache_key(self, request: DataRequest) -> str:
        """Generate cache key for a request."""
        import hashlib
        import json
        
        key_data = {
            "service_id": request.service_id,
            "endpoint": request.endpoint,
            "method": request.method.value,
            "parameters": request.parameters,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _record_usage(
        self,
        request: DataRequest,
        response_time_ms: float,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record usage for analytics."""
        usage = DataServiceUsage(
            usage_id=str(uuid.uuid4()),
            subscription_id="",
            service_id=request.service_id,
            user_id=request.user_id or "anonymous",
            endpoint=request.endpoint,
            method=request.method,
            response_time_ms=response_time_ms,
            success=success,
            error_message=error_message,
        )
        self._usage_records.append(usage)
        
        if len(self._usage_records) > 10000:
            self._usage_records = self._usage_records[-5000:]

    async def aggregate_requests(
        self,
        requests: list[DataRequest],
    ) -> dict[str, DataResponse]:
        """Execute multiple requests in parallel."""
        tasks = [self.route_request(req) for req in requests]
        responses = await asyncio.gather(*tasks)
        
        return {
            req.request_id: resp
            for req, resp in zip(requests, responses)
        }

    def get_usage_stats(
        self,
        service_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Get usage statistics."""
        records = self._usage_records
        
        if service_id:
            records = [r for r in records if r.service_id == service_id]
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        
        if not records:
            return {"total_requests": 0}
        
        total = len(records)
        successful = sum(1 for r in records if r.success)
        avg_response_time = sum(r.response_time_ms for r in records) / total
        
        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "avg_response_time_ms": avg_response_time,
        }

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
        logger.info("Cache cleared")


_gateway: DataGateway | None = None


def get_data_gateway() -> DataGateway:
    """Get the global data gateway instance."""
    global _gateway
    if _gateway is None:
        _gateway = DataGateway()
    return _gateway
