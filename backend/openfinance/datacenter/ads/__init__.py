"""
ADS (Analytical Data Store) Models.

This package provides a unified data model layer for all analytical data.
ADS models serve as the single source of truth for business logic.
"""

from openfinance.datacenter.ads.base import (
    ADSModel,
    ADSModelWithCode,
    ADSModelWithDate,
    ADSModelWithReportDate,
    ADSDataBatch,
    DataCategory,
    DataQuality,
    FieldMapping,
    ModelMapping,
    MarketType,
    ReportPeriod,
)

from openfinance.datacenter.ads.market import (
    ADSKLineModel,
    ADSMoneyFlowModel,
    ADSOptionQuoteModel,
    ADSFutureQuoteModel,
    ADSStockBasicModel,
)

from openfinance.datacenter.ads.financial import (
    ADSFinancialIndicatorModel,
    ADSBalanceSheetModel,
    ADSIncomeStatementModel,
    ADSCashFlowModel,
)

from openfinance.datacenter.ads.shareholder import (
    ADSShareholderModel,
    ADSShareholderChangeModel,
    ADSInsiderTradingModel,
)

from openfinance.datacenter.ads.sentiment import (
    ADSMarketSentimentModel,
    ADSNewsModel,
    ADSStockSentimentModel,
)

from openfinance.datacenter.ads.macro import (
    ADSMacroEconomicModel,
    ADSInterestRateModel,
    ADSExchangeRateModel,
)

from openfinance.datacenter.ads.quant import (
    ADSFactorModel,
    ADSSignalModel,
    ADSBacktestResultModel,
)

from openfinance.datacenter.ads.meta import (
    ADSMetaModel,
    ADSFieldMetaModel,
)


__all__ = [
    "ADSModel",
    "ADSModelWithCode",
    "ADSModelWithDate",
    "ADSModelWithReportDate",
    "ADSDataBatch",
    "DataCategory",
    "DataQuality",
    "FieldMapping",
    "ModelMapping",
    "MarketType",
    "ReportPeriod",
    "ADSKLineModel",
    "ADSMoneyFlowModel",
    "ADSOptionQuoteModel",
    "ADSFutureQuoteModel",
    "ADSStockBasicModel",
    "ADSFinancialIndicatorModel",
    "ADSBalanceSheetModel",
    "ADSIncomeStatementModel",
    "ADSCashFlowModel",
    "ADSShareholderModel",
    "ADSShareholderChangeModel",
    "ADSInsiderTradingModel",
    "ADSMarketSentimentModel",
    "ADSNewsModel",
    "ADSStockSentimentModel",
    "ADSMacroEconomicModel",
    "ADSInterestRateModel",
    "ADSExchangeRateModel",
    "ADSFactorModel",
    "ADSSignalModel",
    "ADSBacktestResultModel",
    "ADSMetaModel",
    "ADSFieldMetaModel",
    "ADSService",
    "ADSConfig",
    "get_ads_service",
]


MODEL_REGISTRY: dict[str, type[ADSModel]] = {
    "kline": ADSKLineModel,
    "money_flow": ADSMoneyFlowModel,
    "option_quote": ADSOptionQuoteModel,
    "future_quote": ADSFutureQuoteModel,
    "stock_basic": ADSStockBasicModel,
    "financial_indicator": ADSFinancialIndicatorModel,
    "balance_sheet": ADSBalanceSheetModel,
    "income_statement": ADSIncomeStatementModel,
    "cash_flow": ADSCashFlowModel,
    "shareholder": ADSShareholderModel,
    "shareholder_change": ADSShareholderChangeModel,
    "insider_trading": ADSInsiderTradingModel,
    "market_sentiment": ADSMarketSentimentModel,
    "news": ADSNewsModel,
    "stock_sentiment": ADSStockSentimentModel,
    "macro_economic": ADSMacroEconomicModel,
    "interest_rate": ADSInterestRateModel,
    "exchange_rate": ADSExchangeRateModel,
    "factor": ADSFactorModel,
    "signal": ADSSignalModel,
    "backtest_result": ADSBacktestResultModel,
    "meta": ADSMetaModel,
    "field_meta": ADSFieldMetaModel,
}


def get_model(model_id: str) -> type[ADSModel] | None:
    """Get ADS model class by model ID."""
    return MODEL_REGISTRY.get(model_id)


def get_ads_service():
    """Get the global ADS service instance (lazy import to avoid circular dependency)."""
    from openfinance.datacenter.ads.service import get_ads_service as _get_ads_service
    return _get_ads_service()


def ADSConfig():
    """ADS Configuration (lazy import)."""
    from openfinance.datacenter.ads.service import ADSConfig as _ADSConfig
    return _ADSConfig


def ADSService():
    """ADS Service (lazy import)."""
    from openfinance.datacenter.ads.service import ADSService as _ADSService
    return _ADSService
