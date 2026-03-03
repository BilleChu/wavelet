"""
Hong Kong Stock market data collectors using EastMoney.

This module provides collectors for HK stock market data including
real-time quotes, historical K-lines, financial statements, and money flow.
"""

import json
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
)
from ..quant_collector import MarketDataCollector
from ...core import safe_float, safe_int

logger = logging.getLogger(__name__)


class HKStockListCollector(MarketDataCollector):
    """
    Collector for HK stock list from EastMoney.
    使用东方财富获取港股列表。
    """

    MARKET_CODES = {
        "港股": "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
        "港股主板": "m:128 t:3,m:128 t:4",
        "港股创业板": "m:128 t:1,m:128 t:2",
    }

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_QUOTE_REALTIME,
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
        market = kwargs.get("market", "港股")
        return await self._collect_stock_list(market)

    async def _collect_stock_list(self, market: str) -> list[StockQuoteData]:
        import aiohttp

        fs = self.MARKET_CODES.get(market, self.MARKET_CODES["港股"])

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

        logger.info(f"Collected {len(all_records)} records for HK market {market}")
        return all_records


class HKStockQuoteCollector(MarketDataCollector):
    """
    Collector for HK stock historical quotes.
    使用东方财富获取港股历史行情。
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

        if isinstance(symbols, str):
            symbols = [symbols]

        return await self._collect_quotes(symbols, start_date, end_date)

    async def _collect_quotes(
        self,
        symbols: list[str],
        start_date: str | None,
        end_date: str | None
    ) -> list[StockQuoteData]:
        import aiohttp

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        start = start_date.replace("-", "")
        end = end_date.replace("-", "")

        fields = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"

        records = []
        async with aiohttp.ClientSession() as session:
            for symbol in symbols:
                try:
                    code_id = f"116.{symbol}" if symbol.startswith("0") else f"116.{symbol}"

                    params = {
                        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                        "fields2": fields,
                        "beg": start,
                        "end": end,
                        "rtntype": "6",
                        "secid": code_id,
                        "klt": "101",
                        "fqt": "1",
                    }

                    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

                    async with session.get(url, params=params) as response:
                        text = await response.text()
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON from eastmoney API: {text[:200]}")
                            continue

                    if data.get("data") and data["data"].get("klines"):
                        name = data["data"].get("name", "")
                        for kline in data["data"]["klines"]:
                            try:
                                parts = kline.split(",")
                                record = StockQuoteData(
                                    code=symbol,
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

                except Exception as e:
                    logger.warning(f"Failed to collect quotes for {symbol}: {e}")

        return records


class HKMoneyFlowCollector(MarketDataCollector):
    """
    Collector for HK stock money flow data.
    使用东方财富获取港股资金流向数据。
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_MONEY_FLOW,
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
        return await self._collect_money_flow()

    async def _collect_money_flow(self) -> list[dict[str, Any]]:
        import aiohttp

        url = "http://push2.eastmoney.com/api/qt/clist/get"

        params = {
            "pn": "1",
            "pz": "500",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:128 t:3,m:128 t:4,m:128 t:1,m:128 t:2",
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f62,f66,f69,f72,f74,f75,f76,f77,f78",
        }

        records = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    try:
                        records.append({
                            "code": item.get("f12", ""),
                            "name": item.get("f14", ""),
                            "trade_date": datetime.now().strftime("%Y-%m-%d"),
                            "main_net_inflow": safe_float(item.get("f66")),
                            "main_net_inflow_pct": safe_float(item.get("f69")),
                            "super_large_net_inflow": safe_float(item.get("f72")),
                            "large_net_inflow": safe_float(item.get("f75")),
                            "medium_net_inflow": safe_float(item.get("f78")),
                            "small_net_inflow": safe_float(item.get("f84")),
                        })
                    except Exception as e:
                        logger.warning(f"Failed to parse money flow record: {e}")

        return records


class HKFinancialStatementCollector(MarketDataCollector):
    """
    Collector for HK stock financial statements.
    使用东方财富获取港股财务报表。
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_FINANCIAL_REPORT,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.QUARTERLY,
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
        symbols = kwargs.get("symbols", self.config.symbols)
        if isinstance(symbols, str):
            symbols = [symbols]

        return await self._collect_financials(symbols)

    async def _collect_financials(self, symbols: list[str]) -> list[dict[str, Any]]:
        import aiohttp

        records = []
        async with aiohttp.ClientSession() as session:
            for symbol in symbols:
                try:
                    code_id = f"116.{symbol}" if symbol.startswith("0") else f"116.{symbol}"

                    url = "https://emweb.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
                    params = {
                        "companyType": "4",
                        "reportDateType": "0",
                        "code": code_id,
                        "dataType": "1",
                    }
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://emweb.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                    }

                    async with session.get(url, params=params, headers=headers) as response:
                        data = await response.json()

                    if data.get("data") and data["data"].get("lr"):
                        for item in data["data"]["lr"]:
                            records.append({
                                "symbol": symbol,
                                "statement_type": "income",
                                "report_date": item.get("date"),
                                "total_revenue": safe_float(item.get("yysr")),
                                "operating_revenue": safe_float(item.get("yysr")),
                                "operating_profit": safe_float(item.get("yylr")),
                                "net_profit": safe_float(item.get("jlr")),
                                "net_profit_attr_parent": safe_float(item.get("gsjlr")),
                                "basic_eps": safe_float(item.get("mgde")),
                            })

                except Exception as e:
                    logger.warning(f"Failed to collect financials for {symbol}: {e}")

        return records
