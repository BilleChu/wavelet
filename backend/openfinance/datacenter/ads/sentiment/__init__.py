"""
Sentiment Data Models.

Provides ADS models for sentiment-related data:
- Market sentiment
- News sentiment
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from openfinance.datacenter.ads.base import (
    ADSModel,
    ADSModelWithCode,
    ADSModelWithDate,
    DataQuality,
)


class ADSMarketSentimentModel(ADSModelWithDate):
    """
    Market sentiment data model.
    
    Tracks overall market sentiment indicators.
    """
    
    market: str = Field(..., description="Market identifier: sh/sz/all")
    
    advance_count: int | None = Field(None, description="Number of advancing stocks")
    decline_count: int | None = Field(None, description="Number of declining stocks")
    unchanged_count: int | None = Field(None, description="Number of unchanged stocks")
    
    limit_up_count: int | None = Field(None, description="Number of limit-up stocks")
    limit_down_count: int | None = Field(None, description="Number of limit-down stocks")
    
    new_high_count: int | None = Field(None, description="Stocks hitting new high")
    new_low_count: int | None = Field(None, description="Stocks hitting new low")
    
    turnover_rate: float | None = Field(None, description="Market turnover rate")
    
    bull_strength: float | None = Field(None, description="Bull strength indicator [-1, 1]")
    fear_greed_index: float | None = Field(None, description="Fear & Greed index [0, 100]")
    
    north_net_inflow: float | None = Field(None, description="Northbound net inflow")
    south_net_inflow: float | None = Field(None, description="Southbound net inflow")
    
    margin_balance: float | None = Field(None, description="Margin trading balance")
    margin_buy_amount: float | None = Field(None, description="Margin buy amount")
    margin_sell_amount: float | None = Field(None, description="Margin sell amount")
    
    @property
    def advance_decline_ratio(self) -> float | None:
        """Calculate advance/decline ratio."""
        if self.advance_count and self.decline_count and self.decline_count > 0:
            return self.advance_count / self.decline_count
        return None
    
    @property
    def sentiment_level(self) -> str | None:
        """Determine sentiment level."""
        if self.bull_strength is None:
            return None
        if self.bull_strength >= 0.5:
            return "very_bullish"
        elif self.bull_strength >= 0.2:
            return "bullish"
        elif self.bull_strength >= -0.2:
            return "neutral"
        elif self.bull_strength >= -0.5:
            return "bearish"
        else:
            return "very_bearish"


class ADSNewsModel(ADSModel):
    """
    News data model.
    
    Contains news content and sentiment analysis.
    """
    
    news_id: str = Field(..., description="Unique news identifier")
    title: str = Field(..., description="News title")
    content: str | None = Field(None, description="News content")
    summary: str | None = Field(None, description="News summary")
    
    source: str = Field(..., description="News source")
    author: str | None = Field(None, description="Author name")
    
    published_at: datetime = Field(..., description="Publication time")
    collected_at: datetime | None = Field(None, description="Collection time")
    
    related_codes: list[str] = Field(
        default_factory=list,
        description="Related stock codes"
    )
    related_entities: list[str] = Field(
        default_factory=list,
        description="Related entity names"
    )
    
    sentiment: str | None = Field(None, description="Sentiment: positive/negative/neutral")
    sentiment_score: float | None = Field(None, description="Sentiment score [-1, 1]")
    confidence: float | None = Field(None, description="Sentiment confidence [0, 1]")
    
    importance: int = Field(default=1, description="Importance level 1-5")
    category: str | None = Field(None, description="News category")
    tags: list[str] = Field(default_factory=list, description="News tags")
    
    url: str | None = Field(None, description="Original URL")
    
    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, v: str | None) -> str | None:
        if v is None:
            return None
        valid = {"positive", "negative", "neutral", "pos", "neg", "neu"}
        if v.lower() not in valid:
            raise ValueError(f"Invalid sentiment: {v}")
        return v.lower()[:8]
    
    @property
    def is_positive(self) -> bool:
        """Check if news is positive."""
        return self.sentiment in ("positive", "pos")
    
    @property
    def is_negative(self) -> bool:
        """Check if news is negative."""
        return self.sentiment in ("negative", "neg")


class ADSStockSentimentModel(ADSModelWithCode, ADSModelWithDate):
    """
    Stock-specific sentiment data model.
    
    Aggregated sentiment for individual stocks.
    """
    
    name: str | None = Field(None, description="Stock name")
    
    news_count: int = Field(default=0, description="Number of related news")
    positive_count: int = Field(default=0, description="Positive news count")
    negative_count: int = Field(default=0, description="Negative news count")
    neutral_count: int = Field(default=0, description="Neutral news count")
    
    overall_sentiment: float | None = Field(None, description="Overall sentiment score [-1, 1]")
    sentiment_momentum: float | None = Field(None, description="Sentiment change from previous")
    
    social_mentions: int | None = Field(None, description="Social media mentions")
    social_sentiment: float | None = Field(None, description="Social sentiment score")
    
    analyst_rating: str | None = Field(None, description="Consensus analyst rating")
    target_price: float | None = Field(None, description="Consensus target price")
    
    @property
    def sentiment_level(self) -> str | None:
        """Determine sentiment level."""
        if self.overall_sentiment is None:
            return None
        if self.overall_sentiment >= 0.3:
            return "bullish"
        elif self.overall_sentiment >= -0.3:
            return "neutral"
        else:
            return "bearish"
    
    @property
    def news_sentiment_ratio(self) -> float | None:
        """Calculate positive/negative ratio."""
        if self.negative_count and self.negative_count > 0:
            return self.positive_count / self.negative_count
        elif self.positive_count and self.positive_count > 0:
            return float('inf')
        return None
