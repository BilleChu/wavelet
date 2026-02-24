"""
Factor Storage Module.

Provides database persistence for factor data and metadata.
Supports PostgreSQL with async operations.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import asyncpg
from pydantic import BaseModel

from ..base import FactorResult, FactorStatus

logger = logging.getLogger(__name__)


class FactorDataRecord(BaseModel):
    """Database record for factor data."""
    
    factor_id: str
    code: str
    trade_date: date
    value: float | None = None
    value_normalized: float | None = None
    value_rank: int | None = None
    value_percentile: float | None = None
    value_neutralized: float | None = None
    signal: float = 0.0
    confidence: float = 0.5
    data_quality: str = "high"
    metadata: dict[str, Any] = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FactorMetadataRecord(BaseModel):
    """Database record for factor metadata."""
    
    factor_id: str
    name: str
    code: str
    description: str = ""
    factor_type: str = "technical"
    category: str = "custom"
    expression: str = ""
    formula: str = ""
    parameters: dict[str, Any] = {}
    default_params: dict[str, Any] = {}
    lookback_period: int = 20
    required_fields: list[str] = []
    normalize_method: str = "zscore"
    supports_neutralization: bool = False
    tags: list[str] = []
    version: str = "1.0.0"
    author: str = "system"
    status: str = "active"
    is_builtin: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    host: str = "localhost"
    port: int = 5432
    database: str = "openfinance"
    user: str = "openfinance"
    password: str = "openfinance"
    min_pool_size: int = 5
    max_pool_size: int = 20
    
    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?client_encoding=utf8"


class FactorStorage:
    """
    Database storage for factor data.
    
    Features:
    - Async database operations
    - Connection pooling
    - Batch insert/update
    - Query optimization
    """
    
    def __init__(self, config: DatabaseConfig | None = None):
        self.config = config or DatabaseConfig()
        self._pool: asyncpg.Pool | None = None
    
    async def initialize(self) -> None:
        """Initialize database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self.config.dsn,
                min_size=self.config.min_pool_size,
                max_size=self.config.max_pool_size,
            )
            logger.info(f"Database pool initialized: {self.config.database}")
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")
    
    async def _ensure_tables(self) -> None:
        """Ensure required tables exist."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS factor_registry (
                    factor_id VARCHAR(100) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    code VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    factor_type VARCHAR(50) DEFAULT 'technical',
                    category VARCHAR(50) DEFAULT 'custom',
                    expression TEXT,
                    formula TEXT,
                    parameters JSONB DEFAULT '{}',
                    default_params JSONB DEFAULT '{}',
                    lookback_period INTEGER DEFAULT 20,
                    required_fields JSONB DEFAULT '[]',
                    normalize_method VARCHAR(50) DEFAULT 'zscore',
                    supports_neutralization BOOLEAN DEFAULT FALSE,
                    tags JSONB DEFAULT '[]',
                    version VARCHAR(20) DEFAULT '1.0.0',
                    author VARCHAR(100) DEFAULT 'system',
                    status VARCHAR(20) DEFAULT 'active',
                    is_builtin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS factor_data (
                    id BIGSERIAL PRIMARY KEY,
                    factor_id VARCHAR(100) NOT NULL,
                    code VARCHAR(20) NOT NULL,
                    trade_date DATE NOT NULL,
                    value DOUBLE PRECISION,
                    value_normalized DOUBLE PRECISION,
                    value_rank INTEGER,
                    value_percentile DOUBLE PRECISION,
                    value_neutralized DOUBLE PRECISION,
                    signal DOUBLE PRECISION DEFAULT 0,
                    confidence DOUBLE PRECISION DEFAULT 0.5,
                    data_quality VARCHAR(20) DEFAULT 'high',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(factor_id, code, trade_date)
                )
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_factor_data_factor_id 
                ON factor_data(factor_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_factor_data_code_date 
                ON factor_data(code, trade_date)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_factor_data_date 
                ON factor_data(trade_date)
            """)
    
    async def save_factor_metadata(
        self,
        record: FactorMetadataRecord,
    ) -> bool:
        """Save factor metadata to database."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO factor_registry (
                    factor_id, name, code, description, factor_type, category,
                    expression, formula, parameters, default_params,
                    lookback_period, required_fields, normalize_method,
                    supports_neutralization, tags, version, author, status, is_builtin
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                ON CONFLICT (factor_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    expression = EXCLUDED.expression,
                    formula = EXCLUDED.formula,
                    parameters = EXCLUDED.parameters,
                    default_params = EXCLUDED.default_params,
                    tags = EXCLUDED.tags,
                    status = EXCLUDED.status,
                    version = EXCLUDED.version,
                    updated_at = CURRENT_TIMESTAMP
            """,
                record.factor_id, record.name, record.code, record.description,
                record.factor_type, record.category, record.expression, record.formula,
                record.parameters, record.default_params, record.lookback_period,
                record.required_fields, record.normalize_method, record.supports_neutralization,
                record.tags, record.version, record.author, record.status, record.is_builtin,
            )
            
            return True
    
    async def get_factor_metadata(
        self,
        factor_id: str,
    ) -> FactorMetadataRecord | None:
        """Get factor metadata from database."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM factor_registry WHERE factor_id = $1",
                factor_id,
            )
            
            if row:
                return FactorMetadataRecord(
                    factor_id=row["factor_id"],
                    name=row["name"],
                    code=row["code"],
                    description=row["description"] or "",
                    factor_type=row["factor_type"],
                    category=row["category"],
                    expression=row["expression"] or "",
                    formula=row["formula"] or "",
                    parameters=row["parameters"] or {},
                    default_params=row["default_params"] or {},
                    lookback_period=row["lookback_period"],
                    required_fields=row["required_fields"] or [],
                    normalize_method=row["normalize_method"],
                    supports_neutralization=row["supports_neutralization"],
                    tags=row["tags"] or [],
                    version=row["version"],
                    author=row["author"],
                    status=row["status"],
                    is_builtin=row["is_builtin"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None
    
    async def list_factor_metadata(
        self,
        factor_type: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[FactorMetadataRecord]:
        """List factor metadata with optional filters."""
        conditions = []
        params = []
        param_idx = 1
        
        if factor_type:
            conditions.append(f"factor_type = ${param_idx}")
            params.append(factor_type)
            param_idx += 1
        
        if category:
            conditions.append(f"category = ${param_idx}")
            params.append(category)
            param_idx += 1
        
        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM factor_registry WHERE {where_clause} ORDER BY updated_at DESC",
                *params,
            )
            
            return [self._row_to_metadata_record(row) for row in rows]
    
    def _row_to_metadata_record(self, row: asyncpg.Record) -> FactorMetadataRecord:
        """Convert database row to metadata record."""
        return FactorMetadataRecord(
            factor_id=row["factor_id"],
            name=row["name"],
            code=row["code"],
            description=row["description"] or "",
            factor_type=row["factor_type"],
            category=row["category"],
            expression=row["expression"] or "",
            formula=row["formula"] or "",
            parameters=row["parameters"] or {},
            default_params=row["default_params"] or {},
            lookback_period=row["lookback_period"],
            required_fields=row["required_fields"] or [],
            normalize_method=row["normalize_method"],
            supports_neutralization=row["supports_neutralization"],
            tags=row["tags"] or [],
            version=row["version"],
            author=row["author"],
            status=row["status"],
            is_builtin=row["is_builtin"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    async def save_factor_data(
        self,
        results: list[FactorResult],
    ) -> int:
        """Save factor calculation results to database."""
        if not results:
            return 0
        
        async with self._pool.acquire() as conn:
            saved = 0
            for result in results:
                try:
                    await conn.execute("""
                        INSERT INTO factor_data (
                            factor_id, code, trade_date, value, value_normalized,
                            value_rank, value_percentile, value_neutralized,
                            signal, confidence, data_quality, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (factor_id, code, trade_date) DO UPDATE SET
                            value = EXCLUDED.value,
                            value_normalized = EXCLUDED.value_normalized,
                            value_rank = EXCLUDED.value_rank,
                            value_percentile = EXCLUDED.value_percentile,
                            value_neutralized = EXCLUDED.value_neutralized,
                            signal = EXCLUDED.signal,
                            confidence = EXCLUDED.confidence,
                            data_quality = EXCLUDED.data_quality,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                    """,
                        result.factor_id, result.code, result.trade_date,
                        result.value, result.value_normalized, result.value_rank,
                        result.value_percentile, result.value_neutralized,
                        result.signal, result.confidence, result.data_quality,
                        result.metadata,
                    )
                    saved += 1
                except Exception as e:
                    logger.error(f"Failed to save factor data: {e}")
            
            return saved
    
    async def save_factor_data_batch(
        self,
        results: list[FactorResult],
    ) -> int:
        """Save factor data in batch for better performance."""
        if not results:
            return 0
        
        async with self._pool.acquire() as conn:
            records = [
                (
                    r.factor_id, r.code, r.trade_date, 
                    r.factor_id, 
                    "technical",
                    r.value,
                    r.value_rank,
                    r.value_percentile,
                    r.value_neutralized is not None,
                )
                for r in results
            ]
            
            await conn.executemany("""
                INSERT INTO openfinance.factor_data (
                    factor_id, code, trade_date, factor_name, factor_category,
                    factor_value, factor_rank, factor_percentile, neutralized
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (factor_id, code, trade_date) DO UPDATE SET
                    factor_value = EXCLUDED.factor_value,
                    factor_rank = EXCLUDED.factor_rank,
                    factor_percentile = EXCLUDED.factor_percentile,
                    neutralized = EXCLUDED.neutralized,
                    collected_at = CURRENT_TIMESTAMP
            """, records)
            
            return len(results)
    
    async def load_factor_data(
        self,
        factor_id: str,
        codes: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
    ) -> list[FactorDataRecord]:
        """Load factor data from database."""
        conditions = ["factor_id = $1"]
        params: list[Any] = [factor_id]
        param_idx = 2
        
        if codes:
            conditions.append(f"code = ANY(${param_idx})")
            params.append(codes)
            param_idx += 1
        
        if start_date:
            conditions.append(f"trade_date >= ${param_idx}")
            params.append(start_date)
            param_idx += 1
        
        if end_date:
            conditions.append(f"trade_date <= ${param_idx}")
            params.append(end_date)
            param_idx += 1
        
        where_clause = " AND ".join(conditions)
        order_clause = "ORDER BY trade_date DESC, code"
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT factor_id, code, trade_date, factor_value as value, "
                f"factor_rank as value_rank, factor_percentile as value_percentile, "
                f"neutralized as value_neutralized, "
                f"0.0 as value_normalized, 0.0 as signal, 0.5 as confidence, 'high' as data_quality, "
                f"'{{}}'::jsonb as metadata, collected_at as created_at, collected_at as updated_at "
                f"FROM openfinance.factor_data WHERE {where_clause} {order_clause} {limit_clause}",
                *params,
            )
            
            return [self._row_to_data_record(row) for row in rows]
    
    def _row_to_data_record(self, row: asyncpg.Record) -> FactorDataRecord:
        """Convert database row to data record."""
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata) if metadata else {}
        elif metadata is None:
            metadata = {}
            
        return FactorDataRecord(
            factor_id=row["factor_id"],
            code=row["code"],
            trade_date=row["trade_date"],
            value=row["value"],
            value_normalized=row.get("value_normalized"),
            value_rank=row.get("value_rank"),
            value_percentile=row.get("value_percentile"),
            value_neutralized=row.get("value_neutralized"),
            signal=row.get("signal", 0.0),
            confidence=row.get("confidence", 0.5),
            data_quality=row.get("data_quality", "high"),
            metadata=metadata,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
    
    async def get_latest_factor_values(
        self,
        factor_id: str,
        codes: list[str] | None = None,
    ) -> dict[str, float]:
        """Get latest factor values for each stock."""
        conditions = ["factor_id = $1"]
        params: list[Any] = [factor_id]
        
        if codes:
            conditions.append("code = ANY($2)")
            params.append(codes)
        
        where_clause = " AND ".join(conditions)
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT DISTINCT ON (code) code, factor_value as value, trade_date
                FROM openfinance.factor_data
                WHERE {where_clause}
                ORDER BY code, trade_date DESC
            """, *params)
            
            return {row["code"]: row["value"] for row in rows if row["value"] is not None}
    
    async def delete_factor_data(
        self,
        factor_id: str,
        before_date: date | None = None,
    ) -> int:
        """Delete factor data from database."""
        conditions = ["factor_id = $1"]
        params: list[Any] = [factor_id]
        
        if before_date:
            conditions.append("trade_date < $2")
            params.append(before_date)
        
        where_clause = " AND ".join(conditions)
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM openfinance.factor_data WHERE {where_clause}",
                *params,
            )
            
            return int(result.split()[-1])
    
    async def get_factor_statistics(
        self,
        factor_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get statistics for a factor."""
        conditions = ["factor_id = $1"]
        params: list[Any] = [factor_id]
        param_idx = 2
        
        if start_date:
            conditions.append(f"trade_date >= ${param_idx}")
            params.append(start_date)
            param_idx += 1
        
        if end_date:
            conditions.append(f"trade_date <= ${param_idx}")
            params.append(end_date)
            param_idx += 1
        
        where_clause = " AND ".join(conditions)
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(f"""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(factor_value) as valid_count,
                    AVG(factor_value) as mean_value,
                    STDDEV(factor_value) as std_value,
                    MIN(factor_value) as min_value,
                    MAX(factor_value) as max_value,
                    MIN(trade_date) as min_date,
                    MAX(trade_date) as max_date
                FROM openfinance.factor_data
                WHERE {where_clause}
            """, *params)
            
            return {
                "total_count": row["total_count"],
                "valid_count": row["valid_count"],
                "mean_value": float(row["mean_value"]) if row["mean_value"] else None,
                "std_value": float(row["std_value"]) if row["std_value"] else None,
                "min_value": float(row["min_value"]) if row["min_value"] else None,
                "max_value": float(row["max_value"]) if row["max_value"] else None,
                "min_date": row["min_date"],
                "max_date": row["max_date"],
            }


_storage: FactorStorage | None = None


async def get_factor_storage() -> FactorStorage:
    """Get the global factor storage instance."""
    global _storage
    if _storage is None:
        _storage = FactorStorage()
        await _storage.initialize()
    return _storage
