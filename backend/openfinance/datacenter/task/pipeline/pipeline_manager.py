"""
Pipeline Manager - Manage pipeline execution using task queue.

Provides:
- Pipeline execution via TaskQueue
- Pipeline scheduling
- Execution monitoring
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from openfinance.datacenter.task.queue import (
    TaskQueue,
    TaskDefinition,
    TaskPriority,
    TaskStatus,
)
from openfinance.datacenter.task.dag_engine import DAGEngine, DAG
from openfinance.datacenter.task.registry import TaskRegistry
from openfinance.datacenter.task.pipeline.pipeline_config import (
    PipelineConfig,
    PipelineRegistry,
    ScheduleType,
)
from openfinance.datacenter.task.pipeline.pipeline_builder import PipelineBuilder

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineExecution:
    """Record of pipeline execution."""
    
    execution_id: str
    pipeline_id: str
    status: TaskStatus
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    task_results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "pipeline_id": self.pipeline_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "task_results": self.task_results,
            "error": self.error,
        }


class PipelineManager:
    """
    Manager for pipeline execution using task queue and DAG engine.
    
    Features:
    - Execute pipelines via TaskQueue
    - Schedule pipelines based on configuration
    - Monitor execution progress
    - Retry failed tasks
    """
    
    _instance: "PipelineManager | None" = None
    
    def __init__(
        self,
        task_queue: TaskQueue | None = None,
        dag_engine: DAGEngine | None = None,
        max_concurrent: int = 5,
    ):
        self.task_queue = task_queue or TaskQueue(max_concurrent=max_concurrent)
        self.dag_engine = dag_engine or DAGEngine(max_concurrent_tasks=max_concurrent)
        self.builder = PipelineBuilder(self.dag_engine)
        
        self._executions: list[PipelineExecution] = []
        self._running_pipelines: dict[str, asyncio.Task] = {}
        self._is_running = False
        
        self._register_executors()
    
    @classmethod
    def get_instance(cls, **kwargs) -> "PipelineManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def _register_executors(self) -> None:
        """Register task executors from TaskRegistry."""
        for task_type, executor in TaskRegistry._executors.items():
            self.dag_engine.register_executor(task_type, self._create_executor_wrapper(executor))
    
    def _create_executor_wrapper(self, executor) -> Callable:
        """Create wrapper for executor to match DAG engine signature."""
        async def wrapper(params: dict, context: dict) -> dict:
            from openfinance.datacenter.task.registry import TaskProgress
            
            progress = TaskProgress(task_id=context.get("task_id", "unknown"))
            result = await executor.execute(params, progress)
            return result
        
        return wrapper
    
    async def start(self) -> None:
        """Start the pipeline manager."""
        if self._is_running:
            return
        
        self._is_running = True
        await self.task_queue.start()
        
        logger.info("PipelineManager started")
    
    async def stop(self) -> None:
        """Stop the pipeline manager."""
        self._is_running = False
        
        for pipeline_id, task in list(self._running_pipelines.items()):
            task.cancel()
        
        await self.task_queue.stop()
        
        logger.info("PipelineManager stopped")
    
    async def execute_pipeline(
        self,
        pipeline_id: str,
        params: dict[str, Any] | None = None,
        on_progress: Callable[[str, str, float], None] | None = None,
    ) -> PipelineExecution:
        """
        Execute a pipeline by ID.
        
        Args:
            pipeline_id: ID of the pipeline to execute
            params: Optional parameters to pass to tasks
            on_progress: Optional callback for progress updates
        
        Returns:
            Execution record
        """
        config = PipelineRegistry().get(pipeline_id)
        if not config:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        return await self.execute_pipeline_config(config, params, on_progress)
    
    async def execute_pipeline_config(
        self,
        config: PipelineConfig,
        params: dict[str, Any] | None = None,
        on_progress: Callable[[str, str, float], None] | None = None,
    ) -> PipelineExecution:
        """
        Execute a pipeline from configuration.
        
        Args:
            config: Pipeline configuration
            params: Optional parameters to pass to tasks
            on_progress: Optional callback for progress updates
        
        Returns:
            Execution record
        """
        import uuid
        
        execution = PipelineExecution(
            execution_id=f"exec_{uuid.uuid4().hex[:8]}",
            pipeline_id=config.pipeline_id,
            status=TaskStatus.RUNNING,
        )
        
        self._executions.append(execution)
        
        logger.info(f"Starting pipeline execution: {config.name} ({execution.execution_id})")
        
        try:
            dag = self.builder.build_and_register(config, execution.execution_id)
            
            context = params or {}
            result = await self.dag_engine.execute_dag(
                dag.dag_id,
                context=context,
                on_progress=on_progress,
            )
            
            execution.status = TaskStatus.COMPLETED if result["status"] == "completed" else TaskStatus.FAILED
            execution.completed_at = datetime.now()
            execution.task_results = result.get("results", {})
            
            if result["status"] == "failed":
                execution.error = f"{result['failed_nodes']} tasks failed"
            
            logger.info(f"Pipeline execution completed: {execution.execution_id}, status={execution.status.value}")
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.completed_at = datetime.now()
            execution.error = str(e)
            
            logger.error(f"Pipeline execution failed: {execution.execution_id}, error={e}")
        
        return execution
    
    async def execute_pipeline_via_queue(
        self,
        pipeline_id: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Execute a pipeline by adding tasks to the queue.
        
        This method respects task dependencies by adding tasks in order.
        
        Args:
            pipeline_id: ID of the pipeline to execute
            params: Optional parameters to pass to tasks
        
        Returns:
            Execution ID
        """
        config = PipelineRegistry().get(pipeline_id)
        if not config:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        import uuid
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        execution = PipelineExecution(
            execution_id=execution_id,
            pipeline_id=config.pipeline_id,
            status=TaskStatus.QUEUED,
        )
        self._executions.append(execution)
        
        task_map: dict[str, str] = {}
        
        for task_config in config.tasks:
            task_def = TaskDefinition(
                task_id=f"{execution_id}_{task_config.task_id}",
                name=task_config.name,
                task_type=task_config.task_type,
                params={**(params or {}), **task_config.params},
                priority=task_config.priority,
                timeout_seconds=task_config.timeout_seconds,
                max_retries=task_config.max_retries,
                dependencies=[task_map[dep] for dep in task_config.dependencies if dep in task_map],
            )
            
            queue_task_id = self.task_queue.enqueue(task_def)
            task_map[task_config.task_id] = queue_task_id
        
        logger.info(f"Pipeline tasks enqueued: {pipeline_id}, execution_id={execution_id}")
        
        return execution_id
    
    def get_execution(self, execution_id: str) -> PipelineExecution | None:
        """Get execution by ID."""
        for execution in self._executions:
            if execution.execution_id == execution_id:
                return execution
        return None
    
    def list_executions(
        self,
        pipeline_id: str | None = None,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[PipelineExecution]:
        """List executions with optional filters."""
        executions = self._executions
        
        if pipeline_id:
            executions = [e for e in executions if e.pipeline_id == pipeline_id]
        if status:
            executions = [e for e in executions if e.status == status]
        
        return executions[-limit:]
    
    def get_pipeline_status(self, pipeline_id: str) -> dict[str, Any]:
        """Get status of a pipeline."""
        config = PipelineRegistry().get(pipeline_id)
        if not config:
            return {"error": "Pipeline not found"}
        
        executions = [e for e in self._executions if e.pipeline_id == pipeline_id]
        
        last_execution = executions[-1] if executions else None
        
        return {
            "pipeline_id": pipeline_id,
            "name": config.name,
            "description": config.description,
            "enabled": config.enabled,
            "schedule_type": config.schedule_type.value,
            "schedule_expr": config.schedule_expr,
            "total_executions": len(executions),
            "last_execution": last_execution.to_dict() if last_execution else None,
        }
    
    def get_stats(self) -> dict[str, Any]:
        """Get overall statistics."""
        total = len(self._executions)
        
        return {
            "total_executions": total,
            "running": sum(1 for e in self._executions if e.status == TaskStatus.RUNNING),
            "completed": sum(1 for e in self._executions if e.status == TaskStatus.COMPLETED),
            "failed": sum(1 for e in self._executions if e.status == TaskStatus.FAILED),
            "queued": sum(1 for e in self._executions if e.status == TaskStatus.QUEUED),
            "queue_stats": self.task_queue.get_stats(),
        }


def get_pipeline_manager() -> PipelineManager:
    """Get the singleton PipelineManager instance."""
    return PipelineManager.get_instance()
