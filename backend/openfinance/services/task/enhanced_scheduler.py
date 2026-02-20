"""
Enhanced Scheduler for Data Center.

Provides advanced scheduling with:
- Daily scheduled tasks (Cron expressions)
- Priority-based execution
- Exponential backoff retry
- Task dependency management
- Real-time monitoring
"""

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Awaitable
import heapq

from pydantic import BaseModel, Field

from openfinance.core.logging_config import get_logger

logger = get_logger(__name__)


class ScheduleType(str, Enum):
    """Types of scheduling."""
    
    INTERVAL = "interval"
    CRON = "cron"
    ONCE = "once"
    DAILY = "daily"


class TaskPriority(int, Enum):
    """Task priority levels."""
    
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class RetryStrategy(str, Enum):
    """Retry strategies."""
    
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass(order=True)
class PrioritizedTask:
    """Task wrapper for priority queue."""
    
    priority: int
    scheduled_time: datetime
    task_id: str = field(compare=False)


class ScheduleConfig(BaseModel):
    """Enhanced schedule configuration."""
    
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_name: str = Field(..., description="Task name")
    task_type: str = Field(default="collection", description="Task type")
    
    schedule_type: ScheduleType = Field(default=ScheduleType.DAILY, description="Schedule type")
    
    interval_seconds: int | None = Field(default=None, description="Interval in seconds")
    cron_expression: str | None = Field(default="0 9 * * 1-5", description="Cron expression")
    scheduled_time: datetime | None = Field(default=None, description="Scheduled time for once")
    daily_time: str | None = Field(default="09:00", description="Daily execution time (HH:MM)")
    
    enabled: bool = Field(default=True, description="Whether task is enabled")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    
    max_retries: int = Field(default=3, description="Max retries on failure")
    retry_strategy: RetryStrategy = Field(default=RetryStrategy.EXPONENTIAL, description="Retry strategy")
    retry_delay_seconds: float = Field(default=5.0, description="Base retry delay")
    retry_backoff_factor: float = Field(default=2.0, description="Backoff factor for exponential retry")
    
    timeout_seconds: float = Field(default=300.0, description="Task timeout")
    
    dependencies: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    
    params: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    
    last_run: datetime | None = Field(default=None, description="Last run time")
    last_status: str | None = Field(default=None, description="Last run status")
    next_run: datetime | None = Field(default=None, description="Next scheduled run")
    
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    
    class Config:
        use_enum_values = True


class TaskExecution(BaseModel):
    """Record of a task execution."""
    
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = Field(..., description="Task ID")
    status: str = Field(default="pending", description="Execution status")
    
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = Field(default=None)
    duration_ms: float | None = Field(default=None)
    
    result: dict[str, Any] | None = Field(default=None)
    error: str | None = Field(default=None)
    
    retry_count: int = Field(default=0)
    is_retry: bool = Field(default=False)


