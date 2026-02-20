"""
Unified Enumeration Definitions for OpenFinance.

This module consolidates all enumeration types used across the project,
eliminating duplicate definitions and providing a single source of truth.

Organization:
- Data Collection Domain: DataSource, DataType, DataCategory, etc.
- Quantitative Analysis Domain: FactorType, StrategyType, etc.
- Knowledge Graph Domain: EntityType, RelationType
- Task Management Domain: TaskStatus, TaskPriority, etc.
- Monitoring Domain: AlertSeverity, AlertStatus, etc.
- Agent Domain: MessageRole, ToolState, etc.
"""

from enum import Enum
from typing import Literal


# ============================================================================
# Data Collection Domain
# ============================================================================

class DataSource(str, Enum):
    """Supported data sources for collection."""
    
    EASTMONEY = "eastmoney"
    JINSHI = "jinshi"
    CLS = "cls"
    SINA = "sina"
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    WIND = "wind"
    XUEQIU = "xueqiu"
    HIBOR = "hibor"
    SSE_OPTION = "sse_option"
    SZSE_OPTION = "szse_option"
    SHFE = "shfe"
    DCE = "dce"
    CZCE = "czce"
    CFFEX = "cffex"
    SYNTRONG = "syntrong"
    HUAZHENG = "huazheng"
    CNINFO = "cninfo"
    THS = "ths"
    EXCHANGE = "exchange"
    RESEARCH = "research"
    CUSTOM = "custom"


class DataType(str, Enum):
    """Types of data for collection."""
    
    STOCK_QUOTE = "stock_quote"
    STOCK_QUOTE_REALTIME = "stock_quote_realtime"
    STOCK_QUOTE_INTRADAY = "stock_quote_intraday"
    STOCK_FUNDAMENTAL = "stock_fundamental"
    STOCK_FINANCIAL_REPORT = "stock_financial_report"
    STOCK_FINANCIAL_INDICATOR = "stock_financial_indicator"
    STOCK_NEWS = "stock_news"
    STOCK_RESEARCH_REPORT = "stock_research_report"
    STOCK_ANALYST_RATING = "stock_analyst_rating"
    STOCK_MONEY_FLOW = "stock_money_flow"
    STOCK_HOLDER = "stock_holder"
    STOCK_INSIDER_TRADE = "stock_insider_trade"
    STOCK_BLOCK_TRADE = "stock_block_trade"
    STOCK_MARGIN_TRADE = "stock_margin_trade"
    STOCK_SHARE_PLEDGE = "stock_share_pledge"
    STOCK_LOCKUP_RELEASE = "stock_lockup_release"
    INDUSTRY_DATA = "industry_data"
    INDUSTRY_MEMBER = "industry_member"
    INDUSTRY_CHAIN = "industry_chain"
    CONCEPT_DATA = "concept_data"
    CONCEPT_MEMBER = "concept_member"
    MACRO_DATA = "macro_data"
    MACRO_GDP = "macro_gdp"
    MACRO_CPI = "macro_cpi"
    MACRO_PPI = "macro_ppi"
    MACRO_PMI = "macro_pmi"
    MACRO_MONEY_SUPPLY = "macro_money_supply"
    MACRO_INTEREST_RATE = "macro_interest_rate"
    MARKET_NEWS = "market_news"
    MARKET_SENTIMENT = "market_sentiment"
    OPTION_QUOTE = "option_quote"
    OPTION_GREEKS = "option_greeks"
    OPTION_IV = "option_iv"
    FUTURE_QUOTE = "future_quote"
    FUTURE_POSITION = "future_position"
    ETF_QUOTE = "etf_quote"
    ETF_HOLDINGS = "etf_holdings"
    FUND_INFO = "fund_info"
    FUND_HOLDINGS = "fund_holdings"
    FUND_NET_VALUE = "fund_net_value"
    INDEX_QUOTE = "index_quote"
    FACTOR_DATA = "factor_data"
    ESG_DATA = "esg_data"


class DataCategory(str, Enum):
    """Categories of data."""
    
    MARKET = "market"
    FUNDAMENTAL = "fundamental"
    DERIVATIVE = "derivative"
    ALTERNATIVE = "alternative"
    MACRO = "macro"
    NEWS = "news"
    FACTOR = "factor"
    GRAPH = "graph"


