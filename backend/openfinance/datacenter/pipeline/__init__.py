"""
Data Pipeline Module for Data Center.

Provides unified data pipeline abstraction with:
- DataSourceAdapter interface for standardized data access
- PipelineBuilder for fluent pipeline construction
- PipelineRegistry for centralized pipeline management
- DAG-based task orchestration
"""

from .builder import PipelineBuilder, Pipeline, PipelineStage, StageType
from .adapter import (
    DataSourceAdapter,
    AdapterConfig,
    AdapterCapability,
    AdapterStatus,
)
from .registry import PipelineRegistry, PipelineTemplate

__all__ = [
    "PipelineBuilder",
    "Pipeline",
    "PipelineStage",
    "StageType",
    "DataSourceAdapter",
    "AdapterConfig",
    "AdapterCapability",
    "AdapterStatus",
    "PipelineRegistry",
    "PipelineTemplate",
]
