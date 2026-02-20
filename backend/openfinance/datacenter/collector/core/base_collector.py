"""
Base Collector for Data Collection Center.

Provides the foundation for all data collectors with lifecycle management,
error handling, and data quality validation.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CollectionStatus(str, Enum):
    """Status of a collection task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataSource(str, Enum):
    """Supported data sources."""

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
    """Data types for collection."""

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
    INDEX_MEMBER = "index_member"
    INDEX_WEIGHT = "index_weight"
    NORTH_MONEY = "north_money"
    DRAGON_TIGER = "dragon_tiger"
    ESG_RATING = "esg_rating"
    PATENT_DATA = "patent_data"
    EXECUTIVE_CHANGE = "executive_change"
    SOCIAL_MEDIA = "social_media"
    FACTOR_DATA = "factor_data"
    KG_ENTITY = "kg_entity"
    KG_RELATION = "kg_relation"
    KG_EVENT = "kg_event"


class DataCategory(str, Enum):
    """Data categories for organization."""

    MARKET = "market"
    FUNDAMENTAL = "fundamental"
    DERIVATIVE = "derivative"
    ALTERNATIVE = "alternative"
    MACRO = "macro"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class DataFrequency(str, Enum):
    """Data update frequency."""

    TICK = "tick"
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    MINUTE_60 = "60m"
    DAILY = "d"
    WEEKLY = "w"
    MONTHLY = "m"
    QUARTERLY = "q"
    YEARLY = "y"


class CollectionConfig(BaseModel):
    """Configuration for data collection."""

    source: DataSource = Field(..., description="Data source")
    data_type: DataType = Field(default=DataType.STOCK_QUOTE, description="Data type")
    category: DataCategory = Field(default=DataCategory.MARKET, description="Data category")
    frequency: DataFrequency = Field(default=DataFrequency.DAILY, description="Data frequency")
    timeout_seconds: float = Field(default=30.0, description="Request timeout")
    retry_count: int = Field(default=3, description="Number of retries")
    retry_delay_seconds: float = Field(default=1.0, description="Delay between retries")
    batch_size: int = Field(default=100, description="Batch size for pagination")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit")
    enable_deduplication: bool = Field(default=True, description="Enable deduplication")
    enable_validation: bool = Field(default=True, description="Enable data validation")
    symbols: list[str] = Field(default_factory=list, description="Symbols to collect")
    start_date: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD)")
    incremental: bool = Field(default=False, description="Enable incremental collection")
    extra_params: dict[str, Any] = Field(default_factory=dict, description="Extra parameters")


T = TypeVar("T")


