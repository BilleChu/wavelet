"""
Trigger Manager for Data Center.

Provides flexible task triggering mechanisms:
- Time-based triggers (interval, cron, one-time)
- Condition-based triggers (data conditions)
- Manual triggers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

from openfinance.core.logging_config import get_logger
from openfinance.datacenter.task.queue import TaskDefinition, TaskQueue

logger = get_logger(__name__)


class TriggerType(str, Enum):
    """Types of triggers."""
    
    INTERVAL = "interval"
    CRON = "cron"
    ONCE = "once"
    CONDITION = "condition"
    MANUAL = "manual"


class TriggerStatus(str, Enum):
    """Status of a trigger."""
    
    ENABLED = "enabled"
    DISABLED = "disabled"
    TRIGGERED = "triggered"
    ERROR = "error"


class IntervalTriggerConfig(BaseModel):
    """Configuration for interval trigger."""
    
    interval_seconds: int = Field(..., description="Interval in seconds")
    start_time: datetime | None = Field(default=None, description="Start time")
    end_time: datetime | None = Field(default=None, description="End time")


class CronTriggerConfig(BaseModel):
    """Configuration for cron trigger."""
    
    cron_expression: str = Field(..., description="Cron expression")
    timezone: str = Field(default="Asia/Shanghai", description="Timezone")


class OnceTriggerConfig(BaseModel):
    """Configuration for one-time trigger."""
    
    scheduled_time: datetime = Field(..., description="Scheduled time")


class ConditionTriggerConfig(BaseModel):
    """Configuration for condition-based trigger."""
    
    condition_type: str = Field(..., description="Condition type (symbol/industry/market)")
    condition_value: str | list[str] = Field(..., description="Condition value(s)")
    check_interval_seconds: int = Field(default=60, description="Check interval")
    
    data_source: str | None = Field(default=None, description="Data source to monitor")
    data_type: str | None = Field(default=None, description="Data type to monitor")


class TriggerDefinition(BaseModel):
    """Definition of a trigger."""
    
    trigger_id: str = Field(..., description="Unique trigger ID")
    name: str = Field(..., description="Trigger name")
    trigger_type: TriggerType = Field(..., description="Trigger type")
    status: TriggerStatus = Field(default=TriggerStatus.ENABLED)
    
    task_template: TaskDefinition = Field(..., description="Task template to create on trigger")
    
    interval_config: IntervalTriggerConfig | None = Field(default=None)
    cron_config: CronTriggerConfig | None = Field(default=None)
    once_config: OnceTriggerConfig | None = Field(default=None)
    condition_config: ConditionTriggerConfig | None = Field(default=None)
    
    last_triggered: datetime | None = Field(default=None)
    next_trigger: datetime | None = Field(default=None)
    trigger_count: int = Field(default=0)
    error_count: int = Field(default=0)
    last_error: str | None = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TriggerManager:
    """
    Manager for task triggers.
    
    Supports:
    - Interval-based triggers
    - Cron-based triggers
    - One-time triggers
    - Condition-based triggers
    - Manual triggers
    """
    
    def __init__(self, task_queue: TaskQueue) -> None:
        self._task_queue = task_queue
        self._triggers: dict[str, TriggerDefinition] = {}
        self._condition_checkers: dict[str, Callable[[], Coroutine[Any, Any, bool]]] = {}
        self._scheduler_task: asyncio.Task | None = None
        self._is_running = False
        
        logger.info_with_context("TriggerManager initialized", context={})
    
    def register_trigger(self, trigger: TriggerDefinition) -> str:
        """Register a trigger."""
        self._triggers[trigger.trigger_id] = trigger
        self._calculate_next_trigger(trigger)
        
        logger.info_with_context(
            f"Trigger registered: {trigger.name}",
            context={
                "trigger_id": trigger.trigger_id,
                "trigger_type": trigger.trigger_type.value,
                "next_trigger": trigger.next_trigger.isoformat() if trigger.next_trigger else None
            }
        )
        
        return trigger.trigger_id
    
    def unregister_trigger(self, trigger_id: str) -> bool:
        """Unregister a trigger."""
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            logger.info_with_context(
                f"Trigger unregistered: {trigger_id}",
                context={"trigger_id": trigger_id}
            )
            return True
        return False
    
    def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a trigger."""
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.status = TriggerStatus.ENABLED
            self._calculate_next_trigger(trigger)
            logger.info_with_context(
                f"Trigger enabled: {trigger.name}",
                context={"trigger_id": trigger_id}
            )
            return True
        return False
    
    def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger."""
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.status = TriggerStatus.DISABLED
            trigger.next_trigger = None
            logger.info_with_context(
                f"Trigger disabled: {trigger.name}",
                context={"trigger_id": trigger_id}
            )
            return True
        return False
    
    def register_condition_checker(
        self,
        condition_type: str,
        checker: Callable[[], Coroutine[Any, Any, bool]],
    ) -> None:
        """Register a condition checker function."""
        self._condition_checkers[condition_type] = checker
        logger.info_with_context(
            f"Condition checker registered: {condition_type}",
            context={"condition_type": condition_type}
        )
    
    async def manual_trigger(self, trigger_id: str) -> str | None:
        """Manually trigger a task."""
        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return None
        
        task = trigger.task_template.model_copy()
        task.task_id = f"{task.task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        task.status = trigger.task_template.status
        
        task_id = self._task_queue.enqueue(task)
        
        trigger.last_triggered = datetime.now()
        trigger.trigger_count += 1
        
        logger.info_with_context(
            f"Manual trigger executed: {trigger.name}",
            context={
                "trigger_id": trigger_id,
                "task_id": task_id
            }
        )
        
        return task_id
    
    async def start(self) -> None:
        """Start the trigger scheduler."""
        if self._is_running:
            return
        
        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        
        logger.info_with_context("TriggerManager scheduler started", context={})
    
    async def stop(self) -> None:
        """Stop the trigger scheduler."""
        self._is_running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info_with_context("TriggerManager scheduler stopped", context={})
    
    async def _run_scheduler(self) -> None:
        """Run the trigger scheduler loop."""
        while self._is_running:
            try:
                now = datetime.now()
                
                for trigger in list(self._triggers.values()):
                    if trigger.status != TriggerStatus.ENABLED:
                        continue
                    
                    if trigger.trigger_type == TriggerType.CONDITION:
                        await self._check_condition_trigger(trigger)
                    elif trigger.next_trigger and trigger.next_trigger <= now:
                        await self._execute_trigger(trigger)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error_with_context(
                    f"Scheduler error: {e}",
                    context={"error_type": type(e).__name__}
                )
                await asyncio.sleep(5)
    
    async def _execute_trigger(self, trigger: TriggerDefinition) -> None:
        """Execute a trigger."""
        try:
            task = trigger.task_template.model_copy()
            task.task_id = f"{task.task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            task_id = self._task_queue.enqueue(task)
            
            trigger.last_triggered = datetime.now()
            trigger.trigger_count += 1
            
            if trigger.trigger_type == TriggerType.ONCE:
                trigger.status = TriggerStatus.TRIGGERED
            else:
                self._calculate_next_trigger(trigger)
            
            logger.info_with_context(
                f"Trigger executed: {trigger.name}",
                context={
                    "trigger_id": trigger.trigger_id,
                    "task_id": task_id,
                    "trigger_type": trigger.trigger_type.value
                }
            )
            
        except Exception as e:
            trigger.error_count += 1
            trigger.last_error = str(e)
            
            logger.error_with_context(
                f"Trigger execution failed: {trigger.name}",
                context={
                    "trigger_id": trigger.trigger_id,
                    "error": str(e)
                }
            )
    
    async def _check_condition_trigger(self, trigger: TriggerDefinition) -> None:
        """Check and execute condition-based triggers."""
        if not trigger.condition_config:
            return
        
        config = trigger.condition_config
        checker = self._condition_checkers.get(config.condition_type)
        
        if not checker:
            return
        
        try:
            should_trigger = await checker()
            
            if should_trigger:
                await self._execute_trigger(trigger)
                
        except Exception as e:
            logger.error_with_context(
                f"Condition check failed: {trigger.name}",
                context={
                    "trigger_id": trigger.trigger_id,
                    "error": str(e)
                }
            )
    
    def _calculate_next_trigger(self, trigger: TriggerDefinition) -> None:
        """Calculate the next trigger time."""
        now = datetime.now()
        
        if trigger.trigger_type == TriggerType.INTERVAL and trigger.interval_config:
            config = trigger.interval_config
            trigger.next_trigger = now + timedelta(seconds=config.interval_seconds)
            
        elif trigger.trigger_type == TriggerType.ONCE and trigger.once_config:
            trigger.next_trigger = trigger.once_config.scheduled_time
            
        elif trigger.trigger_type == TriggerType.CRON and trigger.cron_config:
            trigger.next_trigger = self._parse_cron_next(trigger.cron_config.cron_expression, now)
        
        elif trigger.trigger_type == TriggerType.CONDITION and trigger.condition_config:
            trigger.next_trigger = now + timedelta(seconds=trigger.condition_config.check_interval_seconds)
    
    def _parse_cron_next(self, expression: str, now: datetime) -> datetime:
        """Parse cron expression and get next run time."""
        parts = expression.split()
        if len(parts) != 5:
            return now + timedelta(hours=1)
        
        minute, hour, day, month, weekday = parts
        
        next_time = now.replace(second=0, microsecond=0)
        next_time = next_time + timedelta(minutes=1)
        
        return next_time
    
    def get_trigger(self, trigger_id: str) -> TriggerDefinition | None:
        """Get trigger by ID."""
        return self._triggers.get(trigger_id)
    
    def list_triggers(
        self,
        status: TriggerStatus | None = None,
        trigger_type: TriggerType | None = None,
    ) -> list[TriggerDefinition]:
        """List triggers with optional filters."""
        triggers = list(self._triggers.values())
        
        if status:
            triggers = [t for t in triggers if t.status == status]
        if trigger_type:
            triggers = [t for t in triggers if t.trigger_type == trigger_type]
        
        return triggers
    
    def get_stats(self) -> dict[str, Any]:
        """Get trigger statistics."""
        triggers = list(self._triggers.values())
        
        return {
            "total_triggers": len(triggers),
            "enabled": sum(1 for t in triggers if t.status == TriggerStatus.ENABLED),
            "disabled": sum(1 for t in triggers if t.status == TriggerStatus.DISABLED),
            "triggered": sum(1 for t in triggers if t.status == TriggerStatus.TRIGGERED),
            "error": sum(1 for t in triggers if t.status == TriggerStatus.ERROR),
            "total_trigger_count": sum(t.trigger_count for t in triggers),
            "is_running": self._is_running,
        }
