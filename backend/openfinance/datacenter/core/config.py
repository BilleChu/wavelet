"""
Unified Configuration System.

Provides centralized configuration management for the entire datacenter,
supporting environment variables, YAML files, and programmatic configuration.

Usage:
    from datacenter.core import get_config, load_config
    
    config = load_config("config.yaml")
    
    source_config = config.get_source("eastmoney")
    collection_settings = config.collection
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SourceSettings:
    """
    Settings for a data source.
    
    Attributes:
        enabled: Whether source is enabled
        base_url: Base URL for API
        api_key: API key (can use env var reference)
        timeout: Request timeout in seconds
        retry_count: Number of retries
        retry_delay: Delay between retries
        rate_limit: Requests per second limit
        headers: Additional headers
    """
    enabled: bool = True
    base_url: str = ""
    api_key: str | None = None
    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    rate_limit: float = 10.0
    headers: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    
    def resolve_api_key(self) -> str | None:
        """Resolve API key from environment variable if needed."""
        if not self.api_key:
            return None
        
        if self.api_key.startswith("${") and self.api_key.endswith("}"):
            env_var = self.api_key[2:-1]
            return os.environ.get(env_var)
        
        if self.api_key.startswith("$"):
            env_var = self.api_key[1:]
            return os.environ.get(env_var)
        
        return self.api_key


@dataclass
class CollectionSettings:
    """
    Data collection settings.
    
    Attributes:
        batch_size: Default batch size for collection
        max_concurrent: Maximum concurrent collections
        default_start_date: Default start date for historical data
        validate_on_collect: Whether to validate data during collection
        dedup_enabled: Whether deduplication is enabled
        quality_threshold: Minimum quality score threshold
    """
    batch_size: int = 1000
    max_concurrent: int = 5
    default_start_date: str = "2020-01-01"
    validate_on_collect: bool = True
    dedup_enabled: bool = True
    quality_threshold: float = 0.95
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class StorageSettings:
    """
    Storage settings.
    
    Attributes:
        database_url: Database connection URL
        pool_size: Connection pool size
        echo_sql: Whether to echo SQL statements
        batch_insert_size: Batch insert size
    """
    database_url: str = "sqlite:///datacenter.db"
    pool_size: int = 10
    echo_sql: bool = False
    batch_insert_size: int = 1000
    timezone: str = "Asia/Shanghai"
    
    def resolve_database_url(self) -> str:
        """Resolve database URL from environment variable if needed."""
        if self.database_url.startswith("${") and self.database_url.endswith("}"):
            env_var = self.database_url[2:-1]
            return os.environ.get(env_var, self.database_url)
        return self.database_url


@dataclass
class CacheSettings:
    """
    Cache settings.
    
    Attributes:
        enabled: Whether caching is enabled
        backend: Cache backend (memory, redis)
        ttl: Default TTL in seconds
        max_size: Maximum cache size (for memory backend)
        redis_url: Redis URL (for redis backend)
    """
    enabled: bool = True
    backend: str = "memory"
    ttl: int = 300
    max_size: int = 10000
    redis_url: str | None = None


@dataclass
class LoggingSettings:
    """
    Logging settings.
    
    Attributes:
        level: Log level
        format: Log format
        file: Log file path
        max_bytes: Maximum log file size
        backup_count: Number of backup files
    """
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = None
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class DatacenterConfig:
    """
    Complete datacenter configuration.
    
    Attributes:
        version: Configuration version
        sources: Data source settings
        collection: Collection settings
        storage: Storage settings
        cache: Cache settings
        logging: Logging settings
    """
    version: str = "1.0"
    sources: dict[str, SourceSettings] = field(default_factory=dict)
    collection: CollectionSettings = field(default_factory=CollectionSettings)
    storage: StorageSettings = field(default_factory=StorageSettings)
    cache: CacheSettings = field(default_factory=CacheSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def get_source(self, source_id: str) -> SourceSettings | None:
        """Get settings for a specific source."""
        return self.sources.get(source_id)
    
    def add_source(self, source_id: str, settings: SourceSettings) -> None:
        """Add or update source settings."""
        self.sources[source_id] = settings
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "sources": {
                k: {
                    "enabled": v.enabled,
                    "base_url": v.base_url,
                    "timeout": v.timeout,
                    "retry_count": v.retry_count,
                    "rate_limit": v.rate_limit,
                }
                for k, v in self.sources.items()
            },
            "collection": {
                "batch_size": self.collection.batch_size,
                "max_concurrent": self.collection.max_concurrent,
                "quality_threshold": self.collection.quality_threshold,
            },
            "storage": {
                "database_url": self.storage.database_url,
                "pool_size": self.storage.pool_size,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "backend": self.cache.backend,
                "ttl": self.cache.ttl,
            },
            "logging": {
                "level": self.logging.level,
            },
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatacenterConfig":
        """Create from dictionary."""
        sources = {}
        for source_id, source_data in data.get("sources", {}).items():
            if isinstance(source_data, dict):
                sources[source_id] = SourceSettings(**source_data)
        
        collection_data = data.get("collection", {})
        collection = CollectionSettings(**collection_data) if collection_data else CollectionSettings()
        
        storage_data = data.get("storage", {})
        storage = StorageSettings(**storage_data) if storage_data else StorageSettings()
        
        cache_data = data.get("cache", {})
        cache = CacheSettings(**cache_data) if cache_data else CacheSettings()
        
        logging_data = data.get("logging", {})
        log_settings = LoggingSettings(**logging_data) if logging_data else LoggingSettings()
        
        return cls(
            version=data.get("version", "1.0"),
            sources=sources,
            collection=collection,
            storage=storage,
            cache=cache,
            logging=log_settings,
            metadata=data.get("metadata", {}),
        )


def load_config(
    config_path: str | Path | None = None,
    env_prefix: str = "DATACENTER_",
) -> DatacenterConfig:
    """
    Load configuration from file and environment.
    
    Args:
        config_path: Path to config file (YAML or JSON)
        env_prefix: Environment variable prefix
        
    Returns:
        Loaded configuration
    """
    config_data: dict[str, Any] = {}
    
    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix in (".yaml", ".yml"):
                    config_data = yaml.safe_load(f) or {}
                elif path.suffix == ".json":
                    config_data = json.load(f)
                else:
                    logger.warning(f"Unknown config format: {path.suffix}")
    
    _apply_env_overrides(config_data, env_prefix)
    
    return DatacenterConfig.from_dict(config_data)


def _apply_env_overrides(config: dict[str, Any], prefix: str) -> None:
    """Apply environment variable overrides to config."""
    env_mappings = {
        f"{prefix}DATABASE_URL": ("storage", "database_url"),
        f"{prefix}LOG_LEVEL": ("logging", "level"),
        f"{prefix}BATCH_SIZE": ("collection", "batch_size"),
        f"{prefix}CACHE_TTL": ("cache", "ttl"),
    }
    
    for env_var, config_path in env_mappings.items():
        value = os.environ.get(env_var)
        if value:
            section, key = config_path
            if section not in config:
                config[section] = {}
            config[section][key] = value


_global_config: DatacenterConfig | None = None


def get_config() -> DatacenterConfig:
    """Get the global configuration."""
    global _global_config
    if _global_config is None:
        config_path = os.environ.get("DATACENTER_CONFIG", "config/datacenter.yaml")
        _global_config = load_config(config_path)
    return _global_config


def set_config(config: DatacenterConfig) -> None:
    """Set the global configuration."""
    global _global_config
    _global_config = config


def create_default_config() -> DatacenterConfig:
    """Create a default configuration with common sources."""
    config = DatacenterConfig(
        version="1.0",
        sources={
            "eastmoney": SourceSettings(
                enabled=True,
                base_url="http://push2.eastmoney.com",
                timeout=30.0,
                rate_limit=10.0,
            ),
            "tushare": SourceSettings(
                enabled=True,
                base_url="https://api.tushare.pro",
                api_key="${TUSHARE_TOKEN}",
                timeout=30.0,
                rate_limit=5.0,
            ),
            "akshare": SourceSettings(
                enabled=True,
                timeout=30.0,
                rate_limit=5.0,
            ),
            "jinshi": SourceSettings(
                enabled=True,
                base_url="https://flash-api.jin10.com",
                timeout=30.0,
                rate_limit=10.0,
            ),
            "cls": SourceSettings(
                enabled=True,
                base_url="https://www.cls.cn",
                timeout=30.0,
                rate_limit=10.0,
            ),
        },
    )
    return config
