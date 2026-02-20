"""
Collection Scheduler for Data Collection Center.

Provides scheduled task management using Celery Beat.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Types of scheduling."""

    INTERVAL = "interval"
    CRON = "cron"
    ONCE = "once"


class ScheduleConfig(BaseModel):
    """Configuration for a scheduled task."""

    task_id: str = Field(..., description="Unique task ID")
    task_name: str = Field(..., description="Task name")
    schedule_type: ScheduleType = Field(..., description="Schedule type")
    
    interval_seconds: int | None = Field(default=None, description="Interval in seconds")
    cron_expression: str | None = Field(default=None, description="Cron expression")
    scheduled_time: datetime | None = Field(default=None, description="Scheduled time for once")
    
    enabled: bool = Field(default=True, description="Whether task is enabled")
    max_retries: int = Field(default=3, description="Max retries on failure")
    timeout_seconds: float = Field(default=300.0, description="Task timeout")
    
    collector_source: str = Field(..., description="Collector source")
    collector_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Collector parameters",
    )

    class Config:
        use_enum_values = True


class TaskExecution(BaseModel):
    """Record of a task execution."""

    execution_id: str = Field(..., description="Execution ID")
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Start time")
    completed_at: datetime | None = Field(default=None, description="Completion time")
    result: dict[str, Any] | None = Field(default=None, description="Execution result")
    error: str | None = Field(default=None, description="Error message")


class CollectionScheduler:
    """Scheduler for data collection tasks.

    Provides:
    - Interval-based scheduling
    - Cron-based scheduling
    - One-time task scheduling
    - Task monitoring and retry
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduleConfig] = {}
        self._executions: list[TaskExecution] = []
        self._handlers: dict[str, Callable] = {}

    def register_task(self, config: ScheduleConfig) -> None:
        """Register a scheduled task."""
        self._tasks[config.task_id] = config
        logger.info(f"Registered task: {config.task_id} ({config.schedule_type})")

    def unregister_task(self, task_id: str) -> None:
        """Unregister a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"Unregistered task: {task_id}")

    def enable_task(self, task_id: str) -> None:
        """Enable a task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            logger.info(f"Enabled task: {task_id}")

    def disable_task(self, task_id: str) -> None:
        """Disable a task."""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            logger.info(f"Disabled task: {task_id}")

    def get_task(self, task_id: str) -> ScheduleConfig | None:
        """Get task configuration."""
        return self._tasks.get(task_id)

    def list_tasks(self, enabled_only: bool = False) -> list[ScheduleConfig]:
        """List all tasks."""
        tasks = list(self._tasks.values())
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return tasks

    def register_handler(
        self,
        task_id: str,
        handler: Callable,
    ) -> None:
        """Register a handler for a task."""
        self._handlers[task_id] = handler
        logger.info(f"Registered handler for task: {task_id}")

    async def execute_task(self, task_id: str) -> TaskExecution:
        """Execute a task manually."""
        config = self._tasks.get(task_id)
        if not config:
            raise ValueError(f"Task not found: {task_id}")

        execution_id = f"{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            status="running",
            started_at=datetime.now(),
        )

        try:
            handler = self._handlers.get(task_id)
            if handler:
                result = await handler(config.collector_params)
                execution.result = result
                execution.status = "completed"
            else:
                execution.status = "failed"
                execution.error = "No handler registered"

        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            logger.exception(f"Task execution failed: {task_id}")

        execution.completed_at = datetime.now()
        self._executions.append(execution)
        return execution

    def get_next_run_time(self, task_id: str) -> datetime | None:
        """Calculate next run time for a task."""
        config = self._tasks.get(task_id)
        if not config or not config.enabled:
            return None

        now = datetime.now()

        if config.schedule_type == ScheduleType.INTERVAL:
            if config.interval_seconds:
                return now + timedelta(seconds=config.interval_seconds)

        elif config.schedule_type == ScheduleType.ONCE:
            return config.scheduled_time

        return None

    def get_execution_history(
        self,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[TaskExecution]:
        """Get execution history."""
        executions = self._executions
        if task_id:
            executions = [e for e in executions if e.task_id == task_id]
        return executions[-limit:]

    def get_task_stats(self, task_id: str) -> dict[str, Any]:
        """Get statistics for a task."""
        executions = [e for e in self._executions if e.task_id == task_id]
        
        if not executions:
            return {
                "task_id": task_id,
                "total_executions": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
            }

        success_count = sum(1 for e in executions if e.status == "completed")
        failure_count = sum(1 for e in executions if e.status == "failed")

        return {
            "task_id": task_id,
            "total_executions": len(executions),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / len(executions),
            "last_execution": executions[-1].model_dump() if executions else None,
        }
