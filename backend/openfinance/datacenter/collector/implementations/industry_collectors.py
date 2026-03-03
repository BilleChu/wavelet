"""
Industry and concept data collectors migrated from qstock industry.py.

This module provides collectors for industry and concept data including
industry members, concept members, and sector data.
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
    StockQuoteData,
)
from ..quant_collector import QuantDataCollector

logger = logging.getLogger(__name__)


class IndustryMemberCollector(QuantDataCollector):
    """
    Collector for industry member stocks.
    Migrated from qstock industry.py ths_industry_member function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.THS,
                data_type=DataType.INDUSTRY_MEMBER,
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
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_industry_member(code)

    async def _collect_industry_member(self, code: str) -> list[dict[str, Any]]:
        import aiohttp
        from bs4 import BeautifulSoup

        if not code.isdigit():
            code = await self._get_industry_code(code)

        url = f"http://q.10jqka.com.cn/thshy/detail/field/199112/order/desc/page/1/ajax/1/code/{code}"

        headers = self._get_ths_header()

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")

        try:
            page_links = soup.find_all("a", attrs={"class": "changePage"})
            total_pages = int(page_links[-1]["page"]) if page_links else 1
        except Exception:
            total_pages = 1

        records = []
        async with aiohttp.ClientSession() as session:
            for page in range(1, total_pages + 1):
                page_url = f"http://q.10jqka.com.cn/thshy/detail/field/199112/order/desc/page/{page}/ajax/1/code/{code}"
                async with session.get(page_url, headers=headers) as response:
                    page_html = await response.text()

                try:
                    import pandas as pd
                    df = pd.read_html(page_html)[0]

                    for _, row in df.iterrows():
                        records.append({
                            "industry_code": code,
                            "stock_code": str(row.get("代码", "")).zfill(6),
                            "stock_name": row.get("名称", ""),
                            "change_pct": self._parse_pct(row.get("涨跌幅(%)", "")),
                            "turnover_rate": self._parse_pct(row.get("换手(%)", "")),
                            "volume": row.get("成交量", 0),
                            "amount": row.get("成交额(亿)", 0),
                            "circulating_market_cap": row.get("流通市值(亿)", 0),
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse industry member page: {e}")

        return records

    async def _get_industry_code(self, name: str) -> str:
        return name

    def _parse_pct(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).strip("%"))
        except (ValueError, TypeError):
            return None

    def _get_ths_header(self) -> dict[str, str]:
        return {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "q.10jqka.com.cn",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }


class ConceptMemberCollector(QuantDataCollector):
    """
    Collector for concept member stocks.
    Migrated from qstock industry.py ths_concept_member function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.THS,
                data_type=DataType.CONCEPT_MEMBER,
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
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_concept_member(code)

    async def _collect_concept_member(self, code: str) -> list[dict[str, Any]]:
        import aiohttp
        from bs4 import BeautifulSoup

        if not code.isdigit():
            code = await self._get_concept_code(code)

        url = f"http://q.10jqka.com.cn/gn/detail/field/264648/order/desc/page/1/ajax/1/code/{code}"

        headers = self._get_ths_header()

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")

        try:
            page_links = soup.find_all("a", attrs={"class": "changePage"})
            total_pages = int(page_links[-1]["page"]) if page_links else 1
        except Exception:
            total_pages = 1

        records = []
        async with aiohttp.ClientSession() as session:
            for page in range(1, total_pages + 1):
                page_url = f"http://q.10jqka.com.cn/gn/detail/field/264648/order/desc/page/{page}/ajax/1/code/{code}"
                async with session.get(page_url, headers=headers) as response:
                    page_html = await response.text()

                try:
                    import pandas as pd
                    df = pd.read_html(page_html)[0]

                    for _, row in df.iterrows():
                        records.append({
                            "concept_code": code,
                            "stock_code": str(row.get("代码", "")).zfill(6),
                            "stock_name": row.get("名称", ""),
                            "change_pct": self._parse_pct(row.get("涨跌幅(%)", "")),
                            "turnover_rate": self._parse_pct(row.get("换手(%)", "")),
                            "volume": row.get("成交量", 0),
                            "amount": row.get("成交额(亿)", 0),
                            "circulating_market_cap": row.get("流通市值(亿)", 0),
                        })
                except Exception as e:
                    logger.warning(f"Failed to parse concept member page: {e}")

        return records

    async def _get_concept_code(self, name: str) -> str:
        return name

    def _parse_pct(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).strip("%"))
        except (ValueError, TypeError):
            return None

    def _get_ths_header(self) -> dict[str, str]:
        return {
            "Accept": "text/html, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Host": "q.10jqka.com.cn",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }


class IndustryDataCollector(QuantDataCollector):
    """
    Collector for industry index data.
    Migrated from qstock industry.py ths_industry_data function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.THS,
                data_type=DataType.INDUSTRY_DATA,
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

    async def _collect(self, **kwargs: Any) -> list[StockQuoteData]:
        code = kwargs.get("code")
        start = kwargs.get("start_date", "20200101")
        end = kwargs.get("end_date")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_industry_data(code, start, end)

    async def _collect_industry_data(
        self, code: str, start: str, end: str | None
    ) -> list[StockQuoteData]:
        import aiohttp

        if not code.isdigit():
            code = await self._get_industry_code(code)

        if end is None:
            end = datetime.now().strftime("%Y%m%d")

        current_year = datetime.now().year
        records = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://q.10jqka.com.cn",
            "Host": "d.10jqka.com.cn",
        }

        async with aiohttp.ClientSession() as session:
            for year in range(2000, current_year + 1):
                url = f"http://d.10jqka.com.cn/v4/line/bk_{code}/01/{year}.js"

                try:
                    async with session.get(url, headers=headers) as response:
                        text = await response.text()

                    json_start = text.find("{")
                    if json_start == -1:
                        continue

                    import json
                    data = json.loads(text[json_start:-1])

                    if data.get("data"):
                        lines = data["data"].split(";")
                        for line in lines:
                            parts = line.split(",")
                            if len(parts) >= 6:
                                try:
                                    date_str = parts[0]
                                    if start <= date_str <= end:
                                        record = StockQuoteData(
                                            code=code,
                                            name="",
                                            trade_date=date_str,
                                            open=self._safe_float(parts[1]),
                                            high=self._safe_float(parts[2]),
                                            low=self._safe_float(parts[3]),
                                            close=self._safe_float(parts[4]),
                                            volume=self._safe_int(parts[5]),
                                        )
                                        records.append(record)
                                except Exception as e:
                                    logger.warning(f"Failed to parse industry data line: {e}")
                except Exception as e:
                    logger.warning(f"Failed to fetch industry data for year {year}: {e}")

        return records

    async def _get_industry_code(self, name: str) -> str:
        return name

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> int | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://data.eastmoney.com/",
}


