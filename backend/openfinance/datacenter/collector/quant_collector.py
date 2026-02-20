"""
Quantitative data collector base classes.

This module provides specialized collectors for quantitative analysis data,
including factor data, market data, and fundamental data optimized for
quantitative models.
"""

import logging
from abc import abstractmethod
from datetime import datetime
from typing import Any, Generic, TypeVar

from .core.base_collector import (
    BaseCollector,
    CollectionConfig,
    CollectionResult,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    FactorData,
    FinancialIndicatorData,
    MoneyFlowData,
    StockQuoteData,
)

T = TypeVar("T")

logger = logging.getLogger(__name__)


class QuantDataCollector(BaseCollector[T], Generic[T]):
    """
    Base class for quantitative analysis data collectors.

    Provides specialized functionality for collecting data optimized for
    quantitative analysis, including factor computation, data normalization,
    and time-series alignment.
    """

    def __init__(self, config: CollectionConfig) -> None:
        if config.category == DataCategory.MARKET:
            config.category = DataCategory.MARKET
        super().__init__(config)
        self._factor_cache: dict[str, Any] = {}
        self._normalization_params: dict[str, dict[str, float]] = {}

    @property
    def collector_type(self) -> str:
        return "quant_data"

    async def collect_for_quant(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        frequency: DataFrequency = DataFrequency.DAILY,
        **kwargs: Any,
    ) -> CollectionResult[T]:
        """
        Collect data optimized for quantitative analysis.

        Args:
            symbols: List of stock codes
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            frequency: Data frequency
            **kwargs: Additional parameters

        Returns:
            CollectionResult with collected data
        """
        self.config.symbols = symbols
        self.config.start_date = start_date
        self.config.end_date = end_date
        self.config.frequency = frequency

        result = await self.collect(**kwargs)

        if result.success and result.data:
            result.data = await self._normalize_for_quant(result.data)
            await self._compute_factors(result.data)

        return result

    @abstractmethod
    async def _normalize_for_quant(self, data: list[T]) -> list[T]:
        """
        Normalize data for quantitative analysis.

        This includes:
        - Handling missing values
        - Removing outliers
        - Standardizing formats
        - Aligning time series
        """
        pass

    @abstractmethod
    async def _compute_factors(self, data: list[T]) -> None:
        """
        Compute quantitative factors from collected data.

        This method populates the factor cache with computed factors
        that can be used for quantitative analysis.
        """
        pass

    def get_factor(self, factor_name: str) -> Any:
        """Get computed factor by name."""
        return self._factor_cache.get(factor_name)

    def get_all_factors(self) -> dict[str, Any]:
        """Get all computed factors."""
        return self._factor_cache.copy()

    def set_normalization_params(
        self, field: str, mean: float, std: float
    ) -> None:
        """Set normalization parameters for a field."""
        self._normalization_params[field] = {"mean": mean, "std": std}

    def normalize_value(self, field: str, value: float) -> float:
        """Normalize a value using stored parameters."""
        params = self._normalization_params.get(field)
        if params:
            return (value - params["mean"]) / params["std"]
        return value


