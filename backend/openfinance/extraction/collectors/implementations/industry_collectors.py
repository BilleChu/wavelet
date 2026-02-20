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
