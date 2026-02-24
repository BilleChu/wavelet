"""
优雅的数据持久化模块

基于配置文件的数据持久化实现，支持：
- 表配置通过 YAML 文件管理
- 动态字段映射
- 多种保存模式（UPSERT/INSERT/APPEND）
- 批量处理
- ORM 模型支持
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
from typing import Any, Callable, Generic, TypeVar, TYPE_CHECKING

import yaml
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SaveMode(str, Enum):
    """数据保存模式"""
    INSERT = "insert"
    UPSERT = "upsert"
    APPEND = "append"
    REPLACE = "replace"


class FieldType(str, Enum):
    """字段数据类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    JSON = "json"


@dataclass
class FieldConfig:
    """单个字段的配置"""
    
    name: str
    source_fields: list[str] = field(default_factory=list)
    data_type: FieldType = FieldType.STRING
    required: bool = False
    default: Any = None
    transform: Callable[[Any], Any] | None = None
    
    def get_value(self, data: dict[str, Any]) -> Any:
        """从数据中提取值，使用源字段"""
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
        """转换值到目标类型"""
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
    """数据库表的配置"""
    
    table_name: str = Field(..., description="目标表名")
    schema_name: str = Field(default="openfinance", description="Schema 名称")
    
    primary_key: list[str] = Field(default_factory=lambda: ["id"], description="主键列")
    unique_keys: list[list[str]] = Field(default_factory=list, description="唯一约束列")
    
    fields: dict[str, dict[str, Any]] = Field(default_factory=dict, description="字段配置")
    
    save_mode: SaveMode = Field(default=SaveMode.UPSERT, description="保存模式")
    batch_size: int = Field(default=500, description="批量大小")
    
    create_if_not_exists: bool = Field(default=True, description="如果表不存在则创建")
    auto_ddl: bool = Field(default=False, description="自动生成 DDL")
    
    pre_save_hook: str | None = Field(default=None, description="保存前钩子函数路径")
    post_save_hook: str | None = Field(default=None, description="保存后钩子函数路径")
    
    def get_full_table_name(self) -> str:
        """获取完全限定的表名"""
        return f"{self.schema_name}.{self.table_name}"
    
    def get_field_config(self, field_name: str) -> FieldConfig:
        """获取字段配置"""
        field_data = self.fields.get(field_name, {})
        return FieldConfig(
            name=field_name,
            source_fields=field_data.get("source_fields", []),
            data_type=FieldType(field_data.get("type", "string")),
            required=field_data.get("required", False),
            default=field_data.get("default"),
        )
    
    def get_upsert_conflict_clause(self) -> str:
        """生成 UPSERT 的 ON CONFLICT 子句"""
        if not self.unique_keys:
            conflict_cols = ", ".join(self.primary_key)
        else:
            conflict_cols = ", ".join(self.unique_keys[0])
        
        return f"ON CONFLICT ({conflict_cols})"


class PersistenceConfig(BaseModel):
    """完整的持久化配置"""
    
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://openfinance:openfinance@localhost:5432/openfinance?client_encoding=utf8"
        ),
        description="数据库连接 URL"
    )
    
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="最大溢出连接数")
    pool_recycle: int = Field(default=3600, description="连接池回收时间（秒）")
    
    default_batch_size: int = Field(default=500, description="默认批量大小")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试延迟（秒）")
    
    tables: dict[str, TableConfig] = Field(
        default_factory=dict,
        description="表配置"
    )
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> "PersistenceConfig":
        """从 YAML 文件加载配置"""
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
    """重试装饰器，使用指数退避"""
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
                            f"数据库操作失败（第 {attempt + 1}/{max_retries} 次尝试），"
                            f"{wait_time}s 后重试: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"数据库操作在 {max_retries} 次尝试后失败: {e}")
            raise last_exception
        return wrapper
    return decorator


