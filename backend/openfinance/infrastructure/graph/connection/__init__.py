"""
Connection Management - System-level connection pooling.

Provides:
- ConnectionPool: Generic connection pool
- ConnectionManager: Multi-backend connection manager
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar
from contextlib import asynccontextmanager


logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ConnectionConfig:
    """Connection configuration."""
    
    backend: str
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    connection_timeout: float = 10.0
    
    def to_url(self) -> str:
        """Convert to connection URL."""
        if self.backend == "postgres":
            return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.backend == "neo4j":
            return f"bolt://{self.host}:{self.port}"
        return ""


class ConnectionPool(Generic[T]):
    """
    Generic connection pool.
    
    Features:
    - Connection reuse
    - Pool size management
    - Health checking
    - Graceful shutdown
    """
    
    def __init__(
        self,
        factory: Callable[[], T],
        config: ConnectionConfig,
    ):
        self._factory = factory
        self._config = config
        self._pool: asyncio.Queue[T] = asyncio.Queue(maxsize=config.pool_size)
        self._active_connections: set[T] = set()
        self._size = 0
        self._lock = asyncio.Lock()
        self._closed = False
    
    async def initialize(self) -> None:
        """Initialize the pool with connections."""
        for _ in range(self._config.pool_size):
            conn = await self._create_connection()
            await self._pool.put(conn)
    
    async def _create_connection(self) -> T:
        """Create a new connection."""
        conn = await self._factory()
        self._active_connections.add(conn)
        self._size += 1
        return conn
    
    @asynccontextmanager
    async def acquire(self) -> T:
        """Acquire a connection from the pool."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        conn = await self._pool.get()
        try:
            yield conn
        finally:
            if not self._closed:
                await self._pool.put(conn)
    
    async def close(self) -> None:
        """Close all connections."""
        self._closed = True
        while not self._pool.empty():
            conn = await self._pool.get()
            if hasattr(conn, 'close'):
                await conn.close()
        self._active_connections.clear()
    
    @property
    def size(self) -> int:
        return self._size
    
    @property
    def available(self) -> int:
        return self._pool.qsize()


class ConnectionManager:
    """
    Multi-backend connection manager.
    
    Manages connections for:
    - PostgreSQL
    - Neo4j
    """
    
    def __init__(self):
        self._pools: dict[str, ConnectionPool] = {}
        self._configs: dict[str, ConnectionConfig] = {}
    
    def register(self, name: str, config: ConnectionConfig) -> None:
        """Register a connection configuration."""
        self._configs[name] = config
    
    async def initialize(self) -> None:
        """Initialize all registered connections."""
        for name, config in self._configs.items():
            if config.backend == "postgres":
                from sqlalchemy.ext.asyncio import create_async_engine
                factory = lambda: create_async_engine(config.to_url())
                pool = ConnectionPool(factory, config)
                await pool.initialize()
                self._pools[name] = pool
            elif config.backend == "neo4j":
                try:
                    from neo4j import AsyncGraphDatabase
                    factory = lambda: AsyncGraphDatabase.driver(
                        config.to_url(),
                        auth=(config.user, config.password)
                    )
                    pool = ConnectionPool(factory, config)
                    await pool.initialize()
                    self._pools[name] = pool
                except ImportError:
                    logger.warning("Neo4j driver not installed")
    
    def get_pool(self, name: str) -> ConnectionPool | None:
        """Get a connection pool by name."""
        return self._pools.get(name)
    
    @asynccontextmanager
    async def acquire(self, name: str):
        """Acquire a connection from named pool."""
        pool = self._pools.get(name)
        if not pool:
            raise ValueError(f"Connection pool not found: {name}")
        async with pool.acquire() as conn:
            yield conn
    
    async def close(self) -> None:
        """Close all connection pools."""
        for pool in self._pools.values():
            await pool.close()
        self._pools.clear()
    
    async def health_check(self) -> dict[str, bool]:
        """Check health of all connections."""
        results = {}
        for name, pool in self._pools.items():
            try:
                async with pool.acquire() as conn:
                    results[name] = True
            except Exception:
                results[name] = False
        return results
