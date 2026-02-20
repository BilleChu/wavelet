"""
Service Monitoring Module.

Provides monitoring, analytics, and alerting capabilities
for data services.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from .models import (
    DataServiceUsage,
    ServiceHealth,
)
from .registry import get_service_registry

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """
    Service monitor for tracking and analyzing service performance.

    Provides:
    - Real-time metrics collection
    - Performance analytics
    - Alert management
    - Usage reporting
    """

    def __init__(self) -> None:
        self._metrics: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._alerts: list[dict[str, Any]] = []
        self._alert_handlers: list[callable] = []
        self._monitoring_task: asyncio.Task | None = None
        self._running = False

    async def start_monitoring(self, interval_seconds: int = 60) -> None:
        """Start the monitoring loop."""
        if self._running:
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(interval_seconds)
        )
        logger.info(f"Started service monitoring with {interval_seconds}s interval")

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped service monitoring")

    async def _monitoring_loop(self, interval: int) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Monitoring error: {e}")
                await asyncio.sleep(interval)

    async def _collect_metrics(self) -> None:
        """Collect metrics from all services."""
        registry = get_service_registry()
        health_list = registry.get_all_health()
        
        timestamp = datetime.now()
        
        for health in health_list:
            metric = {
                "timestamp": timestamp,
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
                "failed_requests": health.failed_requests,
                "avg_response_time_ms": health.avg_response_time_ms,
                "success_rate": (
                    health.successful_requests / health.total_requests
                    if health.total_requests > 0
                    else 1.0
                ),
            }
            
            self._metrics[health.service_id].append(metric)
            
            if len(self._metrics[health.service_id]) > 1000:
                self._metrics[health.service_id] = self._metrics[health.service_id][-500:]

    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        registry = get_service_registry()
        
        for service_id, metrics in self._metrics.items():
            if not metrics:
                continue
            
            latest = metrics[-1]
            
            if latest["success_rate"] < 0.95:
                await self._trigger_alert(
                    service_id=service_id,
                    alert_type="low_success_rate",
                    severity="warning",
                    message=f"Success rate {latest['success_rate']:.2%} is below 95%",
                    data=latest,
                )
            
            if latest["avg_response_time_ms"] > 1000:
                await self._trigger_alert(
                    service_id=service_id,
                    alert_type="high_latency",
                    severity="warning",
                    message=f"Average response time {latest['avg_response_time_ms']:.0f}ms exceeds 1000ms",
                    data=latest,
                )
            
            service = registry.get_service(service_id)
            if service:
                health = registry.get_health(service_id)
                if health and health.failed_requests > 10:
                    recent_failures = health.failed_requests
                    if recent_failures > health.total_requests * 0.1:
                        await self._trigger_alert(
                            service_id=service_id,
                            alert_type="high_failure_rate",
                            severity="critical",
                            message=f"High failure rate detected: {recent_failures} failures",
                            data=latest,
                        )

    async def _trigger_alert(
        self,
        service_id: str,
        alert_type: str,
        severity: str,
        message: str,
        data: dict[str, Any],
    ) -> None:
        """Trigger an alert."""
        alert = {
            "alert_id": f"{service_id}:{alert_type}:{datetime.now().isoformat()}",
            "service_id": service_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "data": data,
            "timestamp": datetime.now(),
            "acknowledged": False,
        }
        
        recent_alerts = [
            a for a in self._alerts
            if a["service_id"] == service_id
            and a["alert_type"] == alert_type
            and datetime.now() - a["timestamp"] < timedelta(minutes=5)
        ]
        
        if not recent_alerts:
            self._alerts.append(alert)
            logger.warning(f"Alert triggered: {message}")
            
            for handler in self._alert_handlers:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.exception(f"Alert handler error: {e}")

    def add_alert_handler(self, handler: callable) -> None:
        """Add an alert handler."""
        self._alert_handlers.append(handler)

    def get_metrics(
        self,
        service_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get metrics for a service."""
        metrics = self._metrics.get(service_id, [])
        
        if start_time:
            metrics = [m for m in metrics if m["timestamp"] >= start_time]
        if end_time:
            metrics = [m for m in metrics if m["timestamp"] <= end_time]
        
        return metrics

    def get_alerts(
        self,
        service_id: str | None = None,
        severity: str | None = None,
        acknowledged: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Get alerts with optional filtering."""
        alerts = self._alerts
        
        if service_id:
            alerts = [a for a in alerts if a["service_id"] == service_id]
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        if acknowledged is not None:
            alerts = [a for a in alerts if a["acknowledged"] == acknowledged]
        
        return alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert["alert_id"] == alert_id:
                alert["acknowledged"] = True
                return True
        return False

    def get_service_summary(self, service_id: str) -> dict[str, Any]:
        """Get a summary of service performance."""
        metrics = self._metrics.get(service_id, [])
        if not metrics:
            return {"error": "No metrics available"}
        
        latest = metrics[-1]
        
        if len(metrics) >= 2:
            previous = metrics[-2]
            response_time_trend = (
                latest["avg_response_time_ms"] - previous["avg_response_time_ms"]
            ) / previous["avg_response_time_ms"] * 100 if previous["avg_response_time_ms"] > 0 else 0
        else:
            response_time_trend = 0
        
        return {
            "service_id": service_id,
            "current": {
                "total_requests": latest["total_requests"],
                "success_rate": latest["success_rate"],
                "avg_response_time_ms": latest["avg_response_time_ms"],
            },
            "trends": {
                "response_time_change_pct": response_time_trend,
            },
            "health_status": "healthy" if latest["success_rate"] > 0.95 else "degraded",
        }

    def get_all_summaries(self) -> dict[str, dict[str, Any]]:
        """Get summaries for all services."""
        return {
            service_id: self.get_service_summary(service_id)
            for service_id in self._metrics.keys()
        }

    def export_metrics(
        self,
        format: str = "json",
    ) -> str | dict:
        """Export metrics in specified format."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "services": {
                service_id: metrics
                for service_id, metrics in self._metrics.items()
            },
        }
        
        if format == "json":
            import json
            return json.dumps(data, default=str, indent=2)
        
        return data


_monitor: ServiceMonitor | None = None


def get_service_monitor() -> ServiceMonitor:
    """Get the global service monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ServiceMonitor()
    return _monitor
