"""
Factor Cache Module.

Provides caching for factor calculation results.
Supports Redis and in-memory caching.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from ..base import FactorResult

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Cache configuration."""
    
    enabled: bool = True
    backend: str = "memory"
    ttl_seconds: int = 3600
    max_memory_items: int = 10000
    
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None


class FactorCache:
    """
    Cache for factor calculation results.
    
    Features:
    - In-memory LRU cache
    - Redis support for distributed caching
    - TTL-based expiration
    - Cache key generation
    """
    
    def __init__(self, config: CacheConfig | None = None):
        self.config = config or CacheConfig()
        
        self._memory_cache: dict[str, tuple[Any, datetime]] = {}
        self._access_order: list[str] = []
        
        self._redis_client = None
    
    async def initialize(self) -> None:
        """Initialize cache backend."""
        if not self.config.enabled:
            return
        
        if self.config.backend == "redis":
            try:
                import redis.asyncio as redis
                
                self._redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password,
                    decode_responses=True,
                )
                
                await self._redis_client.ping()
                logger.info("Redis cache initialized")
            except ImportError:
                logger.warning("Redis package not installed, falling back to memory cache")
                self.config.backend = "memory"
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, falling back to memory cache")
                self.config.backend = "memory"
    
    async def close(self) -> None:
        """Close cache connections."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
    
    def _generate_key(
        self,
        factor_id: str,
        code: str,
        trade_date: date,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Generate cache key."""
        key_parts = [factor_id, code, trade_date.isoformat()]
        
        if params:
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        
        return ":".join(key_parts)
    
    def _generate_series_key(
        self,
        factor_id: str,
        code: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Generate cache key for series data."""
        key_parts = [factor_id, code, "series"]
        
        if params:
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        
        return ":".join(key_parts)
    
    async def get(
        self,
        factor_id: str,
        code: str,
        trade_date: date,
        params: dict[str, Any] | None = None,
    ) -> FactorResult | None:
        """Get cached factor result."""
        if not self.config.enabled:
            return None
        
        key = self._generate_key(factor_id, code, trade_date, params)
        
        if self.config.backend == "redis" and self._redis_client:
            return await self._get_redis(key)
        else:
            return self._get_memory(key)
    
    async def _get_redis(self, key: str) -> FactorResult | None:
        """Get from Redis cache."""
        try:
            data = await self._redis_client.get(key)
            if data:
                result_dict = json.loads(data)
                return FactorResult(**result_dict)
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
        return None
    
    def _get_memory(self, key: str) -> FactorResult | None:
        """Get from memory cache."""
        if key not in self._memory_cache:
            return None
        
        value, timestamp = self._memory_cache[key]
        
        if datetime.now() - timestamp > timedelta(seconds=self.config.ttl_seconds):
            del self._memory_cache[key]
            return None
        
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        return value
    
    async def set(
        self,
        result: FactorResult,
        params: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Cache a factor result."""
        if not self.config.enabled:
            return False
        
        key = self._generate_key(
            result.factor_id,
            result.code,
            result.trade_date,
            params,
        )
        
        ttl = ttl_seconds or self.config.ttl_seconds
        
        if self.config.backend == "redis" and self._redis_client:
            return await self._set_redis(key, result, ttl)
        else:
            return self._set_memory(key, result)
    
    async def _set_redis(self, key: str, result: FactorResult, ttl: int) -> bool:
        """Set in Redis cache."""
        try:
            data = result.model_dump_json()
            await self._redis_client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False
    
    def _set_memory(self, key: str, result: FactorResult) -> bool:
        """Set in memory cache."""
        while len(self._memory_cache) >= self.config.max_memory_items:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                self._memory_cache.pop(oldest_key, None)
            else:
                break
        
        self._memory_cache[key] = (result, datetime.now())
        
        if key not in self._access_order:
            self._access_order.append(key)
        
        return True
    
    async def get_series(
        self,
        factor_id: str,
        code: str,
        params: dict[str, Any] | None = None,
    ) -> list[FactorResult] | None:
        """Get cached series data."""
        if not self.config.enabled:
            return None
        
        key = self._generate_series_key(factor_id, code, params)
        
        if self.config.backend == "redis" and self._redis_client:
            try:
                data = await self._redis_client.get(key)
                if data:
                    results = json.loads(data)
                    return [FactorResult(**r) for r in results]
            except Exception as e:
                logger.error(f"Redis get series failed: {e}")
        else:
            if key in self._memory_cache:
                value, timestamp = self._memory_cache[key]
                if datetime.now() - timestamp <= timedelta(seconds=self.config.ttl_seconds):
                    return value
        
        return None
    
    async def set_series(
        self,
        results: list[FactorResult],
        params: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Cache series data."""
        if not self.config.enabled or not results:
            return False
        
        first = results[0]
        key = self._generate_series_key(first.factor_id, first.code, params)
        ttl = ttl_seconds or self.config.ttl_seconds
        
        if self.config.backend == "redis" and self._redis_client:
            try:
                data = json.dumps([r.model_dump() for r in results])
                await self._redis_client.setex(key, ttl, data)
                return True
            except Exception as e:
                logger.error(f"Redis set series failed: {e}")
                return False
        else:
            self._memory_cache[key] = (results, datetime.now())
            return True
    
    async def delete(
        self,
        factor_id: str,
        code: str,
        trade_date: date,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """Delete cached result."""
        key = self._generate_key(factor_id, code, trade_date, params)
        
        if self.config.backend == "redis" and self._redis_client:
            try:
                await self._redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete failed: {e}")
                return False
        else:
            self._memory_cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)
            return True
    
    async def clear_factor(self, factor_id: str) -> int:
        """Clear all cached data for a factor."""
        cleared = 0
        
        if self.config.backend == "redis" and self._redis_client:
            try:
                pattern = f"{factor_id}:*"
                keys = []
                async for key in self._redis_client.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    cleared = await self._redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear factor failed: {e}")
        else:
            keys_to_delete = [
                k for k in self._memory_cache
                if k.startswith(factor_id)
            ]
            for key in keys_to_delete:
                del self._memory_cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                cleared += 1
        
        return cleared
    
    async def clear_all(self) -> int:
        """Clear all cached data."""
        cleared = len(self._memory_cache)
        
        if self.config.backend == "redis" and self._redis_client:
            try:
                await self._redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis clear all failed: {e}")
        
        self._memory_cache.clear()
        self._access_order.clear()
        
        return cleared
    
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "enabled": self.config.enabled,
            "backend": self.config.backend,
            "memory_items": len(self._memory_cache),
            "max_memory_items": self.config.max_memory_items,
            "ttl_seconds": self.config.ttl_seconds,
        }


_cache: FactorCache | None = None


async def get_factor_cache() -> FactorCache:
    """Get the global factor cache instance."""
    global _cache
    if _cache is None:
        _cache = FactorCache()
        await _cache.initialize()
    return _cache
