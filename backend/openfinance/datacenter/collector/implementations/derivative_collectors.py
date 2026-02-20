"""
Derivative data collectors for options and futures.

This module provides collectors for derivative instruments including
stock options, index options, and futures contracts.
"""

import logging
from datetime import datetime
from typing import Any

from ..core.base_collector import (
    CollectionConfig,
    CollectionResult,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    FutureData,
    OptionData,
)
from ..quant_collector import QuantDataCollector

logger = logging.getLogger(__name__)


class OptionDataCollector(QuantDataCollector[OptionData]):
    """
    Collector for stock/index options data.

    Collects option chain data including prices, Greeks, and implied volatility
    from Shanghai and Shenzhen stock exchanges.
    """

    EXCHANGE_URLS = {
        DataSource.SSE_OPTION: "https://www.sse.com.cn",
        DataSource.SZSE_OPTION: "http://www.szse.cn",
    }

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.SSE_OPTION,
                data_type=DataType.OPTION_QUOTE,
                category=DataCategory.DERIVATIVE,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return self.config.source

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[OptionData]:
        underlying = kwargs.get("underlying", "510050")
        return await self._collect_option_chain(underlying)

    async def _collect_option_chain(self, underlying: str) -> list[OptionData]:
        import aiohttp

        url = "https://stock.finance.sina.com.cn/futures/api/jsonp.php/var=/Option/OptionChain"
        params = {
            "type": "futures",
            "underlying": underlying,
            "exchange": "null",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://stock.finance.sina.com.cn/",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                text = await response.text()

        records = []
        try:
            import json
            import re

            match = re.search(r"var\s+=\s+(\[.*\])", text)
            if match:
                data = json.loads(match.group(1))

                for item in data:
                    try:
                        record = OptionData(
                            code=item.get("option_code", ""),
                            name=item.get("name", ""),
                            underlying=underlying,
                            strike_price=self._safe_float(item.get("strike")),
                            expiry_date=item.get("expire_date", ""),
                            option_type=item.get("option_type", "call"),
                            last_price=self._safe_float(item.get("last")),
                            bid_price=self._safe_float(item.get("bid")),
                            ask_price=self._safe_float(item.get("ask")),
                            volume=self._safe_int(item.get("volume")),
                            open_interest=self._safe_int(item.get("open_interest")),
                            implied_volatility=self._safe_float(item.get("iv")),
                            delta=self._safe_float(item.get("delta")),
                            gamma=self._safe_float(item.get("gamma")),
                            theta=self._safe_float(item.get("theta")),
                            vega=self._safe_float(item.get("vega")),
                            rho=self._safe_float(item.get("rho")),
                            trade_date=datetime.now().strftime("%Y-%m-%d"),
                        )
                        records.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to parse option record: {e}")

        except Exception as e:
            logger.error(f"Failed to parse option chain data: {e}")

        logger.info(f"Collected {len(records)} option records for {underlying}")
        return records

    async def _normalize_for_quant(self, data: list[OptionData]) -> list[OptionData]:
        return data

    async def _compute_factors(self, data: list[OptionData]) -> None:
        if not data:
            return

        ivs = [d.implied_volatility for d in data if d.implied_volatility]
        if ivs:
            self._factor_cache["avg_iv"] = sum(ivs) / len(ivs)

        deltas = [d.delta for d in data if d.delta]
        if deltas:
            self._factor_cache["avg_delta"] = sum(deltas) / len(deltas)

    def _get_record_hash(self, record: OptionData) -> str:
        return f"{record.code}_{record.trade_date}"

    async def _is_valid(self, record: OptionData) -> bool:
        return bool(record.code and record.trade_date)

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


class FutureDataCollector(QuantDataCollector[FutureData]):
    """
    Collector for futures data.

    Collects futures contract data from major Chinese exchanges:
    - SHFE: Shanghai Futures Exchange
    - DCE: Dalian Commodity Exchange
    - CZCE: Zhengzhou Commodity Exchange
    - CFFEX: China Financial Futures Exchange
    """

    EXCHANGE_MAP = {
        "SHFE": DataSource.SHFE,
        "DCE": DataSource.DCE,
        "CZCE": DataSource.CZCE,
        "CFFEX": DataSource.CFFEX,
    }

    EXCHANGE_NAMES = {
        DataSource.SHFE: "上海期货交易所",
        DataSource.DCE: "大连商品交易所",
        DataSource.CZCE: "郑州商品交易所",
        DataSource.CFFEX: "中国金融期货交易所",
    }

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.SHFE,
                data_type=DataType.FUTURE_QUOTE,
                category=DataCategory.DERIVATIVE,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return self.config.source

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[FutureData]:
        exchange = kwargs.get("exchange", "SHFE")
        return await self._collect_future_quotes(exchange)

    async def _collect_future_quotes(self, exchange: str) -> list[FutureData]:
        import aiohttp

        url = "https://push2.eastmoney.com/api/qt/clist/get"
        exchange_code = self.EXCHANGE_MAP.get(exchange, DataSource.SHFE)

        fs_map = {
            "SHFE": "m:113",
            "DCE": "m:114",
            "CZCE": "m:115",
            "CFFEX": "m:8",
        }

        fs = fs_map.get(exchange, "m:113")

        params = {
            "pn": "1",
            "pz": "500",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": fs,
            "fields": "f1,f2,f3,f4,f5,f6,f7,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f140,f141,f207,f208,f209,f222,f225,f239,f240,f241,f242,f243,f244,f245,f246,f247,f248,f250,f251,f252,f253,f254,f255,f256",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()

        records = []
        if data.get("data") and data["data"].get("diff"):
            for item in data["data"]["diff"]:
                try:
                    record = FutureData(
                        code=item.get("f12", ""),
                        name=item.get("f14", ""),
                        exchange=exchange,
                        delivery_month=self._extract_delivery_month(item.get("f14", "")),
                        open=self._safe_float(item.get("f17")),
                        high=self._safe_float(item.get("f15")),
                        low=self._safe_float(item.get("f16")),
                        close=self._safe_float(item.get("f2")),
                        pre_settlement=self._safe_float(item.get("f18")),
                        settlement=self._safe_float(item.get("f2")),
                        change=self._safe_float(item.get("f4")),
                        change_pct=self._safe_float(item.get("f3")),
                        volume=self._safe_int(item.get("f5")),
                        amount=self._safe_float(item.get("f6")),
                        open_interest=self._safe_int(item.get("f7")),
                        trade_date=datetime.now().strftime("%Y-%m-%d"),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse future record: {e}")

        logger.info(f"Collected {len(records)} future records for {exchange}")
        return records

    def _extract_delivery_month(self, name: str) -> str:
        import re

        match = re.search(r"(\d{4})", name)
        if match:
            return match.group(1)
        return ""

    async def _normalize_for_quant(self, data: list[FutureData]) -> list[FutureData]:
        return data

    async def _compute_factors(self, data: list[FutureData]) -> None:
        if not data:
            return

        changes = [d.change_pct for d in data if d.change_pct is not None]
        if changes:
            self._factor_cache["avg_change_pct"] = sum(changes) / len(changes)

        volumes = [d.volume for d in data if d.volume is not None]
        if volumes:
            self._factor_cache["total_volume"] = sum(volumes)

        oi = [d.open_interest for d in data if d.open_interest is not None]
        if oi:
            self._factor_cache["total_open_interest"] = sum(oi)

    def _get_record_hash(self, record: FutureData) -> str:
        return f"{record.code}_{record.trade_date}"

    async def _is_valid(self, record: FutureData) -> bool:
        return bool(record.code and record.trade_date)

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


class OptionGreeksCollector(OptionDataCollector):
    """
    Specialized collector for option Greeks data.

    Focuses on collecting and computing Greeks for options analysis.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.SSE_OPTION,
                data_type=DataType.OPTION_GREEKS,
                category=DataCategory.DERIVATIVE,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[OptionData]:
        underlying = kwargs.get("underlying", "510050")
        records = await self._collect_option_chain(underlying)

        for record in records:
            if record.delta is None or record.gamma is None:
                computed = await self._compute_greeks(record)
                record.delta = computed.get("delta")
                record.gamma = computed.get("gamma")
                record.theta = computed.get("theta")
                record.vega = computed.get("vega")
                record.rho = computed.get("rho")

        return records

    async def _compute_greeks(self, option: OptionData) -> dict[str, float]:
        import math

        S = 2.5
        K = option.strike_price or S
        T = 0.25
        r = 0.03
        sigma = option.implied_volatility or 0.2

        if sigma <= 0:
            sigma = 0.2

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        def norm_cdf(x):
            return 0.5 * (1 + math.erf(x / math.sqrt(2)))

        def norm_pdf(x):
            return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

        delta = norm_cdf(d1) if option.option_type == "call" else norm_cdf(d1) - 1
        gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
        theta = (
            -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T) * norm_cdf(d2)
        ) / 365
        vega = S * norm_pdf(d1) * math.sqrt(T) / 100
        rho = K * T * math.exp(-r * T) * norm_cdf(d2) / 100

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 4),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
            "rho": round(rho, 4),
        }


class ImpliedVolatilityCollector(OptionDataCollector):
    """
    Specialized collector for implied volatility data.

    Collects and computes implied volatility surface data.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.SSE_OPTION,
                data_type=DataType.OPTION_IV,
                category=DataCategory.DERIVATIVE,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    async def _collect(self, **kwargs: Any) -> list[OptionData]:
        underlying = kwargs.get("underlying", "510050")
        records = await self._collect_option_chain(underlying)

        iv_surface = self._build_iv_surface(records)
        self._factor_cache["iv_surface"] = iv_surface

        return records

    def _build_iv_surface(self, records: list[OptionData]) -> dict[str, Any]:
        surface = {"calls": {}, "puts": {}}

        for record in records:
            if record.implied_volatility is None:
                continue

            expiry = record.expiry_date
            strike = record.strike_price

            key = f"{expiry}_{strike}"

            if record.option_type == "call":
                if expiry not in surface["calls"]:
                    surface["calls"][expiry] = {}
                surface["calls"][expiry][strike] = record.implied_volatility
            else:
                if expiry not in surface["puts"]:
                    surface["puts"][expiry] = {}
                surface["puts"][expiry][strike] = record.implied_volatility

        return surface
