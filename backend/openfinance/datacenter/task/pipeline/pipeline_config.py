"""
Pipeline Configuration - Load pipeline definitions from YAML configuration.

Pipelines are defined in config/pipelines.yaml and loaded at runtime.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

from openfinance.datacenter.task.queue import TaskPriority
from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class ScheduleType(str, Enum):
    """Schedule type for pipeline execution."""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"
    MANUAL = "manual"


@dataclass
class ScheduleConfig:
    """Schedule configuration for a pipeline."""
    type: ScheduleType = ScheduleType.MANUAL
    expression: str | None = None
    timezone: str = "Asia/Shanghai"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "expression": self.expression,
            "timezone": self.timezone,
        }


@dataclass
class PipelineTaskConfig:
    """Configuration for a task within a pipeline."""
    
    task_id: str
    name: str
    task_type: str
    params: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout_seconds: float = 300.0
    max_retries: int = 3
    dependencies: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "params": self.params,
            "priority": self.priority.value,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "dependencies": self.dependencies,
        }


@dataclass
class PipelineConfig:
    """Configuration for a complete pipeline."""
    
    pipeline_id: str
    name: str
    description: str = ""
    tasks: list[PipelineTaskConfig] = field(default_factory=list)
    
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    enabled: bool = True
    timeout_seconds: float = 3600.0
    max_concurrent_tasks: int = 5
    
    metadata: dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
            "schedule": self.schedule.to_dict(),
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "metadata": self.metadata,
        }
    
    def get_task(self, task_id: str) -> PipelineTaskConfig | None:
        """Get a task by ID."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None


def _parse_priority(value: str | int) -> TaskPriority:
    """Parse priority from string or int."""
    if isinstance(value, int):
        return TaskPriority(value)
    
    priority_map = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "normal": TaskPriority.NORMAL,
        "low": TaskPriority.LOW,
        "background": TaskPriority.BACKGROUND,
    }
    return priority_map.get(value.lower(), TaskPriority.NORMAL)


def _parse_schedule(schedule_data: dict | None) -> ScheduleConfig:
    """Parse schedule configuration."""
    if not schedule_data:
        return ScheduleConfig()
    
    schedule_type = ScheduleType(schedule_data.get("type", "manual"))
    
    return ScheduleConfig(
        type=schedule_type,
        expression=schedule_data.get("expression"),
        timezone=schedule_data.get("timezone", "Asia/Shanghai"),
    )


def _parse_task(task_data: dict) -> PipelineTaskConfig:
    """Parse task configuration."""
    return PipelineTaskConfig(
        task_id=task_data["task_id"],
        name=task_data.get("name", task_data["task_id"]),
        task_type=task_data["task_type"],
        params=task_data.get("params", {}),
        priority=_parse_priority(task_data.get("priority", "normal")),
        timeout_seconds=float(task_data.get("timeout_seconds", 300)),
        max_retries=task_data.get("max_retries", 3),
        dependencies=task_data.get("dependencies", []),
    )


def _parse_pipeline(pipeline_id: str, pipeline_data: dict) -> PipelineConfig:
    """Parse pipeline configuration."""
    tasks = [_parse_task(t) for t in pipeline_data.get("tasks", [])]
    schedule = _parse_schedule(pipeline_data.get("schedule"))
    
    return PipelineConfig(
        pipeline_id=pipeline_id,
        name=pipeline_data.get("name", pipeline_id),
        description=pipeline_data.get("description", ""),
        tasks=tasks,
        schedule=schedule,
        enabled=pipeline_data.get("enabled", True),
        timeout_seconds=float(pipeline_data.get("timeout_seconds", 3600)),
        max_concurrent_tasks=pipeline_data.get("max_concurrent_tasks", 5),
        metadata=pipeline_data.get("metadata", {}),
    )


class PipelineRegistry:
    """
    Registry for pipeline configurations loaded from YAML files.
    """
    
    _instance: "PipelineRegistry | None" = None
    _pipelines: dict[str, PipelineConfig] = {}
    _config_path: Path | None = None
    
    def __new__(cls) -> "PipelineRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pipelines = {}
            cls._instance._config_path = None
        return cls._instance
    
    def load_from_file(self, config_path: str | Path | None = None) -> None:
        """Load pipeline configurations from YAML file."""
        if config_path:
            self._config_path = Path(config_path)
        elif self._config_path is None:
            self._config_path = Path(__file__) / "config" / "pipelines.yaml"
        
        if not self._config_path.exists():
            logger.warning(f"Pipeline config file not found: {self._config_path}")
            return
        
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or "pipelines" not in config_data:
                logger.warning("No pipelines found in config file")
                return
            
            for pipeline_id, pipeline_data in config_data["pipelines"].items():
                pipeline = _parse_pipeline(pipeline_id, pipeline_data)
                self._pipelines[pipeline_id] = pipeline
                logger.info(f"Loaded pipeline: {pipeline_id} ({len(pipeline.tasks)} tasks)")
            
        except Exception as e:
            logger.error(f"Failed to load pipeline config: {e}")
    
    def register(self, pipeline: PipelineConfig) -> None:
        """Register a pipeline configuration."""
        self._pipelines[pipeline.pipeline_id] = pipeline
    
    def unregister(self, pipeline_id: str) -> bool:
        """Unregister a pipeline."""
        if pipeline_id in self._pipelines:
            del self._pipelines[pipeline_id]
            return True
        return False
    
    def get(self, pipeline_id: str) -> PipelineConfig | None:
        """Get a pipeline by ID."""
        if not self._pipelines:
            self.load_from_file()
        return self._pipelines.get(pipeline_id)
    
    def list_all(self) -> list[PipelineConfig]:
        """List all registered pipelines."""
        if not self._pipelines:
            self.load_from_file()
        return list(self._pipelines.values())
    
    def reload(self) -> None:
        """Reload configurations from file."""
        self._pipelines.clear()
        self.load_from_file()


def get_pipeline(pipeline_id: str) -> PipelineConfig | None:
    """Get a pipeline configuration by ID."""
    return PipelineRegistry().get(pipeline_id)


def get_all_pipelines() -> list[PipelineConfig]:
    """Get all registered pipeline configurations."""
    return PipelineRegistry().list_all()


def reload_pipelines() -> None:
    """Reload pipeline configurations from file."""
    PipelineRegistry().reload()
