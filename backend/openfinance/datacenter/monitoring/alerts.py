"""
Alert Manager for Data Center.

Provides alerting capabilities with:
- Rule-based alerting
- Multiple notification channels
- Alert deduplication
- Escalation policies
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status."""
    
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class Alert:
    """An alert instance."""
    
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    
    status: AlertStatus = AlertStatus.FIRING
    starts_at: datetime = field(default_factory=datetime.now)
    ends_at: datetime | None = None
    
    source: str | None = None
    fingerprint: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "labels": self.labels,
            "annotations": self.annotations,
            "status": self.status.value,
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "source": self.source,
            "fingerprint": self.fingerprint,
        }


class AlertRule(BaseModel):
    """A rule for triggering alerts."""
    
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    description: str = Field(default="", description="Rule description")
    
    condition: str = Field(..., description="Condition expression")
    threshold: float | None = Field(default=None, description="Threshold value")
    
    severity: AlertSeverity = Field(
        default=AlertSeverity.MEDIUM,
        description="Alert severity when triggered"
    )
    
    duration_seconds: int = Field(
        default=0,
        description="Duration condition must be true before alerting"
    )
    
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Labels to add to alerts"
    )
    
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="Annotations to add to alerts"
    )
    
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    
    silence_duration_minutes: int = Field(
        default=60,
        description="Duration to silence duplicate alerts"
    )
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "duration_seconds": self.duration_seconds,
            "labels": self.labels,
            "annotations": self.annotations,
            "enabled": self.enabled,
        }


@dataclass
class NotificationChannel:
    """A notification channel for alerts."""
    
    channel_id: str
    channel_type: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    async def send(self, alert: Alert) -> bool:
        """Send alert notification."""
        if self.channel_type == "log":
            logger.warning(f"ALERT [{alert.severity.value}] {alert.name}: {alert.message}")
            return True
        
        elif self.channel_type == "webhook":
            return await self._send_webhook(alert)
        
        elif self.channel_type == "email":
            return await self._send_email(alert)
        
        return False
    
    async def _send_webhook(self, alert: Alert) -> bool:
        """Send alert via webhook."""
        try:
            import aiohttp
            
            url = self.config.get("url")
            if not url:
                return False
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=alert.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    async def _send_email(self, alert: Alert) -> bool:
        """Send alert via email."""
        logger.info(f"Email notification for alert: {alert.name}")
        return True


