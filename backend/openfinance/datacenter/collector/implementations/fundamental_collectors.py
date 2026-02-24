"""
Fundamental data collectors migrated from qstock fundamental.py.

This module provides collectors for fundamental data including
institutional ratings, shareholders, main business, and financial indicators.
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


class InstitutionalRatingCollector(FundamentalDataCollector):
    """
    Collector for institutional ratings.
    Migrated from qstock fundamental.py stock_institutional_rating function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_ANALYST_RATING,
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
        return await self._collect_rating(code)

    async def _collect_rating(self, code: str) -> list[dict[str, Any]]:
        import aiohttp

        code_id = self._get_code_id(code)[2:]
        current_date = datetime.now().strftime("%Y-%m-%d")
        prev_month = self._get_previous_month()

        params = {
            "beginTime": prev_month,
            "endTime": current_date,
            "pageNo": "1",
            "qType": "1",
            "pageSize": "10",
            "code": code_id,
            "fields": "orgSName,emRatingName,title,publishDate",
        }

        url = "http://reportapi.eastmoney.com/report/list"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                text = await response.text()
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {}

        records = []
        if data.get("data"):
            for item in data["data"]:
                records.append({
                    "code": code,
                    "org_name": item.get("orgSName"),
                    "rating": item.get("emRatingName"),
                    "title": item.get("title"),
                    "publish_date": item.get("publishDate"),
                })

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('publish_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_code_id(self, code: str) -> str:
        if code.isdigit():
            if code.startswith("6"):
                return f"1.{code}"
            else:
                return f"0.{code}"
        return f"0.{code}"


class IncomeStatementCollector(FundamentalDataCollector):
    """
    Collector for income statement data (利润表).
    采集利润表数据，包括营业收入、净利润、归母净利润等。
    Returns ADSIncomeStatementModel instances.
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

    async def _collect(self, **kwargs: Any) -> list[Any]:
        from openfinance.datacenter.models.analytical.financial import ADSIncomeStatementModel
        
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_income_statement(code)

    async def _collect_income_statement(self, code: str) -> list[Any]:
        from datetime import datetime
        from openfinance.datacenter.models.analytical.financial import ADSIncomeStatementModel
        import aiohttp

        code_id = self._get_code_id(code)
        
        url = "https://emweb.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
        params = {
            "companyType": "4",
            "reportDateType": "0",
            "code": code_id,
            "dataType": "1",
        }

        records = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                
                if data.get("data") and data["data"].get("lr"):
                    for item in data["data"]["lr"]:
                        report_date_str = item.get("date")
                        report_date = None
                        if report_date_str:
                            try:
                                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                pass
                        
                        records.append(ADSIncomeStatementModel(
                            code=code,
                            report_date=report_date,
                            report_period=item.get("type", "annual"),
                            total_revenue=self._safe_float(item.get("yysr")),
                            operating_revenue=self._safe_float(item.get("yysr")),
                            total_operating_cost=self._safe_float(item.get("yycb")),
                            cost_of_goods_sold=self._safe_float(item.get("yycb")),
                            operating_profit=self._safe_float(item.get("yylr")),
                            total_profit=self._safe_float(item.get("ze")),
                            net_profit=self._safe_float(item.get("jlr")),
                            net_profit_attr_parent=self._safe_float(item.get("gsjlr")),
                            basic_eps=self._safe_float(item.get("mgde")),
                            diluted_eps=self._safe_float(item.get("xsmgde")),
                        ))
            except Exception as e:
                logger.warning(f"Failed to collect income statement for {code}: {e}")

        return records

    def _get_record_hash(self, record: Any) -> str:
        return f"{record.code}_{record.report_date}_{getattr(record, 'report_period', 'annual')}"

    async def _is_valid(self, record: Any) -> bool:
        return record.code is not None and record.report_date is not None

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


class BalanceSheetCollector(FundamentalDataCollector):
    """
    Collector for balance sheet data (资产负债表).
    采集资产负债表数据，包括总资产、总负债、净资产等。
    Returns ADSBalanceSheetModel instances.
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

    async def _collect(self, **kwargs: Any) -> list[Any]:
        from openfinance.datacenter.models.analytical.financial import ADSBalanceSheetModel
        
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_balance_sheet(code)

    async def _collect_balance_sheet(self, code: str) -> list[Any]:
        import aiohttp

        code_id = self._get_code_id(code)
        
        url = "https://emweb.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
        params = {
            "companyType": "4",
            "reportDateType": "0",
            "code": code_id,
            "dataType": "3",
        }

        records = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                
                if data.get("data") and data["data"].get("zc"):
                    for item in data["data"]["zc"]:
                        report_date_str = item.get("date")
                        report_date = None
                        if report_date_str:
                            try:
                                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                pass
                        
                        records.append(ADSBalanceSheetModel(
                            code=code,
                            report_date=report_date,
                            report_period=item.get("type", "annual"),
                            total_assets=self._safe_float(item.get("zzc")),
                            total_liabilities=self._safe_float(item.get("zfz")),
                            total_equity=self._safe_float(item.get("gdqy")),
                            net_equity_attr=self._safe_float(item.get("sgdqy")),
                            current_assets=self._safe_float(item.get("ldzc")),
                            current_liabilities=self._safe_float(item.get("ldfz")),
                            cash=self._safe_float(item.get("hbzj")),
                            inventory=self._safe_float(item.get("ch")),
                        ))
            except Exception as e:
                logger.warning(f"Failed to collect balance sheet for {code}: {e}")

        return records

    def _get_record_hash(self, record: Any) -> str:
        return f"{record.code}_{record.report_date}_{getattr(record, 'report_period', 'annual')}"

    async def _is_valid(self, record: Any) -> bool:
        return record.code is not None and record.report_date is not None

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


class DividendDataCollector(FundamentalDataCollector):
    """
    Collector for dividend data (股息分红数据).
    采集历史分红数据，包括每股股息、分红方案等。
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_FUNDAMENTAL,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.ANNUALLY,
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
        return await self._collect_dividend(code)

    async def _collect_dividend(self, code: str) -> list[dict[str, Any]]:
        import aiohttp

        code_id = self._get_code_id(code)
        
        url = "https://emweb.eastmoney.com/PC_HSF10/BonusFinancing/PageAjax"
        params = {
            "code": code_id,
        }

        records = []
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()
                
                if data.get("fhps"):
                    for item in data["fhps"]:
                        records.append({
                            "code": code,
                            "report_year": item.get("rq", "")[:4] if item.get("rq") else None,
                            "ex_date": item.get("cqcxr"),
                            "dividend_per_share": self._safe_float(item.get("sg")),
                            "bonus_per_share": self._safe_float(item.get("pg")),
                            "transfer_per_share": self._safe_float(item.get("zz")),
                            "total_dividend": self._safe_float(item.get("hj")),
                            "dividend_yield": self._safe_float(item.get("gxl")),
                        })
            except Exception as e:
                logger.warning(f"Failed to collect dividend data for {code}: {e}")

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('report_year')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None and record.get("report_year") is not None

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

    def _get_previous_month(self) -> str:
        from datetime import timedelta
        prev = datetime.now() - timedelta(days=30)
        return prev.strftime("%Y-%m-%d")


class Top10HolderCollector(FundamentalDataCollector):
    """
    Collector for top 10 shareholders.
    Migrated from qstock fundamental.py stock_holder_top10 function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_HOLDER,
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
        code = kwargs.get("code")
        n = kwargs.get("n", 1)
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_holders(code, n)

    async def _collect_holders(self, code: str, n: int = 1) -> list[dict[str, Any]]:
        import aiohttp

        code_id = self._get_code_id(code)
        mk = code_id.split(".")[0]
        stock_code = code_id.split(".")[1]
        fc = f"{stock_code}02" if mk == "0" else f"{stock_code}01"

        url0 = "https://emh5.eastmoney.com/api/GuBenGuDong/GetFirstRequest2Data"
        data0 = {"fc": fc}

        async with aiohttp.ClientSession() as session:
            async with session.post(url0, json=data0) as response:
                text = await response.text()
                try:
                    res = json.loads(text)
                except json.JSONDecodeError:
                    res = {}

        dates = []
        if res.get("Result") and res["Result"].get("BaoGaoQi"):
            dates = res["Result"]["BaoGaoQi"]

        records = []
        url = "https://emh5.eastmoney.com/api/GuBenGuDong/GetShiDaLiuTongGuDong"

        async with aiohttp.ClientSession() as session:
            for date in dates[:n]:
                data = {"fc": fc, "BaoGaoQi": date}
                async with session.post(url, json=data) as response:
                    text = await response.text()
                    try:
                        res = json.loads(text)
                    except json.JSONDecodeError:
                        res = {}

                if res.get("Result") and res["Result"].get("ShiDaLiuTongGuDongList"):
                    for item in res["Result"]["ShiDaLiuTongGuDongList"]:
                        records.append({
                            "code": stock_code,
                            "report_date": date,
                            "holder_name": item.get("GuDongMingCheng"),
                            "holder_code": item.get("GuDongDaiMa"),
                            "shares": item.get("ChiGuShu"),
                            "ratio": item.get("ChiGuBiLi"),
                            "change": item.get("ZengJian"),
                            "change_ratio": item.get("BianDongBiLi"),
                        })

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('holder_name')}_{record.get('report_date')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_code_id(self, code: str) -> str:
        if code.isdigit():
            if code.startswith("6"):
                return f"1.{code}"
            else:
                return f"0.{code}"
        return f"0.{code}"


class MainBusinessCollector(FundamentalDataCollector):
    """
    Collector for main business data.
    Migrated from qstock fundamental.py main_business function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_FUNDAMENTAL,
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
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_main_business(code)

    async def _collect_main_business(self, code: str) -> list[dict[str, Any]]:
        import aiohttp
        from bs4 import BeautifulSoup

        if not code.isdigit():
            code = await self._get_code_from_name(code)

        url = f"http://f10.emoney.cn/f10/zygc/{code}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")
        records = []

        try:
            year_items = soup.find(attrs={"class": "swlab_t"})
            if year_items:
                year_list = [item.text.strip() for item in year_items.find_all("li")]

                import pandas as pd
                tables = pd.read_html(html)

                for i, year in enumerate(year_list):
                    if i + 2 < len(tables):
                        df = tables[i + 2]
                        for _, row in df.iterrows():
                            records.append({
                                "code": code,
                                "report_period": year,
                                "classification_direction": row.iloc[0] if len(row) > 0 else None,
                                "classification": row.iloc[1] if len(row) > 1 else None,
                                "operating_income": row.iloc[2] if len(row) > 2 else None,
                                "yoy_growth": row.iloc[3] if len(row) > 3 else None,
                                "income_ratio": row.iloc[4] if len(row) > 4 else None,
                            })
        except Exception as e:
            logger.warning(f"Failed to parse main business: {e}")

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}_{record.get('report_period')}_{record.get('classification')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    async def _get_code_from_name(self, name: str) -> str:
        return name


class FinancialIndicatorCollector(FundamentalDataCollector):
    """
    Collector for financial indicators.
    Migrated from qstock fundamental.py stock_indicator function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.SINA,
                data_type=DataType.STOCK_FINANCIAL_INDICATOR,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.QUARTERLY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.SINA

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[FinancialIndicatorData]:
        code = kwargs.get("code")
        if not code:
            raise ValueError("code parameter is required")
        return await self._collect_indicators(code)

    async def _collect_indicators(self, code: str) -> list[FinancialIndicatorData]:
        import aiohttp
        from bs4 import BeautifulSoup

        if not code.isdigit():
            code = await self._get_code_from_name(code)

        url = f"https://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/stockid/{code}/ctrl/2020/displaytype/4.phtml"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")
        records = []

        try:
            year_context = soup.find(attrs={"id": "con02-1"})
            if year_context:
                year_items = year_context.find("table").find_all("a")
                year_list = [item.text for item in year_items[:5]]

                import pandas as pd

                for year in year_list:
                    year_url = f"https://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/stockid/{code}/ctrl/{year}/displaytype/4.phtml"
                    async with session.get(year_url) as response:
                        year_html = await response.text()

                    try:
                        tables = pd.read_html(year_html)
                        if len(tables) > 12:
                            df = tables[12]
                            if len(df) > 1:
                                df.columns = df.iloc[0]
                                df = df.iloc[1:]

                                for col in df.columns[1:]:
                                    try:
                                        record = FinancialIndicatorData(
                                            code=code,
                                            name="",
                                            report_date=col,
                                            eps=self._safe_float(df.get("每股收益(元)", {}).get(col)),
                                            bps=self._safe_float(df.get("每股净资产(元)", {}).get(col)),
                                            roe=self._safe_float(df.get("净资产收益率(%)", {}).get(col)),
                                        )
                                        records.append(record)
                                    except Exception:
                                        pass
                    except Exception as e:
                        logger.warning(f"Failed to parse year {year}: {e}")
        except Exception as e:
            logger.warning(f"Failed to parse financial indicators: {e}")

        return records

    async def _get_code_from_name(self, name: str) -> str:
        return name

    def _safe_float(self, value: Any) -> float | None:
        if value is None or value == "-" or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class StockValuationCollector(FundamentalDataCollector):
    """
    Collector for stock valuation data.
    Migrated from qstock fundamental.py stock_valuation_by_name function.
    """

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
        return await self._collect_valuation(code)

    async def _collect_valuation(self, code: str) -> list[dict[str, Any]]:
        import aiohttp

        code_id = self._get_code_id(code)

        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "invt": "2",
            "fltt": "2",
            "fields": "f163,f164,f167",
            "secid": code_id,
        }

        url = "http://push2.eastmoney.com/api/qt/stock/get"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data"):
            item = data["data"]
            records.append({
                "code": code,
                "pe_ratio": item.get("f163"),
                "ttm_pe_ratio": item.get("f164"),
                "pb_ratio": item.get("f167"),
            })

        return records

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return f"{record.get('code')}"

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return record.get("code") is not None

    def _get_code_id(self, code: str) -> str:
        if code.isdigit():
            if code.startswith("6"):
                return f"1.{code}"
            else:
                return f"0.{code}"
        return f"0.{code}"