class MarketDataCollector(QuantDataCollector[StockQuoteData]):
    """
    Collector for market data (quotes, prices, volumes).

    Specialized for collecting and processing market data for
    quantitative analysis.
    """

    def __init__(self, config: CollectionConfig) -> None:
        if config.data_type == DataType.STOCK_QUOTE:
            config.data_type = DataType.STOCK_QUOTE
        super().__init__(config)
        self._price_adjustment_factor: float = 1.0

    async def _normalize_for_quant(
        self, data: list[StockQuoteData]
    ) -> list[StockQuoteData]:
        """Normalize market data for quantitative analysis."""
        normalized = []
        for record in data:
            if record.close is not None and record.close > 0:
                normalized.append(record)
        return normalized

    async def _compute_factors(self, data: list[StockQuoteData]) -> None:
        """Compute market-based factors."""
        if not data:
            return

        returns = []
        volumes = []
        for record in data:
            if record.close and record.pre_close and record.pre_close > 0:
                ret = (record.close - record.pre_close) / record.pre_close
                returns.append(ret)
            if record.volume:
                volumes.append(record.volume)

        if returns:
            self._factor_cache["avg_return"] = sum(returns) / len(returns)
            self._factor_cache["volatility"] = self._calculate_std(returns)

        if volumes:
            self._factor_cache["avg_volume"] = sum(volumes) / len(volumes)

    def _calculate_std(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance**0.5

    def _get_record_hash(self, record: StockQuoteData) -> str:
        return f"{record.code}_{record.trade_date}"

    async def _is_valid(self, record: StockQuoteData) -> bool:
        if not record.code or not record.trade_date:
            return False
        if record.close is not None and record.close < 0:
            return False
        return True


class FundamentalDataCollector(QuantDataCollector[FinancialIndicatorData]):
    """
    Collector for fundamental data (financial indicators, ratios).

    Specialized for collecting and processing fundamental data for
    quantitative analysis.
    """

    def __init__(self, config: CollectionConfig) -> None:
        if config.data_type == DataType.STOCK_FINANCIAL_INDICATOR:
            config.data_type = DataType.STOCK_FINANCIAL_INDICATOR
        super().__init__(config)

    async def _normalize_for_quant(
        self, data: list[FinancialIndicatorData]
    ) -> list[FinancialIndicatorData]:
        """Normalize fundamental data for quantitative analysis."""
        normalized = []
        for record in data:
            if record.roe is not None and -100 < record.roe < 100:
                normalized.append(record)
        return normalized

    async def _compute_factors(self, data: list[FinancialIndicatorData]) -> None:
        """Compute fundamental factors."""
        if not data:
            return

        roe_values = [r.roe for r in data if r.roe is not None]
        revenue_growth = [r.revenue_yoy for r in data if r.revenue_yoy is not None]

        if roe_values:
            self._factor_cache["avg_roe"] = sum(roe_values) / len(roe_values)
        if revenue_growth:
            self._factor_cache["avg_revenue_growth"] = sum(revenue_growth) / len(
                revenue_growth
            )

    def _get_record_hash(self, record: FinancialIndicatorData) -> str:
        return f"{record.code}_{record.report_date}"

    async def _is_valid(self, record: FinancialIndicatorData) -> bool:
        if not record.code or not record.report_date:
            return False
        return True


class MoneyFlowDataCollector(QuantDataCollector[MoneyFlowData]):
    """
    Collector for money flow data.

    Specialized for collecting and processing money flow data for
    quantitative analysis.
    """

    def __init__(self, config: CollectionConfig) -> None:
        if config.data_type == DataType.STOCK_MONEY_FLOW:
            config.data_type = DataType.STOCK_MONEY_FLOW
        super().__init__(config)

    async def _normalize_for_quant(
        self, data: list[MoneyFlowData]
    ) -> list[MoneyFlowData]:
        """Normalize money flow data for quantitative analysis."""
        return data

    async def _compute_factors(self, data: list[MoneyFlowData]) -> None:
        """Compute money flow factors."""
        if not data:
            return

        main_inflows = [r.main_net_inflow for r in data if r.main_net_inflow]
        north_inflows = [r.north_net_inflow for r in data if r.north_net_inflow]

        if main_inflows:
            self._factor_cache["total_main_inflow"] = sum(main_inflows)
        if north_inflows:
            self._factor_cache["total_north_inflow"] = sum(north_inflows)

    def _get_record_hash(self, record: MoneyFlowData) -> str:
        return f"{record.code}_{record.trade_date}"

    async def _is_valid(self, record: MoneyFlowData) -> bool:
        if not record.code or not record.trade_date:
            return False
        return True


class FactorDataCollector(QuantDataCollector[FactorData]):
    """
    Collector for pre-computed factor data.

    Specialized for collecting and storing factor values from
    external factor libraries or computed factors.
    """

    def __init__(self, config: CollectionConfig) -> None:
        config.data_type = DataType.FACTOR_DATA
        config.category = DataCategory.MARKET
        super().__init__(config)

    async def _normalize_for_quant(self, data: list[FactorData]) -> list[FactorData]:
        """Normalize factor data."""
        return data

    async def _compute_factors(self, data: list[FactorData]) -> None:
        """Store factor values in cache."""
        for record in data:
            key = f"{record.factor_id}_{record.code}_{record.trade_date}"
            self._factor_cache[key] = record.factor_value

    def _get_record_hash(self, record: FactorData) -> str:
        return f"{record.factor_id}_{record.code}_{record.trade_date}"

    async def _is_valid(self, record: FactorData) -> bool:
        if not record.factor_id or not record.code or not record.trade_date:
            return False
        return True
