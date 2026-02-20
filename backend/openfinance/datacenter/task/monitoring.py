"""
Monitoring and Alerting Module for Data Center.

Provides comprehensive monitoring with:
- Task execution monitoring
- Performance metrics collection
- Anomaly detection
- Alert notifications
- Historical statistics
"""

import asyncio
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of metrics."""
    
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    THROUGHPUT = "throughput"
    ERROR_COUNT = "error_count"
    QUEUE_SIZE = "queue_size"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"


class AlertStatus(str, Enum):
    """Alert status."""
    
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


@dataclass
class MetricPoint:
    """A single metric data point."""
    
    timestamp: datetime
    value: float
    labels: dict[str, str] = field(default_factory=dict)


class Metric(BaseModel):
    """A metric with historical data."""
    
    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    metric_type: MetricType = Field(..., description="Type of metric")
    name: str = Field(..., description="Metric name")
    
    points: list[dict[str, Any]] = Field(default_factory=list)
    
    unit: str = Field(default="", description="Unit of measurement")
    description: str = Field(default="", description="Metric description")
    
    def add_point(self, value: float, labels: dict[str, str] | None = None) -> None:
        self.points.append({
            "timestamp": datetime.now().isoformat(),
            "value": value,
            "labels": labels or {},
        })
        
        if len(self.points) > 1000:
            self.points = self.points[-1000:]
    
    def get_latest(self) -> float | None:
        if not self.points:
            return None
        return self.points[-1]["value"]
    
    def get_average(self, window_minutes: int = 60) -> float | None:
        if not self.points:
            return None
        
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [
            p for p in self.points
            if datetime.fromisoformat(p["timestamp"]) > cutoff
        ]
        
        if not recent:
            return None
        
        return sum(p["value"] for p in recent) / len(recent)


class Alert(BaseModel):
    """An alert instance."""
    
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    alert_type: str = Field(..., description="Type of alert")
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING, description="Alert severity")
    
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    
    task_id: str | None = Field(default=None, description="Related task ID")
    chain_id: str | None = Field(default=None, description="Related chain ID")
    
    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="Alert status")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    resolved_at: datetime | None = Field(default=None)
    
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    def resolve(self) -> None:
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()
    
    def acknowledge(self) -> None:
        self.status = AlertStatus.ACKNOWLEDGED
        self.updated_at = datetime.now()


class AlertRule(BaseModel):
    """Rule for generating alerts."""
    
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    
    metric_type: MetricType = Field(..., description="Metric to monitor")
    condition: str = Field(..., description="Condition expression (e.g., '> 0.5', '< 10')")
    
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING)
    
    enabled: bool = Field(default=True)
    cooldown_minutes: int = Field(default=5, description="Cooldown between alerts")
    
    last_triggered: datetime | None = Field(default=None)
    trigger_count: int = Field(default=0)


class MonitoringConfig(BaseModel):
    """Configuration for monitoring."""
    
    metrics_retention_hours: int = Field(default=24, description="Hours to retain metrics")
    alerts_retention_days: int = Field(default=30, description="Days to retain alerts")
    
    check_interval_seconds: int = Field(default=30, description="Monitoring check interval")
    
    enable_webhook: bool = Field(default=False, description="Enable webhook notifications")
    webhook_url: str | None = Field(default=None, description="Webhook URL for notifications")
    
    enable_email: bool = Field(default=False, description="Enable email notifications")
    email_recipients: list[str] = Field(default_factory=list)


class TaskMonitor:
    """
    Task execution monitor.
    
    Features:
    - Real-time task status tracking
    - Performance metrics collection
    - Anomaly detection
    - Alert generation
    """
    
    def __init__(self, config: MonitoringConfig | None = None) -> None:
        self.config = config or MonitoringConfig()
        
        self._metrics: dict[str, Metric] = {}
        self._alerts: list[Alert] = []
        self._rules: dict[str, AlertRule] = {}
        
        self._task_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "total_executions": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_duration_ms": 0,
            "last_execution": None,
            "last_status": None,
        })
        
        self._is_running = False
        self._monitor_task: asyncio.Task | None = None
        
        self._alert_callbacks: list[Callable[[Alert], Awaitable[None]]] = []
    
    def register_alert_callback(self, callback: Callable[[Alert], Awaitable[None]]) -> None:
        """Register a callback for new alerts."""
        self._alert_callbacks.append(callback)
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.rule_id] = rule
        logger.info_with_context(
            "Alert rule added",
            context={"rule_id": rule.rule_id, "name": rule.name}
        )
    
    def remove_rule(self, rule_id: str) -> None:
        """Remove an alert rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
    
    def record_task_execution(
        self,
        task_id: str,
        status: str,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        """Record a task execution event."""
        stats = self._task_stats[task_id]
        
        stats["total_executions"] += 1
        stats["last_execution"] = datetime.now()
        stats["last_status"] = status
        
        if status == "completed":
            stats["success_count"] += 1
        elif status == "failed":
            stats["failure_count"] += 1
        
        stats["total_duration_ms"] += duration_ms
        
        self._record_metric(
            MetricType.EXECUTION_TIME,
            f"task.{task_id}.duration",
            duration_ms,
            {"task_id": task_id, "status": status},
        )
        
        if status == "failed":
            self._create_alert(
                alert_type="task_failure",
                severity=AlertSeverity.ERROR,
                title=f"Task Failed: {task_id}",
                message=f"Task {task_id} execution failed. Error: {error}",
                task_id=task_id,
            )
    
    def _record_metric(
        self,
        metric_type: MetricType,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a metric data point."""
        metric_key = f"{metric_type.value if hasattr(metric_type, 'value') else str(metric_type)}.{name}"
        
        if metric_key not in self._metrics:
            self._metrics[metric_key] = Metric(
                metric_type=metric_type,
                name=name,
            )
        
        self._metrics[metric_key].add_point(value, labels)
    
    def _create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        task_id: str | None = None,
        chain_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Alert:
        """Create and store a new alert."""
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            task_id=task_id,
            chain_id=chain_id,
            metadata=metadata or {},
        )
        
        self._alerts.append(alert)
        
        logger.warning_with_context(
            "Alert created",
            context={
                "alert_id": alert.alert_id,
                "type": alert_type,
                "severity": severity.value if hasattr(severity, 'value') else str(severity),
                "title": title,
            }
        )
        
        for callback in self._alert_callbacks:
            asyncio.create_task(callback(alert))
        
        return alert
    
    def _evaluate_rule(self, rule: AlertRule) -> bool:
        """Evaluate an alert rule against current metrics."""
        relevant_metrics = [
            m for m in self._metrics.values()
            if m.metric_type == rule.metric_type
        ]
        
        if not relevant_metrics:
            return False
        
        for metric in relevant_metrics:
            latest = metric.get_latest()
            if latest is None:
                continue
            
            condition = rule.condition.strip()
            
            try:
                if condition.startswith(">="):
                    threshold = float(condition[2:].strip())
                    if latest >= threshold:
                        return True
                elif condition.startswith("<="):
                    threshold = float(condition[2:].strip())
                    if latest <= threshold:
                        return True
                elif condition.startswith(">"):
                    threshold = float(condition[1:].strip())
                    if latest > threshold:
                        return True
                elif condition.startswith("<"):
                    threshold = float(condition[1:].strip())
                    if latest < threshold:
                        return True
                elif condition.startswith("=="):
                    threshold = float(condition[2:].strip())
                    if latest == threshold:
                        return True
            except (ValueError, IndexError):
                continue
        
        return False
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_running:
            for rule_id, rule in self._rules.items():
                if not rule.enabled:
                    continue
                
                if rule.last_triggered:
                    cooldown = timedelta(minutes=rule.cooldown_minutes)
                    if datetime.now() - rule.last_triggered < cooldown:
                        continue
                
                if self._evaluate_rule(rule):
                    self._create_alert(
                        alert_type=f"rule.{rule.name}",
                        severity=rule.severity,
                        title=f"Alert Rule Triggered: {rule.name}",
                        message=f"Rule '{rule.name}' condition '{rule.condition}' was triggered.",
                        metadata={"rule_id": rule_id},
                    )
                    
                    rule.last_triggered = datetime.now()
                    rule.trigger_count += 1
            
            self._cleanup_old_data()
            
            await asyncio.sleep(self.config.check_interval_seconds)
    
    def _cleanup_old_data(self) -> None:
        """Clean up old metrics and alerts."""
        metrics_cutoff = datetime.now() - timedelta(hours=self.config.metrics_retention_hours)
        alerts_cutoff = datetime.now() - timedelta(days=self.config.alerts_retention_days)
        
        for metric in self._metrics.values():
            metric.points = [
                p for p in metric.points
                if datetime.fromisoformat(p["timestamp"]) > metrics_cutoff
            ]
        
        self._alerts = [
            a for a in self._alerts
            if a.created_at > alerts_cutoff
        ]
    
    async def start(self) -> None:
        """Start the monitoring loop."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info_with_context("Monitoring started", context={})
    
    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info_with_context("Monitoring stopped", context={})
    
    def get_task_stats(self, task_id: str) -> dict[str, Any]:
        """Get statistics for a task."""
        stats = self._task_stats.get(task_id, {})
        
        if not stats or stats["total_executions"] == 0:
            return {"task_id": task_id, "no_data": True}
        
        success_rate = stats["success_count"] / stats["total_executions"]
        avg_duration = stats["total_duration_ms"] / stats["total_executions"]
        
        return {
            "task_id": task_id,
            "total_executions": stats["total_executions"],
            "success_count": stats["success_count"],
            "failure_count": stats["failure_count"],
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration,
            "last_execution": stats["last_execution"].isoformat() if stats["last_execution"] else None,
            "last_status": stats["last_status"],
        }
    
    def get_metrics(
        self,
        metric_type: MetricType | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get metrics, optionally filtered by type."""
        metrics = list(self._metrics.values())
        
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        
        return [
            {
                "metric_id": m.metric_id,
                "metric_type": m.metric_type.value if hasattr(m.metric_type, 'value') else str(m.metric_type),
                "name": m.name,
                "latest_value": m.get_latest(),
                "avg_value": m.get_average(),
                "points_count": len(m.points),
            }
            for m in metrics[:limit]
        ]
    
    def get_alerts(
        self,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts, optionally filtered."""
        alerts = self._alerts
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts[-limit:]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolve()
                return True
        return False
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledge()
                return True
        return False
    
    def get_summary(self) -> dict[str, Any]:
        """Get monitoring summary."""
        total_executions = sum(s["total_executions"] for s in self._task_stats.values())
        total_success = sum(s["success_count"] for s in self._task_stats.values())
        total_failures = sum(s["failure_count"] for s in self._task_stats.values())
        
        active_alerts = sum(1 for a in self._alerts if a.status == AlertStatus.ACTIVE)
        critical_alerts = sum(1 for a in self._alerts if a.severity == AlertSeverity.CRITICAL and a.status == AlertStatus.ACTIVE)
        
        return {
            "total_tasks_monitored": len(self._task_stats),
            "total_executions": total_executions,
            "total_success": total_success,
            "total_failures": total_failures,
            "overall_success_rate": total_success / total_executions if total_executions > 0 else 0,
            "total_alerts": len(self._alerts),
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "metrics_count": len(self._metrics),
            "rules_count": len(self._rules),
        }


def create_default_alert_rules() -> list[AlertRule]:
    """Create default alert rules."""
    return [
        AlertRule(
            rule_id="high_failure_rate",
            name="High Failure Rate",
            description="Alert when task failure rate exceeds 50%",
            metric_type=MetricType.SUCCESS_RATE,
            condition="< 0.5",
            severity=AlertSeverity.ERROR,
            cooldown_minutes=10,
        ),
        AlertRule(
            rule_id="slow_execution",
            name="Slow Execution",
            description="Alert when average execution time exceeds 60 seconds",
            metric_type=MetricType.EXECUTION_TIME,
            condition="> 60000",
            severity=AlertSeverity.WARNING,
            cooldown_minutes=15,
        ),
        AlertRule(
            rule_id="high_error_count",
            name="High Error Count",
            description="Alert when error count is high",
            metric_type=MetricType.ERROR_COUNT,
            condition="> 10",
            severity=AlertSeverity.WARNING,
            cooldown_minutes=5,
        ),
    ]
