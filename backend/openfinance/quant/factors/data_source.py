"""
Factor Data Source Module.

Provides data access layer for factor calculations.
Integrates with the datacenter module for K-Line data.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np

from openfinance.datacenter.models.analytical import ADSKLineModel

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """Data source configuration."""
    
    source_type: str = "datacenter"
    cache_enabled: bool = True
    cache_ttl: int = 300
    max_retries: int = 3
    retry_delay: float = 0.5


class KLineDataSource(ABC):
    """Abstract base class for K-Line data sources."""
    
    @abstractmethod
    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs: Any,
    ) -> list[ADSKLineModel]:
        """Get K-Line data for a stock."""
        pass
    
    @abstractmethod
    async def get_latest_klines(
        self,
        code: str,
        count: int,
    ) -> list[ADSKLineModel]:
        """Get latest N K-Lines for a stock."""
        pass
    
    @abstractmethod
    async def get_klines_batch(
        self,
        codes: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, list[ADSKLineModel]]:
        """Get K-Line data for multiple stocks."""
        pass


class DataCenterDataSource(KLineDataSource):
    """
    Data source using the datacenter module.
    
    Provides access to K-Line data from the ADS (Analytical Data Store).
    """
    
    def __init__(self, config: DataSourceConfig | None = None):
        self.config = config or DataSourceConfig()
        self._datacenter = None
    
    def _get_datacenter(self):
        """Get datacenter instance (lazy initialization)."""
        if self._datacenter is None:
            try:
                from openfinance.datacenter.models.analytical import get_ads_client
                self._datacenter = get_ads_client()
            except ImportError:
                logger.warning("Datacenter module not available")
        return self._datacenter
    
    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs: Any,
    ) -> list[ADSKLineModel]:
        """Get K-Line data for a stock."""
        datacenter = self._get_datacenter()
        
        if datacenter:
            try:
                klines = await datacenter.get_klines(
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                )
                return sorted(klines, key=lambda k: k.trade_date)
            except Exception as e:
                logger.error(f"Failed to get klines for {code}: {e}")
        
        return self._generate_mock_klines(code, start_date, end_date)
    
    async def get_latest_klines(
        self,
        code: str,
        count: int,
    ) -> list[ADSKLineModel]:
        """Get latest N K-Lines for a stock."""
        end_date = date.today()
        start_date = end_date - timedelta(days=count * 2)
        
        klines = await self.get_klines(code, start_date, end_date)
        
        if len(klines) > count:
            return klines[-count:]
        return klines
    
    async def get_klines_batch(
        self,
        codes: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, list[ADSKLineModel]]:
        """Get K-Line data for multiple stocks."""
        results = {}
        
        for code in codes:
            klines = await self.get_klines(code, start_date, end_date)
            if klines:
                results[code] = klines
        
        return results
    
    def _generate_mock_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
    ) -> list[ADSKLineModel]:
        """Generate mock K-Line data for testing."""
        import random
        
        klines = []
        current_date = start_date
        price = random.uniform(10, 100)
        
        while current_date <= end_date:
            if current_date.weekday() < 5:
                change = random.uniform(-0.03, 0.03)
                open_price = price
                close_price = price * (1 + change)
                high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
                low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
                volume = random.randint(100000, 10000000)
                
                kline = ADSKLineModel(
                    code=code,
                    trade_date=current_date,
                    open=round(open_price, 2),
                    high=round(high_price, 2),
                    low=round(low_price, 2),
                    close=round(close_price, 2),
                    volume=volume,
                    amount=volume * close_price,
                    pre_close=price,
                    turnover=random.uniform(0.5, 5.0),
                )
                klines.append(kline)
                
                price = close_price
            
            current_date += timedelta(days=1)
        
        return klines


class MockDataSource(KLineDataSource):
    """Mock data source for testing."""
    
    def __init__(self, config: DataSourceConfig | None = None):
        self.config = config or DataSourceConfig()
    
    async def get_klines(
        self,
        code: str,
        start_date: date,
        end_date: date,
        **kwargs: Any,
    ) -> list[ADSKLineModel]:
        """Generate mock K-Line data."""
        import random
        
        klines = []
        current_date = start_date
        price = random.uniform(10, 100)
        
        while current_date <= end_date:
            if current_date.weekday() < 5:
                change = random.uniform(-0.03, 0.03)
                open_price = price
                close_price = price * (1 + change)
                high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
                low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
                volume = random.randint(100000, 10000000)
                
                kline = ADSKLineModel(
                    code=code,
                    trade_date=current_date,
                    open=round(open_price, 2),
                    high=round(high_price, 2),
                    low=round(low_price, 2),
                    close=round(close_price, 2),
                    volume=volume,
                    amount=volume * close_price,
                    pre_close=price,
                    turnover=random.uniform(0.5, 5.0),
                )
                klines.append(kline)
                
                price = close_price
            
            current_date += timedelta(days=1)
        
        return klines
    
    async def get_latest_klines(
        self,
        code: str,
        count: int,
    ) -> list[ADSKLineModel]:
        """Get latest N mock K-Lines."""
        end_date = date.today()
        start_date = end_date - timedelta(days=count * 2)
        
        klines = await self.get_klines(code, start_date, end_date)
        return klines[-count:] if len(klines) > count else klines
    
    async def get_klines_batch(
        self,
        codes: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, list[ADSKLineModel]]:
        """Get mock K-Line data for multiple stocks."""
        results = {}
        for code in codes:
            klines = await self.get_klines(code, start_date, end_date)
            if klines:
                results[code] = klines
        return results


def create_data_source(
    config: DataSourceConfig | None = None,
) -> KLineDataSource:
    """Create a data source based on configuration."""
    config = config or DataSourceConfig()
    
    if config.source_type == "datacenter":
        return DataCenterDataSource(config)
    elif config.source_type == "mock":
        return MockDataSource(config)
    else:
        logger.warning(f"Unknown data source type: {config.source_type}, using mock")
        return MockDataSource(config)


_data_source: KLineDataSource | None = None


def get_data_source() -> KLineDataSource:
    """Get the global data source instance."""
    global _data_source
    if _data_source is None:
        _data_source = create_data_source()
    return _data_source
