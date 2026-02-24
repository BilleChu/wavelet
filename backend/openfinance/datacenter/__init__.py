"""
Data Center System for OpenFinance.

架构:
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
│                    ADS Models Layer                          │
│         (ADSModelRegistry, Repository, ADS Models)          │
├─────────────────────────────────────────────────────────────┤
│                    ORM Models Layer                          │
│         (SQLAlchemy Models, Mappings)                       │
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
    ADSModelRegistry,
    ADSModelDefinition,
    register_ads_model,
    GenericADSRepository,
    ADSKLineRepository,
    ADSFactorRepository,
    get_model as get_ads_model,
)

from openfinance.datacenter.models import (
    register_all_mappings,
    Base,
    EntityModel,
    RelationModel,
    StockDailyQuoteModel,
    FactorDataModel,
    IncomeStatementModel,
    BalanceSheetModel,
    CashFlowModel,
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
    "ADSModelRegistry",
    "ADSModelDefinition",
    "register_ads_model",
    "GenericADSRepository",
    "ADSKLineRepository",
    "ADSFactorRepository",
    "get_ads_model",
    "register_all_mappings",
    "Base",
    "EntityModel",
    "RelationModel",
    "StockDailyQuoteModel",
    "FactorDataModel",
    "IncomeStatementModel",
    "BalanceSheetModel",
    "CashFlowModel",
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