class DataFrequency(str, Enum):
    """Data update frequency."""
    
    TICK = "tick"
    MINUTE_1 = "1min"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"
    MINUTE_60 = "60min"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class CollectionStatus(str, Enum):
    """Status of a collection task."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Quantitative Analysis Domain
# ============================================================================

class FactorType(str, Enum):
    """Types of factors."""
    
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"
    CUSTOM = "custom"


class FactorCategory(str, Enum):
    """Categories of factors."""
    
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VALUE = "value"
    QUALITY = "quality"
    GROWTH = "growth"
    LIQUIDITY = "liquidity"
    SENTIMENT = "sentiment"
    SIZE = "size"


class FactorStatus(str, Enum):
    """Status of a factor."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class NormalizeMethod(str, Enum):
    """Normalization methods for factors."""
    
    NONE = "none"
    ZSCORE = "zscore"
    MINMAX = "minmax"
    RANK = "rank"
    PERCENTILE = "percentile"


class NeutralizationType(str, Enum):
    """Neutralization types for factors."""
    
    NONE = "none"
    INDUSTRY = "industry"
    MARKET_CAP = "market_cap"
    BOTH = "both"


class StrategyType(str, Enum):
    """Types of strategies."""
    
    SINGLE_FACTOR = "single_factor"
    MULTI_FACTOR = "multi_factor"
    COMBO = "combo"


class WeightMethod(str, Enum):
    """Weight calculation methods."""
    
    EQUAL = "equal"
    MARKET_CAP = "market_cap"
    RISK_PARITY = "risk_parity"
    MIN_VARIANCE = "min_variance"
    OPTIMIZATION = "optimization"


class BacktestStatus(str, Enum):
    """Status of a backtest."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BacktestMode(str, Enum):
    """Backtest execution mode."""
    
    VECTOR = "vector"
    EVENT = "event"


class PositionSide(str, Enum):
    """Position side."""
    
    LONG = "long"
    SHORT = "short"


class OrderStatus(str, Enum):
    """Order status."""
    
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Frequency(str, Enum):
    """Data frequency for analysis."""
    
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


# ============================================================================
# Knowledge Graph Domain
# ============================================================================

class EntityType(str, Enum):
    """Types of entities in knowledge graph."""
    
    COMPANY = "company"
    INDUSTRY = "industry"
    CONCEPT = "concept"
    PERSON = "person"
    STOCK = "stock"
    FUND = "fund"
    EVENT = "event"
    SECTOR = "sector"
    INDEX = "index"
    INVESTOR = "investor"


class RelationType(str, Enum):
    """Types of relations in knowledge graph."""
    
    BELONGS_TO = "belongs_to"
    HAS_CONCEPT = "has_concept"
    COMPETES_WITH = "competes_with"
    SUPPLIES_TO = "supplies_to"
    SUPPLIES = "supplies"
    INVESTS_IN = "invests_in"
    AFFECTS = "affects"
    WORKS_FOR = "works_for"
    MANAGES = "manages"
    OWNS = "owns"
    PARENT_OF = "parent_of"
    SUBSIDIARY_OF = "subsidiary_of"
    CEO_OF = "ceo_of"
    DIRECTOR_OF = "director_of"
    FOUNDED = "founded"
    ACQUIRED = "acquired"
    MERGED_WITH = "merged_with"
    OPERATES_IN = "operates_in"
    REGULATED_BY = "regulated_by"
    RELATED_TO = "related_to"
    LISTED_ON = "listed_on"
    PARTNERS_WITH = "partners_with"
    CUSTOMER_OF = "customer_of"
    PRODUCES = "produces"
    ANALYZED_BY = "analyzed_by"
    REPORTED_BY = "reported_by"


EntityTypeLiteral = Literal[
    "company", "industry", "concept", "person", "stock",
    "fund", "event", "sector", "index", "investor",
]

RelationTypeLiteral = Literal[
    "belongs_to", "has_concept", "competes_with", "supplies_to",
    "invests_in", "affects", "works_for", "manages", "owns",
    "parent_of", "subsidiary_of", "ceo_of", "director_of",
    "founded", "acquired", "merged_with", "operates_in",
    "regulated_by", "related_to", "listed_on",
]


# ============================================================================
# Task Management Domain
# ============================================================================

class TaskStatus(str, Enum):
    """Status of a task."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class ChainStatus(str, Enum):
    """Status of a task chain."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeType(str, Enum):
    """Types of nodes in a task chain."""
    
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"


class ScheduleType(str, Enum):
    """Types of scheduling."""
    
    ONCE = "once"
    INTERVAL = "interval"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


class TriggerType(str, Enum):
    """Types of triggers."""
    
    MANUAL = "manual"
    SCHEDULE = "schedule"
    EVENT = "event"
    DEPENDENCY = "dependency"


class RetryStrategy(str, Enum):
    """Retry strategies."""
    
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


# ============================================================================
# Monitoring Domain
# ============================================================================

class AlertSeverity(str, Enum):
    """Severity levels for alerts."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Status of an alert."""
    
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


