"""
Economic Calendar Task Executors.

Provides task executors for economic calendar data collection.
Follows the project's TaskExecutor pattern for high cohesion.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Any

from .registry import (
    TaskExecutor,
    TaskCategory,
    TaskPriority,
    TaskParameter,
    TaskOutput,
    TaskProgress,
    task_executor,
)
from ..collector.implementations.calendar_collector import (
    EconomicEvent,
    EconomicCalendarCollector,
)

logger = logging.getLogger(__name__)


@task_executor(
    task_type="economic_calendar",
    name="经济日历采集",
    description="从Investing.com采集全球经济日历事件数据",
    category=TaskCategory.MACRO,
    source="investing.com",
    priority=TaskPriority.HIGH,
    timeout=120.0,
    parameters=[
        TaskParameter(
            name="past_days",
            type="integer",
            default=7,
            description="向前查找天数",
        ),
        TaskParameter(
            name="future_days",
            type="integer",
            default=30,
            description="向后查找天数",
        ),
        TaskParameter(
            name="countries",
            type="array",
            default=None,
            description="国家过滤列表",
        ),
        TaskParameter(
            name="importances",
            type="array",
            default=None,
            description="重要性过滤列表",
            choices=[["high"], ["medium"], ["low"], ["high", "medium"]],
        ),
        TaskParameter(
            name="strategy",
            type="string",
            default="auto",
            description="抓取策略",
            choices=["auto", "investpy", "cloudscraper", "requests", "selenium"],
        ),
    ],
    output=TaskOutput(
        data_type="economic_calendar_event",
        table_name="economic_calendar_events",
        description="经济日历事件数据",
        fields=[
            "event_id", "event_date", "event_time", "country", "currency",
            "importance", "event_name", "actual", "forecast", "previous", "source"
        ],
    ),
    tags=["macro", "calendar", "economic", "global"],
)
class EconomicCalendarExecutor(TaskExecutor[EconomicEvent]):
    """Executor for economic calendar collection tasks."""
    
    def __init__(self):
        self._collector = None
    
    async def _get_collector(self) -> EconomicCalendarCollector:
        """Get or create collector instance."""
        if self._collector is None:
            self._collector = EconomicCalendarCollector()
            await self._collector.start()
        return self._collector
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[EconomicEvent]:
        """Collect economic calendar events."""
        past_days = params.get("past_days", 7)
        future_days = params.get("future_days", 30)
        countries = params.get("countries")
        importances = params.get("importances")
        strategy = params.get("strategy", "auto")
        
        progress.details["past_days"] = past_days
        progress.details["future_days"] = future_days
        progress.details["strategy"] = strategy
        
        from_date = date.today() - timedelta(days=past_days)
        to_date = date.today() + timedelta(days=future_days)
        
        collector = await self._get_collector()
        result = await collector.collect(
            from_date=from_date,
            to_date=to_date,
            countries=countries,
            importances=importances,
            strategy=strategy,
        )
        
        progress.details["source"] = "investing.com"
        progress.details["collection_status"] = result.status.value
        
        if result.errors:
            progress.details["errors"] = result.errors
        
        return result.data or []
    
    async def validate(self, data: list[EconomicEvent]) -> list[EconomicEvent]:
        """Validate collected events."""
        validated = []
        seen_ids = set()
        
        for event in data:
            if not event.event_id or not event.event_date or not event.event_name:
                continue
            
            if event.event_id in seen_ids:
                continue
            
            seen_ids.add(event.event_id)
            validated.append(event)
        
        return validated
    
    async def save(self, data: list[EconomicEvent], progress: TaskProgress) -> int:
        """Save events to database using persistence layer."""
        from ..persistence import persistence
        
        records = []
        for event in data:
            records.append({
                "event_id": event.event_id,
                "event_date": event.event_date,
                "event_time": event.event_time,
                "country": event.country,
                "currency": event.currency,
                "importance": event.importance,
                "event_name": event.event_name,
                "actual": event.actual,
                "forecast": event.forecast,
                "previous": event.previous,
                "source": event.source,
                "is_historical": event.event_date < date.today(),
                "collected_at": datetime.now(),
            })
        
        if not records:
            return 0
        
        saved = await persistence.save("economic_calendar_events", records)
        progress.saved_records = saved
        progress.details["table"] = "economic_calendar_events"
        
        return saved


@task_executor(
    task_type="economic_calendar_important",
    name="重要经济事件采集",
    description="采集高重要性的经济日历事件",
    category=TaskCategory.MACRO,
    source="investing.com",
    priority=TaskPriority.CRITICAL,
    timeout=60.0,
    parameters=[
        TaskParameter(
            name="days",
            type="integer",
            default=7,
            description="查找未来天数",
        ),
    ],
    output=TaskOutput(
        data_type="economic_calendar_event",
        table_name="economic_calendar_events",
        description="高重要性经济事件",
    ),
    tags=["macro", "calendar", "important"],
)
class ImportantEventsExecutor(TaskExecutor[EconomicEvent]):
    """Executor for collecting high-importance events only."""
    
    def __init__(self):
        self._executor = None
    
    async def _get_executor(self) -> EconomicCalendarExecutor:
        if self._executor is None:
            self._executor = EconomicCalendarExecutor()
        return self._executor
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[EconomicEvent]:
        days = params.get("days", 7)
        
        executor = await self._get_executor()
        all_events = await executor.collect(
            {"past_days": 0, "future_days": days, "importances": ["high"]},
            progress,
        )
        
        return [e for e in all_events if e.importance == "high"]
    
    async def validate(self, data: list[EconomicEvent]) -> list[EconomicEvent]:
        executor = await self._get_executor()
        return await executor.validate(data)
    
    async def save(self, data: list[EconomicEvent], progress: TaskProgress) -> int:
        executor = await self._get_executor()
        return await executor.save(data, progress)


@task_executor(
    task_type="economic_calendar_daily",
    name="每日经济日历更新",
    description="每日定时更新经济日历数据",
    category=TaskCategory.MACRO,
    source="investing.com",
    priority=TaskPriority.HIGH,
    timeout=180.0,
    parameters=[
        TaskParameter(
            name="update_range",
            type="boolean",
            default=True,
            description="是否更新历史和未来范围",
        ),
    ],
    output=TaskOutput(
        data_type="economic_calendar_event",
        table_name="economic_calendar_events",
        description="每日更新的经济日历事件",
    ),
    tags=["macro", "calendar", "scheduled", "daily"],
)
class DailyCalendarUpdateExecutor(TaskExecutor[EconomicEvent]):
    """Executor for daily calendar update tasks."""
    
    def __init__(self):
        self._executor = None
    
    async def _get_executor(self) -> EconomicCalendarExecutor:
        if self._executor is None:
            self._executor = EconomicCalendarExecutor()
        return self._executor
    
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[EconomicEvent]:
        update_range = params.get("update_range", True)
        
        if update_range:
            past_days = 7
            future_days = 30
        else:
            past_days = 1
            future_days = 7
        
        executor = await self._get_executor()
        return await executor.collect(
            {"past_days": past_days, "future_days": future_days},
            progress,
        )
    
    async def validate(self, data: list[EconomicEvent]) -> list[EconomicEvent]:
        executor = await self._get_executor()
        return await executor.validate(data)
    
    async def save(self, data: list[EconomicEvent], progress: TaskProgress) -> int:
        executor = await self._get_executor()
        return await executor.save(data, progress)


def register_calendar_executors():
    """Register all calendar executors with the task registry."""
    from .registry import TaskRegistry
    
    TaskRegistry.register(EconomicCalendarExecutor())
    TaskRegistry.register(ImportantEventsExecutor())
    TaskRegistry.register(DailyCalendarUpdateExecutor())
    
    logger.info("Registered economic calendar executors")
