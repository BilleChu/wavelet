"""
Factor Base Module for OpenFinance Quantitative System.

This module provides a unified abstract base class for all quantitative factors.
All factors must be calculated from K-Line base data (OHLCV) or approved data sources.

Classes:
- FactorBase: Unified abstract base class for all factors
- FactorMetadata: Factor metadata container
- FactorConfig: Factor calculation configuration
- FactorResult: Result of factor calculation
- ParameterDefinition: Definition of a factor parameter
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable, Generic, TypeVar

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator

from openfinance.datacenter.models.analytical import ADSKLineModel
from openfinance.domain.models.quant import (
    FactorType,
    FactorCategory,
    FactorStatus,
    NormalizeMethod,
    NeutralizationType,
)


__all__ = [
    'FactorType', 'FactorCategory', 'FactorStatus',
    'NormalizeMethod', 'NeutralizationType',
    'FactorBase', 'FactorMetadata', 'FactorConfig',
    'ParameterDefinition', 'ValidationResult', 'create_factor',
    'FactorResult',
]


@dataclass
class FactorMetadata:
    """Factor metadata with comprehensive information."""
    
    factor_id: str
    name: str
    description: str = ""
    factor_type: FactorType = FactorType.TECHNICAL
    category: FactorCategory = FactorCategory.CUSTOM
    version: str = "1.0.0"
    author: str = "system"
    tags: list[str] = field(default_factory=list)
    required_fields: list[str] = field(default_factory=lambda: ["close"])
    lookback_period: int = 1
    normalize_method: NormalizeMethod = NormalizeMethod.ZSCORE
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: FactorStatus = FactorStatus.ACTIVE
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "description": self.description,
            "factor_type": self.factor_type.value,
            "category": self.category.value,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "required_fields": self.required_fields,
            "lookback_period": self.lookback_period,
            "normalize_method": self.normalize_method.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
        }


class ParameterDefinition(BaseModel):
    """Definition of a factor parameter."""
    
    name: str = Field(..., description="Parameter name")
    type: str = Field("float", description="Parameter type: int, float, str, bool")
    default: Any = Field(None, description="Default value")
    min_value: float | None = Field(None, description="Minimum value for numeric types")
    max_value: float | None = Field(None, description="Maximum value for numeric types")
    options: list[Any] | None = Field(None, description="Allowed values for enum types")
    description: str = Field("", description="Parameter description")
    required: bool = Field(False, description="Whether parameter is required")
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"int", "float", "str", "bool", "list", "dict"}
        if v not in allowed:
            raise ValueError(f"Invalid type: {v}. Must be one of {allowed}")
        return v


class FactorConfig(BaseModel):
    """Configuration for factor calculation."""
    
    lookback_period: int = Field(14, ge=1, description="Lookback period")
    normalize: bool = Field(True, description="Whether to normalize")
    normalize_method: NormalizeMethod = Field(NormalizeMethod.ZSCORE)
    fill_na: bool = Field(True, description="Whether to fill NA values")
    use_cache: bool = Field(True, description="Whether to use cache")
    parameters: dict[str, Any] = Field(default_factory=dict)


class FactorResult(BaseModel):
    """Result of factor calculation."""
    
    factor_id: str = Field(..., description="Factor identifier")
    code: str = Field(..., description="Stock code")
    trade_date: date = Field(..., description="Trading date")
    value: float | None = Field(None, description="Raw factor value")
    value_normalized: float | None = Field(None, description="Normalized value")
    value_rank: int | None = Field(None, description="Rank among all stocks")
    value_percentile: float | None = Field(None, description="Percentile rank")
    value_neutralized: float | None = Field(None, description="Neutralized value")
    signal: float = Field(0.0, ge=-1.0, le=1.0, description="Trading signal")
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Signal confidence")
    data_quality: str = Field("high", description="Data quality indicator")
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        return self.value is not None and not np.isnan(self.value) if self.value else False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "code": self.code,
            "trade_date": self.trade_date.isoformat(),
            "value": self.value,
            "value_normalized": self.value_normalized,
            "value_rank": self.value_rank,
            "value_percentile": self.value_percentile,
            "value_neutralized": self.value_neutralized,
            "signal": self.signal,
            "confidence": self.confidence,
            "data_quality": self.data_quality,
            "metadata": self.metadata,
        }


class ValidationResult(BaseModel):
    """Result of input validation."""
    
    is_valid: bool = Field(True)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


T = TypeVar("T")


class FactorBase(ABC, Generic[T]):
    """
    Unified abstract base class for all quantitative factors.
    
    Usage:
        @register_factor(is_builtin=True)
        class RSIFactor(FactorBase):
            def _default_metadata(self) -> FactorMetadata:
                return FactorMetadata(factor_id="factor_rsi", name="RSI")
            
            def _calculate(self, klines, **params) -> float | None:
                # RSI calculation logic
                return rsi_value
    """
    
    def __init__(
        self,
        factor_id: str = "",
        name: str = "",
        code: str = "",
        description: str = "",
        factor_type: str | FactorType = FactorType.TECHNICAL,
        category: str | FactorCategory = FactorCategory.CUSTOM,
        lookback_period: int = 20,
        parameters: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        metadata: FactorMetadata | None = None,
        config: FactorConfig | None = None,
    ):
        if metadata:
            self._metadata = metadata
            self.factor_id = metadata.factor_id
            self.name = metadata.name
            self.description = metadata.description
            self.factor_type = metadata.factor_type.value
            self.category = metadata.category.value
            self.lookback_period = metadata.lookback_period
            self.tags = metadata.tags
            self.version = metadata.version
            self.status = metadata.status.value
        else:
            self._metadata = None
            self.factor_id = factor_id
            self.name = name
            self.description = description
            self.factor_type = factor_type.value if isinstance(factor_type, FactorType) else factor_type
            self.category = category.value if isinstance(category, FactorCategory) else category
            self.lookback_period = lookback_period
            self.tags = tags or []
            self.version = "1.0.0"
            self.status = "active"
        
        self.code = code or self.factor_id.replace("factor_", "")
        self.parameters = parameters or {}
        self._config = config or FactorConfig()
        self._parameter_defs: dict[str, ParameterDefinition] = self._define_parameters()
    
    @property
    def metadata(self) -> FactorMetadata:
        if self._metadata is None:
            if self.factor_id:
                self._metadata = FactorMetadata(
                    factor_id=self.factor_id,
                    name=self.name,
                    description=self.description,
                    factor_type=FactorType(self.factor_type),
                    category=FactorCategory(self.category),
                    version=self.version,
                    tags=self.tags,
                    lookback_period=self.lookback_period,
                )
            else:
                self._metadata = self._default_metadata()
                self.factor_id = self._metadata.factor_id
                self.name = self._metadata.name
        return self._metadata
    
    @property
    def config(self) -> FactorConfig:
        return self._config
    
    @property
    def parameter_definitions(self) -> dict[str, ParameterDefinition]:
        return self._parameter_defs
    
    def _default_metadata(self) -> FactorMetadata:
        return FactorMetadata(factor_id=self.factor_id, name=self.name)
    
    def _define_parameters(self) -> dict[str, ParameterDefinition]:
        return {}
    
    @abstractmethod
    def _calculate(
        self,
        klines: list[ADSKLineModel],
        **params: Any,
    ) -> T | None:
        """
        Core calculation logic. Must be implemented by subclasses.
        
        Args:
            klines: K-Line data (sorted by date, oldest first)
            **params: Factor-specific parameters
        
        Returns:
            Calculated factor value, or None if calculation fails
        """
        raise NotImplementedError
    
    def calculate(
        self,
        klines: list[ADSKLineModel],
        **params: Any,
    ) -> FactorResult | None:
        """Calculate factor with full result."""
        import time
        start_time = time.perf_counter()
        
        try:
            _ = self.metadata
            
            merged_params = {**self._config.parameters, **params}
            value = self._calculate(klines, **merged_params)
            
            if value is None:
                return None
            
            latest = klines[-1]
            
            result = FactorResult(
                factor_id=self.factor_id,
                code=latest.code,
                trade_date=latest.trade_date,
                value=float(value) if not isinstance(value, float) else value,
            )
            
            if self._config.normalize:
                result.value_normalized = self.normalize(result.value)
            
            result.metadata["calculation_time_ms"] = (time.perf_counter() - start_time) * 1000
            return result
            
        except Exception:
            return None
    
    def normalize(
        self,
        value: float,
        universe_values: list[float] | None = None,
    ) -> float:
        """Normalize factor value using z-score."""
        if universe_values and len(universe_values) > 1:
            arr = np.array(universe_values)
            mean, std = np.nanmean(arr), np.nanstd(arr)
            if std > 0:
                return (value - mean) / std
        return 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "factor_type": self.factor_type,
            "category": self.category,
            "lookback_period": self.lookback_period,
            "parameters": self.parameters,
            "tags": self.tags,
            "version": self.version,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(factor_id='{self.factor_id}', name='{self.name}')"


def create_factor(
    factor_id: str,
    calculation_func: Callable[[list[ADSKLineModel]], float | None],
    metadata: FactorMetadata | None = None,
) -> FactorBase:
    """Factory function to create a custom factor instance."""
    default_meta = metadata or FactorMetadata(
        factor_id=factor_id,
        name=factor_id.replace("_", " ").title(),
    )
    
    class CustomFactor(FactorBase):
        def _default_metadata(self) -> FactorMetadata:
            return default_meta
        
        def _calculate(self, klines: list[ADSKLineModel], **params) -> float | None:
            return calculation_func(klines, **params)
    
    instance = CustomFactor(metadata=default_meta)
    instance.__class__.__name__ = f"{factor_id.title().replace('_', '')}Factor"
    return instance
