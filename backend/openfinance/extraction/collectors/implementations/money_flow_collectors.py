"""
Money flow data collectors migrated from qstock money.py.

This module provides collectors for money flow data including
intraday money, daily money, north money, and sector money flow.
"""

import logging
from datetime import datetime
from typing import Any

from ..core.base_collector import (
    CollectionConfig,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    MoneyFlowData,
)
from ..quant_collector import MoneyFlowDataCollector

logger = logging.getLogger(__name__)


class IntradayMoneyFlowCollector(MoneyFlowDataCollector):
    """
    Collector for intraday money flow data.
    Migrated from qstock money.py intraday_money function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_MONEY_FLOW,
                category=DataCategory.MARKET,
                frequency=DataFrequency.MINUTE_1,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[MoneyFlowData]:
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_intraday_money(code)

    async def _collect_intraday_money(self, code: str) -> list[MoneyFlowData]:
        import aiohttp

        code_id = self._get_code_id(code)

        params = {
            "lmt": "0",
            "klt": "1",
            "secid": code_id,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        }

        url = "http://push2.eastmoney.com/api/qt/stock/fflow/kline/get"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data") and data["data"].get("klines"):
            name = data["data"].get("name", "")
            stock_code = code_id.split(".")[-1]

            for kline in data["data"]["klines"]:
                try:
                    parts = kline.split(",")
                    if len(parts) >= 6:
                        record = MoneyFlowData(
                            code=stock_code,
                            name=name,
                            trade_date=parts[0],
                            main_net_inflow=self._safe_float(parts[1]),
                            small_net_inflow=self._safe_float(parts[2]),
                            medium_net_inflow=self._safe_float(parts[3]),
                            large_net_inflow=self._safe_float(parts[4]),
                            super_large_net_inflow=self._safe_float(parts[5]),
                        )
                        records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse money flow: {e}")

        return records

    def _get_code_id(self, code: str) -> str:
        if code.isdigit():
            if code.startswith("6"):
                return f"1.{code}"
            else:
                return f"0.{code}"
        return f"0.{code}"

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class DailyMoneyFlowCollector(MoneyFlowDataCollector):
    """
    Collector for daily money flow data.
    Migrated from qstock money.py daily_money function.
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

    async def _collect(self, **kwargs: Any) -> list[MoneyFlowData]:
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_daily_money(code)

    async def _collect_daily_money(self, code: str) -> list[MoneyFlowData]:
        import aiohttp

        code_id = self._get_code_id(code)

        params = {
            "lmt": "30",
            "klt": "101",
            "secid": code_id,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        }

        url = "http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data") and data["data"].get("klines"):
            name = data["data"].get("name", "")
            stock_code = code_id.split(".")[-1]

            for kline in data["data"]["klines"]:
                try:
                    parts = kline.split(",")
                    if len(parts) >= 13:
                        record = MoneyFlowData(
                            code=stock_code,
                            name=name,
                            trade_date=parts[0],
                            main_net_inflow=self._safe_float(parts[1]),
                            small_net_inflow=self._safe_float(parts[2]),
                            medium_net_inflow=self._safe_float(parts[3]),
                            large_net_inflow=self._safe_float(parts[4]),
                            super_large_net_inflow=self._safe_float(parts[5]),
                            main_net_inflow_pct=self._safe_float(parts[6]),
                        )
                        records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse daily money flow: {e}")

        return records

    def _get_code_id(self, code: str) -> str:
        if code.isdigit():
            if code.startswith("6"):
                return f"1.{code}"
            else:
                return f"0.{code}"
        return f"0.{code}"

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class NorthMoneyCollector(MoneyFlowDataCollector):
    """
    Collector for north money (foreign investment) data.
    Migrated from qstock money.py north_money function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.NORTH_MONEY,
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
        flag = kwargs.get("flag", "北上")
        n = kwargs.get("n", 1)

        if flag == "个股":
            return await self._collect_north_money_stock(n)
        elif flag in ["行业", "概念", "地域"]:
            return await self._collect_north_money_sector(flag, n)
        else:
            return await self._collect_north_money_flow(flag)

    async def _collect_north_money_flow(self, flag: str = "北上") -> list[dict[str, Any]]:
        import aiohttp

        url = "http://push2his.eastmoney.com/api/qt/kamt.kline/get"

        params = {
            "fields1": "f1,f3,f5",
            "fields2": "f51,f52",
            "klt": "101",
            "lmt": "5000",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data"):
            flag_dict = {"沪股通": "hk2sh", "深股通": "hk2sz", "北上": "s2n"}
            fd = flag_dict.get(flag, "s2n")

            if data["data"].get(fd):
                for item in data["data"][fd]:
                    parts = item.split(",")
                    if len(parts) >= 2:
                        records.append({
                            "code": "north_money",
                            "trade_date": parts[0],
                            "net_inflow": float(parts[1]) / 10000 if parts[1] else None,
                        })

        return records

    async def _collect_north_money_stock(self, n: int = 1) -> list[dict[str, Any]]:
        import aiohttp

        url = "http://datacenter-web.eastmoney.com/api/data/v1/get"

        type_dict = {"1": "今日", "3": "3日", "5": "5日", "10": "10日", "M": "月", "Q": "季", "Y": "年"}
        _type = str(n).upper()
        period = type_dict.get(_type, "今日")

        params = {
            "sortColumns": "ADD_MARKET_CAP",
            "sortTypes": "-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_MUTUAL_STOCK_NORTHSTA",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
        }

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
                        "trade_date": datetime.now().strftime("%Y-%m-%d"),
                        "name": item.get("SECURITY_NAME_ABBR"),
                        "close": item.get("CLOSE_PRICE"),
                        "change_pct": item.get("CHANGE_RATE"),
                        "shares": item.get("HOLDER_NUM"),
                        "market_value": item.get("MARKET_CAP"),
                        f"{period}_add_value": item.get("ADD_MARKET_CAP"),
                    })

                page += 1
                if page > data["result"].get("pages", 1):
                    break

        return records

    async def _collect_north_money_sector(self, flag: str, n: int = 1) -> list[dict[str, Any]]:
        import aiohttp

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        flag_dict = {"行业": "5", "概念": "4", "地域": "3"}
        _type = str(n).upper()

        params = {
            "sortColumns": "ADD_MARKET_CAP",
            "sortTypes": "-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_MUTUAL_BOARD_HOLDRANK_WEB",
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "filter": f'(BOARD_TYPE="{flag_dict[flag]}")(INTERVAL_TYPE="{_type}")',
        }

        records = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                records.append({
                    "code": item.get("BOARD_CODE", ""),
                    "trade_date": datetime.now().strftime("%Y-%m-%d"),
                    "name": item.get("BOARD_NAME"),
                    "change_pct": item.get("CHANGE_RATE"),
                    "add_stocks": item.get("ADD_STOCK_NUM"),
                    "hold_stocks": item.get("HOLDER_STOCK_NUM"),
                    "add_value": item.get("ADD_MARKET_CAP"),
                    "add_ratio": item.get("ADD_MARKET_CAP_RATIO"),
                })

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('trade_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None


class SectorMoneyFlowCollector(MoneyFlowDataCollector):
    """
    Collector for sector money flow data.
    Migrated from qstock money.py concept_money_flow and industry_money_flow functions.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.THS,
                data_type=DataType.STOCK_MONEY_FLOW,
                category=DataCategory.MARKET,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.THS

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        sector_type = kwargs.get("sector_type", "行业")
        return await self._collect_sector_money_flow(sector_type)

    async def _collect_sector_money_flow(self, sector_type: str = "行业") -> list[dict[str, Any]]:
        import aiohttp
        from bs4 import BeautifulSoup

        if sector_type == "概念":
            url = "http://data.10jqka.com.cn/funds/gnzjl/field/tradezdf/order/desc/ajax/1/free/1/"
        else:
            url = "http://data.10jqka.com.cn/funds/hyzjl/field/tradezdf/order/desc/ajax/1/free/1/"

        headers = self._get_ths_header()

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")
        records = []

        try:
            page_info = soup.find("span", attrs={"class": "page_info"})
            if page_info:
                total_pages = int(page_info.text.split("/")[1])

                import pandas as pd

                for page in range(1, min(total_pages + 1, 10)):
                    page_url = url.replace("/ajax/1/", f"/page/{page}/ajax/1/")
                    async with session.get(page_url, headers=headers) as response:
                        page_html = await response.text()

                    try:
                        df = pd.read_html(page_html)[0]
                        for _, row in df.iterrows():
                            records.append({
                                "code": str(row.iloc[1]) if len(row) > 1 else "",
                                "trade_date": datetime.now().strftime("%Y-%m-%d"),
                                "sector_name": row.iloc[1] if len(row) > 1 else None,
                                "sector_index": row.iloc[2] if len(row) > 2 else None,
                                "change_pct": str(row.iloc[3]).strip("%") if len(row) > 3 else None,
                                "net_inflow": row.iloc[6] if len(row) > 6 else None,
                                "leading_stock": row.iloc[8] if len(row) > 8 else None,
                            })
                    except Exception as e:
                        logger.warning(f"Failed to parse sector money flow page: {e}")
        except Exception as e:
            logger.warning(f"Failed to parse sector money flow: {e}")

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('trade_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_ths_header(self) -> dict[str, str]:
        return {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "data.10jqka.com.cn",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
