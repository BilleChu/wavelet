"""
ADS (Analytical Data Store) Models.

This package provides a unified data model layer for all analytical data.
ADS models serve as the single source of truth for business logic.
"""

from openfinance.datacenter.models.analytical.base import (
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

from openfinance.datacenter.models.analytical.market import (
    ADSKLineModel,
    ADSMoneyFlowModel,
    ADSOptionQuoteModel,
    ADSFutureQuoteModel,
    ADSStockBasicModel,
)

from openfinance.datacenter.models.analytical.financial import (
    ADSFinancialIndicatorModel,
    ADSBalanceSheetModel,
    ADSIncomeStatementModel,
    ADSCashFlowModel,
)

from openfinance.datacenter.models.analytical.shareholder import (
    ADSShareholderModel,
    ADSShareholderChangeModel,
    ADSInsiderTradingModel,
)

from openfinance.datacenter.models.analytical.sentiment import (
    ADSMarketSentimentModel,
    ADSNewsModel,
    ADSStockSentimentModel,
)

from openfinance.datacenter.models.analytical.macro import (
    ADSMacroEconomicModel,
    ADSInterestRateModel,
    ADSExchangeRateModel,
)

from openfinance.datacenter.models.analytical.quant import (
    ADSFactorModel,
    ADSSignalModel,
    ADSBacktestResultModel,
)

from openfinance.datacenter.models.analytical.meta import (
    ADSMetaModel,
    ADSFieldMetaModel,
)

from openfinance.datacenter.models.analytical.repository import (
    GenericADSRepository,
    ADSKLineRepository,
    ADSFactorRepository,
    ADSRepository,
)

from openfinance.datacenter.models.analytical.registry import (
    ADSModelRegistry,
    ADSModelDefinition,
    ADSFieldDefinition,
    register_ads_model,
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
    "GenericADSRepository",
    "ADSKLineRepository",
    "ADSFactorRepository",
    "ADSRepository",
    "ADSModelRegistry",
    "ADSModelDefinition",
    "ADSFieldDefinition",
    "register_ads_model",
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
    from openfinance.datacenter.models.analytical.service import get_ads_service as _get_ads_service
    return _get_ads_service()


def ADSConfig():
    """ADS Configuration (lazy import)."""
    from openfinance.datacenter.models.analytical.service import ADSConfig as _ADSConfig
    return _ADSConfig


def ADSService():
    """ADS Service (lazy import)."""
    from openfinance.datacenter.models.analytical.service import ADSService as _ADSService
    return _ADSService
