"""
Configurable Data Persistence Module.

Provides:
- Table configuration via YAML/JSON
- Dynamic field mapping
- Pluggable storage strategies
- UPSERT/INSERT/APPEND modes
"""

from __future__ import annotations

import logging
import os
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

import yaml
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SaveMode(str, Enum):
    """Data save mode."""
    INSERT = "insert"
    UPSERT = "upsert"
    APPEND = "append"
    REPLACE = "replace"


class FieldType(str, Enum):
    """Field data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    JSON = "json"


@dataclass
class FieldConfig:
    """Configuration for a single field."""
    
    name: str
    source_fields: list[str] = field(default_factory=list)
    data_type: FieldType = FieldType.STRING
    required: bool = False
    default: Any = None
    transform: Callable[[Any], Any] | None = None
    
    def get_value(self, data: dict[str, Any]) -> Any:
        """Extract value from data using source fields."""
        for source_field in self.source_fields or [self.name]:
            if source_field in data:
                value = data[source_field]
                break
        else:
            value = data.get(self.name)
        
        if value is None:
            value = self.default
        
        if value is not None and self.transform:
            value = self.transform(value)
        
        return self._convert_type(value)
    
    def _convert_type(self, value: Any) -> Any:
        """Convert value to target type."""
        if value is None:
            return None
        
        if self.data_type == FieldType.DATE:
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
            return None
        
        if self.data_type == FieldType.DATETIME:
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    pass
            return None
        
        if self.data_type == FieldType.FLOAT:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        
        if self.data_type == FieldType.INTEGER:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        
        if self.data_type == FieldType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes")
            return bool(value)
        
        return str(value) if value is not None else None


class TableConfig(BaseModel):
    """Configuration for a database table."""
    
    table_name: str = Field(..., description="Target table name")
    schema_name: str = Field(default="openfinance", description="Schema name")
    
    primary_key: list[str] = Field(default_factory=lambda: ["id"], description="Primary key columns")
    unique_keys: list[list[str]] = Field(default_factory=list, description="Unique constraint columns")
    
    fields: dict[str, dict[str, Any]] = Field(default_factory=dict, description="Field configurations")
    
    save_mode: SaveMode = Field(default=SaveMode.UPSERT, description="Save mode")
    batch_size: int = Field(default=500, description="Batch size for inserts")
    
    create_if_not_exists: bool = Field(default=True, description="Create table if not exists")
    auto_ddl: bool = Field(default=False, description="Auto-generate DDL from field configs")
    
    pre_save_hook: str | None = Field(default=None, description="Pre-save hook function path")
    post_save_hook: str | None = Field(default=None, description="Post-save hook function path")
    
    def get_full_table_name(self) -> str:
        """Get fully qualified table name."""
        return f"{self.schema_name}.{self.table_name}"
    
    def get_field_config(self, field_name: str) -> FieldConfig:
        """Get field configuration."""
        field_data = self.fields.get(field_name, {})
        return FieldConfig(
            name=field_name,
            source_fields=field_data.get("source_fields", []),
            data_type=FieldType(field_data.get("type", "string")),
            required=field_data.get("required", False),
            default=field_data.get("default"),
        )
    
    def get_upsert_conflict_clause(self) -> str:
        """Generate ON CONFLICT clause for UPSERT."""
        if not self.unique_keys:
            conflict_cols = ", ".join(self.primary_key)
        else:
            conflict_cols = ", ".join(self.unique_keys[0])
        
        return f"ON CONFLICT ({conflict_cols})"


class PersistenceConfig(BaseModel):
    """Complete persistence configuration."""
    
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://openfinance:openfinance@localhost:5432/openfinance?client_encoding=utf8"
        ),
        description="Database connection URL"
    )
    
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_recycle: int = Field(default=3600, description="Pool recycle time in seconds")
    
    default_batch_size: int = Field(default=500, description="Default batch size")
    max_retries: int = Field(default=3, description="Max retry attempts")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    
    tables: dict[str, TableConfig] = Field(
        default_factory=dict,
        description="Table configurations"
    )
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> "PersistenceConfig":
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        tables = {}
        for table_name, table_data in data.get("tables", {}).items():
            tables[table_name] = TableConfig(table_name=table_name, **table_data)
        
        return cls(
            database_url=data.get("database_url"),
            pool_size=data.get("pool_size", 10),
            tables=tables,
        )


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (OperationalError, DBAPIError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


class ConfigurablePersistence:
    """
    Configurable data persistence handler.
    
    Features:
    - Table configuration via config objects
    - Dynamic field mapping
    - Multiple save modes (INSERT, UPSERT, APPEND)
    - Batch processing
    - Retry logic
    - Pre/post save hooks
    
    Usage:
        config = PersistenceConfig.from_yaml("persistence.yaml")
        persistence = ConfigurablePersistence(config)
        
        # Save data
        await persistence.save("stock_daily_quote", quotes)
    """
    
    def __init__(
        self,
        config: PersistenceConfig | None = None,
        table_configs: dict[str, TableConfig] | None = None,
    ) -> None:
        self._config = config or PersistenceConfig()
        
        if table_configs:
            self._config.tables.update(table_configs)
        
        self._engine = create_async_engine(
            self._config.database_url,
            echo=False,
            pool_size=self._config.pool_size,
            max_overflow=self._config.max_overflow,
            pool_pre_ping=True,
            pool_recycle=self._config.pool_recycle,
        )
        
        self._session_maker = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )
        
        self._register_builtin_tables()
    
    def _register_builtin_tables(self) -> None:
        """Register built-in table configurations."""
        builtin_tables = {
            "stock_daily_quote": TableConfig(
                table_name="stock_daily_quote",
                primary_key=["code", "trade_date"],
                unique_keys=[["code", "trade_date"]],
                fields={
                    "code": {"type": "string", "required": True, "source_fields": ["code", "symbol"]},
                    "name": {"type": "string", "source_fields": ["name", "stock_name"]},
                    "trade_date": {"type": "date", "required": True, "source_fields": ["trade_date", "date"]},
                    "open": {"type": "float"},
                    "high": {"type": "float"},
                    "low": {"type": "float"},
                    "close": {"type": "float"},
                    "volume": {"type": "float"},
                    "amount": {"type": "float"},
                    "change": {"type": "float", "source_fields": ["change", "chg"]},
                    "change_pct": {"type": "float", "source_fields": ["change_pct", "pct_chg"]},
                    "turnover_rate": {"type": "float"},
                    "market_cap": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "stock_basic": TableConfig(
                table_name="stock_basic",
                primary_key=["code"],
                unique_keys=[["code"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "industry": {"type": "string"},
                    "market": {"type": "string"},
                    "list_date": {"type": "date"},
                    "market_cap": {"type": "float"},
                    "pe_ratio": {"type": "float"},
                    "pb_ratio": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "news": TableConfig(
                table_name="news",
                primary_key=["news_id"],
                unique_keys=[["news_id"]],
                fields={
                    "news_id": {"type": "string", "required": True, "source_fields": ["news_id", "id"]},
                    "title": {"type": "string", "required": True},
                    "content": {"type": "string"},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "published_at": {"type": "datetime", "source_fields": ["published_at", "publish_time"]},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "stock_money_flow": TableConfig(
                table_name="stock_money_flow",
                primary_key=["code", "trade_date"],
                unique_keys=[["code", "trade_date"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "trade_date": {"type": "date", "required": True, "source_fields": ["trade_date", "date"]},
                    "main_net_inflow": {"type": "float"},
                    "main_net_inflow_pct": {"type": "float"},
                    "super_large_net_inflow": {"type": "float"},
                    "large_net_inflow": {"type": "float"},
                    "medium_net_inflow": {"type": "float"},
                    "small_net_inflow": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "stock_financial_indicator": TableConfig(
                table_name="stock_financial_indicator",
                primary_key=["code", "report_date"],
                unique_keys=[["code", "report_date"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "report_date": {"type": "date", "required": True},
                    "eps": {"type": "float"},
                    "bps": {"type": "float"},
                    "roe": {"type": "float"},
                    "roa": {"type": "float"},
                    "gross_margin": {"type": "float"},
                    "net_margin": {"type": "float"},
                    "revenue": {"type": "float"},
                    "net_profit": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "north_money": TableConfig(
                table_name="north_money",
                primary_key=["trade_date"],
                unique_keys=[["trade_date"]],
                fields={
                    "trade_date": {"type": "date", "required": True, "source_fields": ["trade_date", "date"]},
                    "sh_net_inflow": {"type": "float"},
                    "sz_net_inflow": {"type": "float"},
                    "total_net_inflow": {"type": "float", "source_fields": ["total_net_inflow", "net_inflow"]},
                },
                save_mode=SaveMode.UPSERT,
            ),
        }
        
        for table_name, table_config in builtin_tables.items():
            if table_name not in self._config.tables:
                self._config.tables[table_name] = table_config
    
    def register_table(self, config: TableConfig) -> None:
        """Register a table configuration."""
        self._config.tables[config.table_name] = config
    
    def get_table_config(self, table_name: str) -> TableConfig | None:
        """Get table configuration."""
        return self._config.tables.get(table_name)
    
    def _to_dict(self, obj: Any) -> dict[str, Any]:
        """Convert object to dictionary."""
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif isinstance(obj, dict):
            return obj
        return {}
    
    @with_retry()
    async def save(
        self,
        table_name: str,
        data: list[Any],
        table_config: TableConfig | None = None,
    ) -> int:
        """
        Save data to a configured table.
        
        Args:
            table_name: Name of the target table
            data: List of data objects to save
            table_config: Optional table configuration (uses registered config if not provided)
        
        Returns:
            Number of records saved
        """
        if not data:
            return 0
        
        config = table_config or self._config.tables.get(table_name)
        if not config:
            raise ValueError(f"No configuration found for table: {table_name}")
        
        saved = 0
        total = len(data)
        batch_size = config.batch_size or self._config.default_batch_size
        
        async with self._session_maker() as session:
            try:
                for i in range(0, total, batch_size):
                    batch = data[i:i + batch_size]
                    batch_saved = await self._save_batch(session, config, batch)
                    saved += batch_saved
                    logger.info(f"Saved batch {i // batch_size + 1}: {batch_saved}/{len(batch)} records")
                
                await session.commit()
                logger.info(f"Successfully saved {saved}/{total} records to {config.get_full_table_name()}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to save data to {table_name}: {e}")
                raise
        
        return saved
    
    async def _save_batch(
        self,
        session: AsyncSession,
        config: TableConfig,
        batch: list[Any],
    ) -> int:
        """Save a batch of data."""
        saved = 0
        
        for item in batch:
            try:
                data = self._to_dict(item)
                processed = self._process_data(config, data)
                
                if config.save_mode == SaveMode.UPSERT:
                    await self._upsert(session, config, processed)
                elif config.save_mode == SaveMode.INSERT:
                    await self._insert(session, config, processed)
                else:
                    await self._insert(session, config, processed)
                
                saved += 1
                
            except IntegrityError as e:
                logger.debug(f"Skipping duplicate: {e}")
            except Exception as e:
                logger.warning(f"Failed to save item: {e}")
        
        return saved
    
    def _process_data(self, config: TableConfig, data: dict[str, Any]) -> dict[str, Any]:
        """Process data using field configurations."""
        processed = {}
        
        for field_name, field_data in config.fields.items():
            field_config = config.get_field_config(field_name)
            value = field_config.get_value(data)
            processed[field_name] = value
        
        return processed
    
    async def _upsert(
        self,
        session: AsyncSession,
        config: TableConfig,
        data: dict[str, Any],
    ) -> None:
        """Execute UPSERT (INSERT ... ON CONFLICT DO UPDATE)."""
        columns = list(config.fields.keys())
        placeholders = ", ".join(f":{col}" for col in columns)
        column_list = ", ".join(columns)
        
        update_parts = []
        for col in columns:
            if col not in config.primary_key:
                update_parts.append(
                    f"{col} = COALESCE(EXCLUDED.{col}, {config.get_full_table_name()}.{col})"
                )
        update_clause = ", ".join(update_parts) if update_parts else ""
        
        sql = f"""
            INSERT INTO {config.get_full_table_name()} ({column_list})
            VALUES ({placeholders})
            {config.get_upsert_conflict_clause()}
            {"DO UPDATE SET " + update_clause if update_clause else "DO NOTHING"}
        """
        
        await session.execute(text(sql), data)
    
    async def _insert(
        self,
        session: AsyncSession,
        config: TableConfig,
        data: dict[str, Any],
    ) -> None:
        """Execute simple INSERT."""
        columns = list(config.fields.keys())
        placeholders = ", ".join(f":{col}" for col in columns)
        column_list = ", ".join(columns)
        
        sql = f"""
            INSERT INTO {config.get_full_table_name()} ({column_list})
            VALUES ({placeholders})
        """
        
        await session.execute(text(sql), data)
    
    async def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        stats = {}
        async with self._session_maker() as session:
            for table_name, config in self._config.tables.items():
                try:
                    result = await session.execute(
                        text(f"SELECT COUNT(*) FROM {config.get_full_table_name()}")
                    )
                    stats[table_name] = result.scalar() or 0
                except Exception:
                    stats[table_name] = 0
        return stats


persistence = ConfigurablePersistence()


class DataPersistence(ConfigurablePersistence):
    """
    Legacy DataPersistence class for backward compatibility.
    
    Provides the same interface as the original DataPersistence class.
    """
    
    def __init__(self, batch_size: int = 500) -> None:
        super().__init__()
        self.batch_size = batch_size
    
    async def save_stock_quotes(self, quotes: list[Any]) -> int:
        """Save stock daily quotes."""
        return await self.save("stock_daily_quote", quotes)
    
    async def save_stock_basic(self, stocks: list[Any]) -> int:
        """Save stock basic info."""
        return await self.save("stock_basic", stocks)
    
    async def save_money_flow(self, flows: list[Any]) -> int:
        """Save money flow data."""
        return await self.save("stock_money_flow", flows)
    
    async def save_news(self, news_list: list[Any]) -> int:
        """Save news data."""
        return await self.save("news", news_list)
    
    async def save_macro_data(self, macro_list: list[Any]) -> int:
        """Save macro economic data."""
        return await self.save("macro_economic", macro_list)
    
    async def save_factor_data(self, factors: list[Any]) -> int:
        """Save factor data."""
        return await self.save("factor_data", factors)
    
    async def save_financial_indicator(self, indicators: list[Any]) -> int:
        """Save financial indicators."""
        return await self.save("stock_financial_indicator", indicators)
    
    async def save_north_money(self, data_list: list[Any]) -> int:
        """Save north money data."""
        return await self.save("north_money", data_list)
    
    async def save_industry_quotes(self, quotes: list[Any]) -> int:
        """Save industry quotes."""
        return await self.save("industry_quote", quotes)
    
    async def save_concept_quotes(self, quotes: list[Any]) -> int:
        """Save concept quotes."""
        return await self.save("concept_quote", quotes)
    
    async def save_company_profiles(self, profiles: list[Any]) -> int:
        """Save company profiles."""
        return await self.save("company_profile", profiles)