class EnhancedScheduler:
    """
    Enhanced scheduler with priority queue and retry support.
    
    Features:
    - Cron-based daily scheduling
    - Priority-based execution
    - Exponential backoff retry
    - Task dependency management
    - Real-time monitoring
    """
    
    def __init__(self, max_concurrent: int = 5) -> None:
        self._tasks: dict[str, ScheduleConfig] = {}
        self._executions: list[TaskExecution] = []
        self._handlers: dict[str, Callable[..., Awaitable]] = {}
        self._priority_queue: list[PrioritizedTask] = []
        self._running_tasks: set[str] = set()
        self._max_concurrent = max_concurrent
        self._is_running = False
        self._scheduler_task: asyncio.Task | None = None
        
        self._stats = {
            "total_scheduled": 0,
            "total_executed": 0,
            "total_succeeded": 0,
            "total_failed": 0,
            "total_retries": 0,
        }
    
    def register_task(self, config: ScheduleConfig) -> None:
        """Register a scheduled task."""
        config.next_run = self._calculate_next_run(config)
        self._tasks[config.task_id] = config
        self._stats["total_scheduled"] += 1
        
        logger.info_with_context(
            "Task registered",
            context={
                "task_id": config.task_id,
                "task_name": config.task_name,
                "schedule_type": config.schedule_type,
                "next_run": config.next_run.isoformat() if config.next_run else None,
            }
        )
    
    def unregister_task(self, task_id: str) -> None:
        """Unregister a scheduled task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info_with_context("Task unregistered", context={"task_id": task_id})
    
    def update_priority(self, task_id: str, priority: TaskPriority) -> None:
        """Dynamically update task priority."""
        if task_id in self._tasks:
            self._tasks[task_id].priority = priority
            logger.info_with_context(
                "Task priority updated",
                context={"task_id": task_id, "priority": priority.name}
            )
    
    def register_handler(
        self,
        task_type: str,
        handler: Callable[..., Awaitable],
    ) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
    
    def _calculate_next_run(self, config: ScheduleConfig) -> datetime | None:
        """Calculate next run time based on schedule type."""
        now = datetime.now()
        
        if config.schedule_type == ScheduleType.INTERVAL:
            if config.interval_seconds:
                return now + timedelta(seconds=config.interval_seconds)
        
        elif config.schedule_type == ScheduleType.DAILY:
            if config.daily_time:
                try:
                    hour, minute = map(int, config.daily_time.split(":"))
                    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                    return next_run
                except (ValueError, AttributeError):
                    pass
        
        elif config.schedule_type == ScheduleType.CRON:
            return self._parse_cron(config.cron_expression, now)
        
        elif config.schedule_type == ScheduleType.ONCE:
            return config.scheduled_time
        
        return None
    
    def _parse_cron(self, expression: str | None, now: datetime) -> datetime | None:
        """Parse cron expression and calculate next run time."""
        if not expression:
            return None
        
        try:
            parts = expression.split()
            if len(parts) != 5:
                return None
            
            minute, hour, day_of_month, month, day_of_week = parts
            
            next_run = now.replace(second=0, microsecond=0)
            
            if minute != "*":
                next_run = next_run.replace(minute=int(minute))
            if hour != "*":
                next_run = next_run.replace(hour=int(hour))
            
            if next_run <= now:
                next_run += timedelta(days=1)
            
            return next_run
            
        except (ValueError, IndexError):
            return None
    
    def _get_retry_delay(self, config: ScheduleConfig, retry_count: int) -> float:
        """Calculate retry delay based on strategy."""
        if config.retry_strategy == RetryStrategy.NONE:
            return 0
        elif config.retry_strategy == RetryStrategy.FIXED:
            return config.retry_delay_seconds
        elif config.retry_strategy == RetryStrategy.EXPONENTIAL:
            return config.retry_delay_seconds * (config.retry_backoff_factor ** retry_count)
        elif config.retry_strategy == RetryStrategy.LINEAR:
            return config.retry_delay_seconds * (retry_count + 1)
        return config.retry_delay_seconds
    
    async def _execute_with_retry(
        self,
        config: ScheduleConfig,
        params: dict[str, Any],
    ) -> TaskExecution:
        """Execute task with retry logic."""
        execution = TaskExecution(
            task_id=config.task_id,
            status="running",
            started_at=datetime.now(),
        )
        
        handler = self._handlers.get(config.task_type)
        if not handler:
            execution.status = "failed"
            execution.error = f"No handler for task type: {config.task_type}"
            execution.completed_at = datetime.now()
            return execution
        
        last_error: Exception | None = None
        
        for attempt in range(config.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._get_retry_delay(config, attempt - 1)
                    await asyncio.sleep(delay)
                    execution.retry_count = attempt
                    execution.is_retry = True
                    self._stats["total_retries"] += 1
                
                result = await asyncio.wait_for(
                    handler(params),
                    timeout=config.timeout_seconds,
                )
                
                execution.result = result
                execution.status = "completed"
                execution.completed_at = datetime.now()
                execution.duration_ms = (execution.completed_at - execution.started_at).total_seconds() * 1000
                
                config.consecutive_failures = 0
                config.last_status = "completed"
                
                self._stats["total_succeeded"] += 1
                
                return execution
                
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Task timed out after {config.timeout_seconds}s")
            except Exception as e:
                last_error = e
            
            logger.warning_with_context(
                "Task execution attempt failed",
                context={
                    "task_id": config.task_id,
                    "attempt": attempt + 1,
                    "max_retries": config.max_retries,
                    "error": str(last_error),
                }
            )
        
        execution.status = "failed"
        execution.error = str(last_error)
        execution.completed_at = datetime.now()
        execution.duration_ms = (execution.completed_at - execution.started_at).total_seconds() * 1000
        
        config.consecutive_failures += 1
        config.last_status = "failed"
        
        self._stats["total_failed"] += 1
        
        return execution
    
    async def execute_task(self, task_id: str, params: dict[str, Any] | None = None) -> TaskExecution:
        """Execute a task manually."""
        config = self._tasks.get(task_id)
        if not config:
            raise ValueError(f"Task not found: {task_id}")
        
        self._stats["total_executed"] += 1
        
        execution = await self._execute_with_retry(config, params or config.params)
        
        config.last_run = datetime.now()
        config.next_run = self._calculate_next_run(config)
        
        self._executions.append(execution)
        
        return execution
    
    def _check_dependencies(self, config: ScheduleConfig) -> bool:
        """Check if all dependencies are satisfied."""
        for dep_id in config.dependencies:
            dep = self._tasks.get(dep_id)
            if not dep or dep.last_status != "completed":
                return False
        return True
    
    async def _schedule_loop(self) -> None:
        """Main scheduling loop."""
        while self._is_running:
            now = datetime.now()
            
            for task_id, config in self._tasks.items():
                if not config.enabled:
                    continue
                
                if task_id in self._running_tasks:
                    continue
                
                if len(self._running_tasks) >= self._max_concurrent:
                    break
                
                if config.next_run and config.next_run <= now:
                    if not self._check_dependencies(config):
                        continue
                    
                    heapq.heappush(
                        self._priority_queue,
                        PrioritizedTask(
                            priority=config.priority if isinstance(config.priority, int) else config.priority.value,
                            scheduled_time=now,
                            task_id=task_id,
                        )
                    )
            
            while self._priority_queue and len(self._running_tasks) < self._max_concurrent:
                prioritized = heapq.heappop(self._priority_queue)
                task_id = prioritized.task_id
                
                if task_id in self._running_tasks:
                    continue
                
                self._running_tasks.add(task_id)
                
                asyncio.create_task(self._run_task(task_id))
            
            await asyncio.sleep(1)
    
    async def _run_task(self, task_id: str) -> None:
        """Run a scheduled task."""
        try:
            await self.execute_task(task_id)
        finally:
            self._running_tasks.discard(task_id)
    
    async def start(self) -> None:
        """Start the scheduler."""
        if self._is_running:
            return
        
        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._schedule_loop())
        
        logger.info_with_context("Scheduler started", context={})
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._is_running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info_with_context("Scheduler stopped", context={})
    
    def get_task(self, task_id: str) -> ScheduleConfig | None:
        """Get task configuration."""
        return self._tasks.get(task_id)
    
    def list_tasks(self, enabled_only: bool = False) -> list[ScheduleConfig]:
        """List all tasks."""
        tasks = list(self._tasks.values())
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return sorted(tasks, key=lambda t: t.priority if isinstance(t.priority, int) else t.priority.value)
    
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
    
    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        return {
            **self._stats,
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "running_tasks": len(self._running_tasks),
            "queued_tasks": len(self._priority_queue),
        }
    
    def get_task_stats(self, task_id: str) -> dict[str, Any]:
        """Get statistics for a specific task."""
        config = self._tasks.get(task_id)
        if not config:
            return {}
        
        executions = [e for e in self._executions if e.task_id == task_id]
        
        success_count = sum(1 for e in executions if e.status == "completed")
        failure_count = sum(1 for e in executions if e.status == "failed")
        
        avg_duration = 0.0
        if executions:
            durations = [e.duration_ms for e in executions if e.duration_ms]
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "task_id": task_id,
            "task_name": config.task_name,
            "enabled": config.enabled,
            "priority": config.priority.name,
            "last_run": config.last_run.isoformat() if config.last_run else None,
            "last_status": config.last_status,
            "next_run": config.next_run.isoformat() if config.next_run else None,
            "total_executions": len(executions),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / len(executions) if executions else 0,
            "avg_duration_ms": avg_duration,
            "consecutive_failures": config.consecutive_failures,
        }


def create_default_scheduled_tasks() -> list[ScheduleConfig]:
    """Create default scheduled tasks for daily data collection."""
    return [
        ScheduleConfig(
            task_id="daily_company_preload",
            task_name="Daily Company Preload",
            task_type="company_preload",
            schedule_type=ScheduleType.DAILY,
            daily_time="08:00",
            priority=TaskPriority.HIGH,
            enabled=True,
        ),
        ScheduleConfig(
            task_id="daily_kline_collection",
            task_name="Daily K-line Collection",
            task_type="kline_collection",
            schedule_type=ScheduleType.DAILY,
            daily_time="09:30",
            priority=TaskPriority.NORMAL,
            enabled=True,
            dependencies=["daily_company_preload"],
        ),
        ScheduleConfig(
            task_id="daily_financial_collection",
            task_name="Daily Financial Collection",
            task_type="financial_collection",
            schedule_type=ScheduleType.DAILY,
            daily_time="09:35",
            priority=TaskPriority.NORMAL,
            enabled=True,
            dependencies=["daily_company_preload"],
        ),
        ScheduleConfig(
            task_id="daily_money_flow_collection",
            task_name="Daily Money Flow Collection",
            task_type="money_flow_collection",
            schedule_type=ScheduleType.DAILY,
            daily_time="09:40",
            priority=TaskPriority.NORMAL,
            enabled=True,
            dependencies=["daily_company_preload"],
        ),
        ScheduleConfig(
            task_id="daily_graph_sync",
            task_name="Daily Graph Sync",
            task_type="graph_sync",
            schedule_type=ScheduleType.DAILY,
            daily_time="10:00",
            priority=TaskPriority.LOW,
            enabled=True,
            dependencies=["daily_kline_collection", "daily_financial_collection", "daily_money_flow_collection"],
        ),
    ]
