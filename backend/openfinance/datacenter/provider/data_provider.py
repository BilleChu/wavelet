"""
Real data provider for stock information.

Supports Tushare and Akshare as data sources.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from openfinance.datacenter.provider.config import DataSourceConfig, DataSourceType

logger = logging.getLogger(__name__)


class DataProviderError(Exception):
    """Exception raised when data provider fails."""
    pass


class BaseDataProvider(ABC):
    """Abstract base class for data providers."""
    
    def __init__(self, config: DataSourceConfig) -> None:
        self.config = config
        self._client: Any = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the data provider client."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the data provider client."""
        pass
    
    @abstractmethod
    async def get_stock_quote(self, code: str) -> dict[str, Any]:
        """Get real-time stock quote."""
        pass
    
    @abstractmethod
    async def get_stock_valuation(self, code: str) -> dict[str, Any]:
        """Get stock valuation metrics."""
        pass
    
    @abstractmethod
    async def get_stock_fundamental(self, code: str, period: str = "latest") -> dict[str, Any]:
        """Get stock fundamental data."""
        pass
    
    @abstractmethod
    async def search_stocks(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search stocks by keyword."""
        pass


class TushareProvider(BaseDataProvider):
    """Tushare data provider implementation."""
    
    async def initialize(self) -> None:
        try:
            import tushare as ts
            ts.set_token(self.config.api_key)
            self._client = ts.pro_api()
            logger.info("Tushare provider initialized successfully")
        except ImportError:
            raise DataProviderError("Tushare package not installed. Run: pip install tushare")
        except Exception as e:
            raise DataProviderError(f"Failed to initialize Tushare: {e}")
    
    async def close(self) -> None:
        self._client = None
    
    async def get_stock_quote(self, code: str) -> dict[str, Any]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            ts_code = self._format_ts_code(code)
            df = self._client.daily(ts_code=ts_code, trade_date=datetime.now().strftime("%Y%m%d"))
            
            if df.empty:
                raise DataProviderError(f"No quote data found for {code}")
            
            row = df.iloc[0]
            return {
                "code": code,
                "name": await self._get_stock_name(code),
                "price": float(row["close"]),
                "change": float(row["change"]),
                "change_pct": float(row["pct_chg"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "volume": int(row["vol"]) * 100,
                "amount": float(row["amount"]) * 1000,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {code}: {e}")
            raise DataProviderError(f"Failed to get quote: {e}")
    
    async def get_stock_valuation(self, code: str) -> dict[str, Any]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            ts_code = self._format_ts_code(code)
            df = self._client.daily_basic(ts_code=ts_code, trade_date=datetime.now().strftime("%Y%m%d"))
            
            if df.empty:
                raise DataProviderError(f"No valuation data found for {code}")
            
            row = df.iloc[0]
            return {
                "code": code,
                "name": await self._get_stock_name(code),
                "pe_ratio": float(row["pe"]) if row["pe"] else None,
                "pb_ratio": float(row["pb"]) if row["pb"] else None,
                "ps_ratio": float(row["ps"]) if row["ps"] else None,
                "market_cap": float(row["total_mv"]) * 100000000 if row["total_mv"] else None,
                "circulating_market_cap": float(row["circ_mv"]) * 100000000 if row["circ_mv"] else None,
                "total_shares": float(row["total_share"]) * 10000 if row["total_share"] else None,
                "float_shares": float(row["float_share"]) * 10000 if row["float_share"] else None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get valuation for {code}: {e}")
            raise DataProviderError(f"Failed to get valuation: {e}")
    
    async def get_stock_fundamental(self, code: str, period: str = "latest") -> dict[str, Any]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            ts_code = self._format_ts_code(code)
            
            income_df = self._client.income(ts_code=ts_code, periods=1 if period == "latest" else None)
            indicator_df = self._client.fina_indicator(ts_code=ts_code, periods=1 if period == "latest" else None)
            
            result = {
                "code": code,
                "name": await self._get_stock_name(code),
                "period": period,
                "timestamp": datetime.now().isoformat(),
            }
            
            if not income_df.empty:
                row = income_df.iloc[0]
                result.update({
                    "revenue": float(row["revenue"]) if row["revenue"] else None,
                    "net_profit": float(row["n_income"]) if row["n_income"] else None,
                    "gross_profit": float(row["total_profit"]) if row["total_profit"] else None,
                })
            
            if not indicator_df.empty:
                row = indicator_df.iloc[0]
                result.update({
                    "roe": float(row["roe"]) if row["roe"] else None,
                    "roa": float(row["roa"]) if row["roa"] else None,
                    "gross_margin": float(row["grossprofit_margin"]) if row["grossprofit_margin"] else None,
                    "net_margin": float(row["netprofit_margin"]) if row["netprofit_margin"] else None,
                    "debt_ratio": float(row["debt_to_assets"]) if row["debt_to_assets"] else None,
                })
            
            return result
        except Exception as e:
            logger.error(f"Failed to get fundamental for {code}: {e}")
            raise DataProviderError(f"Failed to get fundamental: {e}")
    
    async def search_stocks(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            df = self._client.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,market,list_date")
            
            mask = df["name"].str.contains(keyword, na=False) | df["symbol"].str.contains(keyword, na=False)
            filtered = df[mask].head(limit)
            
            return [
                {
                    "code": row["symbol"],
                    "ts_code": row["ts_code"],
                    "name": row["name"],
                    "industry": row["industry"],
                    "market": row["market"],
                }
                for _, row in filtered.iterrows()
            ]
        except Exception as e:
            logger.error(f"Failed to search stocks with keyword {keyword}: {e}")
            raise DataProviderError(f"Failed to search stocks: {e}")
    
    async def _get_stock_name(self, code: str) -> str:
        try:
            ts_code = self._format_ts_code(code)
            df = self._client.stock_basic(ts_code=ts_code, fields="name")
            if not df.empty:
                return df.iloc[0]["name"]
        except Exception:
            pass
        return f"股票{code}"
    
    def _format_ts_code(self, code: str) -> str:
        if "." in code:
            return code
        if code.startswith("6"):
            return f"{code}.SH"
        return f"{code}.SZ"


class AkshareProvider(BaseDataProvider):
    """Akshare data provider implementation."""
    
    async def initialize(self) -> None:
        try:
            import akshare as ak
            self._client = ak
            logger.info("Akshare provider initialized successfully")
        except ImportError:
            raise DataProviderError("Akshare package not installed. Run: pip install akshare")
        except Exception as e:
            raise DataProviderError(f"Failed to initialize Akshare: {e}")
    
    async def close(self) -> None:
        self._client = None
    
    async def get_stock_quote(self, code: str) -> dict[str, Any]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            df = self._client.stock_zh_a_spot_em()
            row = df[df["代码"] == code]
            
            if row.empty:
                raise DataProviderError(f"No quote data found for {code}")
            
            data = row.iloc[0]
            return {
                "code": code,
                "name": data["名称"],
                "price": float(data["最新价"]),
                "change": float(data["涨跌额"]),
                "change_pct": float(data["涨跌幅"]),
                "open": float(data["今开"]),
                "high": float(data["最高"]),
                "low": float(data["最低"]),
                "volume": int(data["成交量"]),
                "amount": float(data["成交额"]),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {code}: {e}")
            raise DataProviderError(f"Failed to get quote: {e}")
    
    async def get_stock_valuation(self, code: str) -> dict[str, Any]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            df = self._client.stock_a_lg_indicator(symbol=code)
            
            if df.empty:
                raise DataProviderError(f"No valuation data found for {code}")
            
            row = df.iloc[0]
            return {
                "code": code,
                "pe_ratio": float(row["pe"]) if "pe" in row and row["pe"] else None,
                "pb_ratio": float(row["pb"]) if "pb" in row and row["pb"] else None,
                "market_cap": float(row["total_mv"]) if "total_mv" in row and row["total_mv"] else None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get valuation for {code}: {e}")
            raise DataProviderError(f"Failed to get valuation: {e}")
    
    async def get_stock_fundamental(self, code: str, period: str = "latest") -> dict[str, Any]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            df = self._client.stock_financial_analysis_indicator(symbol=code)
            
            if df.empty:
                raise DataProviderError(f"No fundamental data found for {code}")
            
            row = df.iloc[0]
            return {
                "code": code,
                "period": row["日期"] if "日期" in row else period,
                "roe": float(row["净资产收益率"]) if "净资产收益率" in row and row["净资产收益率"] else None,
                "gross_margin": float(row["销售毛利率"]) if "销售毛利率" in row and row["销售毛利率"] else None,
                "net_margin": float(row["销售净利率"]) if "销售净利率" in row and row["销售净利率"] else None,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get fundamental for {code}: {e}")
            raise DataProviderError(f"Failed to get fundamental: {e}")
    
    async def search_stocks(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self._client:
            raise DataProviderError("Provider not initialized")
        
        try:
            df = self._client.stock_zh_a_spot_em()
            
            mask = df["名称"].str.contains(keyword, na=False) | df["代码"].str.contains(keyword, na=False)
            filtered = df[mask].head(limit)
            
            return [
                {
                    "code": row["代码"],
                    "name": row["名称"],
                }
                for _, row in filtered.iterrows()
            ]
        except Exception as e:
            logger.error(f"Failed to search stocks with keyword {keyword}: {e}")
            raise DataProviderError(f"Failed to search stocks: {e}")


class MockProvider(BaseDataProvider):
    """Mock data provider for development and testing."""
    
    def __init__(self, config: DataSourceConfig) -> None:
        super().__init__(config)
        self._mock_data = {
            "600000": {
                "name": "浦发银行",
                "industry": "银行",
                "market": "上海",
            },
            "000001": {
                "name": "平安银行",
                "industry": "银行",
                "market": "深圳",
            },
            "600519": {
                "name": "贵州茅台",
                "industry": "白酒",
                "market": "上海",
            },
        }
    
    async def initialize(self) -> None:
        logger.warning("Using MOCK data provider - NOT suitable for production!")
    
    async def close(self) -> None:
        pass
    
    async def get_stock_quote(self, code: str) -> dict[str, Any]:
        import random
        base_price = random.uniform(10, 100)
        change = random.uniform(-5, 5)
        
        return {
            "code": code,
            "name": self._mock_data.get(code, {}).get("name", f"股票{code}"),
            "price": round(base_price, 2),
            "change": round(change, 2),
            "change_pct": round(change / base_price * 100, 2),
            "open": round(base_price * 0.98, 2),
            "high": round(base_price * 1.02, 2),
            "low": round(base_price * 0.97, 2),
            "volume": random.randint(100000, 10000000),
            "amount": round(base_price * random.randint(100000, 10000000), 2),
            "timestamp": datetime.now().isoformat(),
            "_mock": True,
        }
    
    async def get_stock_valuation(self, code: str) -> dict[str, Any]:
        import random
        
        return {
            "code": code,
            "name": self._mock_data.get(code, {}).get("name", f"股票{code}"),
            "pe_ratio": round(random.uniform(5, 30), 2),
            "pb_ratio": round(random.uniform(0.5, 5), 2),
            "ps_ratio": round(random.uniform(1, 10), 2),
            "market_cap": round(random.uniform(100, 10000) * 1e8, 2),
            "timestamp": datetime.now().isoformat(),
            "_mock": True,
        }
    
    async def get_stock_fundamental(self, code: str, period: str = "latest") -> dict[str, Any]:
        import random
        
        return {
            "code": code,
            "name": self._mock_data.get(code, {}).get("name", f"股票{code}"),
            "period": period,
            "revenue": round(random.uniform(100, 10000), 2),
            "net_profit": round(random.uniform(10, 1000), 2),
            "roe": round(random.uniform(5, 25), 2),
            "gross_margin": round(random.uniform(20, 60), 2),
            "net_margin": round(random.uniform(5, 30), 2),
            "timestamp": datetime.now().isoformat(),
            "_mock": True,
        }
    
    async def search_stocks(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        results = []
        for code, data in self._mock_data.items():
            if keyword.lower() in data["name"].lower() or keyword in code:
                results.append({
                    "code": code,
                    "name": data["name"],
                    "industry": data["industry"],
                })
        return results[:limit]


def create_data_provider(config: DataSourceConfig) -> BaseDataProvider:
    """Create a data provider based on configuration."""
    providers = {
        DataSourceType.TUSHARE: TushareProvider,
        DataSourceType.AKSHARE: AkshareProvider,
        DataSourceType.MOCK: MockProvider,
    }
    
    provider_class = providers.get(config.type)
    if not provider_class:
        raise DataProviderError(f"Unknown data source type: {config.type}")
    
    return provider_class(config)
