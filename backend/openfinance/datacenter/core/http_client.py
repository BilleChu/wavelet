"""
HTTP Client Abstraction Layer.

Provides a unified HTTP client with built-in retry, rate limiting,
and error handling capabilities.

Usage:
    from datacenter.core import HttpClient, RetryPolicy, RateLimitPolicy
    
    client = HttpClient(
        retry_policy=RetryPolicy(max_retries=3),
        rate_limit_policy=RateLimitPolicy(requests_per_second=10),
    )
    
    response = await client.get("https://api.example.com/data", params={"key": "value"})
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import aiohttp

logger = logging.getLogger(__name__)


class HttpMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class RetryPolicy:
    """
    Retry policy configuration.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds between retries
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        retryable_status_codes: HTTP status codes that trigger retry
        retryable_exceptions: Exception types that trigger retry
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retryable_status_codes: set[int] = field(
        default_factory=lambda: {429, 500, 502, 503, 504}
    )
    retryable_exceptions: tuple[type[Exception], ...] = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
    )
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


@dataclass
class RateLimitPolicy:
    """
    Rate limiting policy configuration.
    
    Attributes:
        requests_per_second: Maximum requests per second
        requests_per_minute: Maximum requests per minute
        burst_size: Maximum burst size
    """
    requests_per_second: float | None = None
    requests_per_minute: int | None = None
    burst_size: int = 10
    
    @property
    def min_interval(self) -> float | None:
        """Minimum interval between requests in seconds."""
        if self.requests_per_second:
            return 1.0 / self.requests_per_second
        if self.requests_per_minute:
            return 60.0 / self.requests_per_minute
        return None


@dataclass
class HttpRequest:
    """
    HTTP request model.
    
    Attributes:
        method: HTTP method
        url: Request URL
        params: Query parameters
        headers: Request headers
        data: Request body data
        json: JSON body data
        timeout: Request timeout in seconds
    """
    method: HttpMethod = HttpMethod.GET
    url: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] | None = None
    json: dict[str, Any] | None = None
    timeout: float = 30.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.value,
            "url": self.url,
            "params": self.params,
            "headers": self.headers,
            "timeout": self.timeout,
        }


@dataclass
class HttpResponse:
    """
    HTTP response model.
    
    Attributes:
        status: HTTP status code
        headers: Response headers
        body: Response body as string
        json: Parsed JSON response
        elapsed: Time elapsed in seconds
        request: Original request
    """
    status: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""
    json: dict[str, Any] | list[Any] | None = None
    elapsed: float = 0.0
    request: HttpRequest | None = None
    
    @property
    def ok(self) -> bool:
        """Check if response is successful (2xx)."""
        return 200 <= self.status < 300
    
    @property
    def is_json(self) -> bool:
        """Check if response is JSON."""
        content_type = self.headers.get("content-type", "")
        return "application/json" in content_type
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "headers": dict(self.headers),
            "body": self.body[:500] if self.body else None,
            "elapsed": self.elapsed,
            "ok": self.ok,
        }


class HttpClientError(Exception):
    """HTTP client error."""
    
    def __init__(
        self,
        message: str,
        response: HttpResponse | None = None,
        request: HttpRequest | None = None,
    ) -> None:
        super().__init__(message)
        self.response = response
        self.request = request


class HttpClient:
    """
    Unified HTTP client with retry and rate limiting.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting
    - Request/response logging
    - Timeout handling
    - Session management
    
    Usage:
        async with HttpClient() as client:
            response = await client.get("https://api.example.com/data")
            if response.ok:
                data = response.json
    """
    
    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
        rate_limit_policy: RateLimitPolicy | None = None,
        default_headers: dict[str, str] | None = None,
        default_timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self.rate_limit_policy = rate_limit_policy
        self.default_headers = default_headers or {}
        self.default_timeout = default_timeout
        self.verify_ssl = verify_ssl
        
        self._session: aiohttp.ClientSession | None = None
        self._last_request_time: float = 0.0
        self._request_count: int = 0
        self._error_count: int = 0
    
    async def __aenter__(self) -> "HttpClient":
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
    
    async def start(self) -> None:
        """Initialize the HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.default_timeout)
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self.default_headers,
            )
            logger.debug("HTTP client session started")
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.debug("HTTP client session closed")
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting before request."""
        if not self.rate_limit_policy:
            return
        
        min_interval = self.rate_limit_policy.min_interval
        if min_interval:
            elapsed = time.time() - self._last_request_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
    
    async def _execute_request(
        self,
        request: HttpRequest,
    ) -> HttpResponse:
        """Execute a single HTTP request."""
        if not self._session:
            await self.start()
        
        await self._apply_rate_limit()
        
        start_time = time.time()
        self._last_request_time = start_time
        self._request_count += 1
        
        try:
            async with self._session.request(
                method=request.method.value,
                url=request.url,
                params=request.params,
                headers=request.headers,
                data=request.data,
                json=request.json,
                timeout=aiohttp.ClientTimeout(total=request.timeout),
            ) as response:
                body = await response.text()
                
                json_data = None
                if "application/json" in response.headers.get("content-type", ""):
                    try:
                        import json
                        json_data = json.loads(body)
                    except json.JSONDecodeError:
                        pass
                
                elapsed = time.time() - start_time
                
                return HttpResponse(
                    status=response.status,
                    headers=dict(response.headers),
                    body=body,
                    json=json_data,
                    elapsed=elapsed,
                    request=request,
                )
        
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            self._error_count += 1
            return HttpResponse(
                status=0,
                body="",
                elapsed=elapsed,
                request=request,
            )
    
    async def request(
        self,
        method: HttpMethod,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """
        Execute HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            headers: Request headers
            data: Request body data
            json: JSON body data
            timeout: Request timeout
            
        Returns:
            HTTP response
        """
        request = HttpRequest(
            method=method,
            url=url,
            params=params or {},
            headers={**self.default_headers, **(headers or {})},
            data=data,
            json=json,
            timeout=timeout or self.default_timeout,
        )
        
        last_response: HttpResponse | None = None
        last_exception: Exception | None = None
        
        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                response = await self._execute_request(request)
                
                if response.ok:
                    return response
                
                if response.status not in self.retry_policy.retryable_status_codes:
                    return response
                
                last_response = response
                
            except self.retry_policy.retryable_exceptions as e:
                last_exception = e
                logger.warning(
                    f"Request failed (attempt {attempt + 1}): {e}"
                )
            
            if attempt < self.retry_policy.max_retries:
                delay = self.retry_policy.calculate_delay(attempt)
                logger.debug(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        if last_response:
            return last_response
        
        raise HttpClientError(
            f"Request failed after {self.retry_policy.max_retries} retries: {last_exception}",
            response=last_response,
            request=request,
        )
    
    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Execute GET request."""
        return await self.request(
            method=HttpMethod.GET,
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
    
    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Execute POST request."""
        return await self.request(
            method=HttpMethod.POST,
            url=url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
        )
    
    @property
    def stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / self._request_count if self._request_count > 0 else 0,
        }