class EastMoneyIndustryListCollector(QuantDataCollector):
    """
    Collector for EastMoney industry classification list.
    获取东方财富行业分类列表，包括申万行业分类。
    """

    EASTMONEY_INDUSTRY_LIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.INDUSTRY_DATA,
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
        industry_type = kwargs.get("industry_type", "industry")
        return await self._collect_industry_list(industry_type)

    async def _collect_industry_list(self, industry_type: str = "industry") -> list[dict[str, Any]]:
        import aiohttp
        import asyncio

        fs_map = {
            "industry": "m:90 t:2 f:!50",
            "concept": "m:90 t:3 f:!50",
            "region": "m:90 t:1 f:!50",
        }

        fs = fs_map.get(industry_type, fs_map["industry"])

        params = {
            "pn": 1,
            "pz": 500,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs,
            "fields": "f1,f2,f3,f4,f12,f13,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f124,f140,f141,f207,f208,f209,f222,f225,f239,f240,f241,f242,f243,f244,f245,f246,f247,f248,f250,f251,f252,f253,f254,f255,f256",
        }

        records = []
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)

        async with aiohttp.ClientSession(headers=EASTMONEY_HEADERS, timeout=timeout, connector=connector) as session:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with session.get(self.EASTMONEY_INDUSTRY_LIST_URL, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            break
                        else:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1.0 * (attempt + 1))
                                continue
                            data = {}
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    logger.warning(f"Failed to fetch industry list: {e}")
                    data = {}

            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    records.append({
                        "type": industry_type,
                        "code": item.get("f12", ""),
                        "name": item.get("f14", ""),
                        "change_pct": self._safe_float(item.get("f3")),
                        "change": self._safe_float(item.get("f4")),
                        "total_market_cap": self._safe_float(item.get("f62")),
                        "turnover_rate": self._safe_float(item.get("f8")),
                        "rise_count": self._safe_int(item.get("f244")),
                        "fall_count": self._safe_int(item.get("f245")),
                        "leading_stock_code": item.get("f140"),
                        "leading_stock_name": item.get("f141"),
                        "leading_stock_change": self._safe_float(item.get("f208")),
                    })

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('type')}_{record.get('code')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None and record.get("name") is not None

    async def _normalize_for_quant(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data

    async def _compute_factors(self, data: list[dict[str, Any]]) -> None:
        if not data:
            return
        change_pcts = [r.get("change_pct") for r in data if r.get("change_pct") is not None]
        if change_pcts:
            self._factor_cache["avg_change_pct"] = sum(change_pcts) / len(change_pcts)

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> int | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


class EastMoneyIndustryMemberCollector(QuantDataCollector):
    """
    Collector for EastMoney industry member stocks.
    获取东方财富行业/概念板块成分股。
    """

    EASTMONEY_INDUSTRY_MEMBER_URL = "https://push2.eastmoney.com/api/qt/clist/get"

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.INDUSTRY_MEMBER,
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
        industry_type = kwargs.get("industry_type", "industry")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_industry_member(code, industry_type)

    async def _collect_industry_member(self, code: str, industry_type: str = "industry") -> list[dict[str, Any]]:
        import aiohttp
        import asyncio

        fs = f"b:{code} f:!50"

        fields = (
            "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,"
            "f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f140,f141,f207,"
            "f208,f209,f222,f225,f239,f240,f241,f242,f243,f244,f245,"
            "f246,f247,f248,f250,f251,f252,f253,f254,f255,f256"
        )

        records = []
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)

        async with aiohttp.ClientSession(headers=EASTMONEY_HEADERS, timeout=timeout, connector=connector) as session:
            page = 1
            page_size = 100
            total_records = 0

            while True:
                params = {
                    "pn": page,
                    "pz": page_size,
                    "po": 1,
                    "np": 1,
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": fs,
                    "fields": fields,
                }

                max_retries = 3
                data = {}
                for attempt in range(max_retries):
                    try:
                        async with session.get(self.EASTMONEY_INDUSTRY_MEMBER_URL, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                break
                            else:
                                if attempt < max_retries - 1:
                                    await asyncio.sleep(1.0 * (attempt + 1))
                                    continue
                    except Exception as e:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1.0 * (attempt + 1))
                            continue
                        logger.warning(f"Failed to fetch industry member page {page}: {e}")

                if not data.get("data") or not data["data"].get("diff"):
                    break

                total = data["data"].get("total", 0)
                diff = data["data"].get("diff", [])

                for item in diff:
                    records.append({
                        "industry_code": code,
                        "industry_type": industry_type,
                        "stock_code": item.get("f12", ""),
                        "stock_name": item.get("f14", ""),
                        "price": self._safe_float(item.get("f2")),
                        "change_pct": self._safe_float(item.get("f3")),
                        "change": self._safe_float(item.get("f4")),
                        "volume": self._safe_int(item.get("f5")),
                        "amount": self._safe_float(item.get("f6")),
                        "amplitude": self._safe_float(item.get("f7")),
                        "turnover_rate": self._safe_float(item.get("f8")),
                        "pe_ratio": self._safe_float(item.get("f9")),
                        "circulating_market_cap": self._safe_float(item.get("f20")),
                        "total_market_cap": self._safe_float(item.get("f21")),
                    })

                total_records += len(diff)
                if total_records >= total:
                    break

                page += 1

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('industry_code')}_{record.get('stock_code')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("stock_code") is not None and record.get("stock_name") is not None

    async def _normalize_for_quant(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data

    async def _compute_factors(self, data: list[dict[str, Any]]) -> None:
        if not data:
            return
        change_pcts = [r.get("change_pct") for r in data if r.get("change_pct") is not None]
        if change_pcts:
            self._factor_cache["avg_change_pct"] = sum(change_pcts) / len(change_pcts)

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> int | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


class EastMoneyStockIndustryCollector(QuantDataCollector):
    """
    Collector for stock industry classification.
    获取单只股票所属的行业分类信息。
    """

    EASTMONEY_STOCK_INDUSTRY_URL = "https://emweb.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax"

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_FUNDAMENTAL,
                category=DataCategory.FUNDAMENTAL,
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
        return await self._collect_stock_industry(code)

    async def _collect_stock_industry(self, code: str) -> list[dict[str, Any]]:
        import aiohttp
        import asyncio

        secid = ""
        if code.startswith("6"):
            secid = f"SH{code}"
        elif code.startswith(("0", "3")):
            secid = f"SZ{code}"
        elif code.startswith(("4", "8")):
            secid = f"BJ{code}"

        if not secid:
            return []

        params = {"code": secid}

        records = []
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)

        async with aiohttp.ClientSession(headers=EASTMONEY_HEADERS, timeout=timeout, connector=connector) as session:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with session.get(self.EASTMONEY_STOCK_INDUSTRY_URL, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            break
                        else:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(1.0 * (attempt + 1))
                                continue
                            data = {}
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    logger.warning(f"Failed to fetch stock industry for {code}: {e}")
                    data = {}

            jbzl = data.get("jbzl", {})
            if jbzl:
                industry_name = jbzl.get("hymc", "")
                sector_name = jbzl.get("sshy", "")
                
                if industry_name:
                    records.append({
                        "stock_code": code,
                        "industry_type": "industry",
                        "industry_name": industry_name,
                        "industry_code": "",
                    })
                
                if sector_name:
                    records.append({
                        "stock_code": code,
                        "industry_type": "sector",
                        "industry_name": sector_name,
                        "industry_code": "",
                    })

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('stock_code')}_{record.get('industry_type')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("stock_code") is not None and record.get("industry_name") is not None

    async def _normalize_for_quant(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return data

    async def _compute_factors(self, data: list[dict[str, Any]]) -> None:
        pass


class ConceptDataCollector(QuantDataCollector):
    """
    Collector for concept index data.
    Migrated from qstock industry.py ths_concept_data function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.THS,
                data_type=DataType.CONCEPT_DATA,
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

    async def _collect(self, **kwargs: Any) -> list[StockQuoteData]:
        code = kwargs.get("code")
        start = kwargs.get("start_date", "2020")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_concept_data(code, start)

    async def _collect_concept_data(self, code: str, start: str) -> list[StockQuoteData]:
        import aiohttp
        from bs4 import BeautifulSoup

        if not code.isdigit():
            code = await self._get_concept_code(code)

        symbol_url = f"http://q.10jqka.com.cn/gn/detail/code/{code}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(symbol_url, headers=headers) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")

        try:
            board_hq = soup.find("div", attrs={"class": "board-hq"})
            symbol_code = board_hq.find("span").text if board_hq else ""
        except Exception:
            symbol_code = ""

        current_year = datetime.now().year
        records = []

        data_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "http://q.10jqka.com.cn",
            "Host": "d.10jqka.com.cn",
        }

        async with aiohttp.ClientSession() as session:
            for year in range(int(start), current_year + 1):
                url = f"http://d.10jqka.com.cn/v4/line/bk_{symbol_code}/01/{year}.js"

                try:
                    async with session.get(url, headers=data_headers) as response:
                        text = await response.text()

                    json_start = text.find("{")
                    if json_start == -1:
                        continue

                    import json
                    data = json.loads(text[json_start:-1])

                    if data.get("data"):
                        lines = data["data"].split(";")
                        for line in lines:
                            parts = line.split(",")
                            if len(parts) >= 6:
                                try:
                                    record = StockQuoteData(
                                        code=code,
                                        name="",
                                        trade_date=parts[0],
                                        open=self._safe_float(parts[1]),
                                        high=self._safe_float(parts[2]),
                                        low=self._safe_float(parts[3]),
                                        close=self._safe_float(parts[4]),
                                        volume=self._safe_int(parts[5]),
                                    )
                                    records.append(record)
                                except Exception as e:
                                    logger.warning(f"Failed to parse concept data line: {e}")
                except Exception as e:
                    logger.warning(f"Failed to fetch concept data for year {year}: {e}")

        return records

    async def _get_concept_code(self, name: str) -> str:
        return name

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> int | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
