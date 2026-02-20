"""
Pipeline Builder for Data Center.

Provides fluent API for building data pipelines with:
- Stage-based pipeline construction
- DAG-based dependency management
- Conditional execution
- Error handling and recovery
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable, Generic, TypeVar

from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class StageType(str, Enum):
    """Types of pipeline stages."""
    
    SOURCE = "source"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    JOIN = "join"
    SPLIT = "split"
    SINK = "sink"
    BRANCH = "branch"
    MERGE = "merge"
    PARALLEL = "parallel"
    LOOP = "loop"


class StageStatus(str, Enum):
    """Status of a pipeline stage."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Status of a pipeline."""
    
    CREATED = "created"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StageResult:
    """Result of a stage execution."""
    
    stage_id: str
    status: StageStatus
    data: Any = None
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    @property
    def duration_ms(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "status": self.status.value,
            "error": self.error,
            "metrics": self.metrics,
            "duration_ms": self.duration_ms,
        }


@dataclass
class PipelineStage(Generic[T]):
    """
    A stage in the data pipeline.
    
    Each stage represents a unit of work in the pipeline,
    with defined inputs, outputs, and execution logic.
    """
    
    stage_id: str
    name: str
    stage_type: StageType
    
    handler: Callable[[Any, dict], Awaitable[Any]] | None = None
    config: dict[str, Any] = field(default_factory=dict)
    
    dependencies: list[str] = field(default_factory=list)
    condition: Callable[[dict], bool] | None = None
    
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    
    status: StageStatus = StageStatus.PENDING
    result: StageResult | None = None
    
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "name": self.name,
            "stage_type": self.stage_type.value,
            "config": self.config,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class PipelineEdge:
    """An edge connecting two stages."""
    
    edge_id: str
    source_id: str
    target_id: str
    condition: Callable[[dict], bool] | None = None
    label: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
        }


class PipelineResult(BaseModel):
    """Result of pipeline execution."""
    
    pipeline_id: str
    status: PipelineStatus
    stages_executed: int = 0
    stages_succeeded: int = 0
    stages_failed: int = 0
    stages_skipped: int = 0
    total_duration_ms: float = 0.0
    output: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    stage_results: list[dict[str, Any]] = Field(default_factory=list)


class Pipeline(BaseModel):
    """
    Definition of a data pipeline.
    
    A pipeline consists of stages connected by edges,
    forming a DAG (Directed Acyclic Graph).
    """
    
    pipeline_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., description="Pipeline name")
    description: str = Field(default="", description="Pipeline description")
    version: str = Field(default="1.0.0", description="Pipeline version")
    
    stages: dict[str, PipelineStage] = Field(default_factory=dict)
    edges: list[PipelineEdge] = Field(default_factory=list)
    
    status: PipelineStatus = Field(default=PipelineStatus.CREATED)
    
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    
    context: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "edges": [e.to_dict() for e in self.edges],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context,
            "tags": self.tags,
        }


