"""
Task Manager for Data Center.

Provides unified task management with:
- Global start/stop
- Priority management
- Dependency handling
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.datacenter.task.queue import TaskQueue, TaskDefinition, TaskStatus, TaskPriority
from openfinance.datacenter.task.trigger import TriggerManager, TriggerDefinition, TriggerType

logger = get_logger(__name__)


class TaskManager:
    """
    Unified task manager for Data Center.
    
    Features:
    - Global start/stop for all tasks
    - Task priority management
    - Dependency resolution
    - Task monitoring
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
    ) -> None:
        self._task_queue = TaskQueue(max_concurrent=max_concurrent)
        self._trigger_manager = TriggerManager(self._task_queue)
        self._is_running = False
        
        logger.info_with_context(
            "TaskManager initialized",
            context={"max_concurrent": max_concurrent}
        )
    
    async def start(self) -> None:
        """Start the task manager."""
        if self._is_running:
            return
        
        self._is_running = True
        await self._task_queue.start()
        await self._trigger_manager.start()
        
        logger.info_with_context("TaskManager started", context={})
    
    async def stop(self) -> None:
        """Stop the task manager."""
        self._is_running = False
        await self._task_queue.stop()
        await self._trigger_manager.stop()
        
        logger.info_with_context("TaskManager stopped", context={})
    
    async def start_all(self) -> dict[str, Any]:
        """
        Start all tasks that have include_in_global_start=True.
        
        Returns:
            Summary of started tasks
        """
        started = []
        skipped = []
        failed = []
        
        tasks = self._task_queue.list_tasks()
        global_tasks = [t for t in tasks if t.include_in_global_start]
        
        for task in global_tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.PAUSED, TaskStatus.FAILED):
                if task.status == TaskStatus.PAUSED:
                    if self._task_queue.resume(task.task_id):
                        started.append(task.task_id)
                    else:
                        failed.append(task.task_id)
                else:
                    task.status = TaskStatus.QUEUED
                    started.append(task.task_id)
            else:
                skipped.append(task.task_id)
        
        logger.info_with_context(
            "Global start executed",
            context={
                "started_count": len(started),
                "skipped_count": len(skipped),
                "failed_count": len(failed)
            }
        )
        
        return {
            "success": True,
            "started": started,
            "skipped": skipped,
            "failed": failed,
            "message": f"Started {len(started)} tasks, skipped {len(skipped)}, failed {len(failed)}",
        }
    
    async def pause_all(self) -> dict[str, Any]:
        """
        Pause all running tasks.
        
        Returns:
            Summary of paused tasks
        """
        paused = []
        skipped = []
        
        tasks = self._task_queue.list_tasks(status=TaskStatus.RUNNING)
        
        for task in tasks:
            if self._task_queue.pause(task.task_id):
                paused.append(task.task_id)
            else:
                skipped.append(task.task_id)
        
        logger.info_with_context(
            "Global pause executed",
            context={
                "paused_count": len(paused),
                "skipped_count": len(skipped)
            }
        )
        
        return {
            "success": True,
            "paused": paused,
            "skipped": skipped,
            "message": f"Paused {len(paused)} tasks, skipped {len(skipped)}",
        }
    
    def create_task(
        self,
        name: str,
        task_type: str,
        params: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        data_source: str | None = None,
        data_type: str | None = None,
        include_in_global_start: bool = True,
        dependencies: list[str] | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 300.0,
    ) -> TaskDefinition:
        """
        Create a new task definition.
        
        Args:
            name: Task name
            task_type: Task type
            params: Task parameters
            priority: Task priority
            data_source: Data source
            data_type: Data type
            include_in_global_start: Include in global start/stop
            dependencies: Task IDs this depends on
            max_retries: Maximum retry attempts
            timeout_seconds: Task timeout
        
        Returns:
            TaskDefinition instance
        """
        task = TaskDefinition(
            name=name,
            task_type=task_type,
            params=params,
            priority=priority,
            data_source=data_source,
            data_type=data_type,
            include_in_global_start=include_in_global_start,
            dependencies=dependencies or [],
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        
        logger.info_with_context(
            f"Task created: {name}",
            context={
                "task_id": task.task_id,
                "task_type": task_type,
                "priority": priority.name
            }
        )
        
        return task
    
    def create_trigger(
        self,
        name: str,
        trigger_type: TriggerType,
        task_template: TaskDefinition,
        interval_seconds: int | None = None,
        cron_expression: str | None = None,
        scheduled_time: datetime | None = None,
        condition_type: str | None = None,
        condition_value: str | list[str] | None = None,
    ) -> TriggerDefinition:
        """
        Create a new trigger.
        
        Args:
            name: Trigger name
            trigger_type: Trigger type
            task_template: Task template to create on trigger
            interval_seconds: Interval for interval triggers
            cron_expression: Cron expression for cron triggers
            scheduled_time: Scheduled time for one-time triggers
            condition_type: Condition type for condition triggers
            condition_value: Condition value for condition triggers
        
        Returns:
            TriggerDefinition instance
        """
        from openfinance.datacenter.task.trigger import (
            IntervalTriggerConfig,
            CronTriggerConfig,
            OnceTriggerConfig,
            ConditionTriggerConfig,
        )
        
        trigger = TriggerDefinition(
            trigger_id=f"trigger_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            name=name,
            trigger_type=trigger_type,
            task_template=task_template,
        )
        
        if trigger_type == TriggerType.INTERVAL and interval_seconds:
            trigger.interval_config = IntervalTriggerConfig(interval_seconds=interval_seconds)
        elif trigger_type == TriggerType.CRON and cron_expression:
            trigger.cron_config = CronTriggerConfig(cron_expression=cron_expression)
        elif trigger_type == TriggerType.ONCE and scheduled_time:
            trigger.once_config = OnceTriggerConfig(scheduled_time=scheduled_time)
        elif trigger_type == TriggerType.CONDITION and condition_type and condition_value:
            trigger.condition_config = ConditionTriggerConfig(
                condition_type=condition_type,
                condition_value=condition_value,
            )
        
        self._trigger_manager.register_trigger(trigger)
        
        logger.info_with_context(
            f"Trigger created: {name}",
            context={
                "trigger_id": trigger.trigger_id,
                "trigger_type": trigger_type.value
            }
        )
        
        return trigger
    
    def enqueue_task(self, task: TaskDefinition) -> str:
        """Enqueue a task."""
        return self._task_queue.enqueue(task)
    
    def get_task(self, task_id: str) -> TaskDefinition | None:
        """Get task by ID."""
        return self._task_queue.get_task(task_id)
    
    def get_trigger(self, trigger_id: str) -> TriggerDefinition | None:
        """Get trigger by ID."""
        return self._trigger_manager.get_trigger(trigger_id)
    
    def list_tasks(
        self,
        status: TaskStatus | None = None,
        task_type: str | None = None,
    ) -> list[TaskDefinition]:
        """List tasks with optional filters."""
        return self._task_queue.list_tasks(status=status, task_type=task_type)
    
    def list_triggers(
        self,
        status: Any = None,
        trigger_type: TriggerType | None = None,
    ) -> list[TriggerDefinition]:
        """List triggers with optional filters."""
        return self._trigger_manager.list_triggers(status=status, trigger_type=trigger_type)
    
    def register_task_handler(
        self,
        task_type: str,
        handler: Any,
    ) -> None:
        """Register a handler for a task type."""
        self._task_queue.register_handler(task_type, handler)
    
    def register_condition_checker(
        self,
        condition_type: str,
        checker: Any,
    ) -> None:
        """Register a condition checker."""
        self._trigger_manager.register_condition_checker(condition_type, checker)
    
    async def manual_trigger(self, trigger_id: str) -> str | None:
        """Manually trigger a task."""
        return await self._trigger_manager.manual_trigger(trigger_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        return self._task_queue.cancel(task_id)
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a task."""
        return self._task_queue.pause(task_id)
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        return self._task_queue.resume(task_id)
    
    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        return self._task_queue.retry(task_id)
    
    def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a trigger."""
        return self._trigger_manager.enable_trigger(trigger_id)
    
    def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger."""
        return self._trigger_manager.disable_trigger(trigger_id)
    
    def get_overview(self) -> dict[str, Any]:
        """Get overview of task manager state."""
        queue_stats = self._task_queue.get_stats()
        trigger_stats = self._trigger_manager.get_stats()
        
        tasks = self._task_queue.list_tasks()
        
        success_rate = 0.0
        if queue_stats["completed"] + queue_stats["failed"] > 0:
            success_rate = queue_stats["completed"] / (queue_stats["completed"] + queue_stats["failed"])
        
        return {
            "is_running": self._is_running,
            "queue": queue_stats,
            "triggers": trigger_stats,
            "success_rate": round(success_rate * 100, 2),
            "recent_tasks": [
                {
                    "task_id": t.task_id,
                    "name": t.name,
                    "status": t.status.value,
                    "progress": t.progress,
                }
                for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)[:10]
            ],
        }
    
    def get_task_executions(
        self,
        task_id: str | None = None,
        limit: int = 100,
    ) -> list[Any]:
        """Get task execution history."""
        return self._task_queue.get_executions(task_id=task_id, limit=limit)
    
    @property
    def task_queue(self) -> TaskQueue:
        """Get the task queue."""
        return self._task_queue
    
    @property
    def trigger_manager(self) -> TriggerManager:
        """Get the trigger manager."""
        return self._trigger_manager
