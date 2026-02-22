"""
Data Center System for OpenFinance.

This module provides comprehensive data management including:
- Collector: Multi-source data acquisition and cleaning
- Models: ORM models, framework, and mappings
- Observability: Quality checking, monitoring, lineage
- Marketplace: Data service marketplace
- Task: Task scheduling and execution
- Core: Core utilities (config, conversion, HTTP client)

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    Marketplace Layer                         │
│         (Data Service Marketplace, Gateway)                 │
├─────────────────────────────────────────────────────────────┤
│                    Task Layer                                │
│         (DAG Engine, Scheduler, Executors)                  │
├─────────────────────────────────────────────────────────────┤
│                    Observability Layer                       │
│         (Quality, Monitoring, Lineage)                      │
├─────────────────────────────────────────────────────────────┤
│                    Models Layer                              │
│         (Analytical, ORM, Framework, Mappings)              │
├─────────────────────────────────────────────────────────────┤
│                    Collector Layer                           │
│         (Source, Core, Implementations)                     │
├─────────────────────────────────────────────────────────────┤
│                    Core Layer                                │
│         (Config, Utils, HTTP Client)                        │
└─────────────────────────────────────────────────────────────┘
"""

from openfinance.datacenter.collector import (
    BaseCollector,
    CollectionConfig,
    CollectionResult,
    CollectionStatus,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    QuantDataCollector,
    MarketDataCollector,
    MarketRealtimeCollector,
    KLineCollector,
    SourceRegistry,
    SourceConfig,
    SourceType,
    SourceStatus,
    get_source_registry,
)

from openfinance.datacenter.core import (
    safe_float,
    safe_int,
    safe_str,
    CodeUtils,
    normalize_code,
    HttpClient,
    FieldMappingRegistry,
    DatacenterConfig,
)

from openfinance.datacenter.observability import (
    DataQualityChecker,
    QualityDimension,
    QualityReport,
    QualityRule,
    DataValidator,
    ValidationRule,
    ValidationResult,
    UnifiedMonitor,
    Alert,
    AlertSeverity,
    AlertRule,
    MetricsCollector,
    get_unified_monitor,
)

from openfinance.datacenter.marketplace import (
    DataGateway,
    DataServiceRegistry,
    ServiceMonitor,
)

from openfinance.datacenter.models.analytical import (
    ADSModel,
    ADSKLineModel,
    ADSFactorModel,
    ADSFinancialIndicatorModel,
    ADSBalanceSheetModel,
    ADSIncomeStatementModel,
    ADSCashFlowModel,
    ADSShareholderModel,
    ADSMarketSentimentModel,
    ADSNewsModel,
    ADSMacroEconomicModel,
    ADSDataBatch,
    DataQuality as ADSDataQuality,
    get_model as get_ads_model,
)

from openfinance.datacenter.models import (
    ModelRegistry,
    ModelTransformer,
    ADSORMTransformer,
    register_ads_orm_mapping,
    register_all_mappings,
    Base,
    EntityModel,
    RelationModel,
)

from openfinance.datacenter.task import (
    TaskManager,
    TaskDefinition,
    TaskStatus,
    TaskPriority,
    TriggerManager,
    TriggerType,
    get_handler,
    TaskRegistry,
    DataLineage,
    LineageTracker,
    LineageNode,
    LineageEdge,
)

__all__ = [
    "BaseCollector",
    "CollectionConfig",
    "CollectionResult",
    "CollectionStatus",
    "DataCategory",
    "DataFrequency",
    "DataSource",
    "DataType",
    "QuantDataCollector",
    "MarketDataCollector",
    "MarketRealtimeCollector",
    "KLineCollector",
    "SourceRegistry",
    "SourceConfig",
    "SourceType",
    "SourceStatus",
    "get_source_registry",
    "safe_float",
    "safe_int",
    "safe_str",
    "CodeUtils",
    "normalize_code",
    "HttpClient",
    "FieldMappingRegistry",
    "DatacenterConfig",
    "DataQualityChecker",
    "QualityDimension",
    "QualityReport",
    "QualityRule",
    "DataValidator",
    "ValidationRule",
    "ValidationResult",
    "DataLineage",
    "LineageTracker",
    "UnifiedMonitor",
    "Alert",
    "AlertSeverity",
    "AlertRule",
    "MetricsCollector",
    "get_unified_monitor",
    "DataGateway",
    "DataServiceRegistry",
    "ServiceMonitor",
    "ADSModel",
    "ADSKLineModel",
    "ADSFactorModel",
    "ADSFinancialIndicatorModel",
    "ADSBalanceSheetModel",
    "ADSIncomeStatementModel",
    "ADSCashFlowModel",
    "ADSShareholderModel",
    "ADSMarketSentimentModel",
    "ADSNewsModel",
    "ADSMacroEconomicModel",
    "ADSDataBatch",
    "ADSDataQuality",
    "get_ads_model",
    "ModelRegistry",
    "ModelTransformer",
    "ADSORMTransformer",
    "register_ads_orm_mapping",
    "register_all_mappings",
    "Base",
    "EntityModel",
    "RelationModel",
    "TaskManager",
    "TaskDefinition",
    "TaskStatus",
    "TaskPriority",
    "TriggerManager",
    "TriggerType",
    "get_handler",
    "TaskRegistry",
    "DataLineage",
    "LineageTracker",
    "LineageNode",
    "LineageEdge",
]