class PipelineBuilder:
    """
    Fluent builder for creating data pipelines.
    
    Usage:
        pipeline = (PipelineBuilder("daily_collection")
            .source("fetch_quotes", fetch_handler)
            .transform("normalize", normalize_handler)
            .validate("validate", validate_handler)
            .sink("save", save_handler)
            .build())
        
        result = await pipeline_executor.execute(pipeline)
    """
    
    def __init__(self, name: str, description: str = "") -> None:
        self._name = name
        self._description = description
        self._pipeline = Pipeline(name=name, description=description)
        self._current_stage: str | None = None
        self._stage_counter = 0
    
    def source(
        self,
        name: str,
        handler: Callable[[Any, dict], Awaitable[Any]],
        config: dict[str, Any] | None = None,
    ) -> "PipelineBuilder":
        """Add a source stage to fetch data."""
        return self._add_stage(
            name=name,
            stage_type=StageType.SOURCE,
            handler=handler,
            config=config or {},
        )
    
    def transform(
        self,
        name: str,
        handler: Callable[[Any, dict], Awaitable[Any]],
        config: dict[str, Any] | None = None,
    ) -> "PipelineBuilder":
        """Add a transform stage to process data."""
        return self._add_stage(
            name=name,
            stage_type=StageType.TRANSFORM,
            handler=handler,
            config=config or {},
        )
    
    def validate(
        self,
        name: str,
        handler: Callable[[Any, dict], Awaitable[Any]],
        config: dict[str, Any] | None = None,
    ) -> "PipelineBuilder":
        """Add a validation stage."""
        return self._add_stage(
            name=name,
            stage_type=StageType.VALIDATE,
            handler=handler,
            config=config or {},
        )
    
    def filter(
        self,
        name: str,
        handler: Callable[[Any, dict], Awaitable[Any]],
        config: dict[str, Any] | None = None,
    ) -> "PipelineBuilder":
        """Add a filter stage."""
        return self._add_stage(
            name=name,
            stage_type=StageType.FILTER,
            handler=handler,
            config=config or {},
        )
    
    def aggregate(
        self,
        name: str,
        handler: Callable[[Any, dict], Awaitable[Any]],
        config: dict[str, Any] | None = None,
    ) -> "PipelineBuilder":
        """Add an aggregation stage."""
        return self._add_stage(
            name=name,
            stage_type=StageType.AGGREGATE,
            handler=handler,
            config=config or {},
        )
    
    def sink(
        self,
        name: str,
        handler: Callable[[Any, dict], Awaitable[Any]],
        config: dict[str, Any] | None = None,
    ) -> "PipelineBuilder":
        """Add a sink stage to output data."""
        return self._add_stage(
            name=name,
            stage_type=StageType.SINK,
            handler=handler,
            config=config or {},
        )
    
    def branch(
        self,
        name: str,
        branches: dict[str, Callable[[Any, dict], Awaitable[Any]]],
        condition: Callable[[Any], str],
    ) -> "PipelineBuilder":
        """
        Add a branching stage.
        
        Args:
            name: Stage name
            branches: Dict mapping branch names to handlers
            condition: Function that returns branch name
        """
        return self._add_stage(
            name=name,
            stage_type=StageType.BRANCH,
            handler=None,
            config={
                "branches": branches,
                "condition": condition,
            },
        )
    
    def parallel(
        self,
        name: str,
        handlers: list[Callable[[Any, dict], Awaitable[Any]]],
        merge_handler: Callable[[list[Any]], Any] | None = None,
    ) -> "PipelineBuilder":
        """
        Add a parallel execution stage.
        
        Args:
            name: Stage name
            handlers: List of handlers to execute in parallel
            merge_handler: Optional handler to merge results
        """
        return self._add_stage(
            name=name,
            stage_type=StageType.PARALLEL,
            handler=None,
            config={
                "handlers": handlers,
                "merge_handler": merge_handler,
            },
        )
    
    def depends_on(self, *stage_names: str) -> "PipelineBuilder":
        """Set dependencies for the current stage."""
        if self._current_stage is None:
            raise ValueError("No current stage to set dependencies for")
        
        stage = self._pipeline.stages.get(self._current_stage)
        if stage:
            stage.dependencies = list(stage_names)
            
            for dep_name in stage_names:
                dep_stage = self._find_stage_by_name(dep_name)
                if dep_stage:
                    self._add_edge(dep_stage.stage_id, self._current_stage)
        
        return self
    
    def with_condition(self, condition: Callable[[dict], bool]) -> "PipelineBuilder":
        """Add a condition for the current stage execution."""
        if self._current_stage is None:
            raise ValueError("No current stage to add condition for")
        
        stage = self._pipeline.stages.get(self._current_stage)
        if stage:
            stage.condition = condition
        
        return self
    
    def with_retry(self, max_retries: int = 3) -> "PipelineBuilder":
        """Set retry policy for the current stage."""
        if self._current_stage is None:
            raise ValueError("No current stage to set retry for")
        
        stage = self._pipeline.stages.get(self._current_stage)
        if stage:
            stage.max_retries = max_retries
        
        return self
    
    def with_timeout(self, seconds: float) -> "PipelineBuilder":
        """Set timeout for the current stage."""
        if self._current_stage is None:
            raise ValueError("No current stage to set timeout for")
        
        stage = self._pipeline.stages.get(self._current_stage)
        if stage:
            stage.timeout_seconds = seconds
        
        return self
    
    def with_config(self, config: dict[str, Any]) -> "PipelineBuilder":
        """Add configuration for the current stage."""
        if self._current_stage is None:
            raise ValueError("No current stage to set config for")
        
        stage = self._pipeline.stages.get(self._current_stage)
        if stage:
            stage.config.update(config)
        
        return self
    
    def with_tag(self, tag: str) -> "PipelineBuilder":
        """Add a tag to the pipeline."""
        if tag not in self._pipeline.tags:
            self._pipeline.tags.append(tag)
        return self
    
    def with_context(self, key: str, value: Any) -> "PipelineBuilder":
        """Add context data to the pipeline."""
        self._pipeline.context[key] = value
        return self
    
    def _add_stage(
        self,
        name: str,
        stage_type: StageType,
        handler: Callable[[Any, dict], Awaitable[Any]] | None,
        config: dict[str, Any],
    ) -> "PipelineBuilder":
        """Add a stage to the pipeline."""
        self._stage_counter += 1
        stage_id = f"stage_{self._stage_counter}"
        
        stage = PipelineStage(
            stage_id=stage_id,
            name=name,
            stage_type=stage_type,
            handler=handler,
            config=config,
        )
        
        if self._current_stage:
            prev_stage = self._pipeline.stages.get(self._current_stage)
            if prev_stage:
                stage.dependencies.append(self._current_stage)
                self._add_edge(self._current_stage, stage_id)
        
        self._pipeline.stages[stage_id] = stage
        self._current_stage = stage_id
        
        return self
    
    def _add_edge(self, source_id: str, target_id: str) -> None:
        """Add an edge between stages."""
        edge = PipelineEdge(
            edge_id=f"edge_{len(self._pipeline.edges) + 1}",
            source_id=source_id,
            target_id=target_id,
        )
        self._pipeline.edges.append(edge)
    
    def _find_stage_by_name(self, name: str) -> PipelineStage | None:
        """Find a stage by name."""
        for stage in self._pipeline.stages.values():
            if stage.name == name:
                return stage
        return None
    
    def build(self) -> Pipeline:
        """Build and validate the pipeline."""
        if not self._validate_dag():
            raise ValueError("Pipeline contains cycles, not a valid DAG")
        
        self._pipeline.status = PipelineStatus.READY
        return self._pipeline
    
    def _validate_dag(self) -> bool:
        """Validate that the pipeline is a valid DAG."""
        from collections import defaultdict
        
        visited = set()
        rec_stack = set()
        
        adj = defaultdict(list)
        for edge in self._pipeline.edges:
            adj[edge.source_id].append(edge.target_id)
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in adj[node_id]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for stage_id in self._pipeline.stages:
            if stage_id not in visited:
                if has_cycle(stage_id):
                    return False
        
        return True


