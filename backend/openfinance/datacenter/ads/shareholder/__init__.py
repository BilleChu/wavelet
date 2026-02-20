"""
Shareholder Data Models.

Provides ADS models for shareholder-related data:
- Shareholder holdings
- Shareholder changes
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


class ADSShareholderModel(ADSModelWithCode):
    """
    Shareholder holdings data model.
    
    Tracks major shareholders and their holdings.
    """
    
    report_date: date = Field(..., description="Report date")
    shareholder_name: str = Field(..., description="Shareholder name")
    shareholder_type: str | None = Field(None, description="Shareholder type: individual/institution/government")
    
    shares_held: float | None = Field(None, description="Number of shares held")
    shares_ratio: float | None = Field(None, description="Holding percentage")
    
    shares_change: float | None = Field(None, description="Shares change from last report")
    shares_change_ratio: float | None = Field(None, description="Change percentage")
    
    is_actual_controller: bool = Field(default=False, description="Is actual controller")
    is_representative: bool = Field(default=False, description="Is legal representative")
    
    pledge_shares: float | None = Field(None, description="Pledged shares")
    pledge_ratio: float | None = Field(None, description="Pledge ratio")
    
    frozen_shares: float | None = Field(None, description="Frozen shares")
    
    @property
    def is_major_shareholder(self) -> bool:
        """Check if this is a major shareholder (>5%)."""
        return self.shares_ratio is not None and self.shares_ratio >= 5.0
    
    @property
    def has_pledge_risk(self) -> bool | None:
        """Check if there is pledge risk."""
        if self.pledge_ratio is not None:
            return self.pledge_ratio > 50.0
        return None


class ADSShareholderChangeModel(ADSModelWithCode):
    """
    Shareholder change data model.
    
    Tracks changes in major shareholdings.
    """
    
    announcement_date: date = Field(..., description="Announcement date")
    change_date: date | None = Field(None, description="Change date")
    
    shareholder_name: str = Field(..., description="Shareholder name")
    shareholder_type: str | None = Field(None, description="Shareholder type")
    
    change_type: str = Field(..., description="Change type: increase/decrease/unchanged")
    change_reason: str | None = Field(None, description="Reason for change")
    
    shares_before: float | None = Field(None, description="Shares before change")
    shares_after: float | None = Field(None, description="Shares after change")
    shares_change: float | None = Field(None, description="Shares changed")
    
    ratio_before: float | None = Field(None, description="Holding ratio before")
    ratio_after: float | None = Field(None, description="Holding ratio after")
    ratio_change: float | None = Field(None, description="Ratio changed")
    
    avg_price: float | None = Field(None, description="Average transaction price")
    total_amount: float | None = Field(None, description="Total transaction amount")
    
    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls, v: str) -> str:
        valid_types = {"increase", "decrease", "unchanged", "buy", "sell"}
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid change type: {v}")
        return v.lower()
    
    @property
    def is_increase(self) -> bool:
        """Check if this is an increase."""
        return self.change_type in ("increase", "buy")
    
    @property
    def is_decrease(self) -> bool:
        """Check if this is a decrease."""
        return self.change_type in ("decrease", "sell")


class ADSInsiderTradingModel(ADSModelWithCode):
    """
    Insider trading data model.
    
    Tracks trading activities by company insiders.
    """
    
    trade_date: date = Field(..., description="Trade date")
    insider_name: str = Field(..., description="Insider name")
    insider_position: str | None = Field(None, description="Position in company")
    
    trade_type: str = Field(..., description="Trade type: buy/sell")
    trade_shares: float | None = Field(None, description="Number of shares traded")
    trade_price: float | None = Field(None, description="Trade price")
    trade_amount: float | None = Field(None, description="Trade amount")
    
    shares_held_after: float | None = Field(None, description="Shares held after trade")
    
    relation_to_company: str | None = Field(None, description="Relation to company")
    
    @field_validator("trade_type")
    @classmethod
    def validate_trade_type(cls, v: str) -> str:
        if v.lower() not in ("buy", "sell"):
            raise ValueError(f"Invalid trade type: {v}")
        return v.lower()