class ConfigurablePersistence:
    """
    可配置的数据持久化处理器
    
    特性：
    - 通过配置对象管理表配置
    - 动态字段映射
    - 多种保存模式（UPSERT/INSERT/APPEND）
    - 批量处理
    - 重试逻辑
    - 保存前/后钩子
    - ORM 模型支持
    
    使用示例：
        config = PersistenceConfig.from_yaml("persistence.yaml")
        persistence = ConfigurablePersistence(config)
        
        # 保存数据
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
        
        self.session_maker = self._session_maker
        
        self._register_builtin_tables()
    
    def _register_builtin_tables(self) -> None:
        """注册内置表配置"""
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
                    "total_shares": {"type": "float"},
                    "circulating_shares": {"type": "float"},
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
            "industry_quote": TableConfig(
                table_name="industry_quote",
                primary_key=["code", "trade_date"],
                unique_keys=[["code", "trade_date"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "trade_date": {"type": "date", "required": True},
                    "open": {"type": "float"},
                    "high": {"type": "float"},
                    "low": {"type": "float"},
                    "close": {"type": "float"},
                    "volume": {"type": "float"},
                    "amount": {"type": "float"},
                    "change_pct": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "concept_quote": TableConfig(
                table_name="concept_quote",
                primary_key=["code", "trade_date"],
                unique_keys=[["code", "trade_date"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "trade_date": {"type": "date", "required": True},
                    "open": {"type": "float"},
                    "high": {"type": "float"},
                    "low": {"type": "float"},
                    "close": {"type": "float"},
                    "volume": {"type": "float"},
                    "amount": {"type": "float"},
                    "change_pct": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "company_profile": TableConfig(
                table_name="company_profile",
                primary_key=["code"],
                unique_keys=[["code"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "name": {"type": "string"},
                    "industry": {"type": "string"},
                    "sector": {"type": "string"},
                    "description": {"type": "string"},
                    "website": {"type": "string"},
                    "employees": {"type": "integer"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "factor_data": TableConfig(
                table_name="factor_data",
                primary_key=["factor_id", "code", "trade_date"],
                unique_keys=[["factor_id", "code", "trade_date"]],
                batch_size=5000,
                fields={
                    "factor_id": {"type": "string", "required": True},
                    "code": {"type": "string", "required": True},
                    "trade_date": {"type": "date", "required": True},
                    "factor_name": {"type": "string"},
                    "factor_category": {"type": "string"},
                    "factor_value": {"type": "float"},
                    "collected_at": {"type": "datetime"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "income_statement": TableConfig(
                table_name="income_statement",
                primary_key=["code", "report_date", "report_period"],
                unique_keys=[["code", "report_date", "report_period"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "report_date": {"type": "date", "required": True},
                    "report_period": {"type": "string", "default": "annual"},
                    "total_revenue": {"type": "float"},
                    "operating_revenue": {"type": "float"},
                    "total_cost_of_goods_sold": {"type": "float"},
                    "gross_profit": {"type": "float"},
                    "operating_profit": {"type": "float"},
                    "total_profit": {"type": "float"},
                    "net_profit": {"type": "float"},
                    "net_profit_attr_parent": {"type": "float"},
                    "basic_eps": {"type": "float"},
                    "diluted_eps": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "balance_sheet": TableConfig(
                table_name="balance_sheet",
                primary_key=["code", "report_date", "report_period"],
                unique_keys=[["code", "report_date", "report_period"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "report_date": {"type": "date", "required": True},
                    "report_period": {"type": "string", "default": "annual"},
                    "total_assets": {"type": "float"},
                    "total_liabilities": {"type": "float"},
                    "total_equity": {"type": "float"},
                    "net_equity_attr": {"type": "float"},
                    "current_assets": {"type": "float"},
                    "current_liabilities": {"type": "float"},
                    "cash": {"type": "float"},
                    "inventory": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "dividend_data": TableConfig(
                table_name="dividend_data",
                primary_key=["code", "report_year"],
                unique_keys=[["code", "report_year"]],
                fields={
                    "code": {"type": "string", "required": True},
                    "report_year": {"type": "string", "required": True},
                    "ex_date": {"type": "date"},
                    "dividend_per_share": {"type": "float"},
                    "bonus_per_share": {"type": "float"},
                    "transfer_per_share": {"type": "float"},
                    "total_dividend": {"type": "float"},
                    "dividend_yield": {"type": "float"},
                },
                save_mode=SaveMode.UPSERT,
            ),
            "macro_economic": TableConfig(
                table_name="macro_economic",
                primary_key=["indicator_id", "report_date"],
                unique_keys=[["indicator_id", "report_date"]],
                fields={
                    "indicator_id": {"type": "string", "required": True},
                    "indicator_name": {"type": "string"},
                    "report_date": {"type": "date", "required": True},
                    "value": {"type": "float"},
                    "unit": {"type": "string"},
                    "source": {"type": "string"},
                },
                save_mode=SaveMode.UPSERT,
            ),
        }
        
        for table_name, table_config in builtin_tables.items():
            if table_name not in self._config.tables:
                self._config.tables[table_name] = table_config
    
    def register_table(self, config: TableConfig) -> None:
        """注册表配置"""
        self._config.tables[config.table_name] = config
    
    def get_table_config(self, table_name: str) -> TableConfig | None:
        """获取表配置"""
        return self._config.tables.get(table_name)
    
    def _to_dict(self, obj: Any) -> dict[str, Any]:
        """将对象转换为字典"""
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
        保存数据到配置的表
        
        Args:
            table_name: 目标表名
            data: 要保存的数据对象列表
            table_config: 可选的表配置（使用已注册的配置）
        
        Returns:
            保存的记录数
        """
        if not data:
            return 0
        
        config = table_config or self._config.tables.get(table_name)
        if not config:
            raise ValueError(f"未找到表的配置: {table_name}")
        
        saved = 0
        total = len(data)
        batch_size = config.batch_size or self._config.default_batch_size
        
        async with self._session_maker() as session:
            try:
                for i in range(0, total, batch_size):
                    batch = data[i:i + batch_size]
                    batch_saved = await self._save_batch(session, config, batch)
                    saved += batch_saved
                    logger.info(f"保存批次 {i // batch_size + 1}: {batch_saved}/{len(batch)} 条记录")
                
                await session.commit()
                logger.info(f"成功保存 {saved}/{total} 条记录到 {config.get_full_table_name()}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"保存数据到 {table_name} 失败: {e}")
                raise
        
        return saved
    
    async def _save_batch(
        self,
        session: AsyncSession,
        config: TableConfig,
        batch: list[Any],
    ) -> int:
        """保存一批数据"""
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
                logger.debug(f"跳过重复记录: {e}")
            except Exception as e:
                logger.warning(f"保存记录失败: {e}")
        
        return saved
    
    def _process_data(self, config: TableConfig, data: dict[str, Any]) -> dict[str, Any]:
        """使用字段配置处理数据"""
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
        """执行 UPSERT（INSERT ... ON CONFLICT DO UPDATE）"""
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
        """执行简单 INSERT"""
        columns = list(config.fields.keys())
        placeholders = ", ".join(f":{col}" for col in columns)
        column_list = ", ".join(columns)
        
        sql = f"""
            INSERT INTO {config.get_full_table_name()} ({column_list})
            VALUES ({placeholders})
        """
        
        await session.execute(text(sql), data)
    
    async def save_orm(
        self,
        table_name: str,
        data: list[Any],
    ) -> int:
        """
        保存 ORM 模型数据
        
        Args:
            table_name: 表名
            data: ORM 模型对象列表
        
        Returns:
            保存的记录数
        """
        if not data:
            return 0
        
        saved = 0
        async with self._session_maker() as session:
            try:
                for item in data:
                    session.add(item)
                    saved += 1
                
                await session.commit()
                logger.info(f"成功保存 {saved}/{len(data)} 条 ORM 记录到 {table_name}")
                
            except Exception as e:
                await session.rollback()
                logger.error(f"保存 ORM 数据到 {table_name} 失败: {e}")
                raise
        
        return saved
    
    async def get_stats(self) -> dict[str, int]:
        """获取数据库统计信息"""
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
