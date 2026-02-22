"""
Task Registry - Centralized task type definitions and execution.

This module provides a plugin-based architecture for data collection tasks:
- Task types are self-describing with metadata
- Collectors and storage handlers are auto-discovered
- Progress tracking and detailed status reporting
- Easy to add new task types without modifying core code
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TaskCategory(str, Enum):
    """Categories for task types."""
    MARKET = "market"
    FUNDAMENTAL = "fundamental"
    NEWS = "news"
    MACRO = "macro"
    DERIVATIVE = "derivative"
    KNOWLEDGE = "knowledge"


class TaskPriority(int, Enum):
    """Priority levels for task execution."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskParameter:
    """Definition of a task parameter."""
    name: str
    type: str
    default: Any = None
    required: bool = False
    description: str = ""
    choices: list[str] | None = None


@dataclass
class TaskOutput:
    """Definition of task output."""
    data_type: str
    table_name: str
    description: str = ""
    fields: list[str] = field(default_factory=list)


@dataclass
class TaskMetadata:
    """Metadata for a task type."""
    task_type: str
    name: str
    description: str
    category: TaskCategory
    priority: TaskPriority = TaskPriority.NORMAL
    source: str = ""
    timeout: float = 300.0
    retry_count: int = 3
    parameters: list[TaskParameter] = field(default_factory=list)
    output: TaskOutput | None = None
    tags: list[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = "system"


@dataclass
class TaskProgress:
    """Progress tracking for task execution."""
    task_id: str
    status: str = "pending"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_records: int = 0
    processed_records: int = 0
    saved_records: int = 0
    error_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress_pct(self) -> float:
        if self.total_records == 0:
            return 0.0
        return min(100.0, (self.processed_records / self.total_records) * 100)
    
    @property
    def duration_seconds(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()


class TaskExecutor(ABC, Generic[T]):
    """Abstract base class for task executors."""
    
    _metadata: TaskMetadata | None = None
    
    @property
    def metadata(self) -> TaskMetadata:
        """Return task metadata."""
        if self._metadata is None:
            raise NotImplementedError("Task metadata not set")
        return self._metadata
    
    @abstractmethod
    async def collect(self, params: dict[str, Any], progress: TaskProgress) -> list[T]:
        """Collect data from source."""
        pass
    
    @abstractmethod
    async def validate(self, data: list[T]) -> list[T]:
        """Validate collected data."""
        pass
    
    @abstractmethod
    async def save(self, data: list[T], progress: TaskProgress) -> int:
        """Save data to storage."""
        pass
    
    async def execute(self, params: dict[str, Any], progress: TaskProgress) -> dict[str, Any]:
        """Execute the full task pipeline."""
        progress.status = "running"
        progress.started_at = datetime.now()
        
        try:
            progress.status = "collecting"
            data = await self.collect(params, progress)
            progress.total_records = len(data)
            progress.processed_records = len(data)
            
            progress.status = "validating"
            validated_data = await self.validate(data)
            
            progress.status = "saving"
            saved = await self.save(validated_data, progress)
            progress.saved_records = saved
            
            progress.status = "completed"
            progress.completed_at = datetime.now()
            
            return {
                "success": True,
                "task_type": self.metadata.task_type,
                "records_collected": len(data),
                "records_validated": len(validated_data),
                "records_saved": saved,
                "duration_seconds": progress.duration_seconds,
            }
            
        except Exception as e:
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.now()
            logger.error(f"Task {self.metadata.task_type} failed: {e}")
            return {
                "success": False,
                "task_type": self.metadata.task_type,
                "error": str(e),
                "duration_seconds": progress.duration_seconds,
            }


class TaskRegistry:
    """Central registry for task types."""
    
    _instance: 'TaskRegistry | None' = None
    _executors: dict[str, TaskExecutor] = {}
    _metadata: dict[str, TaskMetadata] = {}
    
    def __new__(cls) -> 'TaskRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, executor: TaskExecutor) -> None:
        """Register a task executor."""
        meta = executor.metadata
        cls._executors[meta.task_type] = executor
        cls._metadata[meta.task_type] = meta
        logger.info(f"Registered task: {meta.task_type} ({meta.name})")
    
    @classmethod
    def get_executor(cls, task_type: str) -> TaskExecutor | None:
        """Get executor for a task type."""
        return cls._executors.get(task_type)
    
    @classmethod
    def get_metadata(cls, task_type: str) -> TaskMetadata | None:
        """Get metadata for a task type."""
        return cls._metadata.get(task_type)
    
    @classmethod
    def list_tasks(cls, category: TaskCategory | None = None) -> list[TaskMetadata]:
        """List all registered tasks."""
        tasks = list(cls._metadata.values())
        if category:
            tasks = [t for t in tasks if t.category == category]
        return sorted(tasks, key=lambda t: (t.priority, t.name))
    
    @classmethod
    def list_categories(cls) -> dict[TaskCategory, int]:
        """List task counts by category."""
        counts: dict[TaskCategory, int] = {}
        for meta in cls._metadata.values():
            counts[meta.category] = counts.get(meta.category, 0) + 1
        return counts


def task_executor(
    task_type: str,
    name: str,
    description: str,
    category: TaskCategory,
    source: str = "",
    priority: TaskPriority = TaskPriority.NORMAL,
    timeout: float = 300.0,
    parameters: list[TaskParameter] | None = None,
    output: TaskOutput | None = None,
    tags: list[str] | None = None,
):
    """Decorator to register a class as a task executor."""
    def decorator(cls):
        meta = TaskMetadata(
            task_type=task_type,
            name=name,
            description=description,
            category=category,
            priority=priority,
            source=source,
            timeout=timeout,
            parameters=parameters or [],
            output=output,
            tags=tags or [],
        )
        
        original_init = cls.__init__
        
        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self._metadata = meta
        
        cls.__init__ = __init__
        cls._metadata = meta
        
        @property
        def metadata(self) -> TaskMetadata:
            return self._metadata
        
        cls.metadata = metadata
        
        return cls
    
    return decorator


def get_task_info(task_type: str) -> dict[str, Any] | None:
    """Get detailed information about a task type for API responses."""
    meta = TaskRegistry.get_metadata(task_type)
    if not meta:
        return None
    
    return {
        "task_type": meta.task_type,
        "name": meta.name,
        "description": meta.description,
        "category": meta.category.value,
        "priority": meta.priority.value,
        "source": meta.source,
        "timeout": meta.timeout,
        "retry_count": meta.retry_count,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "default": p.default,
                "required": p.required,
                "description": p.description,
                "choices": p.choices,
            }
            for p in meta.parameters
        ],
        "output": {
            "data_type": meta.output.data_type,
            "table_name": meta.output.table_name,
            "description": meta.output.description,
            "fields": meta.output.fields,
        } if meta.output else None,
        "tags": meta.tags,
        "version": meta.version,
    }


def get_all_task_types() -> list[dict[str, Any]]:
    """Get all registered task types with their metadata."""
    return [get_task_info(meta.task_type) for meta in TaskRegistry.list_tasks()]


def get_tasks_by_category() -> dict[str, list[dict[str, Any]]]:
    """Get tasks grouped by category."""
    result = {}
    for category in TaskCategory:
        tasks = TaskRegistry.list_tasks(category=category)
        if tasks:
            result[category.value] = [get_task_info(t.task_type) for t in tasks]
    return result
