"""
Data Models Module for Data Center.

This module provides:
- Analytical: Analytical Data Store models (unified business layer)
- Framework: Generic model management infrastructure
- ORM: SQLAlchemy database models

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    Analytical Models (Business Layer)        │
│         Unified data models for all business logic          │
├─────────────────────────────────────────────────────────────┤
│                    Model Framework                           │
│         (registry, transformer, mapping)                     │
├─────────────────────────────────────────────────────────────┤
│                    ORM Models                                │
│         (SQLAlchemy models for database)                     │
└─────────────────────────────────────────────────────────────┘
"""

from .framework import (
    ModelRegistry,
    ModelMetadata,
    ModelCapability,
    register_model,
    ModelTransformer,
    FieldMapping,
    ADSORMTransformer,
    create_orm_to_ads_transformer,
    register_ads_orm_mapping,
)

from .mappings import (
    register_all_mappings,
    MAPPING_CONFIG,
)

from .orm import (
    Base,
    EntityModel,
    RelationModel,
    TaskChainModel,
    TaskExecutionModel,
    MonitoringMetricModel,
    AlertModel,
    ScheduledTaskModel,
    StockBasicModel,
    StockDailyQuoteModel,
    StockFinancialIndicatorModel,
    StockMoneyFlowModel,
    OptionQuoteModel,
    FutureQuoteModel,
    FactorDataModel,
    NewsModel,
    MacroEconomicModel,
    ESGRatingModel,
    EventModel,
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
    ENTITY_TYPE_LABELS,
    RELATION_TYPE_LABELS,
)

from openfinance.datacenter.models.analytical import (
    ADSModel,
    ADSModelWithCode,
    ADSModelWithDate,
    ADSModelWithReportDate,
    ADSDataBatch,
    DataCategory,
    DataQuality,
    MarketType,
    ReportPeriod,
    ADSKLineModel,
    ADSMoneyFlowModel,
    ADSOptionQuoteModel,
    ADSFutureQuoteModel,
    ADSStockBasicModel,
    ADSFinancialIndicatorModel,
    ADSBalanceSheetModel,
    ADSIncomeStatementModel,
    ADSCashFlowModel,
    ADSShareholderModel,
    ADSShareholderChangeModel,
    ADSInsiderTradingModel,
    ADSMarketSentimentModel,
    ADSNewsModel,
    ADSStockSentimentModel,
    ADSMacroEconomicModel,
    ADSInterestRateModel,
    ADSExchangeRateModel,
    ADSFactorModel,
    ADSSignalModel,
    ADSBacktestResultModel,
    ADSMetaModel,
    ADSFieldMetaModel,
    get_model as get_ads_model,
)

__all__ = [
    "ModelRegistry",
    "ModelMetadata",
    "ModelCapability",
    "register_model",
    "ModelTransformer",
    "FieldMapping",
    "ADSORMTransformer",
    "create_orm_to_ads_transformer",
    "register_ads_orm_mapping",
    "register_all_mappings",
    "MAPPING_CONFIG",
    "Base",
    "EntityModel",
    "RelationModel",
    "TaskChainModel",
    "TaskExecutionModel",
    "MonitoringMetricModel",
    "AlertModel",
    "ScheduledTaskModel",
    "StockBasicModel",
    "StockDailyQuoteModel",
    "StockFinancialIndicatorModel",
    "StockMoneyFlowModel",
    "OptionQuoteModel",
    "FutureQuoteModel",
    "FactorDataModel",
    "NewsModel",
    "MacroEconomicModel",
    "ESGRatingModel",
    "EventModel",
    "VALID_ENTITY_TYPES",
    "VALID_RELATION_TYPES",
    "ENTITY_TYPE_LABELS",
    "RELATION_TYPE_LABELS",
    "ADSModel",
    "ADSModelWithCode",
    "ADSModelWithDate",
    "ADSModelWithReportDate",
    "ADSDataBatch",
    "DataCategory",
    "DataQuality",
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
    "get_ads_model",
]
