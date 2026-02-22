"""
Metadata Data Models.

Provides ADS models for metadata:
- Data source metadata
- Table statistics
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from openfinance.datacenter.models.analytical.base import (
    ADSModel,
    DataQuality,
)


class ADSMetaModel(ADSModel):
    """
    Data source metadata model.
    
    Tracks metadata about data sources and tables.
    """
    
    table_name: str = Field(..., description="Table name")
    data_type: str = Field(..., description="Data type classification")
    
    record_count: int = Field(default=0, description="Total record count")
    
    date_start: date | None = Field(None, description="Earliest data date")
    date_end: date | None = Field(None, description="Latest data date")
    
    completeness: float = Field(
        default=0.0,
        description="Data completeness [0, 1]",
        ge=0,
        le=1
    )
    validity: float = Field(
        default=0.0,
        description="Data validity [0, 1]",
        ge=0,
        le=1
    )
    
    processing_status: str = Field(
        default="pending",
        description="Processing status: pending/processing/completed/failed"
    )
    
    notes: list[str] = Field(default_factory=list, description="Notes")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    
    last_sync_at: datetime | None = Field(None, description="Last sync timestamp")
    next_sync_at: datetime | None = Field(None, description="Next scheduled sync")
    
    @property
    def is_healthy(self) -> bool:
        """Check if data source is healthy."""
        return (
            self.processing_status == "completed"
            and self.completeness >= 0.9
            and self.validity >= 0.95
            and len(self.errors) == 0
        )
    
    @property
    def needs_sync(self) -> bool:
        """Check if data source needs sync."""
        if self.next_sync_at is None:
            return False
        return datetime.now() >= self.next_sync_at


class ADSFieldMetaModel(ADSModel):
    """
    Field-level metadata model.
    
    Tracks metadata about individual fields.
    """
    
    table_name: str = Field(..., description="Table name")
    field_name: str = Field(..., description="Field name")
    field_type: str = Field(..., description="Field data type")
    
    nullable: bool = Field(default=True, description="Whether field can be null")
    default_value: Any = Field(default=None, description="Default value")
    
    min_value: float | None = Field(None, description="Minimum value (for numeric)")
    max_value: float | None = Field(None, description="Maximum value (for numeric)")
    avg_value: float | None = Field(None, description="Average value (for numeric)")
    
    null_count: int = Field(default=0, description="Count of null values")
    distinct_count: int | None = Field(None, description="Count of distinct values")
    
    description: str | None = Field(None, description="Field description")
    business_meaning: str | None = Field(None, description="Business meaning")
    
    @property
    def null_rate(self) -> float | None:
        """Calculate null rate."""
        if self.distinct_count is not None and self.distinct_count > 0:
            return self.null_count / self.distinct_count
        return None
