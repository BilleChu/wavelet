"""
US Stock market data collectors using yfinance.

This module provides collectors for US stock market data including
real-time quotes, historical K-lines, financial statements, and company info.
"""

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

logger = logging.getLogger(__name__)


class USStockListCollector(MarketDataCollector):
    """
    Collector for US stock list from major indices (S&P 500, NASDAQ 100, DOW).
    使用 yfinance 获取美股主要指数成分股列表。
    """

    MARKET_CODES = {
        "sp500": "^GSPC",
        "nasdaq100": "^NDX",
        "dow": "^DJI",
        "russell2000": "^RUT",
    }

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.YFINANCE,
                data_type=DataType.STOCK_QUOTE_REALTIME,
                category=DataCategory.MARKET,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.YFINANCE

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[StockQuoteData]:
        index = kwargs.get("index", "sp500")
        return await self._collect_stock_list(index)

    async def _collect_stock_list(self, index: str) -> list[StockQuoteData]:
        import yfinance as yf

        ticker_symbol = self.MARKET_CODES.get(index, "^GSPC")

        records = []
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1d")

            if not hist.empty:
                record = StockQuoteData(
                    code=ticker_symbol,
                    name=f"{index.upper()} Index",
                    trade_date=datetime.now().strftime("%Y-%m-%d"),
                    open=float(hist['Open'].iloc[0]),
                    high=float(hist['High'].iloc[0]),
                    low=float(hist['Low'].iloc[0]),
                    close=float(hist['Close'].iloc[0]),
                    volume=int(hist['Volume'].iloc[0]),
                )
                records.append(record)
        except Exception as e:
            logger.warning(f"Failed to collect {index} data: {e}")

        return records


class USStockQuoteCollector(MarketDataCollector):
    """
    Collector for US stock real-time and historical quotes.
    使用 yfinance 获取美股实时和历史行情数据。
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.YFINANCE,
                data_type=DataType.STOCK_QUOTE,
                category=DataCategory.MARKET,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.YFINANCE

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
        import yfinance as yf

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        records = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)

                for index, row in hist.iterrows():
                    record = StockQuoteData(
                        code=symbol,
                        name=symbol,
                        trade_date=index.strftime("%Y-%m-%d"),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume']),
                    )
                    records.append(record)

            except Exception as e:
                logger.warning(f"Failed to collect quotes for {symbol}: {e}")

        return records


class USFinancialStatementCollector(MarketDataCollector):
    """
    Collector for US stock financial statements.
    使用 yfinance 获取美股财务报表数据。
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.YFINANCE,
                data_type=DataType.STOCK_FINANCIAL_REPORT,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.QUARTERLY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.YFINANCE

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
        import yfinance as yf

        records = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)

                income_stmt = ticker.financials
                if not income_stmt.empty:
                    for col in income_stmt.columns:
                        for idx in income_stmt.index:
                            records.append({
                                "symbol": symbol,
                                "statement_type": "income",
                                "item": idx,
                                "value": income_stmt.loc[idx, col],
                                "report_date": col.strftime("%Y-%m-%d"),
                            })

                balance_sheet = ticker.balance_sheet
                if not balance_sheet.empty:
                    for col in balance_sheet.columns:
                        for idx in balance_sheet.index:
                            records.append({
                                "symbol": symbol,
                                "statement_type": "balance",
                                "item": idx,
                                "value": balance_sheet.loc[idx, col],
                                "report_date": col.strftime("%Y-%m-%d"),
                            })

                cash_flow = ticker.cashflow
                if not cash_flow.empty:
                    for col in cash_flow.columns:
                        for idx in cash_flow.index:
                            records.append({
                                "symbol": symbol,
                                "statement_type": "cashflow",
                                "item": idx,
                                "value": cash_flow.loc[idx, col],
                                "report_date": col.strftime("%Y-%m-%d"),
                            })

            except Exception as e:
                logger.warning(f"Failed to collect financials for {symbol}: {e}")

        return records


class USCompanyInfoCollector(MarketDataCollector):
    """
    Collector for US stock company information.
    使用 yfinance 获取美股公司基本信息。
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.YFINANCE,
                data_type=DataType.STOCK_FUNDAMENTAL,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.YFINANCE

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        symbols = kwargs.get("symbols", self.config.symbols)
        if isinstance(symbols, str):
            symbols = [symbols]

        return await self._collect_company_info(symbols)

    async def _collect_company_info(self, symbols: list[str]) -> list[dict[str, Any]]:
        import yfinance as yf

        records = []
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                records.append({
                    "symbol": symbol,
                    "company_name": info.get("longName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "country": info.get("country"),
                    "website": info.get("website"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "dividend_yield": info.get("dividendYield"),
                    "beta": info.get("beta"),
                    "avg_volume": info.get("averageVolume"),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                    "description": info.get("longBusinessSummary"),
                })

            except Exception as e:
                logger.warning(f"Failed to collect company info for {symbol}: {e}")

        return records


class USMacroDataCollector(MarketDataCollector):
    """
    Collector for US macro economic data from FRED.
    使用 fredapi 获取美国宏观经济数据。
    """

    INDICATOR_NAMES = {
        "GDP": "Gross Domestic Product",
        "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
        "UNRATE": "Unemployment Rate",
        "FEDFUNDS": "Federal Funds Rate",
        "DGS10": "10-Year Treasury Yield",
    }

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.FRED,
                data_type=DataType.MACRO_DATA,
                category=DataCategory.MACRO,
                frequency=DataFrequency.MONTHLY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.FRED

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        indicators = kwargs.get("indicators", ["GDP", "CPIAUCSL", "UNRATE"])
        return await self._collect_macro_data(indicators)

    async def _collect_macro_data(self, indicators: list[str]) -> list[dict[str, Any]]:
        try:
            from fredapi import Fred
            import os

            fred = Fred(api_key=os.getenv("FRED_API_KEY"))

            records = []
            for indicator in indicators:
                try:
                    data = fred.get_series(indicator)
                    for date, value in data.items():
                        records.append({
                            "indicator_code": indicator,
                            "indicator_name": self.INDICATOR_NAMES.get(indicator, indicator),
                            "value": float(value),
                            "period": date.strftime("%Y-%m-%d"),
                            "country": "US",
                            "source": "fred",
                        })
                except Exception as e:
                    logger.warning(f"Failed to collect {indicator}: {e}")

            return records

        except ImportError:
            logger.warning("fredapi not installed, skipping FRED data collection")
            return []
