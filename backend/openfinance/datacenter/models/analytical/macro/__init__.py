"""
Macro Economic Data Models.

Provides ADS models for macroeconomic data:
- Economic indicators
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from openfinance.datacenter.models.analytical.base import (
    ADSModel,
    ADSModelWithDate,
    DataQuality,
)


class ADSMacroEconomicModel(ADSModelWithDate):
    """
    Macroeconomic indicator data model.
    
    Tracks key economic indicators.
    """
    
    indicator_id: str = Field(..., description="Indicator identifier")
    indicator_name: str = Field(..., description="Indicator name")
    indicator_type: str = Field(..., description="Indicator type: leading/coincident/lagging")
    
    country: str = Field(default="CN", description="Country code")
    
    value: float | None = Field(None, description="Indicator value")
    value_yoy: float | None = Field(None, description="Year-over-year change")
    value_mom: float | None = Field(None, description="Month-over-month change")
    
    unit: str | None = Field(None, description="Unit of measurement")
    frequency: str = Field(default="monthly", description="Data frequency: daily/monthly/quarterly")
    
    previous_value: float | None = Field(None, description="Previous period value")
    consensus: float | None = Field(None, description="Market consensus")
    
    importance: int = Field(default=3, description="Importance level 1-5")
    
    @field_validator("indicator_type")
    @classmethod
    def validate_indicator_type(cls, v: str) -> str:
        valid_types = {"leading", "coincident", "lagging"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid indicator type: {v}")
        return v.lower()
    
    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        valid_freqs = {"daily", "weekly", "monthly", "quarterly", "annual"}
        if v.lower() not in valid_freqs:
            raise ValueError(f"Invalid frequency: {v}")
        return v.lower()
    
    @property
    def surprise(self) -> float | None:
        """Calculate surprise vs consensus."""
        if self.value is not None and self.consensus is not None:
            return self.value - self.consensus
        return None
    
    @property
    def is_positive_surprise(self) -> bool | None:
        """Check if value beats consensus."""
        surprise = self.surprise
        if surprise is not None:
            return surprise > 0
        return None


class ADSInterestRateModel(ADSModelWithDate):
    """
    Interest rate data model.
    
    Tracks various interest rates.
    """
    
    rate_type: str = Field(..., description="Rate type: lpr/shibor/treasury")
    term: str = Field(..., description="Term: overnight/1w/1m/3m/6m/1y/5y/10y")
    
    rate: float | None = Field(None, description="Interest rate")
    rate_change: float | None = Field(None, description="Rate change from previous")
    
    @property
    def is_short_term(self) -> bool:
        """Check if short-term rate."""
        return self.term in ("overnight", "1w", "1m")
    
    @property
    def is_long_term(self) -> bool:
        """Check if long-term rate."""
        return self.term in ("5y", "10y", "30y")


class ADSExchangeRateModel(ADSModelWithDate):
    """
    Exchange rate data model.
    
    Tracks currency exchange rates.
    """
    
    base_currency: str = Field(..., description="Base currency code")
    quote_currency: str = Field(..., description="Quote currency code")
    
    rate: float | None = Field(None, description="Exchange rate")
    rate_change: float | None = Field(None, description="Rate change")
    rate_change_pct: float | None = Field(None, description="Rate change percentage")
    
    bid: float | None = Field(None, description="Bid rate")
    ask: float | None = Field(None, description="Ask rate")
    
    @property
    def pair(self) -> str:
        """Get currency pair string."""
        return f"{self.base_currency}/{self.quote_currency}"
