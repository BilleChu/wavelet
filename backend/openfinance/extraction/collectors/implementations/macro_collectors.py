"""
Macro economic data collectors migrated from qstock macro.py.

This module provides collectors for macro economic data including
LPR, money supply, CPI, GDP, PPI, PMI, and other indicators.
"""

import json
import logging
from datetime import datetime
from typing import Any

from ..core.base_collector import (
    CollectionConfig,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    MacroData,
)
from ..quant_collector import QuantDataCollector

logger = logging.getLogger(__name__)


async def _get_json_response(response) -> dict:
    """Helper to parse JSON response that may have incorrect content-type."""
    text = await response.text()
    return json.loads(text)


class MacroDataCollector(QuantDataCollector):
    """
    Base collector for macro economic data.
    """

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _normalize_for_quant(self, data: list[MacroData]) -> list[MacroData]:
        return data

    async def _compute_factors(self, data: list[MacroData]) -> None:
        pass

    def _get_record_hash(self, record: MacroData) -> str:
        return f"{record.indicator_code}_{record.period}"

    async def _is_valid(self, record: MacroData) -> bool:
        return record.indicator_code is not None and record.period is not None


class LPRCollector(MacroDataCollector):
    """
    Collector for Loan Prime Rate (LPR) data.
    Migrated from qstock macro.py lpr function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_INTEREST_RATE,
                category=DataCategory.MACRO,
                frequency=DataFrequency.MONTHLY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        return await self._collect_lpr()

    async def _collect_lpr(self) -> list[MacroData]:
        import aiohttp

        url = "http://datacenter.eastmoney.com/api/data/get"

        params = {
            "type": "RPTA_WEB_RATE",
            "sty": "ALL",
            "token": "894050c76af8597a853f5b408b759f5d",
            "p": "1",
            "ps": "2000",
            "st": "TRADE_DATE",
            "sr": "-1",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                import json
                data = json.loads(text)

        records = []
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                try:
                    record = MacroData(
                        indicator_code="LPR",
                        indicator_name="贷款市场报价利率",
                        value=self._safe_float(item.get("LPR1Y")),
                        unit="%",
                        period=item.get("TRADE_DATE", "").split()[0] if item.get("TRADE_DATE") else "",
                        country="CN",
                        source="eastmoney",
                        published_at=datetime.strptime(item.get("TRADE_DATE", ""), "%Y-%m-%d %H:%M:%S") if item.get("TRADE_DATE") else datetime.now(),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse LPR record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class MoneySupplyCollector(MacroDataCollector):
    """
    Collector for money supply (M0, M1, M2) data.
    Migrated from qstock macro.py money_supply function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_MONEY_SUPPLY,
                category=DataCategory.MACRO,
                frequency=DataFrequency.MONTHLY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        return await self._collect_money_supply()

    async def _collect_money_supply(self) -> list[MacroData]:
        import aiohttp

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "columns": "TIME,BASIC_CURRENCY,BASIC_CURRENCY_SAME,BASIC_CURRENCY_SEQUENTIAL,CURRENCY,"
                       "CURRENCY_SAME,CURRENCY_SEQUENTIAL,FREE_CASH,FREE_CASH_SAME,FREE_CASH_SEQUENTIAL",
            "pageNumber": "1",
            "pageSize": "100",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB",
            "reportName": "RPT_ECONOMY_CURRENCY_SUPPLY",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                data = json.loads(text)

        records = []
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                try:
                    record = MacroData(
                        indicator_code="MONEY_SUPPLY",
                        indicator_name="货币供应量",
                        value=self._safe_float(item.get("CURRENCY")),
                        unit="亿元",
                        period=item.get("TIME", ""),
                        country="CN",
                        source="eastmoney",
                        published_at=datetime.now(),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse money supply record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class CPICollector(MacroDataCollector):
    """
    Collector for Consumer Price Index (CPI) data.
    Migrated from qstock macro.py cpi function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_CPI,
                category=DataCategory.MACRO,
                frequency=DataFrequency.MONTHLY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        return await self._collect_cpi()

    async def _collect_cpi(self) -> list[MacroData]:
        import aiohttp

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "columns": "TIME,NATIONAL_SAME,NATIONAL_BASE,NATIONAL_SEQUENTIAL,NATIONAL_ACCUMULATE",
            "pageNumber": "1",
            "pageSize": "100",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB",
            "reportName": "RPT_ECONOMY_CPI",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                data = json.loads(text)

        records = []
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                try:
                    record = MacroData(
                        indicator_code="CPI",
                        indicator_name="消费者物价指数",
                        value=self._safe_float(item.get("NATIONAL_SAME")),
                        unit="%",
                        period=item.get("TIME", ""),
                        country="CN",
                        source="eastmoney",
                        published_at=datetime.now(),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse CPI record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class GDPCollector(MacroDataCollector):
    """
    Collector for Gross Domestic Product (GDP) data.
    Migrated from qstock macro.py gdp function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_GDP,
                category=DataCategory.MACRO,
                frequency=DataFrequency.QUARTERLY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        return await self._collect_gdp()

    async def _collect_gdp(self) -> list[MacroData]:
        import aiohttp

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "columns": "TIME,DOMESTICL_PRODUCT_BASE,FIRST_PRODUCT_BASE,SECOND_PRODUCT_BASE,THIRD_PRODUCT_BASE,"
                       "SUM_SAME,FIRST_SAME,SECOND_SAME,THIRD_SAME",
            "pageNumber": "1",
            "pageSize": "100",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB",
            "reportName": "RPT_ECONOMY_GDP",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                data = json.loads(text)

        records = []
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                try:
                    record = MacroData(
                        indicator_code="GDP",
                        indicator_name="国内生产总值",
                        value=self._safe_float(item.get("DOMESTICL_PRODUCT_BASE")),
                        unit="亿元",
                        period=item.get("TIME", ""),
                        country="CN",
                        source="eastmoney",
                        published_at=datetime.now(),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse GDP record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class PPICollector(MacroDataCollector):
    """
    Collector for Producer Price Index (PPI) data.
    Migrated from qstock macro.py ppi function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_PPI,
                category=DataCategory.MACRO,
                frequency=DataFrequency.MONTHLY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        return await self._collect_ppi()

    async def _collect_ppi(self) -> list[MacroData]:
        import aiohttp

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "columns": "TIME,BASE,BASE_SAME,BASE_ACCUMULATE",
            "pageNumber": "1",
            "pageSize": "100",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB",
            "reportName": "RPT_ECONOMY_PPI",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                data = json.loads(text)

        records = []
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                try:
                    record = MacroData(
                        indicator_code="PPI",
                        indicator_name="生产者物价指数",
                        value=self._safe_float(item.get("BASE")),
                        unit="%",
                        period=item.get("TIME", ""),
                        country="CN",
                        source="eastmoney",
                        published_at=datetime.now(),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse PPI record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class PMICollector(MacroDataCollector):
    """
    Collector for Purchasing Managers Index (PMI) data.
    Migrated from qstock macro.py pmi function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_PMI,
                category=DataCategory.MACRO,
                frequency=DataFrequency.MONTHLY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        return await self._collect_pmi()

    async def _collect_pmi(self) -> list[MacroData]:
        import aiohttp

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        params = {
            "columns": "TIME,MAKE_INDEX,MAKE_SAME,NMAKE_INDEX,NMAKE_SAME",
            "pageNumber": "1",
            "pageSize": "100",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB",
            "reportName": "RPT_ECONOMY_PMI",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                data = json.loads(text)

        records = []
        if data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                try:
                    record = MacroData(
                        indicator_code="PMI",
                        indicator_name="采购经理人指数",
                        value=self._safe_float(item.get("MAKE_INDEX")),
                        unit="%",
                        period=item.get("TIME", ""),
                        country="CN",
                        source="eastmoney",
                        published_at=datetime.now(),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse PMI record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0


class InterbankRateCollector(MacroDataCollector):
    """
    Collector for interbank offered rate data.
    Migrated from qstock macro.py interbank_rate function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.MACRO_INTEREST_RATE,
                category=DataCategory.MACRO,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[MacroData]:
        market = kwargs.get("market", "sh")
        return await self._collect_interbank_rate(market)

    async def _collect_interbank_rate(self, market: str = "sh") -> list[MacroData]:
        import aiohttp

        market_dict = {
            "sh": "001",
            "ch": "002",
            "l": "003",
            "eu": "004",
            "hk": "005",
            "s": "006",
        }

        indicator_dict = {
            "隔夜": "001",
            "1周": "101",
            "2周": "102",
            "1月": "201",
            "3月": "203",
            "6月": "206",
            "1年": "301",
        }

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        records = []
        async with aiohttp.ClientSession() as session:
            for indicator_name, indicator_id in indicator_dict.items():
                params = {
                    "reportName": "RPT_IMP_INTRESTRATEN",
                    "columns": "REPORT_DATE,REPORT_PERIOD,IR_RATE,CHANGE_RATE",
                    "filter": f'(MARKET_CODE="{market_dict.get(market, "001")}")(CURRENCY_CODE="CNY")(INDICATOR_ID="{indicator_id}")',
                    "pageNumber": "1",
                    "pageSize": "100",
                    "sortTypes": "-1",
                    "sortColumns": "REPORT_DATE",
                    "source": "WEB",
                    "client": "WEB",
                }

                async with session.get(url, params=params) as response:
                    text = await response.text()
                    data = json.loads(text)

                if data.get("result") and data["result"].get("data"):
                    for item in data["result"]["data"]:
                        try:
                            record = MacroData(
                                indicator_code=f"SHIBOR_{indicator_name}",
                                indicator_name=f"上海银行间同业拆放利率-{indicator_name}",
                                value=self._safe_float(item.get("IR_RATE")),
                                unit="%",
                                period=item.get("REPORT_DATE", "").split()[0] if item.get("REPORT_DATE") else "",
                                country="CN",
                                source="eastmoney",
                                published_at=datetime.now(),
                            )
                            records.append(record)
                        except Exception as e:
                            logger.warning(f"Failed to parse interbank rate record: {e}")

        return records

    def _safe_float(self, value: Any) -> float:
        if value is None or value == "-" or value == "":
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