class MetricType(str, Enum):
    """Types of metrics."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# ============================================================================
# Data Quality Domain
# ============================================================================

class QualityDimension(str, Enum):
    """Dimensions of data quality."""
    
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    TIMELINESS = "timeliness"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"


class QualitySeverity(str, Enum):
    """Severity levels for quality issues."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DataQuality(str, Enum):
    """Data quality levels."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


# ============================================================================
# Agent Domain
# ============================================================================

class MessageRole(str, Enum):
    """Roles in a conversation."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ToolState(str, Enum):
    """States of tool execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PermissionDecision(str, Enum):
    """Permission decisions."""
    
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class HookEvent(str, Enum):
    """Hook event types."""
    
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_LLM_CALL = "pre_llm_call"
    POST_LLM_CALL = "post_llm_call"


class SkillState(str, Enum):
    """States of a skill."""
    
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    EXECUTING = "executing"
    PAUSED = "paused"
    ERROR = "error"


class SkillType(str, Enum):
    """Types of skills."""
    
    ANALYSIS = "analysis"
    SEARCH = "search"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"


# ============================================================================
# Data Service Domain
# ============================================================================

class DataServiceCategory(str, Enum):
    """Categories of data services."""
    
    ANALYSIS = "analysis"
    GRAPH = "graph"
    QUANT = "quant"
    MARKET = "market"
    FUNDAMENTAL = "fundamental"


class DataServiceStatus(str, Enum):
    """Status of a data service."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class SubscriptionStatus(str, Enum):
    """Status of a subscription."""
    
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SubscriptionPlan(str, Enum):
    """Subscription plans."""
    
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PricingModel(str, Enum):
    """Pricing models."""
    
    FREE = "free"
    PER_REQUEST = "per_request"
    PER_MONTH = "per_month"
    PER_VOLUME = "per_volume"
    TIERED = "tiered"


# ============================================================================
# Platform Domain
# ============================================================================

class PlatformType(str, Enum):
    """Platform types."""
    
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"


class UserRole(str, Enum):
    """User roles."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(str, Enum):
    """Intent types for NLU."""
    
    STOCK_SEARCH = "stock_search"
    INDUSTRY_SEARCH = "industry_search"
    MACRO_SEARCH = "macro_search"
    STRATEGY_SEARCH = "strategy_search"
    STOCK_ANALYSIS = "stock_analysis"
    INDUSTRY_ANALYSIS = "industry_analysis"
    MACRO_ANALYSIS = "macro_analysis"
    ROLE_OPINION = "role_opinion"
    STOCK_RANK = "stock_rank"
    UNKNOWN = "unknown"


# ============================================================================
# Enum Registry
# ============================================================================

ENUM_REGISTRY: dict[str, type[Enum]] = {
    "DataSource": DataSource,
    "DataType": DataType,
    "DataCategory": DataCategory,
    "DataFrequency": DataFrequency,
    "CollectionStatus": CollectionStatus,
    "FactorType": FactorType,
    "FactorCategory": FactorCategory,
    "FactorStatus": FactorStatus,
    "NormalizeMethod": NormalizeMethod,
    "NeutralizationType": NeutralizationType,
    "StrategyType": StrategyType,
    "WeightMethod": WeightMethod,
    "BacktestStatus": BacktestStatus,
    "BacktestMode": BacktestMode,
    "PositionSide": PositionSide,
    "OrderStatus": OrderStatus,
    "Frequency": Frequency,
    "EntityType": EntityType,
    "RelationType": RelationType,
    "TaskStatus": TaskStatus,
    "TaskPriority": TaskPriority,
    "ChainStatus": ChainStatus,
    "NodeType": NodeType,
    "ScheduleType": ScheduleType,
    "TriggerType": TriggerType,
    "RetryStrategy": RetryStrategy,
    "AlertSeverity": AlertSeverity,
    "AlertStatus": AlertStatus,
    "MetricType": MetricType,
    "QualityDimension": QualityDimension,
    "QualitySeverity": QualitySeverity,
    "DataQuality": DataQuality,
    "MessageRole": MessageRole,
    "ToolState": ToolState,
    "PermissionDecision": PermissionDecision,
    "HookEvent": HookEvent,
    "SkillState": SkillState,
    "SkillType": SkillType,
    "DataServiceCategory": DataServiceCategory,
    "DataServiceStatus": DataServiceStatus,
    "SubscriptionStatus": SubscriptionStatus,
    "SubscriptionPlan": SubscriptionPlan,
    "PricingModel": PricingModel,
    "PlatformType": PlatformType,
    "UserRole": UserRole,
    "IntentType": IntentType,
}


def get_enum(name: str) -> type[Enum] | None:
    """Get an enum by name."""
    return ENUM_REGISTRY.get(name)


def get_enum_values(name: str) -> list[str]:
    """Get all values of an enum by name."""
    enum_class = ENUM_REGISTRY.get(name)
    if enum_class:
        return [e.value for e in enum_class]
    return []
