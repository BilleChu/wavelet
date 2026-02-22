"""
Market data collectors migrated from qstock trade.py.

This module provides collectors for real-time market data, K-line data,
intraday data, and other trading-related information.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from ..core.base_collector import (
    CollectionConfig,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    StockQuoteData,
    StockData,
)
from ..quant_collector import MarketDataCollector
from ...core import safe_float, safe_int, CodeUtils

logger = logging.getLogger(__name__)


class MarketRealtimeCollector(MarketDataCollector):
    """
    Collector for real-time market data from EastMoney.
    Migrated from qstock trade.py market_realtime function.
    """

    MARKET_CODES = {
        "沪深A": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23",
        "上证A": "m:1 t:2,m:1 t:23",
        "沪A": "m:1 t:2,m:1 t:23",
        "深证A": "m:0 t:6,m:0 t:80",
        "深A": "m:0 t:6,m:0 t:80",
        "北证A": "m:0 t:81 s:2048",
        "北A": "m:0 t:81 s:2048",
        "创业板": "m:0 t:80",
        "科创板": "m:1 t:23",
        "沪深京A": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "沪股通": "b:BK0707",
        "深股通": "b:BK0804",
        "风险警示板": "m:0 f:4,m:1 f:4",
        "新股": "m:0 f:8,m:1 f:8",
        "美股": "m:105,m:106,m:107",
        "港股": "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
        "中概股": "b:MK0201",
        "行业板块": "m:90 t:2 f:!50",
        "概念板块": "m:90 t:3 f:!50",
        "沪深指数": "m:1 s:2,m:0 t:5",
        "上证指数": "m:1 s:2",
        "深证指数": "m:0 t:5",
        "可转债": "b:MK0354",
        "期货": "m:113,m:114,m:115,m:8,m:142",
        "ETF": "b:MK0021,b:MK0022,b:MK0023,b:MK0024",
        "LOF": "b:MK0404,b:MK0405,b:MK0406,b:MK0407",
    }

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_QUOTE_REALTIME,
                category=DataCategory.MARKET,
                frequency=DataFrequency.TICK,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[StockQuoteData]:
        market = kwargs.get("market", "沪深A")
        return await self._collect_market_realtime(market)

    async def _collect_market_realtime(self, market: str) -> list[StockQuoteData]:
        import aiohttp

        fs = self.MARKET_CODES.get(market, self.MARKET_CODES["沪深A"])

        fields = (
            "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,"
            "f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f140,f141,f207,"
            "f208,f209,f222,f225,f239,f240,f241,f242,f243,f244,f245,"
            "f246,f247,f248,f250,f251,f252,f253,f254,f255,f256"
        )

        url = "http://push2.eastmoney.com/api/qt/clist/get"
        
        page_size = 100
        all_records = []
        page = 1
        
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    "pn": str(page),
                    "pz": str(page_size),
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": fs,
                    "fields": fields,
                }
                
                async with session.get(url, params=params) as response:
                    data = await response.json()

                if not data.get("data") or not data["data"].get("diff"):
                    break
                
                total = data["data"].get("total", 0)
                diff = data["data"].get("diff", [])
                
                for item in diff:
                    try:
                        record = StockQuoteData(
                            code=item.get("f12", ""),
                            name=item.get("f14", ""),
                            trade_date=datetime.now().strftime("%Y-%m-%d"),
                            open=safe_float(item.get("f17")),
                            high=safe_float(item.get("f15")),
                            low=safe_float(item.get("f16")),
                            close=safe_float(item.get("f2")),
                            pre_close=safe_float(item.get("f18")),
                            change=safe_float(item.get("f4")),
                            change_pct=safe_float(item.get("f3")),
                            volume=safe_int(item.get("f5")),
                            amount=safe_float(item.get("f6")),
                            turnover_rate=safe_float(item.get("f8")),
                            amplitude=safe_float(item.get("f7")),
                        )
                        all_records.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to parse record: {e}")
                
                logger.info(f"Page {page}: collected {len(diff)} records, total: {len(all_records)}/{total}")
                
                if len(all_records) >= total:
                    break
                
                page += 1

        logger.info(f"Collected {len(all_records)} records for market {market}")
        return all_records


class StockRealtimeCollector(MarketDataCollector):
    """
    Collector for real-time stock data.
    Migrated from qstock trade.py stock_realtime function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_QUOTE_REALTIME,
                category=DataCategory.MARKET,
                frequency=DataFrequency.TICK,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[StockQuoteData]:
        codes = kwargs.get("codes", self.config.symbols)
        if isinstance(codes, str):
            codes = [codes]
        return await self._collect_stock_realtime(codes)

    async def _collect_stock_realtime(self, codes: list[str]) -> list[StockQuoteData]:
        import aiohttp

        secids = [CodeUtils.to_eastmoney_format(code) for code in codes]

        fields = (
            "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,"
            "f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f140,f141,f207,"
            "f208,f209,f222,f225,f239,f240,f241,f242,f243,f244,f245,"
            "f246,f247,f248,f250,f251,f252,f253,f254,f255,f256"
        )

        params = {
            "OSVersion": "14.3",
            "appVersion": "6.3.8",
            "fields": fields,
            "fltt": "2",
            "plat": "Iphone",
            "product": "EFund",
            "secids": ",".join(secids),
            "serverVersion": "6.3.6",
            "version": "6.3.8",
        }

        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                try:
                    record = StockQuoteData(
                        code=item.get("f12", ""),
                        name=item.get("f14", ""),
                        trade_date=datetime.now().strftime("%Y-%m-%d"),
                        open=safe_float(item.get("f17")),
                        high=safe_float(item.get("f15")),
                        low=safe_float(item.get("f16")),
                        close=safe_float(item.get("f2")),
                        pre_close=safe_float(item.get("f18")),
                        change=safe_float(item.get("f4")),
                        change_pct=safe_float(item.get("f3")),
                        volume=safe_int(item.get("f5")),
                        amount=safe_float(item.get("f6")),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse record: {e}")

        return records


class KLineCollector(MarketDataCollector):
    """
    Collector for historical K-line data.
    Migrated from qstock trade.py web_data function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_QUOTE,
                category=DataCategory.MARKET,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[StockQuoteData]:
        symbols = kwargs.get("symbols", self.config.symbols)
        start_date = kwargs.get("start_date", self.config.start_date)
        end_date = kwargs.get("end_date", self.config.end_date)
        freq = kwargs.get("freq", "d")
        fqt = kwargs.get("fqt", 1)

        if isinstance(symbols, str):
            symbols = [symbols]

        all_records = []
        for symbol in symbols:
            records = await self._collect_kline(symbol, start_date, end_date, freq, fqt)
            all_records.extend(records)

        return all_records

    async def _collect_kline(
        self,
        code: str,
        start_date: str | None,
        end_date: str | None,
        freq: str = "d",
        fqt: int = 1,
    ) -> list[StockQuoteData]:
        import aiohttp

        code_id = CodeUtils.to_eastmoney_format(code)

        freq_map = {"d": 101, "w": 102, "m": 103, "1": 1, "5": 5, "15": 15, "30": 30, "60": 60}
        klt = freq_map.get(freq.lower(), 101)

        start = start_date.replace("-", "") if start_date else "19000101"
        end = end_date.replace("-", "") if end_date else datetime.now().strftime("%Y%m%d")

        fields = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"

        params = {
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": fields,
            "beg": start,
            "end": end,
            "rtntype": "6",
            "secid": code_id,
            "klt": str(klt),
            "fqt": str(fqt),
        }

        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data") and data["data"].get("klines"):
            name = data["data"].get("name", "")
            for kline in data["data"]["klines"]:
                try:
                    parts = kline.split(",")
                    record = StockQuoteData(
                        code=code,
                        name=name,
                        trade_date=parts[0],
                        open=safe_float(parts[1]) if len(parts) > 1 else None,
                        close=safe_float(parts[2]) if len(parts) > 2 else None,
                        high=safe_float(parts[3]) if len(parts) > 3 else None,
                        low=safe_float(parts[4]) if len(parts) > 4 else None,
                        volume=safe_int(parts[5]) if len(parts) > 5 else None,
                        amount=safe_float(parts[6]) if len(parts) > 6 else None,
                        amplitude=safe_float(parts[7]) if len(parts) > 7 else None,
                        change_pct=safe_float(parts[8]) if len(parts) > 8 else None,
                        turnover_rate=safe_float(parts[9]) if len(parts) > 9 else None,
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse kline: {e}")

        return records


class IntradayDataCollector(MarketDataCollector):
    """
    Collector for intraday tick data.
    Migrated from qstock trade.py intraday_data function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_QUOTE_INTRADAY,
                category=DataCategory.MARKET,
                frequency=DataFrequency.TICK,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[StockData]:
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_intraday(code)

    async def _collect_intraday(self, code: str) -> list[StockData]:
        import aiohttp

        code_id = CodeUtils.to_eastmoney_format(code)

        params = {
            "secid": code_id,
            "fields1": "f1,f2,f3,f4,f5",
            "fields2": "f51,f52,f53,f54,f55",
            "pos": "-10000000",
        }

        url = "https://push2.eastmoney.com/api/qt/stock/details/get"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data") and data["data"].get("details"):
            pre_price = data["data"].get("prePrice", 0)
            for detail in data["data"]["details"]:
                try:
                    parts = detail.split(",")
                    if len(parts) >= 4:
                        record = StockData(
                            code=code,
                            name="",
                            market="SH" if code.startswith("6") else "SZ",
                            price=safe_float(parts[1]),
                            volume=safe_int(parts[2]),
                            timestamp=datetime.strptime(
                                f"{datetime.now().strftime('%Y-%m-%d')} {parts[0]}",
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        )
                        records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse intraday detail: {e}")

        return records

    def _get_record_hash(self, record: StockData) -> str:
        return f"{record.code}_{record.timestamp.isoformat()}"

    async def _is_valid(self, record: StockData) -> bool:
        if not record.code:
            return False
        if record.price is not None and record.price < 0:
            return False
        return True


class StockBillboardCollector(MarketDataCollector):
    """
    Collector for dragon-tiger list data.
    Migrated from qstock trade.py stock_billboard function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.DRAGON_TIGER,
                category=DataCategory.MARKET,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        start = kwargs.get("start_date")
        end = kwargs.get("end_date")
        return await self._collect_billboard(start, end)

    async def _collect_billboard(
        self, start_date: str | None, end_date: str | None
    ) -> list[dict[str, Any]]:
        import aiohttp

        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        params = {
            "sortColumns": "TRADE_DATE,SECURITY_CODE",
            "sortTypes": "-1,1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_DAILYBILLBOARD_DETAILS",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f"(TRADE_DATE<='{end_date}')(TRADE_DATE>='{start_date}')",
        }

        url = "http://datacenter-web.eastmoney.com/api/data/v1/get"

        records = []
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["pageNumber"] = str(page)
                async with session.get(url, params=params) as response:
                    data = await response.json()

                if not data.get("result") or not data["result"].get("data"):
                    break

                for item in data["result"]["data"]:
                    records.append({
                        "code": item.get("SECURITY_CODE"),
                        "name": item.get("SECURITY_NAME_ABBR"),
                        "trade_date": item.get("TRADE_DATE", "").split()[0] if item.get("TRADE_DATE") else None,
                        "close": item.get("CLOSE_PRICE"),
                        "change_pct": item.get("CHANGE_RATE"),
                        "turnover_rate": item.get("TURNOVERRATE"),
                        "net_buy": item.get("BILLBOARD_NET_AMT"),
                        "reason": item.get("EXPLANATION"),
                    })

                page += 1
                if page > data["result"].get("pages", 1):
                    break

        return records


class IndexMemberCollector(MarketDataCollector):
    """
    Collector for index constituent stocks.
    Migrated from qstock trade.py index_member function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.INDEX_MEMBER,
                category=DataCategory.MARKET,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_index_member(code)

    async def _collect_index_member(self, code: str) -> list[dict[str, Any]]:
        import aiohttp

        code_id = CodeUtils.to_eastmoney_format(code).split(".")[1]

        params = {
            "IndexCode": code_id,
            "pageIndex": "1",
            "pageSize": "10000",
            "deviceid": "1234567890",
            "version": "6.9.9",
            "product": "EFund",
            "plat": "Iphone",
            "ServerVersion": "6.9.9",
        }

        url = "https://fundztapi.eastmoney.com/FundSpecialApiNew/FundSpecialZSB30ZSCFG"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("Datas"):
            for item in data["Datas"]:
                records.append({
                    "index_code": item.get("IndexCode"),
                    "index_name": item.get("IndexName"),
                    "stock_code": item.get("StockCode"),
                    "stock_name": item.get("StockName"),
                    "weight": item.get("MARKETCAPPCT"),
                })

        return records
