"""
Data Collection Center for OpenFinance.

Provides multi-source data acquisition, cleaning, and lifecycle management.

Modules:
- source: Data source management (configuration, health, registry)
- core: Base collectors and orchestrator
- implementations: Specific data collectors
"""

from openfinance.datacenter.collector.core.base_collector import (
    BaseCollector,
    CollectionConfig,
    CollectionResult,
    CollectionStatus,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    ESGData,
    FactorData,
    FinancialIndicatorData,
    FutureData,
    IndustryChainData,
    KGEntityData,
    KGEventData,
    KGRelationData,
    MacroData,
    MoneyFlowData,
    NewsData,
    OptionData,
    SocialMediaData,
    StockData,
    StockQuoteData,
)
from openfinance.datacenter.collector.core.orchestrator import CollectionOrchestrator
from openfinance.datacenter.collector.implementations import (
    CLSNewsCollector,
    JinshiNewsCollector,
    KLineCollector,
    MarketRealtimeCollector,
)
from openfinance.datacenter.collector.quant_collector import (
    FactorDataCollector,
    FundamentalDataCollector,
    MarketDataCollector,
    MoneyFlowDataCollector,
    QuantDataCollector,
)
from openfinance.datacenter.collector.source import (
    SourceRegistry,
    SourceConfig,
    SourceType,
    SourceStatus,
    AuthType,
    CollectionRule,
    ConnectionConfig,
    AuthConfig,
    RateLimitConfig,
    RetryConfig,
    HealthChecker,
    SourceHealth,
    HealthCheckResult,
    get_source_registry,
)

__all__ = [
    "BaseCollector",
    "CollectionConfig",
    "CollectionResult",
    "CollectionOrchestrator",
    "CollectionStatus",
    "DataCategory",
    "DataFrequency",
    "DataSource",
    "DataType",
    "QuantDataCollector",
    "MarketDataCollector",
    "FundamentalDataCollector",
    "MoneyFlowDataCollector",
    "FactorDataCollector",
    "MarketRealtimeCollector",
    "KLineCollector",
    "JinshiNewsCollector",
    "CLSNewsCollector",
    "StockData",
    "StockQuoteData",
    "NewsData",
    "MacroData",
    "MoneyFlowData",
    "FinancialIndicatorData",
    "OptionData",
    "FutureData",
    "FactorData",
    "KGEntityData",
    "KGRelationData",
    "KGEventData",
    "ESGData",
    "SocialMediaData",
    "IndustryChainData",
    "SourceRegistry",
    "SourceConfig",
    "SourceType",
    "SourceStatus",
    "AuthType",
    "CollectionRule",
    "ConnectionConfig",
    "AuthConfig",
    "RateLimitConfig",
    "RetryConfig",
    "HealthChecker",
    "SourceHealth",
    "HealthCheckResult",
    "get_source_registry",
]
