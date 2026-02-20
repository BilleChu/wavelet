"""
Data Models Module for Data Center.

This module provides:
- ADS: Analytical Data Store models (unified business layer)
- Framework: Generic model management infrastructure
- ORM: SQLAlchemy database models

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    ADS Models (Business Layer)               │
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
]
