"""
Market Data Models.

Provides ADS models for market-related data:
- K-Line (OHLCV) data
- Money flow data
- Option quotes
- Future quotes
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


class ADSKLineModel(ADSModelWithCode, ADSModelWithDate):
    """
    Standardized K-Line (Candlestick) data model.
    
    This is the fundamental data structure for quantitative analysis.
    All technical indicators are calculated from this base data.
    
    Field Naming Convention:
    - Price fields: open, high, low, close, pre_close
    - Volume fields: volume, amount
    - Rate fields: turnover_rate, amplitude, change_pct
    - Market value: market_cap, circulating_market_cap
    """
    
    name: str | None = Field(None, description="Stock name")
    
    open: float | None = Field(None, description="Opening price", ge=0)
    high: float | None = Field(None, description="Highest price", ge=0)
    low: float | None = Field(None, description="Lowest price", ge=0)
    close: float | None = Field(None, description="Closing price", ge=0)
    
    volume: int | None = Field(None, description="Trading volume", ge=0)
    amount: float | None = Field(None, description="Trading amount", ge=0)
    
    pre_close: float | None = Field(None, description="Previous closing price", ge=0)
    change: float | None = Field(None, description="Price change")
    change_pct: float | None = Field(None, description="Price change percentage")
    
    turnover_rate: float | None = Field(None, description="Turnover rate")
    amplitude: float | None = Field(None, description="Amplitude percentage")
    
    market_cap: float | None = Field(None, description="Total market cap", ge=0)
    circulating_market_cap: float | None = Field(None, description="Circulating market cap", ge=0)
    
    @field_validator("high", "low", "open", "close")
    @classmethod
    def validate_price(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError(f"Price cannot be negative: {v}")
        return v
    
    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError(f"Volume cannot be negative: {v}")
        return v
    
    @property
    def is_valid(self) -> bool:
        """Check if K-Line data is valid for analysis."""
        return all([
            self.open is not None,
            self.high is not None,
            self.low is not None,
            self.close is not None,
            self.high >= self.low,
            self.high >= self.open,
            self.high >= self.close,
            self.low <= self.open,
            self.low <= self.close,
        ])
    
    @property
    def typical_price(self) -> float | None:
        """Calculate typical price (HLC/3)."""
        if self.high and self.low and self.close:
            return (self.high + self.low + self.close) / 3
        return None
    
    @property
    def true_range(self) -> float | None:
        """Calculate true range."""
        if not self.is_valid:
            return None
        
        ranges = [self.high - self.low]
        if self.pre_close:
            ranges.append(abs(self.high - self.pre_close))
            ranges.append(abs(self.low - self.pre_close))
        
        return max(ranges)
    
    @property
    def average_price(self) -> float | None:
        """Calculate VWAP approximation."""
        if self.amount and self.volume and self.volume > 0:
            return self.amount / self.volume
        return None


class ADSMoneyFlowModel(ADSModelWithCode, ADSModelWithDate):
    """
    Money flow data model.
    
    Tracks capital inflow/outflow by investor type.
    """
    
    name: str | None = Field(None, description="Stock name")
    
    main_net_inflow: float | None = Field(None, description="Main force net inflow")
    main_net_inflow_pct: float | None = Field(None, description="Main force net inflow percentage")
    
    super_large_net_inflow: float | None = Field(None, description="Super large order net inflow")
    large_net_inflow: float | None = Field(None, description="Large order net inflow")
    medium_net_inflow: float | None = Field(None, description="Medium order net inflow")
    small_net_inflow: float | None = Field(None, description="Small order net inflow")
    
    north_net_inflow: float | None = Field(None, description="Northbound capital net inflow")
    
    @property
    def total_net_inflow(self) -> float | None:
        """Calculate total net inflow."""
        inflows = [
            self.super_large_net_inflow or 0,
            self.large_net_inflow or 0,
            self.medium_net_inflow or 0,
            self.small_net_inflow or 0,
        ]
        return sum(inflows)


class ADSOptionQuoteModel(ADSModelWithCode, ADSModelWithDate):
    """
    Option quote data model.
    
    Contains option pricing and Greeks data.
    """
    
    name: str | None = Field(None, description="Option name")
    underlying: str = Field(..., description="Underlying asset code")
    strike_price: float = Field(..., description="Strike price", ge=0)
    expiry_date: date = Field(..., description="Expiration date")
    option_type: str = Field(..., description="Option type: call/put")
    
    last_price: float | None = Field(None, description="Last traded price")
    bid_price: float | None = Field(None, description="Bid price")
    ask_price: float | None = Field(None, description="Ask price")
    
    volume: int | None = Field(None, description="Trading volume")
    open_interest: int | None = Field(None, description="Open interest")
    
    implied_volatility: float | None = Field(None, description="Implied volatility")
    
    delta: float | None = Field(None, description="Delta")
    gamma: float | None = Field(None, description="Gamma")
    theta: float | None = Field(None, description="Theta")
    vega: float | None = Field(None, description="Vega")
    rho: float | None = Field(None, description="Rho")
    
    @field_validator("option_type")
    @classmethod
    def validate_option_type(cls, v: str) -> str:
        if v.lower() not in ("call", "put", "c", "p"):
            raise ValueError(f"Invalid option type: {v}")
        return v.lower()[:4]
    
    @property
    def is_call(self) -> bool:
        """Check if this is a call option."""
        return self.option_type in ("call", "c")
    
    @property
    def bid_ask_spread(self) -> float | None:
        """Calculate bid-ask spread."""
        if self.bid_price and self.ask_price:
            return self.ask_price - self.bid_price
        return None


class ADSFutureQuoteModel(ADSModelWithCode, ADSModelWithDate):
    """
    Future quote data model.
    
    Contains futures pricing and contract information.
    """
    
    name: str | None = Field(None, description="Future name")
    exchange: str = Field(..., description="Exchange code")
    delivery_month: str | None = Field(None, description="Delivery month (YYYYMM)")
    
    open: float | None = Field(None, description="Opening price")
    high: float | None = Field(None, description="Highest price")
    low: float | None = Field(None, description="Lowest price")
    close: float | None = Field(None, description="Closing price")
    
    pre_settlement: float | None = Field(None, description="Previous settlement price")
    settlement: float | None = Field(None, description="Settlement price")
    
    change: float | None = Field(None, description="Price change")
    change_pct: float | None = Field(None, description="Price change percentage")
    
    volume: int | None = Field(None, description="Trading volume")
    amount: float | None = Field(None, description="Trading amount")
    open_interest: int | None = Field(None, description="Open interest")
    
    @property
    def is_valid(self) -> bool:
        """Check if future quote is valid."""
        return all([
            self.open is not None,
            self.high is not None,
            self.low is not None,
            self.close is not None,
        ])


class ADSStockBasicModel(ADSModelWithCode):
    """
    Stock basic information model.
    
    Contains static/semi-static stock information.
    """
    
    name: str = Field(..., description="Stock name")
    industry: str | None = Field(None, description="Industry classification")
    sector: str | None = Field(None, description="Sector classification")
    market_type: str | None = Field(None, description="Market type")
    listing_date: date | None = Field(None, description="Listing date")
    status: str = Field(default="L", description="Listing status: L/D/P")
    
    @property
    def is_listed(self) -> bool:
        """Check if stock is actively listed."""
        return self.status == "L"
    
    @property
    def is_delisted(self) -> bool:
        """Check if stock is delisted."""
        return self.status == "D"