class CollectionResult(BaseModel, Generic[T]):
    """Result of a collection task."""

    task_id: str = Field(..., description="Task ID")
    source: DataSource = Field(..., description="Data source")
    status: CollectionStatus = Field(..., description="Collection status")
    records_collected: int = Field(default=0, description="Number of records collected")
    records_valid: int = Field(default=0, description="Number of valid records")
    records_deduplicated: int = Field(default=0, description="Number of duplicates removed")
    error_message: str | None = Field(default=None, description="Error message if failed")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp")
    duration_seconds: float | None = Field(default=None, description="Duration in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    data: list[T] = Field(default_factory=list, description="Collected data records")


class BaseCollector(ABC, Generic[T]):
    """Abstract base class for data collectors.

    Provides common functionality for:
    - Lifecycle management (start, stop, health check)
    - Error handling with retries
    - Rate limiting
    - Data validation and deduplication
    """

    def __init__(self, config: CollectionConfig) -> None:
        self.config = config
        self._is_running = False
        self._last_collection_time: datetime | None = None
        self._collection_count = 0
        self._error_count = 0
        self._semaphore = asyncio.Semaphore(1)

    @property
    def source(self) -> DataSource:
        """Get the data source for this collector."""
        return self.config.source

    @property
    def is_running(self) -> bool:
        """Check if collector is running."""
        return self._is_running

    async def start(self) -> None:
        """Start the collector."""
        if self._is_running:
            logger.warning(f"Collector {self.source} is already running")
            return

        self._is_running = True
        logger.info(f"Started collector for {self.source}")
        await self._initialize()

    async def stop(self) -> None:
        """Stop the collector."""
        self._is_running = False
        logger.info(f"Stopped collector for {self.source}")
        await self._cleanup()

    async def health_check(self) -> dict[str, Any]:
        """Check collector health status."""
        return {
            "source": self.source.value,
            "is_running": self._is_running,
            "last_collection": self._last_collection_time.isoformat() if self._last_collection_time else None,
            "collection_count": self._collection_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._collection_count, 1),
        }

    async def collect(self, **kwargs: Any) -> CollectionResult:
        """Execute data collection with error handling and retries."""
        task_id = f"{self.source.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        started_at = datetime.now()

        async with self._semaphore:
            try:
                records = await self._collect_with_retry(**kwargs)

                if self.config.enable_deduplication:
                    records = await self._deduplicate(records)

                if self.config.enable_validation:
                    records = await self._validate(records)

                self._collection_count += 1
                self._last_collection_time = datetime.now()

                completed_at = datetime.now()
                return CollectionResult(
                    task_id=task_id,
                    source=self.source,
                    status=CollectionStatus.COMPLETED,
                    records_collected=len(records),
                    records_valid=len(records),
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_seconds=(completed_at - started_at).total_seconds(),
                    data=records,
                )

            except Exception as e:
                self._error_count += 1
                logger.exception(f"Collection failed for {self.source}: {e}")
                return CollectionResult(
                    task_id=task_id,
                    source=self.source,
                    status=CollectionStatus.FAILED,
                    error_message=str(e),
                    started_at=started_at,
                    data=[],
                )

    async def _collect_with_retry(self, **kwargs: Any) -> list[T]:
        """Collect data with retry logic."""
        last_error: Exception | None = None

        for attempt in range(self.config.retry_count):
            try:
                return await self._collect(**kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_count - 1:
                    delay = self.config.retry_delay_seconds * (2**attempt)
                    logger.warning(
                        f"Collection attempt {attempt + 1} failed for {self.source}, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)

        raise last_error if last_error else RuntimeError("Collection failed")

    @abstractmethod
    async def _collect(self, **kwargs: Any) -> list[T]:
        """Implement actual data collection logic."""
        pass

    @abstractmethod
    async def _initialize(self) -> None:
        """Initialize collector resources."""
        pass

    @abstractmethod
    async def _cleanup(self) -> None:
        """Cleanup collector resources."""
        pass

    async def _deduplicate(self, records: list[T]) -> list[T]:
        """Remove duplicate records."""
        seen = set()
        unique_records = []

        for record in records:
            record_hash = self._get_record_hash(record)
            if record_hash not in seen:
                seen.add(record_hash)
                unique_records.append(record)

        logger.info(
            f"Deduplication removed {len(records) - len(unique_records)} duplicates "
            f"from {len(records)} records"
        )
        return unique_records

    async def _validate(self, records: list[T]) -> list[T]:
        """Validate records and filter invalid ones."""
        valid_records = []

        for record in records:
            if await self._is_valid(record):
                valid_records.append(record)

        logger.info(
            f"Validation filtered {len(records) - len(valid_records)} invalid records "
            f"from {len(records)} records"
        )
        return valid_records

    @abstractmethod
    def _get_record_hash(self, record: T) -> str:
        """Get hash for deduplication."""
        pass

    @abstractmethod
    async def _is_valid(self, record: T) -> bool:
        """Check if a record is valid."""
        pass


class StockData(BaseModel):
    """Stock data model."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    market: str = Field(..., description="Market (SH/SZ)")
    price: float | None = Field(default=None, description="Current price")
    change_pct: float | None = Field(default=None, description="Change percentage")
    volume: int | None = Field(default=None, description="Trading volume")
    amount: float | None = Field(default=None, description="Trading amount")
    timestamp: datetime = Field(..., description="Data timestamp")


class NewsData(BaseModel):
    """News data model."""

    news_id: str = Field(..., description="News ID")
    title: str = Field(..., description="News title")
    content: str = Field(..., description="News content")
    source: str = Field(..., description="News source")
    category: str | None = Field(default=None, description="News category")
    keywords: list[str] = Field(default_factory=list, description="Keywords")
    published_at: datetime = Field(..., description="Publish time")
    collected_at: datetime = Field(
        default_factory=datetime.now,
        description="Collection time",
    )


class MacroData(BaseModel):
    """Macro economic data model."""

    indicator_code: str = Field(..., description="Indicator code")
    indicator_name: str = Field(..., description="Indicator name")
    value: float = Field(..., description="Indicator value")
    unit: str = Field(..., description="Unit")
    period: str = Field(..., description="Period (e.g., 2023Q1)")
    country: str = Field(default="CN", description="Country code")
    source: str = Field(..., description="Data source")
    published_at: datetime = Field(..., description="Publish time")
    collected_at: datetime = Field(
        default_factory=datetime.now,
        description="Collection time",
    )


class StockQuoteData(BaseModel):
    """Stock quote data model for daily/intraday quotes."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    trade_date: str = Field(..., description="Trade date (YYYY-MM-DD)")
    open: float | None = Field(default=None, description="Open price")
    high: float | None = Field(default=None, description="High price")
    low: float | None = Field(default=None, description="Low price")
    close: float | None = Field(default=None, description="Close price")
    pre_close: float | None = Field(default=None, description="Previous close")
    change: float | None = Field(default=None, description="Price change")
    change_pct: float | None = Field(default=None, description="Change percentage")
    volume: int | None = Field(default=None, description="Trading volume")
    amount: float | None = Field(default=None, description="Trading amount")
    turnover_rate: float | None = Field(default=None, description="Turnover rate")
    amplitude: float | None = Field(default=None, description="Amplitude")
    market_cap: float | None = Field(default=None, description="Market cap")
    circulating_market_cap: float | None = Field(default=None, description="Circulating market cap")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class MoneyFlowData(BaseModel):
    """Money flow data model."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    trade_date: str = Field(..., description="Trade date")
    main_net_inflow: float | None = Field(default=None, description="Main net inflow")
    main_net_inflow_pct: float | None = Field(default=None, description="Main net inflow percentage")
    super_large_net_inflow: float | None = Field(default=None, description="Super large net inflow")
    large_net_inflow: float | None = Field(default=None, description="Large net inflow")
    medium_net_inflow: float | None = Field(default=None, description="Medium net inflow")
    small_net_inflow: float | None = Field(default=None, description="Small net inflow")
    north_net_inflow: float | None = Field(default=None, description="North money net inflow")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class FinancialIndicatorData(BaseModel):
    """Financial indicator data model."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    report_date: str = Field(..., description="Report date")
    eps: float | None = Field(default=None, description="Earnings per share")
    bps: float | None = Field(default=None, description="Book value per share")
    roe: float | None = Field(default=None, description="Return on equity")
    roa: float | None = Field(default=None, description="Return on assets")
    gross_margin: float | None = Field(default=None, description="Gross margin")
    net_margin: float | None = Field(default=None, description="Net margin")
    debt_ratio: float | None = Field(default=None, description="Debt ratio")
    current_ratio: float | None = Field(default=None, description="Current ratio")
    quick_ratio: float | None = Field(default=None, description="Quick ratio")
    revenue: float | None = Field(default=None, description="Revenue")
    net_profit: float | None = Field(default=None, description="Net profit")
    revenue_yoy: float | None = Field(default=None, description="Revenue YoY growth")
    net_profit_yoy: float | None = Field(default=None, description="Net profit YoY growth")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class OptionData(BaseModel):
    """Option data model."""

    code: str = Field(..., description="Option code")
    name: str = Field(..., description="Option name")
    underlying: str = Field(..., description="Underlying asset")
    strike_price: float = Field(..., description="Strike price")
    expiry_date: str = Field(..., description="Expiry date")
    option_type: str = Field(..., description="Option type (call/put)")
    last_price: float | None = Field(default=None, description="Last price")
    bid_price: float | None = Field(default=None, description="Bid price")
    ask_price: float | None = Field(default=None, description="Ask price")
    volume: int | None = Field(default=None, description="Volume")
    open_interest: int | None = Field(default=None, description="Open interest")
    implied_volatility: float | None = Field(default=None, description="Implied volatility")
    delta: float | None = Field(default=None, description="Delta")
    gamma: float | None = Field(default=None, description="Gamma")
    theta: float | None = Field(default=None, description="Theta")
    vega: float | None = Field(default=None, description="Vega")
    rho: float | None = Field(default=None, description="Rho")
    trade_date: str = Field(..., description="Trade date")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class FutureData(BaseModel):
    """Future data model."""

    code: str = Field(..., description="Future code")
    name: str = Field(..., description="Future name")
    exchange: str = Field(..., description="Exchange")
    delivery_month: str = Field(..., description="Delivery month")
    open: float | None = Field(default=None, description="Open price")
    high: float | None = Field(default=None, description="High price")
    low: float | None = Field(default=None, description="Low price")
    close: float | None = Field(default=None, description="Close price")
    pre_settlement: float | None = Field(default=None, description="Previous settlement")
    settlement: float | None = Field(default=None, description="Settlement price")
    change: float | None = Field(default=None, description="Change")
    change_pct: float | None = Field(default=None, description="Change percentage")
    volume: int | None = Field(default=None, description="Volume")
    amount: float | None = Field(default=None, description="Amount")
    open_interest: int | None = Field(default=None, description="Open interest")
    trade_date: str = Field(..., description="Trade date")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class FactorData(BaseModel):
    """Factor data model for quantitative analysis."""

    factor_id: str = Field(..., description="Factor ID")
    factor_name: str = Field(..., description="Factor name")
    factor_category: str = Field(..., description="Factor category (value/momentum/quality/etc)")
    code: str = Field(..., description="Stock code")
    trade_date: str = Field(..., description="Trade date")
    factor_value: float = Field(..., description="Factor value")
    factor_rank: int | None = Field(default=None, description="Factor rank")
    factor_percentile: float | None = Field(default=None, description="Factor percentile")
    neutralized: bool = Field(default=False, description="Whether factor is neutralized")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class KGEntityData(BaseModel):
    """Knowledge graph entity data model."""

    entity_id: str = Field(..., description="Entity ID")
    entity_type: str = Field(..., description="Entity type (company/industry/concept/person)")
    name: str = Field(..., description="Entity name")
    aliases: list[str] = Field(default_factory=list, description="Aliases")
    description: str | None = Field(default=None, description="Description")
    code: str | None = Field(default=None, description="Related code (for company)")
    industry: str | None = Field(default=None, description="Industry")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    source: str = Field(..., description="Data source")
    confidence: float = Field(default=1.0, description="Confidence score")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class KGRelationData(BaseModel):
    """Knowledge graph relation data model."""

    relation_id: str = Field(..., description="Relation ID")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relation_type: str = Field(..., description="Relation type")
    weight: float = Field(default=1.0, description="Relation weight")
    confidence: float = Field(default=1.0, description="Confidence score")
    evidence: str | None = Field(default=None, description="Evidence text")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    source: str = Field(..., description="Data source")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class KGEventData(BaseModel):
    """Knowledge graph event data model."""

    event_id: str = Field(..., description="Event ID")
    event_type: str = Field(..., description="Event type")
    title: str = Field(..., description="Event title")
    content: str | None = Field(default=None, description="Event content")
    related_entities: list[str] = Field(default_factory=list, description="Related entity IDs")
    event_date: str = Field(..., description="Event date")
    impact_level: str | None = Field(default=None, description="Impact level (high/medium/low)")
    sentiment: float | None = Field(default=None, description="Sentiment score (-1 to 1)")
    source: str = Field(..., description="Data source")
    confidence: float = Field(default=1.0, description="Confidence score")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class ESGData(BaseModel):
    """ESG rating data model."""

    code: str = Field(..., description="Stock code")
    name: str = Field(..., description="Stock name")
    rating_agency: str = Field(..., description="Rating agency")
    esg_score: float | None = Field(default=None, description="ESG total score")
    e_score: float | None = Field(default=None, description="Environment score")
    s_score: float | None = Field(default=None, description="Social score")
    g_score: float | None = Field(default=None, description="Governance score")
    esg_rating: str | None = Field(default=None, description="ESG rating grade")
    rating_date: str = Field(..., description="Rating date")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class SocialMediaData(BaseModel):
    """Social media sentiment data model."""

    platform: str = Field(..., description="Platform name")
    code: str | None = Field(default=None, description="Related stock code")
    post_id: str = Field(..., description="Post ID")
    content: str = Field(..., description="Post content")
    author: str | None = Field(default=None, description="Author")
    likes: int | None = Field(default=None, description="Likes count")
    comments: int | None = Field(default=None, description="Comments count")
    reposts: int | None = Field(default=None, description="Reposts count")
    sentiment: float | None = Field(default=None, description="Sentiment score")
    keywords: list[str] = Field(default_factory=list, description="Extracted keywords")
    published_at: datetime = Field(..., description="Publish time")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")


class IndustryChainData(BaseModel):
    """Industry chain data model."""

    chain_id: str = Field(..., description="Chain ID")
    chain_name: str = Field(..., description="Chain name")
    upstream: list[dict[str, Any]] = Field(default_factory=list, description="Upstream companies")
    midstream: list[dict[str, Any]] = Field(default_factory=list, description="Midstream companies")
    downstream: list[dict[str, Any]] = Field(default_factory=list, description="Downstream companies")
    relations: list[dict[str, Any]] = Field(default_factory=list, description="Chain relations")
    source: str = Field(..., description="Data source")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection time")
