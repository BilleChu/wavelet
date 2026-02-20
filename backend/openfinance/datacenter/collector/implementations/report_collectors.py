"""
Financial report data collectors migrated from qstock report.py.

This module provides collectors for financial report data including
balance sheet, income statement, cash flow statement, and performance reports.
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
    FinancialIndicatorData,
)
from ..quant_collector import FundamentalDataCollector

logger = logging.getLogger(__name__)


class BalanceSheetCollector(FundamentalDataCollector):
    """
    Collector for balance sheet data.
    Migrated from qstock report.py balance_sheet function.
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
        date = kwargs.get("date")
        return await self._collect_balance_sheet(date)

    async def _collect_balance_sheet(self, date: str | None = None) -> list[dict[str, Any]]:
        import aiohttp

        if date is None:
            date = self._get_latest_report_date()
        else:
            date = "".join(date.split("-"))

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        date_str = "-".join([date[:4], date[4:6], date[6:]])
        params = {
            "sortColumns": "NOTICE_DATE,SECURITY_CODE",
            "sortTypes": "-1,-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_DMSK_FN_BALANCE",
            "columns": "ALL",
            "filter": f'(SECURITY_TYPE_CODE in ("058001001","058001008"))(TRADE_MARKET_CODE!="069001017")(REPORT_DATE=\'{date_str}\')',
        }

        records = []
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["pageNumber"] = str(page)
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        break

                if not data.get("result") or not data.get("result", {}).get("data"):
                    break

                for item in data["result"]["data"]:
                    records.append({
                        "code": item.get("SECURITY_CODE"),
                        "name": item.get("SECURITY_NAME_ABBR"),
                        "report_date": item.get("REPORT_DATE"),
                        "total_assets": item.get("TOTAL_ASSETS"),
                        "monetary_funds": item.get("MONETARY_CAPITAL"),
                        "accounts_receivable": item.get("ACCOUNT_RECEIVABLE"),
                        "inventory": item.get("INVENTORY"),
                        "total_liabilities": item.get("TOTAL_LIABILITIES"),
                        "accounts_payable": item.get("ACCOUNTS_PAYABLE"),
                        "shareholders_equity": item.get("TOTAL_EQUITY"),
                        "asset_liability_ratio": item.get("ASSET_LIAB_RATIO"),
                    })

                page += 1
                if page > data.get("result", {}).get("pages", 1):
                    break

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('report_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_latest_report_date(self) -> str:
        now = datetime.now()
        year = now.year
        month = now.month

        if month < 4:
            return f"{year - 1}0930"
        elif month < 7:
            return f"{year}0331"
        elif month < 10:
            return f"{year}0630"
        else:
            return f"{year}0930"


class IncomeStatementCollector(FundamentalDataCollector):
    """
    Collector for income statement data.
    Migrated from qstock report.py income_statement function.
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
        date = kwargs.get("date")
        return await self._collect_income_statement(date)

    async def _collect_income_statement(self, date: str | None = None) -> list[dict[str, Any]]:
        import aiohttp

        if date is None:
            date = self._get_latest_report_date()
        else:
            date = "".join(date.split("-"))

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        date_str = "-".join([date[:4], date[4:6], date[6:]])
        params = {
            "sortColumns": "NOTICE_DATE,SECURITY_CODE",
            "sortTypes": "-1,-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_DMSK_FN_INCOME",
            "columns": "ALL",
            "filter": f'(SECURITY_TYPE_CODE in ("058001001","058001008"))(TRADE_MARKET_CODE!="069001017")(REPORT_DATE=\'{date_str}\')',
        }

        records = []
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["pageNumber"] = str(page)
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        break

                if not data.get("result") or not data.get("result", {}).get("data"):
                    break

                for item in data["result"]["data"]:
                    records.append({
                        "code": item.get("SECURITY_CODE"),
                        "name": item.get("SECURITY_NAME_ABBR"),
                        "report_date": item.get("REPORT_DATE"),
                        "net_profit": item.get("PARENT_NETPROFIT"),
                        "total_revenue": item.get("TOTAL_OPERATE_INCOME"),
                        "total_cost": item.get("TOTAL_OPERATE_COST"),
                        "operating_cost": item.get("OPERATE_COST"),
                        "selling_expense": item.get("SALE_EXPENSE"),
                        "admin_expense": item.get("MANAGE_EXPENSE"),
                        "financial_expense": item.get("FINANCE_EXPENSE"),
                        "operating_profit": item.get("OPERATE_PROFIT"),
                        "total_profit": item.get("TOTAL_PROFIT"),
                    })

                page += 1
                if page > data.get("result", {}).get("pages", 1):
                    break

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('report_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_latest_report_date(self) -> str:
        now = datetime.now()
        year = now.year
        month = now.month

        if month < 4:
            return f"{year - 1}0930"
        elif month < 7:
            return f"{year}0331"
        elif month < 10:
            return f"{year}0630"
        else:
            return f"{year}0930"


class CashFlowStatementCollector(FundamentalDataCollector):
    """
    Collector for cash flow statement data.
    Migrated from qstock report.py cashflow_statement function.
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
        date = kwargs.get("date")
        return await self._collect_cashflow_statement(date)

    async def _collect_cashflow_statement(self, date: str | None = None) -> list[dict[str, Any]]:
        import aiohttp

        if date is None:
            date = self._get_latest_report_date()
        else:
            date = "".join(date.split("-"))

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

        date_str = "-".join([date[:4], date[4:6], date[6:]])
        params = {
            "sortColumns": "NOTICE_DATE,SECURITY_CODE",
            "sortTypes": "-1,-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_DMSK_FN_CASHFLOW",
            "columns": "ALL",
            "filter": f'(SECURITY_TYPE_CODE in ("058001001","058001008"))(TRADE_MARKET_CODE!="069001017")(REPORT_DATE=\'{date_str}\')',
        }

        records = []
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["pageNumber"] = str(page)
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        break

                if not data.get("result") or not data.get("result", {}).get("data"):
                    break

                for item in data["result"]["data"]:
                    records.append({
                        "code": item.get("SECURITY_CODE"),
                        "name": item.get("SECURITY_NAME_ABBR"),
                        "report_date": item.get("REPORT_DATE"),
                        "net_operating_cash_flow": item.get("OPERATE_CASH_FLOW_PS"),
                        "net_investing_cash_flow": item.get("INVEST_CASH_FLOW_PS"),
                        "net_financing_cash_flow": item.get("FINANCE_CASH_FLOW_PS"),
                    })

                page += 1
                if page > data.get("result", {}).get("pages", 1):
                    break

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('report_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_latest_report_date(self) -> str:
        now = datetime.now()
        year = now.year
        month = now.month

        if month < 4:
            return f"{year - 1}0930"
        elif month < 7:
            return f"{year}0331"
        elif month < 10:
            return f"{year}0630"
        else:
            return f"{year}0930"


class PerformanceReportCollector(FundamentalDataCollector):
    """
    Collector for performance report data.
    Migrated from qstock report.py stock_yjbb function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_FINANCIAL_INDICATOR,
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

    async def _collect(self, **kwargs: Any) -> list[FinancialIndicatorData]:
        date = kwargs.get("date")
        return await self._collect_performance_report(date)

    async def _collect_performance_report(self, date: str | None = None) -> list[FinancialIndicatorData]:
        import aiohttp

        if date is None:
            date = self._get_latest_report_date()
        else:
            date = "".join(date.split("-"))

        url = "http://datacenter.eastmoney.com/api/data/get"

        date_str = "-".join([date[:4], date[4:6], date[6:]])
        params = {
            "st": "UPDATE_DATE,SECURITY_CODE",
            "sr": "-1,-1",
            "ps": "500",
            "p": "1",
            "type": "RPT_LICO_FN_CPD",
            "sty": "ALL",
            "token": "894050c76af8597a853f5b408b759f5d",
            "filter": f"(REPORTDATE='{date_str}')",
        }

        records = []
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["p"] = str(page)
                params["ps"] = "500"
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        break

                if not data.get("result") or not data.get("result", {}).get("data"):
                    break

                for item in data["result"]["data"]:
                    try:
                        record = FinancialIndicatorData(
                            code=item.get("SECURITY_CODE", ""),
                            name=item.get("SECURITY_NAME_ABBR", ""),
                            report_date=item.get("REPORTDATE", ""),
                            eps=self._safe_float(item.get("BASIC_EPS")),
                            bps=self._safe_float(item.get("BPS")),
                            roe=self._safe_float(item.get("WEIGHTAVG_ROE")),
                            revenue=self._safe_float(item.get("TOTAL_OPERATE_INCOME")),
                            net_profit=self._safe_float(item.get("PARENT_NETPROFIT")),
                            revenue_yoy=self._safe_float(item.get("YSTZ")),
                            net_profit_yoy=self._safe_float(item.get("SJLTZ")),
                            gross_margin=self._safe_float(item.get("XSMLL")),
                        )
                        records.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to parse performance report: {e}")

                page += 1
                if page > data.get("result", {}).get("pages", 1):
                    break

        return records

    def _get_latest_report_date(self) -> str:
        now = datetime.now()
        year = now.year
        month = now.month

        if month < 4:
            return f"{year - 1}0930"
        elif month < 7:
            return f"{year}0331"
        elif month < 10:
            return f"{year}0630"
        else:
            return f"{year}0930"

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class PerformanceForecastCollector(FundamentalDataCollector):
    """
    Collector for performance forecast data.
    Migrated from qstock report.py stock_yjyg function.
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
        date = kwargs.get("date")
        return await self._collect_performance_forecast(date)

    async def _collect_performance_forecast(self, date: str | None = None) -> list[dict[str, Any]]:
        import aiohttp

        if date is None:
            date = self._get_latest_report_date()
        else:
            date = "".join(date.split("-"))

        url = "http://datacenter.eastmoney.com/securities/api/data/v1/get"

        date_str = "-".join([date[:4], date[4:6], date[6:]])
        params = {
            "sortColumns": "NOTICE_DATE,SECURITY_CODE",
            "sortTypes": "-1,-1",
            "pageSize": "500",
            "pageNumber": "1",
            "reportName": "RPT_PUBLIC_OP_NEWPREDICT",
            "columns": "ALL",
            "token": "894050c76af8597a853f5b408b759f5d",
            "filter": f"(REPORT_DATE='{date_str}')",
        }

        records = []
        async with aiohttp.ClientSession() as session:
            page = 1
            while True:
                params["pageNumber"] = str(page)
                async with session.get(url, params=params) as response:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        break

                if not data.get("result") or not data.get("result", {}).get("data"):
                    break

                for item in data["result"]["data"]:
                    records.append({
                        "code": item.get("SECURITY_CODE"),
                        "name": item.get("SECURITY_NAME_ABBR"),
                        "report_date": item.get("REPORT_DATE"),
                        "notice_date": item.get("NOTICE_DATE"),
                        "forecast_indicator": item.get("FORECAST_INDEX"),
                        "performance_change": item.get("PERFORMANCE_CHANGE"),
                        "forecast_value": item.get("FORECAST_VALUE"),
                        "change_range": item.get("CHANGE_RANGE"),
                        "change_reason": item.get("CHANGE_REASON"),
                        "forecast_type": item.get("FORECAST_TYPE"),
                    })

                page += 1
                if page > data.get("result", {}).get("pages", 1):
                    break

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('report_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_latest_report_date(self) -> str:
        now = datetime.now()
        year = now.year
        month = now.month

        if month < 4:
            return f"{year - 1}0930"
        elif month < 7:
            return f"{year}0331"
        elif month < 10:
            return f"{year}0630"
        else:
            return f"{year}0930"
