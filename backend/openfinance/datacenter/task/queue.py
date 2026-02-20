"""
Task Queue for Data Center.

Provides priority-based task queue with:
- Batch processing
- Failure retry
- Checkpoint/resume support
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """Status of a task in the queue."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(int, Enum):
    """Task priority levels."""
    
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskDefinition(BaseModel):
    """Definition of a task."""
    
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., description="Task name")
    description: str = Field(default="", description="Task description")
    task_type: str = Field(..., description="Task type (collection/processing/sync)")
    
    data_source: str | None = Field(default=None, description="Data source")
    data_type: str | None = Field(default=None, description="Data type")
    
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status")
    
    params: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_count: int = Field(default=0, description="Current retry count")
    retry_delay_seconds: float = Field(default=5.0, description="Delay between retries")
    
    timeout_seconds: float = Field(default=300.0, description="Task timeout")
    
    include_in_global_start: bool = Field(default=True, description="Include in global start/stop")
    dependencies: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    
    progress: float = Field(default=0.0, description="Progress percentage (0-100)")
    progress_message: str = Field(default="", description="Progress message")
    
    checkpoint_data: dict[str, Any] | None = Field(default=None, description="Checkpoint for resume")
    
    result: dict[str, Any] | None = Field(default=None, description="Task result")
    error: str | None = Field(default=None, description="Error message if failed")


class TaskExecution(BaseModel):
    """Record of task execution."""
    
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str = Field(..., description="Task ID")
    status: TaskStatus = Field(..., description="Execution status")
    
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = Field(default=None)
    duration_ms: float | None = Field(default=None)
    
    records_processed: int = Field(default=0)
    records_failed: int = Field(default=0)
    
    result: dict[str, Any] | None = Field(default=None)
    error: str | None = Field(default=None)
    
    checkpoint: dict[str, Any] | None = Field(default=None)


@dataclass(order=True)
class PrioritizedTask:
    """Task wrapper for priority queue."""
    
    priority: int
    created_at: float = field(compare=True)
    task: TaskDefinition = field(compare=False)