class PipelineExecutor:
    """
    Executor for running data pipelines.
    
    Features:
    - DAG-based execution order
    - Parallel execution of independent stages
    - Error handling and retry
    - Progress tracking
    """
    
    def __init__(self) -> None:
        self._running_pipelines: dict[str, Pipeline] = {}
    
    async def execute(
        self,
        pipeline: Pipeline,
        initial_data: Any = None,
        stop_on_failure: bool = True,
    ) -> PipelineResult:
        """
        Execute a pipeline.
        
        Args:
            pipeline: The pipeline to execute
            initial_data: Initial input data
            stop_on_failure: Whether to stop on first failure
            
        Returns:
            PipelineResult with execution statistics
        """
        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.now()
        self._running_pipelines[pipeline.pipeline_id] = pipeline
        
        result = PipelineResult(
            pipeline_id=pipeline.pipeline_id,
            status=PipelineStatus.RUNNING,
        )
        
        context = {"data": initial_data, **pipeline.context}
        start_time = datetime.now()
        
        try:
            while True:
                ready_stages = self._get_ready_stages(pipeline)
                
                if not ready_stages:
                    break
                
                tasks = [
                    self._execute_stage(pipeline, stage_id, context)
                    for stage_id in ready_stages
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for stage_id, stage_result in zip(ready_stages, results):
                    result.stages_executed += 1
                    
                    if isinstance(stage_result, Exception):
                        result.stages_failed += 1
                        result.errors.append(f"{stage_id}: {str(stage_result)}")
                        
                        if stop_on_failure:
                            pipeline.status = PipelineStatus.FAILED
                            break
                    else:
                        result.stages_succeeded += 1
                        result.stage_results.append(stage_result.to_dict())
                
                if pipeline.status == PipelineStatus.FAILED:
                    break
            
            if pipeline.status == PipelineStatus.RUNNING:
                pipeline.status = PipelineStatus.COMPLETED
                result.output = context
            
        except Exception as e:
            pipeline.status = PipelineStatus.FAILED
            result.errors.append(str(e))
        
        pipeline.completed_at = datetime.now()
        result.status = pipeline.status
        result.total_duration_ms = (
            pipeline.completed_at - start_time
        ).total_seconds() * 1000
        
        return result
    
    def _get_ready_stages(self, pipeline: Pipeline) -> list[str]:
        """Get stages ready for execution."""
        ready = []
        
        for stage_id, stage in pipeline.stages.items():
            if stage.status != StageStatus.PENDING:
                continue
            
            deps = stage.dependencies
            if not deps:
                ready.append(stage_id)
                continue
            
            all_deps_completed = all(
                pipeline.stages.get(dep, PipelineStage(
                    stage_id="", name="", stage_type=StageType.SOURCE
                )).status == StageStatus.COMPLETED
                for dep in deps
            )
            
            if all_deps_completed:
                ready.append(stage_id)
        
        return ready
    
    async def _execute_stage(
        self,
        pipeline: Pipeline,
        stage_id: str,
        context: dict[str, Any],
    ) -> StageResult:
        """Execute a single stage."""
        stage = pipeline.stages[stage_id]
        stage.status = StageStatus.RUNNING
        
        result = StageResult(
            stage_id=stage_id,
            status=StageStatus.RUNNING,
            started_at=datetime.now(),
        )
        
        try:
            if stage.condition and not stage.condition(context):
                stage.status = StageStatus.SKIPPED
                result.status = StageStatus.SKIPPED
                result.completed_at = datetime.now()
                return result
            
            if stage.handler is None:
                raise ValueError(f"No handler for stage {stage_id}")
            
            output = await asyncio.wait_for(
                stage.handler(context.get("data"), context),
                timeout=stage.timeout_seconds,
            )
            
            context["data"] = output
            stage.status = StageStatus.COMPLETED
            result.status = StageStatus.COMPLETED
            result.data = output
            result.completed_at = datetime.now()
            
            logger.info_with_context(
                f"Stage completed: {stage.name}",
                context={
                    "pipeline_id": pipeline.pipeline_id,
                    "stage_id": stage_id,
                    "duration_ms": result.duration_ms,
                }
            )
            
        except asyncio.TimeoutError:
            stage.status = StageStatus.FAILED
            result.status = StageStatus.FAILED
            result.error = f"Timeout after {stage.timeout_seconds}s"
            result.completed_at = datetime.now()
            raise
            
        except Exception as e:
            stage.retry_count += 1
            if stage.retry_count < stage.max_retries:
                stage.status = StageStatus.PENDING
                logger.warning_with_context(
                    f"Stage failed, will retry: {stage.name}",
                    context={
                        "pipeline_id": pipeline.pipeline_id,
                        "stage_id": stage_id,
                        "error": str(e),
                        "retry_count": stage.retry_count,
                    }
                )
            else:
                stage.status = StageStatus.FAILED
                result.status = StageStatus.FAILED
                result.error = str(e)
                result.completed_at = datetime.now()
            raise
        
        stage.result = result
        return result
    
    def get_pipeline(self, pipeline_id: str) -> Pipeline | None:
        """Get a running pipeline by ID."""
        return self._running_pipelines.get(pipeline_id)
    
    async def cancel(self, pipeline_id: str) -> bool:
        """Cancel a running pipeline."""
        pipeline = self._running_pipelines.get(pipeline_id)
        if not pipeline:
            return False
        
        pipeline.status = PipelineStatus.CANCELLED
        pipeline.completed_at = datetime.now()
        
        for stage in pipeline.stages.values():
            if stage.status == StageStatus.RUNNING:
                stage.status = StageStatus.PENDING
        
        return True
