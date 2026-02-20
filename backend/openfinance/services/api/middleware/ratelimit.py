"""
Rate Limiting Middleware.

Provides rate limiting functionality for API endpoints.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limit configuration."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed.
        
        Returns:
            tuple: (is_allowed, current_count, remaining)
        """
        async with self._lock:
            now = time.time()
            requests = self._requests[key]
            
            requests[:] = [t for t in requests if now - t < window_seconds]
            
            current_count = len(requests)
            remaining = max(0, limit - current_count)
            
            if current_count >= limit:
                return False, current_count, 0
            
            requests.append(now)
            return True, current_count + 1, remaining - 1

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        async with self._lock:
            if key in self._requests:
                del self._requests[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Adds rate limiting headers to responses and blocks requests
    that exceed the rate limit.
    """

    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 60,
        burst_limit: int = 10,
        key_func: Callable | None = None,
    ) -> None:
        super().__init__(app)
        self.default_limit = default_limit
        self.burst_limit = burst_limit
        self.key_func = key_func or self._default_key_func
        self._limiter = InMemoryRateLimiter()

    def _default_key_func(self, request: Request) -> str:
        """Get the rate limit key from the request."""
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        auth = request.headers.get("Authorization")
        if auth:
            return f"auth:{hash(auth)}"
        
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with rate limiting."""
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        
        if request.url.path.startswith("/api/health"):
            return await call_next(request)
        
        key = self.key_func(request)
        
        allowed, current, remaining = await self._limiter.is_allowed(
            key=key,
            limit=self.default_limit,
            window_seconds=60,
        )
        
        response = await call_next(request) if allowed else None
        
        if not allowed:
            from fastapi.responses import JSONResponse
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60,
                },
            )
            response.headers["X-RateLimit-Limit"] = str(self.default_limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
            response.headers["Retry-After"] = "60"
        else:
            response.headers["X-RateLimit-Limit"] = str(self.default_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response


def get_rate_limit_tier(subscription_tier: str) -> RateLimitConfig:
    """Get rate limit configuration for a subscription tier."""
    configs = {
        "free": RateLimitConfig(
            requests_per_minute=20,
            requests_per_hour=500,
            burst_limit=5,
        ),
        "basic": RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=2000,
            burst_limit=10,
        ),
        "professional": RateLimitConfig(
            requests_per_minute=200,
            requests_per_hour=10000,
            burst_limit=30,
        ),
        "enterprise": RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=50000,
            burst_limit=100,
        ),
    }
    return configs.get(subscription_tier, configs["free"])