class TaskQueue:
    """
    Priority-based task queue with retry and checkpoint support.
    
    Features:
    - Priority-based execution
    - Batch processing
    - Failure retry with exponential backoff
    - Checkpoint/resume for long-running tasks
    - Concurrent execution limit
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        checkpoint_dir: Path | None = None,
    ) -> None:
        self._queue: asyncio.PriorityQueue[PrioritizedTask] = asyncio.PriorityQueue()
        self._tasks: dict[str, TaskDefinition] = {}
        self._executions: list[TaskExecution] = []
        self._handlers: dict[str, Callable[..., Coroutine[Any, Any, dict[str, Any]]]] = {}
        
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_tasks: dict[str, asyncio.Task] = {}
        
        self._checkpoint_dir = checkpoint_dir or Path(__file__).parent.parent.parent.parent / "checkpoints"
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self._is_running = False
        self._processor_task: asyncio.Task | None = None
        
        logger.info_with_context(
            "TaskQueue initialized",
            context={"max_concurrent": max_concurrent, "checkpoint_dir": str(self._checkpoint_dir)}
        )
    
    def register_handler(
        self,
        task_type: str,
        handler: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    ) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
        logger.info_with_context(
            f"Handler registered for task type: {task_type}",
            context={"task_type": task_type}
        )
    
    def enqueue(self, task: TaskDefinition) -> str:
        """
        Add a task to the queue.
        
        Args:
            task: Task definition
        
        Returns:
            Task ID
        """
        self._tasks[task.task_id] = task
        task.status = TaskStatus.QUEUED
        
        prioritized = PrioritizedTask(
            priority=task.priority.value,
            created_at=task.created_at.timestamp(),
            task=task,
        )
        self._queue.put_nowait(prioritized)
        
        logger.info_with_context(
            f"Task enqueued: {task.name}",
            context={
                "task_id": task.task_id,
                "task_type": task.task_type,
                "priority": task.priority.name
            }
        )
        
        return task.task_id
    
    def enqueue_batch(self, tasks: list[TaskDefinition]) -> list[str]:
        """Enqueue multiple tasks."""
        return [self.enqueue(task) for task in tasks]
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in (TaskStatus.RUNNING, TaskStatus.QUEUED):
            task.status = TaskStatus.CANCELLED
            logger.info_with_context(
                f"Task cancelled: {task.name}",
                context={"task_id": task_id}
            )
            return True
        
        return False
    
    def pause(self, task_id: str) -> bool:
        """Pause a running task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        task.status = TaskStatus.PAUSED
        self._save_checkpoint(task)
        
        logger.info_with_context(
            f"Task paused: {task.name}",
            context={"task_id": task_id}
        )
        return True
    
    def resume(self, task_id: str) -> bool:
        """Resume a paused task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        checkpoint = self._load_checkpoint(task_id)
        if checkpoint:
            task.checkpoint_data = checkpoint
        
        task.status = TaskStatus.QUEUED
        prioritized = PrioritizedTask(
            priority=task.priority.value,
            created_at=task.created_at.timestamp(),
            task=task,
        )
        self._queue.put_nowait(prioritized)
        
        logger.info_with_context(
            f"Task resumed: {task.name}",
            context={"task_id": task_id, "has_checkpoint": checkpoint is not None}
        )
        return True
    
    def retry(self, task_id: str) -> bool:
        """Retry a failed task."""
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        
        if task.retry_count >= task.max_retries:
            logger.warning_with_context(
                f"Task max retries exceeded: {task.name}",
                context={"task_id": task_id, "retry_count": task.retry_count}
            )
            return False
        
        task.retry_count += 1
        task.status = TaskStatus.QUEUED
        task.error = None
        
        prioritized = PrioritizedTask(
            priority=task.priority.value,
            created_at=task.created_at.timestamp(),
            task=task,
        )
        self._queue.put_nowait(prioritized)
        
        logger.info_with_context(
            f"Task retry enqueued: {task.name}",
            context={"task_id": task_id, "retry_count": task.retry_count}
        )
        return True
    
    async def start(self) -> None:
        """Start the queue processor."""
        if self._is_running:
            return
        
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_queue())
        
        logger.info_with_context("TaskQueue processor started", context={})
    
    async def stop(self) -> None:
        """Stop the queue processor."""
        self._is_running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        for task_id, running_task in list(self._running_tasks.items()):
            running_task.cancel()
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.PAUSED
                self._save_checkpoint(task)
        
        logger.info_with_context("TaskQueue processor stopped", context={})
    
    async def _process_queue(self) -> None:
        """Process tasks from the queue."""
        while self._is_running:
            try:
                prioritized = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                task = prioritized.task
                
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                asyncio.create_task(self._execute_task(task))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error_with_context(
                    f"Queue processor error: {e}",
                    context={"error_type": type(e).__name__}
                )
    
    async def _execute_task(self, task: TaskDefinition) -> TaskExecution:
        """Execute a single task."""
        async with self._semaphore:
            execution = TaskExecution(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
            )
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            logger.info_with_context(
                f"Task execution started: {task.name}",
                context={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "retry_count": task.retry_count
                }
            )
            
            try:
                handler = self._handlers.get(task.task_type)
                if not handler:
                    raise ValueError(f"No handler for task type: {task.task_type}")
                
                params = {**task.params}
                if task.checkpoint_data:
                    params["_checkpoint"] = task.checkpoint_data
                
                result = await asyncio.wait_for(
                    handler(task, params),
                    timeout=task.timeout_seconds
                )
                
                execution.status = TaskStatus.COMPLETED
                execution.result = result
                task.status = TaskStatus.COMPLETED
                task.result = result
                
                logger.info_with_context(
                    f"Task completed: {task.name}",
                    context={
                        "task_id": task.task_id,
                        "duration_ms": round((datetime.now() - task.started_at).total_seconds() * 1000, 2)
                    }
                )
                
            except asyncio.TimeoutError:
                execution.status = TaskStatus.FAILED
                execution.error = "Task timeout"
                task.status = TaskStatus.FAILED
                task.error = "Task timeout"
                
                logger.error_with_context(
                    f"Task timeout: {task.name}",
                    context={"task_id": task.task_id, "timeout_seconds": task.timeout_seconds}
                )
                
            except Exception as e:
                execution.status = TaskStatus.FAILED
                execution.error = str(e)
                task.status = TaskStatus.FAILED
                task.error = str(e)
                
                logger.error_with_context(
                    f"Task failed: {task.name}",
                    context={
                        "task_id": task.task_id,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                
                if task.retry_count < task.max_retries:
                    await asyncio.sleep(task.retry_delay_seconds * (2 ** task.retry_count))
                    self.retry(task.task_id)
            
            execution.completed_at = datetime.now()
            execution.duration_ms = (execution.completed_at - execution.started_at).total_seconds() * 1000
            
            task.completed_at = execution.completed_at
            self._executions.append(execution)
            
            self._clear_checkpoint(task.task_id)
            
            return execution
    
    def _save_checkpoint(self, task: TaskDefinition) -> None:
        """Save task checkpoint."""
        checkpoint_file = self._checkpoint_dir / f"{task.task_id}.json"
        checkpoint_data = {
            "task_id": task.task_id,
            "checkpoint": task.checkpoint_data,
            "progress": task.progress,
            "progress_message": task.progress_message,
            "saved_at": datetime.now().isoformat(),
        }
        checkpoint_file.write_text(json.dumps(checkpoint_data, ensure_ascii=False, indent=2))
    
    def _load_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """Load task checkpoint."""
        checkpoint_file = self._checkpoint_dir / f"{task_id}.json"
        if checkpoint_file.exists():
            data = json.loads(checkpoint_file.read_text())
            return data.get("checkpoint")
        return None
    
    def _clear_checkpoint(self, task_id: str) -> None:
        """Clear task checkpoint."""
        checkpoint_file = self._checkpoint_dir / f"{task_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
    
    def get_task(self, task_id: str) -> TaskDefinition | None:
        """Get task by ID."""
        return self._tasks.get(task_id)
    
    def list_tasks(
        self,
        status: TaskStatus | None = None,
        task_type: str | None = None,
    ) -> list[TaskDefinition]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        return tasks
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def get_running_count(self) -> int:
        """Get count of running tasks."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
    
    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        tasks = list(self._tasks.values())
        
        return {
            "total_tasks": len(tasks),
            "queued": sum(1 for t in tasks if t.status == TaskStatus.QUEUED),
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "paused": sum(1 for t in tasks if t.status == TaskStatus.PAUSED),
            "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
            "max_concurrent": self._max_concurrent,
            "is_running": self._is_running,
        }
    
    def get_executions(
        self,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[TaskExecution]:
        """Get execution history."""
        executions = self._executions
        if task_id:
            executions = [e for e in executions if e.task_id == task_id]
        return executions[-limit:]