class AlertManager:
    """
    Manager for alerting in Data Center.
    
    Features:
    - Rule-based alerting
    - Multiple notification channels
    - Alert deduplication
    - Silence management
    
    Usage:
        manager = AlertManager()
        
        # Add notification channel
        manager.add_channel(NotificationChannel(
            channel_id="log",
            channel_type="log",
        ))
        
        # Add alert rule
        manager.add_rule(AlertRule(
            rule_id="collection_failure",
            name="Collection Failure",
            condition="failure_rate > 0.1",
            severity=AlertSeverity.HIGH,
        ))
        
        # Check and fire alerts
        manager.check_and_fire("collection_failure", {
            "failure_rate": 0.15,
            "source": "eastmoney",
        })
    """
    
    def __init__(self) -> None:
        self._rules: dict[str, AlertRule] = {}
        self._channels: dict[str, NotificationChannel] = {}
        self._alerts: dict[str, Alert] = {}
        self._silences: dict[str, datetime] = {}
        self._alert_counter = 0
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels[channel.channel_id] = channel
        logger.info(f"Added notification channel: {channel.channel_id}")
    
    def remove_channel(self, channel_id: str) -> bool:
        """Remove a notification channel."""
        if channel_id in self._channels:
            del self._channels[channel_id]
            return True
        return False
    
    def check_and_fire(
        self,
        rule_id: str,
        context: dict[str, Any],
    ) -> Alert | None:
        """
        Check a rule and fire alert if condition is met.
        
        Args:
            rule_id: Rule to check
            context: Context for condition evaluation
        
        Returns:
            Alert if fired, None otherwise
        """
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled:
            return None
        
        fingerprint = self._compute_fingerprint(rule_id, context)
        
        if self._is_silenced(fingerprint):
            return None
        
        if self._evaluate_condition(rule, context):
            alert = self._create_alert(rule, context, fingerprint)
            self._alerts[alert.alert_id] = alert
            
            asyncio.create_task(self._send_notifications(alert))
            
            silence_until = datetime.now() + timedelta(
                minutes=rule.silence_duration_minutes
            )
            self._silences[fingerprint] = silence_until
            
            return alert
        
        return None
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.ends_at = datetime.now()
            return True
        return False
    
    def silence(
        self,
        fingerprint: str,
        duration_minutes: int = 60,
    ) -> None:
        """Silence alerts with a fingerprint."""
        self._silences[fingerprint] = datetime.now() + timedelta(
            minutes=duration_minutes
        )
    
    def get_alerts(
        self,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
    ) -> list[Alert]:
        """Get alerts with optional filters."""
        alerts = list(self._alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    def _evaluate_condition(
        self,
        rule: AlertRule,
        context: dict[str, Any],
    ) -> bool:
        """Evaluate rule condition against context."""
        try:
            condition = rule.condition
            
            if ">" in condition:
                parts = condition.split(">")
                if len(parts) == 2:
                    key = parts[0].strip()
                    threshold = float(parts[1].strip())
                    value = context.get(key, 0)
                    return float(value) > threshold
            
            elif "<" in condition:
                parts = condition.split("<")
                if len(parts) == 2:
                    key = parts[0].strip()
                    threshold = float(parts[1].strip())
                    value = context.get(key, 0)
                    return float(value) < threshold
            
            elif "==" in condition:
                parts = condition.split("==")
                if len(parts) == 2:
                    key = parts[0].strip()
                    expected = parts[1].strip().strip('"\'')
                    return str(context.get(key, "")) == expected
            
            elif "!=" in condition:
                parts = condition.split("!=")
                if len(parts) == 2:
                    key = parts[0].strip()
                    expected = parts[1].strip().strip('"\'')
                    return str(context.get(key, "")) != expected
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition: {e}")
            return False
    
    def _create_alert(
        self,
        rule: AlertRule,
        context: dict[str, Any],
        fingerprint: str,
    ) -> Alert:
        """Create an alert from a rule."""
        self._alert_counter += 1
        
        return Alert(
            alert_id=f"alert_{self._alert_counter}",
            name=rule.name,
            severity=rule.severity,
            message=f"Rule '{rule.name}' triggered: {rule.condition}",
            labels={**rule.labels, **context},
            annotations=rule.annotations,
            fingerprint=fingerprint,
            source=context.get("source"),
        )
    
    def _compute_fingerprint(
        self,
        rule_id: str,
        context: dict[str, Any],
    ) -> str:
        """Compute fingerprint for alert deduplication."""
        import hashlib
        
        key_parts = [rule_id]
        for k in sorted(context.keys()):
            if k not in ["timestamp", "value"]:
                key_parts.append(f"{k}={context[k]}")
        
        key = "|".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def _is_silenced(self, fingerprint: str) -> bool:
        """Check if an alert is silenced."""
        silence_until = self._silences.get(fingerprint)
        if silence_until:
            return datetime.now() < silence_until
        return False
    
    async def _send_notifications(self, alert: Alert) -> None:
        """Send alert to all notification channels."""
        for channel in self._channels.values():
            if channel.enabled:
                try:
                    await channel.send(alert)
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get alert manager statistics."""
        alerts = list(self._alerts.values())
        
        return {
            "rules_count": len(self._rules),
            "channels_count": len(self._channels),
            "alerts_count": len(alerts),
            "firing_count": sum(1 for a in alerts if a.status == AlertStatus.FIRING),
            "resolved_count": sum(1 for a in alerts if a.status == AlertStatus.RESOLVED),
            "silenced_count": len(self._silences),
            "by_severity": {
                s.value: sum(1 for a in alerts if a.severity == s)
                for s in AlertSeverity
            },
        }


def create_default_alert_rules() -> list[AlertRule]:
    """Create default alert rules."""
    return [
        AlertRule(
            rule_id="collection_failure_rate",
            name="High Collection Failure Rate",
            description="Alert when collection failure rate exceeds 10%",
            condition="failure_rate > 0.1",
            severity=AlertSeverity.HIGH,
            labels={"category": "collection"},
        ),
        AlertRule(
            rule_id="collection_timeout",
            name="Collection Timeout",
            description="Alert when collection times out",
            condition="status == 'timeout'",
            severity=AlertSeverity.MEDIUM,
            labels={"category": "collection"},
        ),
        AlertRule(
            rule_id="quality_score_low",
            name="Low Data Quality Score",
            description="Alert when quality score falls below 90%",
            condition="quality_score < 0.9",
            severity=AlertSeverity.MEDIUM,
            labels={"category": "quality"},
        ),
        AlertRule(
            rule_id="task_queue_backlog",
            name="Task Queue Backlog",
            description="Alert when task queue has too many pending tasks",
            condition="queue_size > 100",
            severity=AlertSeverity.MEDIUM,
            labels={"category": "task"},
        ),
        AlertRule(
            rule_id="adapter_error",
            name="Adapter Error",
            description="Alert on adapter errors",
            condition="error_count > 5",
            severity=AlertSeverity.HIGH,
            labels={"category": "adapter"},
        ),
    ]
