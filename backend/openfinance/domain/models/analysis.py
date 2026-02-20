"""
Analysis models for OpenFinance.

Defines data structures for the intelligent analysis canvas.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataSource(str, Enum):
    """Data source types."""

    WIND = "wind"
    EASTMONEY = "eastmoney"
    TUSHARE = "tushare"
    SINA = "sina"
    GOVERNMENT = "government"
    COMPANY_REPORT = "company_report"
    NEWS = "news"
    AI_ANALYSIS = "ai_analysis"


class ConfidenceLevel(str, Enum):
    """Data confidence levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataPoint(BaseModel):
    """Single data point with metadata."""

    value: float = Field(..., description="Data value")
    timestamp: datetime = Field(..., description="Data timestamp")
    source: DataSource = Field(..., description="Data source")
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence level",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class MacroIndicator(BaseModel):
    """Macro economic indicator."""

    code: str = Field(..., description="Indicator code")
    name: str = Field(..., description="Indicator name")
    name_en: str | None = Field(default=None, description="English name")
    category: str = Field(..., description="Category (GDP, CPI, PMI, etc.)")
    unit: str = Field(..., description="Unit of measurement")
    current_value: DataPoint = Field(..., description="Current value")
    previous_value: DataPoint | None = Field(default=None, description="Previous value")
    yoy_change: float | None = Field(default=None, description="Year-over-year change %")
    mom_change: float | None = Field(default=None, description="Month-over-month change %")
    trend: str = Field(default="stable", description="Trend direction")
    historical_data: list[DataPoint] = Field(
        default_factory=list,
        description="Historical data points",
    )


class PolicyItem(BaseModel):
    """Policy or regulation item."""

    policy_id: str = Field(..., description="Policy ID")
    title: str = Field(..., description="Policy title")
    summary: str = Field(..., description="Policy summary")
    source: DataSource = Field(..., description="Source")
    publish_date: datetime = Field(..., description="Publish date")
    effective_date: datetime | None = Field(default=None, description="Effective date")
    issuer: str = Field(..., description="Issuing authority")
    category: str = Field(..., description="Policy category")
    impact_level: str = Field(default="medium", description="Impact level")
    affected_sectors: list[str] = Field(
        default_factory=list,
        description="Affected sectors",
    )
    affected_stocks: list[str] = Field(
        default_factory=list,
        description="Affected stock codes",
    )
    sentiment: str = Field(default="neutral", description="Sentiment")
    relevance_score: float = Field(default=0.5, description="Relevance score 0-1")
    url: str | None = Field(default=None, description="Original URL")


class CompanyFinancial(BaseModel):
    """Company financial data."""

    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    report_date: datetime = Field(..., description="Report date")
    report_type: str = Field(..., description="Report type (Q1, Q2, Q3, Annual)")

    revenue: DataPoint | None = Field(default=None, description="Revenue")
    net_profit: DataPoint | None = Field(default=None, description="Net profit")
    gross_margin: DataPoint | None = Field(default=None, description="Gross margin %")
    net_margin: DataPoint | None = Field(default=None, description="Net margin %")
    roe: DataPoint | None = Field(default=None, description="ROE %")
    roa: DataPoint | None = Field(default=None, description="ROA %")
    debt_ratio: DataPoint | None = Field(default=None, description="Debt ratio %")
    current_ratio: DataPoint | None = Field(default=None, description="Current ratio")
    pe_ratio: float | None = Field(default=None, description="P/E ratio")
    pb_ratio: float | None = Field(default=None, description="P/B ratio")

    yoy_revenue_growth: float | None = Field(default=None, description="YoY revenue growth %")
    yoy_profit_growth: float | None = Field(default=None, description="YoY profit growth %")

    news: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Related news",
    )
    ai_insight: str | None = Field(default=None, description="AI generated insight")


