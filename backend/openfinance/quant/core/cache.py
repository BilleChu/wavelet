"""
High-performance caching layer for quantitative analytics.

Optimizations:
- LRU cache for frequently accessed data
- Async caching with TTL support
- Memory-efficient storage
- Cache invalidation strategies
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, TypeVar
from functools import wraps
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    value: T
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


class LRUCache(Generic[T]):
    """
    Thread-safe LRU cache implementation.
    
    Features:
    - O(1) get and put operations
    - Configurable max size
    - TTL support
    - Access-time based eviction
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
        """
        self._cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if time.time() - entry.created_at > self._default_ttl:
                del self._cache[key]
                return None
            
            # Update access info
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            return entry.value
    
    async def put(self, key: str, value: T, ttl: Optional[float] = None) -> None:
        """Put value in cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
            
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = CacheEntry(
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=0,
            )
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_entries = len(self._cache)
            total_accesses = sum(e.access_count for e in self._cache.values())
            avg_access_count = total_accesses / total_entries if total_entries > 0 else 0
            
            return {
                "size": total_entries,
                "max_size": self._max_size,
                "total_accesses": total_accesses,
                "avg_access_count": avg_access_count,
                "memory_usage_estimate_kb": self._estimate_memory_usage(),
            }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in KB."""
        # Rough estimate
        total_size = 0
        for entry in self._cache.values():
            try:
                total_size += len(json.dumps(entry.value))
            except Exception:
                total_size += 1024  # Assume 1KB per entry on average
        return total_size / 1024


class PerformanceMetricsCache(LRUCache[Any]):
    """Specialized cache for performance metrics calculations."""
    
    def __init__(self):
        super().__init__(max_size=500, default_ttl=1800)  # 30 min TTL
    
    @staticmethod
    def generate_key(backtest_id: str, include_benchmark: bool) -> str:
        """Generate cache key for performance metrics."""
        return f"perf:{backtest_id}:{include_benchmark}"


class RiskMetricsCache(LRUCache[Any]):
    """Specialized cache for risk analysis results."""
    
    def __init__(self):
        super().__init__(max_size=300, default_ttl=900)  # 15 min TTL
    
    @staticmethod
    def generate_key(
        backtest_id: str,
        var_method: str,
        confidence_level: float,
        horizon: int,
    ) -> str:
        """Generate cache key for risk metrics."""
        return f"risk:{backtest_id}:{var_method}:{confidence_level}:{horizon}"


# Global cache instances
_performance_cache = PerformanceMetricsCache()
_risk_cache = RiskMetricsCache()
_generic_cache = LRUCache(max_size=1000, default_ttl=3600)


def get_performance_cache() -> PerformanceMetricsCache:
    """Get global performance metrics cache."""
    return _performance_cache


def get_risk_cache() -> RiskMetricsCache:
    """Get global risk metrics cache."""
    return _risk_cache


def get_generic_cache() -> LRUCache[Any]:
    """Get generic cache instance."""
    return _generic_cache


# Decorator for automatic caching
def async_cache(
    cache_instance: LRUCache,
    key_generator: Optional[Callable[..., str]] = None,
    ttl: Optional[float] = None,
):
    """
    Decorator for automatic async function caching.
    
    Args:
        cache_instance: Cache to use
        key_generator: Function to generate cache key from arguments
        ttl: Time-to-live override
    
    Usage:
        @async_cache(performance_cache, key_generator=lambda bid, ib: f"perf:{bid}:{ib}")
        async def calculate_metrics(backtest_id: str, include_benchmark: bool):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_generator:
                key = key_generator(*args, **kwargs)
            else:
                # Default: hash of arguments
                key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
                key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Try cache first
            cached_value = await cache_instance.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {key}")
                return cached_value
            
            # Calculate and cache
            logger.debug(f"Cache miss for key: {key}, computing...")
            result = await func(*args, **kwargs)
            
            await cache_instance.put(key, result, ttl=ttl)
            return result
        
        return wrapper
    return decorator


# Performance monitoring
class CachePerformanceMonitor:
    """Monitor cache performance metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
    
    async def record_hit(self):
        """Record cache hit."""
        self.hits += 1
        self.total_requests += 1
    
    async def record_miss(self):
        """Record cache miss."""
        self.misses += 1
        self.total_requests += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests
    
    def get_stats(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": self.hit_rate,
        }


_cache_monitor = CachePerformanceMonitor()


async def get_cache_monitor_stats() -> dict[str, Any]:
    """Get cache monitoring statistics."""
    return _cache_monitor.get_stats()
