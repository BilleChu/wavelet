"""
ADS Base Models and Enums.

Provides foundational classes and enumerations for all ADS models.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, ConfigDict


class DataQuality(str, Enum):
    """Data quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class DataCategory(str, Enum):
    """Data category for classification."""
    MARKET = "market"
    FINANCIAL = "financial"
    SHAREHOLDER = "shareholder"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    QUANT = "quant"
    META = "meta"


class ReportPeriod(str, Enum):
    """Financial report period types."""
    ANNUAL = "annual"
    SEMI_ANNUAL = "semi_annual"
    QUARTERLY = "quarterly"
    INTERIM = "interim"


class MarketType(str, Enum):
    """Market types."""
    SH = "sh"
    SZ = "sz"
    BJ = "bj"
    HK = "hk"
    US = "us"


class ADSModel(BaseModel):
    """
    Base model for all ADS data models.
    
    Provides common configuration and utilities:
    - ORM compatibility (from_attributes)
    - JSON serialization for Decimal and date types
    - Common metadata fields
    """
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: float(v),
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        },
        populate_by_name=True,
        validate_assignment=True,
    )
    
    quality: DataQuality = Field(
        default=DataQuality.UNKNOWN,
        description="Data quality level"
    )
    source: str = Field(
        default="unknown",
        description="Data source identifier"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp"
    )


class ADSModelWithCode(ADSModel):
    """Base model for stock-related data with code field."""
    
    code: str = Field(
        ...,
        description="Stock code (6-digit)",
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$"
    )
    
    @property
    def market(self) -> MarketType:
        """Determine market from code prefix."""
        if self.code.startswith(("60", "68")):
            return MarketType.SH
        elif self.code.startswith(("00", "30")):
            return MarketType.SZ
        elif self.code.startswith(("4", "8")):
            return MarketType.BJ
        else:
            return MarketType.SH


class ADSModelWithDate(ADSModel):
    """Base model for time-series data with date field."""
    
    trade_date: date = Field(
        ...,
        description="Trading date"
    )


class ADSModelWithReportDate(ADSModel):
    """Base model for financial data with report date."""
    
    report_date: date = Field(
        ...,
        description="Financial report date"
    )
    period: ReportPeriod = Field(
        default=ReportPeriod.QUARTERLY,
        description="Report period type"
    )


T = TypeVar("T", bound=ADSModel)


class ADSDataBatch(BaseModel, Generic[T]):
    """
    Batch container for ADS data with pagination support.
    
    Provides:
    - Generic data container
    - Pagination metadata
    - Batch tracking
    """
    
    data: list[T] = Field(
        default_factory=list,
        description="Data records"
    )
    total_count: int = Field(
        default=0,
        description="Total count before pagination"
    )
    batch_id: str = Field(
        ...,
        description="Batch identifier for tracking"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Batch creation time"
    )
    
    @property
    def count(self) -> int:
        """Current batch size."""
        return len(self.data)
    
    @property
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.data) == 0
    
    @property
    def has_more(self) -> bool:
        """Check if more data available."""
        return self.total_count > self.count


@dataclass
class FieldMapping:
    """
    Field mapping configuration for ORM to ADS transformation.
    
    Attributes:
        orm_field: Field name in ORM model
        ads_field: Field name in ADS model
        transform: Optional transformation function
        default: Default value if field is None
    """
    orm_field: str
    ads_field: str
    transform: callable | None = None
    default: Any = None


@dataclass
class ModelMapping:
    """
    Complete model mapping configuration.
    
    Attributes:
        orm_model: SQLAlchemy ORM model class
        ads_model: ADS model class
        field_mappings: List of field mappings
        computed_fields: Fields computed from other fields
    """
    orm_model: type
    ads_model: type
    field_mappings: list[FieldMapping] = field(default_factory=list)
    computed_fields: dict[str, callable] = field(default_factory=dict)
