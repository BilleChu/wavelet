"""
Pipeline Monitor - Monitoring and alerting for pipeline execution.

Provides:
- Task execution metrics
- Alert management
- Performance tracking
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""
    TASK_FAILURE = "task_failure"
    TASK_TIMEOUT = "task_timeout"
    DATA_QUALITY = "data_quality"
    DATA_DELAY = "data_delay"
    SYSTEM_ERROR = "system_error"
    THRESHOLD_BREACH = "threshold_breach"


@dataclass
class Alert:
    """Alert data structure."""
    
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
        }


class AlertChannel(ABC):
    """Abstract base class for alert channels."""
    
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send alert through this channel."""
        pass


class LogAlertChannel(AlertChannel):
    """Alert channel that logs alerts."""
    
    def __init__(self, log_level: int = logging.WARNING):
        self.log_level = log_level
    
    async def send(self, alert: Alert) -> bool:
        log_msg = f"[{alert.severity.value.upper()}] {alert.title}: {alert.message}"
        
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(log_msg)
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(log_msg)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return True


class WebhookAlertChannel(AlertChannel):
    """Alert channel that sends to webhook."""
    
    def __init__(self, webhook_url: str, headers: dict | None = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    async def send(self, alert: Alert) -> bool:
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=alert.to_dict(),
                    headers=self.headers,
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class AlertManager:
    """
    Manager for alert handling and routing.
    """
    
    def __init__(
        self,
        channels: list[AlertChannel] | None = None,
        dedup_window_minutes: int = 30,
        rate_limit_per_hour: int = 100,
    ):
        self.channels = channels or [LogAlertChannel()]
        self.dedup_window = timedelta(minutes=dedup_window_minutes)
        self.rate_limit = rate_limit_per_hour
        
        self._alerts: list[Alert] = []
        self._alert_hashes: dict[str, datetime] = {}
        self._hourly_count: int = 0
        self._hourly_reset: datetime = datetime.now()
    
    async def send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> Alert | None:
        """Send an alert through configured channels."""
        import hashlib
        
        alert_hash = hashlib.md5(f"{alert_type.value}:{title}:{source}".encode()).hexdigest()
        
        if alert_hash in self._alert_hashes:
            last_time = self._alert_hashes[alert_hash]
            if datetime.now() - last_time < self.dedup_window:
                logger.debug(f"Skipping duplicate alert: {title}")
                return self._alerts[-1] if self._alerts else None
        
        if not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded, dropping alert: {title}")
            return None
        
        alert = Alert(
            alert_id=f"alert_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {},
        )
        
        self._alerts.append(alert)
        self._alert_hashes[alert_hash] = datetime.now()
        
        for channel in self.channels:
            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(f"Failed to send alert through channel: {e}")
        
        return alert
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded."""
        now = datetime.now()
        
        if (now - self._hourly_reset) > timedelta(hours=1):
            self._hourly_count = 0
            self._hourly_reset = now
        
        if self._hourly_count >= self.rate_limit:
            return False
        
        self._hourly_count += 1
        return True
    
    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        source: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Get alerts with filtering."""
        alerts = self._alerts
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if source:
            alerts = [a for a in alerts if a.source == source]
        if since:
            alerts = [a for a in alerts if a.timestamp >= since]
        
        return alerts[-limit:]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = acknowledged_by
                return True
        return False


class TaskMetrics:
    """Metrics for task execution."""
    
    def __init__(self):
        self._metrics: dict[str, list[dict]] = defaultdict(list)
        self._start_times: dict[str, datetime] = {}
    
    def start_task(self, task_id: str) -> None:
        """Record task start."""
        self._start_times[task_id] = datetime.now()
    
    def end_task(
        self,
        task_id: str,
        success: bool,
        records_processed: int = 0,
        error: str | None = None,
    ) -> None:
        """Record task end."""
        start_time = self._start_times.pop(task_id, None)
        
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
            
            metric = {
                "task_id": task_id,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": duration,
                "success": success,
                "records_processed": records_processed,
                "error": error,
            }
            
            self._metrics[task_id].append(metric)
    
    def get_task_stats(self, task_id: str) -> dict[str, Any]:
        """Get statistics for a task."""
        metrics = self._metrics.get(task_id, [])
        
        if not metrics:
            return {"error": "No metrics found"}
        
        durations = [m["duration_seconds"] for m in metrics if m["success"]]
        successes = sum(1 for m in metrics if m["success"])
        
        return {
            "task_id": task_id,
            "total_runs": len(metrics),
            "successful_runs": successes,
            "failed_runs": len(metrics) - successes,
            "success_rate": successes / len(metrics) if metrics else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "last_run": metrics[-1] if metrics else None,
        }
    
    def get_summary(self) -> dict[str, Any]:
        """Get overall metrics summary."""
        all_metrics = []
        for metrics_list in self._metrics.values():
            all_metrics.extend(metrics_list)
        
        if not all_metrics:
            return {"error": "No metrics found"}
        
        successes = sum(1 for m in all_metrics if m["success"])
        
        return {
            "total_tasks": len(self._metrics),
            "total_runs": len(all_metrics),
            "successful_runs": successes,
            "failed_runs": len(all_metrics) - successes,
            "overall_success_rate": successes / len(all_metrics),
        }


class PipelineMonitor:
    """
    Comprehensive monitoring for pipeline execution.
    """
    
    def __init__(
        self,
        alert_channels: list[AlertChannel] | None = None,
    ):
        self.alert_manager = AlertManager(channels=alert_channels)
        self.task_metrics = TaskMetrics()
    
    async def on_task_start(self, task_id: str) -> None:
        """Handle task start event."""
        self.task_metrics.start_task(task_id)
        logger.info(f"Task started: {task_id}")
    
    async def on_task_complete(
        self,
        task_id: str,
        success: bool,
        records_processed: int = 0,
        error: str | None = None,
    ) -> None:
        """Handle task complete event."""
        self.task_metrics.end_task(task_id, success, records_processed, error)
        
        if not success:
            await self.alert_manager.send_alert(
                alert_type=AlertType.TASK_FAILURE,
                severity=AlertSeverity.ERROR,
                title=f"Task failed: {task_id}",
                message=error or "Unknown error",
                source=task_id,
                metadata={"records_processed": records_processed},
            )
        
        logger.info(f"Task completed: {task_id}, success={success}, records={records_processed}")
    
    def get_dashboard_data(self) -> dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            "metrics_summary": self.task_metrics.get_summary(),
            "recent_alerts": [a.to_dict() for a in self.alert_manager.get_alerts(limit=10)],
        }
