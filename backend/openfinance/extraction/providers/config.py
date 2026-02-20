"""
Data source configuration for OpenFinance.

Provides configuration for external data providers.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DataSourceType(str, Enum):
    """Supported data source types."""
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"
    MOCK = "mock"


@dataclass
class DataSourceConfig:
    """Configuration for a data source."""
    type: DataSourceType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True


def get_data_source_config() -> DataSourceConfig:
    """Get the primary data source configuration from environment."""
    tushare_token = os.getenv("TUSHARE_TOKEN", "")
    akshare_token = os.getenv("AKSHARE_TOKEN", "")
    
    if tushare_token:
        return DataSourceConfig(
            type=DataSourceType.TUSHARE,
            api_key=tushare_token,
            base_url="https://api.tushare.pro",
        )
    
    if akshare_token:
        return DataSourceConfig(
            type=DataSourceType.AKSHARE,
            api_key=akshare_token,
        )
    
    return DataSourceConfig(
        type=DataSourceType.MOCK,
        enabled=True,
    )


def get_fallback_config() -> Optional[DataSourceConfig]:
    """Get fallback data source configuration."""
    tushare_token = os.getenv("TUSHARE_TOKEN", "")
    akshare_token = os.getenv("AKSHARE_TOKEN", "")
    
    primary = get_data_source_config()
    
    if primary.type == DataSourceType.TUSHARE and akshare_token:
        return DataSourceConfig(
            type=DataSourceType.AKSHARE,
            api_key=akshare_token,
        )
    
    if primary.type == DataSourceType.AKSHARE and tushare_token:
        return DataSourceConfig(
            type=DataSourceType.TUSHARE,
            api_key=tushare_token,
            base_url="https://api.tushare.pro",
        )
    
    return None