class TechIndicator(BaseModel):
    """Technical indicator data."""

    stock_code: str = Field(..., description="Stock code")
    stock_name: str = Field(..., description="Stock name")
    timestamp: datetime = Field(..., description="Data timestamp")

    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change")
    change_pct: float = Field(..., description="Price change %")
    volume: float = Field(..., description="Volume")
    amount: float = Field(..., description="Amount")

    ma5: float | None = Field(default=None, description="5-day MA")
    ma10: float | None = Field(default=None, description="10-day MA")
    ma20: float | None = Field(default=None, description="20-day MA")
    ma60: float | None = Field(default=None, description="60-day MA")

    rsi_14: float | None = Field(default=None, description="RSI(14)")
    macd: float | None = Field(default=None, description="MACD")
    macd_signal: float | None = Field(default=None, description="MACD signal")
    macd_hist: float | None = Field(default=None, description="MACD histogram")

    kdj_k: float | None = Field(default=None, description="KDJ K")
    kdj_d: float | None = Field(default=None, description="KDJ D")
    kdj_j: float | None = Field(default=None, description="KDJ J")

    boll_upper: float | None = Field(default=None, description="Bollinger upper")
    boll_mid: float | None = Field(default=None, description="Bollinger mid")
    boll_lower: float | None = Field(default=None, description="Bollinger lower")

    trend_signal: str = Field(default="neutral", description="Trend signal")
    support_level: float | None = Field(default=None, description="Support level")
    resistance_level: float | None = Field(default=None, description="Resistance level")


class AnalysisRequest(BaseModel):
    """Request for AI analysis."""

    query: str = Field(..., description="User query")
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Analysis context",
    )
    panels: list[str] = Field(
        default_factory=list,
        description="Related panel IDs",
    )
    include_historical: bool = Field(
        default=False,
        description="Include historical analysis",
    )


class AnalysisResponse(BaseModel):
    """Response from AI analysis."""

    analysis_id: str = Field(..., description="Analysis ID")
    query: str = Field(..., description="Original query")
    content: str = Field(..., description="Analysis content")
    data_sources: list[DataSource] = Field(
        default_factory=list,
        description="Data sources used",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Overall confidence",
    )
    related_entities: list[str] = Field(
        default_factory=list,
        description="Related entity IDs",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        description="Follow-up query suggestions",
    )
    duration_ms: float = Field(..., description="Processing duration")


class CanvasState(BaseModel):
    """State of the analysis canvas."""

    session_id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )

    selected_stocks: list[str] = Field(
        default_factory=list,
        description="Selected stock codes",
    )
    selected_indicators: list[str] = Field(
        default_factory=list,
        description="Selected macro indicators",
    )
    watchlist: list[str] = Field(
        default_factory=list,
        description="Watchlist items",
    )

    panel_configs: dict[str, Any] = Field(
        default_factory=dict,
        description="Panel configurations",
    )
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Active filters",
    )


class MacroPanelData(BaseModel):
    """Data for macro panel."""

    indicators: list[MacroIndicator] = Field(
        default_factory=list,
        description="Macro indicators",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )
    next_update: datetime | None = Field(
        default=None,
        description="Next scheduled update",
    )


class PolicyPanelData(BaseModel):
    """Data for policy panel."""

    policies: list[PolicyItem] = Field(
        default_factory=list,
        description="Policy items",
    )
    hot_topics: list[str] = Field(
        default_factory=list,
        description="Hot policy topics",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )


class CompanyPanelData(BaseModel):
    """Data for company panel."""

    companies: list[CompanyFinancial] = Field(
        default_factory=list,
        description="Company financials",
    )
    news: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Related news",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )


class TechPanelData(BaseModel):
    """Data for technical panel."""

    indicators: list[TechIndicator] = Field(
        default_factory=list,
        description="Technical indicators",
    )
    signals: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Trading signals",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )


class CanvasData(BaseModel):
    """Complete canvas data."""

    macro: MacroPanelData = Field(
        default_factory=MacroPanelData,
        description="Macro panel data",
    )
    policy: PolicyPanelData = Field(
        default_factory=PolicyPanelData,
        description="Policy panel data",
    )
    company: CompanyPanelData = Field(
        default_factory=CompanyPanelData,
        description="Company panel data",
    )
    tech: TechPanelData = Field(
        default_factory=TechPanelData,
        description="Tech panel data",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )
