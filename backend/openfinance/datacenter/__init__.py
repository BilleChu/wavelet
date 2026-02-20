"""
Data Center System for OpenFinance.

This module provides comprehensive data management including:
- ADS: Analytical Data Store - unified data models
- Collector: Multi-source data acquisition and cleaning
- Models: ORM models, framework, and mappings
- Provider: Data source abstraction and MCP framework
- Quality: Data quality checking and validation
- Marketplace: Data service marketplace
- Task: Task scheduling and execution
- Core: Core utilities (config, conversion, HTTP client)

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    Marketplace Layer                         │
│         (Data Service Marketplace, Gateway)                 │
├─────────────────────────────────────────────────────────────┤
│                    Provider Layer                            │
│         (Data Sources, MCP Framework)                       │
├─────────────────────────────────────────────────────────────┤
│                    ADS Layer                                 │
│         (Unified Data Models)                               │
├─────────────────────────────────────────────────────────────┤
│                    Models Layer                              │
│         (ORM, Framework, Mappings)                          │
├─────────────────────────────────────────────────────────────┤
│                    Core Layer                                │
│         (Config, Utils, Quality, Task, Collector)           │
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
)

from openfinance.datacenter.provider import (
    MCPService,
    MCPServerConfig,
    ServiceRegistry,
    BaseDataProvider,
    DataProviderError,
    create_data_provider,
)

from openfinance.datacenter.core import (
    safe_float,
    safe_int,
    safe_str,
    CodeUtils,
    normalize_code,
    HttpClient,
    FieldMappingRegistry,
    SourceRegistry,
    DatacenterConfig,
    ConfigDrivenCollector,
    CollectorConfig,
)

from openfinance.datacenter.quality import (
    DataQualityChecker,
    QualityDimension,
    QualityReport,
    QualityRule,
    DataValidator,
    ValidationRule,
    ValidationResult,
    DataLineage,
    LineageTracker,
)

from openfinance.datacenter.monitoring import (
    MetricsCollector,
    AlertManager,
    AlertRule,
    AlertSeverity,
)

from openfinance.datacenter.marketplace import (
    DataGateway,
    DataServiceRegistry,
    ServiceMonitor,
)

from openfinance.datacenter.ads import (
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
    "MCPService",
    "MCPServerConfig",
    "ServiceRegistry",
    "BaseDataProvider",
    "DataProviderError",
    "create_data_provider",
    "safe_float",
    "safe_int",
    "safe_str",
    "CodeUtils",
    "normalize_code",
    "HttpClient",
    "FieldMappingRegistry",
    "SourceRegistry",
    "DatacenterConfig",
    "ConfigDrivenCollector",
    "CollectorConfig",
    "DataQualityChecker",
    "QualityDimension",
    "QualityReport",
    "QualityRule",
    "DataValidator",
    "ValidationRule",
    "ValidationResult",
    "DataLineage",
    "LineageTracker",
    "MetricsCollector",
    "AlertManager",
    "AlertRule",
    "AlertSeverity",
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
]
