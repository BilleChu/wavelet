"""
Unified Monitor - Centralized monitoring service.

Provides:
- Task execution tracking
- Collection result tracking
- Alert management
- Metric collection
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from openfinance.datacenter.observability.config import get_config

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class MetricType(str, Enum):
    """Types of metrics."""
    TASK_EXECUTION = "task_execution"
    COLLECTION_RESULT = "collection_result"
    DATA_QUALITY = "data_quality"
    SYSTEM_PERFORMANCE = "system_performance"
    ERROR_RATE = "error_rate"


class Alert(BaseModel):
    """Alert data structure."""
    
    alert_id: str = Field(..., description="Unique alert ID")
    alert_type: str = Field(..., description="Type of alert")
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING)
    status: AlertStatus = Field(default=AlertStatus.ACTIVE)
    
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    source: str = Field(..., description="Source of the alert")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class Metric(BaseModel):
    """Metric data structure."""
    
    metric_id: str = Field(..., description="Unique metric ID")
    metric_type: MetricType = Field(..., description="Type of metric")
    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: str | None = None
    
    source: str = Field(..., description="Source of the metric")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class AlertRule(BaseModel):
    """Rule for generating alerts."""
    
    rule_id: str = Field(..., description="Unique rule ID")
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    
    metric_type: MetricType = Field(..., description="Metric type to monitor")
    condition: str = Field(..., description="Condition expression")
    threshold: float | None = None
    
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING)
    cooldown_minutes: int = Field(default=5)
    
    enabled: bool = Field(default=True)
    
    last_triggered: datetime | None = None
    trigger_count: int = 0
    
    class Config:
        use_enum_values = True


class TaskExecutionRecord(BaseModel):
    """Record of a task execution."""
    
    task_id: str
    task_name: str
    task_type: str
    
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    
    duration_seconds: float = 0.0
    records_processed: int = 0
    records_failed: int = 0
    
    error_message: str | None = None
    retry_count: int = 0
    
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionResultRecord(BaseModel):
    """Record of a collection result."""
    
    source_id: str
    collection_type: str
    
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    
    records_collected: int = 0
    records_processed: int = 0
    records_stored: int = 0
    
    data_size_bytes: int = 0
    duration_seconds: float = 0.0
    
    error_message: str | None = None
    
    quality_score: float | None = None


class UnifiedMonitor:
    """
    Unified monitoring service for data center operations.
    
    Features:
    - Task execution tracking
    - Collection result tracking
    - Alert management
    - Metric collection
    """
    
    _instance: "UnifiedMonitor | None" = None
    
    def __init__(
        self,
        max_alerts: int | None = None,
        max_metrics: int | None = None,
        max_records: int | None = None,
    ):
        config = get_config()
        
        self.max_alerts = max_alerts or config.max_alerts
        self.max_metrics = max_metrics or config.max_metrics
        self.max_records = max_records or config.max_records
        
        self._alerts: list[Alert] = []
        self._alert_rules: dict[str, AlertRule] = {}
        self._alert_hashes: dict[str, datetime] = {}
        
        self._metrics: dict[MetricType, list[Metric]] = defaultdict(list)
        
        self._task_executions: dict[str, list[TaskExecutionRecord]] = defaultdict(list)
        self._collection_results: dict[str, list[CollectionResultRecord]] = defaultdict(list)
        
        self._alert_handlers: list[Callable[[Alert], None]] = []
        
        self._load_rules_from_config()
    
    @classmethod
    def get_instance(cls, **kwargs) -> "UnifiedMonitor":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def _load_rules_from_config(self) -> None:
        """Load alert rules from configuration."""
        config = get_config()
        
        for rule_config in config.alert_rules:
            rule = AlertRule(
                rule_id=rule_config.rule_id,
                name=rule_config.name,
                description=rule_config.description,
                metric_type=MetricType.ERROR_RATE,
                condition=rule_config.condition,
                severity=AlertSeverity(rule_config.severity),
                cooldown_minutes=rule_config.cooldown_minutes,
                enabled=rule_config.enabled,
            )
            self._alert_rules[rule.rule_id] = rule
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a handler for new alerts."""
        self._alert_handlers.append(handler)
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._alert_rules[rule.rule_id] = rule
    
    async def record_task_execution(
        self,
        task_id: str,
        task_name: str,
        task_type: str,
        status: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        records_processed: int = 0,
        records_failed: int = 0,
        error_message: str | None = None,
        retry_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> TaskExecutionRecord:
        """Record a task execution."""
        duration = 0.0
        if completed_at and started_at:
            duration = (completed_at - started_at).total_seconds()
        
        record = TaskExecutionRecord(
            task_id=task_id,
            task_name=task_name,
            task_type=task_type,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            records_processed=records_processed,
            records_failed=records_failed,
            error_message=error_message,
            retry_count=retry_count,
            metadata=metadata or {},
        )
        
        self._task_executions[task_id].append(record)
        
        if len(self._task_executions[task_id]) > self.max_records:
            self._task_executions[task_id] = self._task_executions[task_id][-self.max_records:]
        
        await self._record_metric(
            metric_type=MetricType.TASK_EXECUTION,
            name=f"task.{task_type}.duration",
            value=duration,
            source=task_id,
            tags={"status": status},
        )
        
        if status == "failed":
            await self.create_alert(
                alert_type="task_failure",
                severity=AlertSeverity.ERROR,
                title=f"Task failed: {task_name}",
                message=error_message or "Unknown error",
                source=task_id,
                metadata={"task_type": task_type, "retry_count": retry_count},
            )
        
        return record
    
    async def record_collection_result(
        self,
        source_id: str,
        collection_type: str,
        status: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        records_collected: int = 0,
        records_processed: int = 0,
        records_stored: int = 0,
        data_size_bytes: int = 0,
        error_message: str | None = None,
        quality_score: float | None = None,
    ) -> CollectionResultRecord:
        """Record a collection result."""
        duration = 0.0
        if completed_at and started_at:
            duration = (completed_at - started_at).total_seconds()
        
        record = CollectionResultRecord(
            source_id=source_id,
            collection_type=collection_type,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            records_collected=records_collected,
            records_processed=records_processed,
            records_stored=records_stored,
            data_size_bytes=data_size_bytes,
            duration_seconds=duration,
            error_message=error_message,
            quality_score=quality_score,
        )
        
        self._collection_results[source_id].append(record)
        
        if len(self._collection_results[source_id]) > self.max_records:
            self._collection_results[source_id] = self._collection_results[source_id][-self.max_records:]
        
        await self._record_metric(
            metric_type=MetricType.COLLECTION_RESULT,
            name=f"collection.{collection_type}.records",
            value=records_collected,
            source=source_id,
            tags={"status": status},
        )
        
        if quality_score is not None and quality_score < 0.9:
            await self.create_alert(
                alert_type="data_quality",
                severity=AlertSeverity.WARNING,
                title=f"Low data quality: {source_id}",
                message=f"Quality score: {quality_score:.2%}",
                source=source_id,
                metadata={"collection_type": collection_type, "quality_score": quality_score},
            )
        
        return record
    
    async def _record_metric(
        self,
        metric_type: MetricType,
        name: str,
        value: float,
        source: str,
        tags: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Metric:
        """Record a metric."""
        metric = Metric(
            metric_id=f"metric_{uuid.uuid4().hex[:12]}",
            metric_type=metric_type,
            name=name,
            value=value,
            source=source,
            tags=tags or {},
            metadata=metadata or {},
        )
        
        self._metrics[metric_type].append(metric)
        
        if len(self._metrics[metric_type]) > self.max_metrics:
            self._metrics[metric_type] = self._metrics[metric_type][-self.max_metrics:]
        
        await self._check_alert_rules(metric)
        
        return metric
    
    async def create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> Alert | None:
        """Create a new alert."""
        alert_hash = self._compute_hash(alert_type, title, source)
        
        if alert_hash in self._alert_hashes:
            last_time = self._alert_hashes[alert_hash]
            if datetime.now() - last_time < timedelta(minutes=5):
                logger.debug(f"Skipping duplicate alert: {title}")
                return None
        
        alert = Alert(
            alert_id=f"alert_{uuid.uuid4().hex[:12]}",
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {},
        )
        
        self._alerts.append(alert)
        self._alert_hashes[alert_hash] = datetime.now()
        
        if len(self._alerts) > self.max_alerts:
            self._alerts = self._alerts[-self.max_alerts:]
        
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        logger.warning(f"Alert created: [{severity.value}] {title}")
        
        return alert
    
    def _compute_hash(self, alert_type: str, title: str, source: str) -> str:
        """Compute hash for deduplication."""
        content = f"{alert_type}:{title}:{source}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _check_alert_rules(self, metric: Metric) -> None:
        """Check alert rules against a metric."""
        for rule in self._alert_rules.values():
            if not rule.enabled:
                continue
            
            if rule.metric_type != metric.metric_type:
                continue
            
            if rule.last_triggered:
                cooldown = timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() - rule.last_triggered < cooldown:
                    continue
            
            try:
                should_trigger = self._evaluate_condition(rule, metric)
                
                if should_trigger:
                    await self.create_alert(
                        alert_type=f"rule_{rule.rule_id}",
                        severity=rule.severity,
                        title=f"Alert rule triggered: {rule.name}",
                        message=f"Metric {metric.name} = {metric.value}",
                        source=metric.source,
                        metadata={"rule_id": rule.rule_id, "metric_id": metric.metric_id},
                    )
                    
                    rule.last_triggered = datetime.now()
                    rule.trigger_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to evaluate alert rule {rule.rule_id}: {e}")
    
    def _evaluate_condition(self, rule: AlertRule, metric: Metric) -> bool:
        """Evaluate if a rule condition is met."""
        if rule.threshold is not None:
            if ">" in rule.condition:
                return metric.value > rule.threshold
            elif "<" in rule.condition:
                return metric.value < rule.threshold
            elif ">=" in rule.condition:
                return metric.value >= rule.threshold
            elif "<=" in rule.condition:
                return metric.value <= rule.threshold
            elif "==" in rule.condition:
                return metric.value == rule.threshold
        
        return False
    
    def get_alerts(
        self,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts with filtering."""
        alerts = self._alerts
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if source:
            alerts = [a for a in alerts if a.source == source]
        
        return alerts[-limit:]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str | None = None) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.now()
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                alert.updated_at = datetime.now()
                return True
        return False
    
    def get_metrics(
        self,
        metric_type: MetricType | None = None,
        source: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Metric]:
        """Get metrics with filtering."""
        if metric_type:
            metrics = self._metrics.get(metric_type, [])
        else:
            metrics = []
            for m_list in self._metrics.values():
                metrics.extend(m_list)
        
        if source:
            metrics = [m for m in metrics if m.source == source]
        if since:
            metrics = [m for m in metrics if m.timestamp >= since]
        
        return metrics[-limit:]
    
    def get_task_stats(self, task_id: str) -> dict[str, Any]:
        """Get statistics for a task."""
        records = self._task_executions.get(task_id, [])
        
        if not records:
            return {"error": "No records found"}
        
        durations = [r.duration_seconds for r in records if r.status == "completed"]
        successes = sum(1 for r in records if r.status == "completed")
        
        return {
            "task_id": task_id,
            "total_executions": len(records),
            "successful_executions": successes,
            "failed_executions": len(records) - successes,
            "success_rate": successes / len(records) if records else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "total_records_processed": sum(r.records_processed for r in records),
            "last_execution": records[-1].model_dump() if records else None,
        }
    
    def get_summary(self) -> dict[str, Any]:
        """Get overall monitoring summary."""
        total_tasks = sum(len(r) for r in self._task_executions.values())
        total_collections = sum(len(r) for r in self._collection_results.values())
        
        active_alerts = sum(1 for a in self._alerts if a.status == AlertStatus.ACTIVE)
        
        return {
            "total_task_executions": total_tasks,
            "total_collection_results": total_collections,
            "active_alerts": active_alerts,
            "total_alerts": len(self._alerts),
            "unique_tasks": len(self._task_executions),
            "unique_sources": len(self._collection_results),
            "alert_rules": len(self._alert_rules),
        }


def get_unified_monitor() -> UnifiedMonitor:
    """Get the singleton UnifiedMonitor instance."""
    return UnifiedMonitor.get_instance()
