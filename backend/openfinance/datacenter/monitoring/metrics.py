"""
Prometheus Metrics for Data Center.

Provides comprehensive metrics collection and exposure for:
- Data collection operations
- Task queue performance
- Data quality metrics
- Pipeline execution
"""

import logging
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Summary,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        start_http_server,
        REGISTRY,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics will be collected but not exposed")


@dataclass
class CollectionMetrics:
    """Metrics for data collection operations."""
    
    source: str
    data_type: str
    
    records_collected: int = 0
    records_valid: int = 0
    records_failed: int = 0
    
    duration_seconds: float = 0.0
    success: bool = True
    error_message: str | None = None
    
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TaskMetrics:
    """Metrics for task execution."""
    
    task_id: str
    task_type: str
    
    status: str
    duration_ms: float = 0.0
    records_processed: int = 0
    
    retry_count: int = 0
    error: str | None = None
    
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class QualityMetrics:
    """Metrics for data quality."""
    
    data_source: str
    data_type: str
    
    completeness_score: float = 0.0
    accuracy_score: float = 0.0
    timeliness_score: float = 0.0
    overall_score: float = 0.0
    
    issues_count: int = 0
    critical_issues: int = 0
    
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MetricsCollector:
    """
    Central metrics collector for Data Center.
    
    Features:
    - Prometheus metrics exposure
    - Custom metrics collection
    - Performance tracking
    - Quality monitoring
    
    Usage:
        collector = MetricsCollector()
        
        # Record collection
        with collector.track_collection("eastmoney", "stock_quote"):
            data = await fetch_data()
        
        # Record task
        collector.record_task(TaskMetrics(
            task_id="task_123",
            task_type="collection",
            status="completed",
        ))
        
        # Start metrics server
        collector.start_server(9090)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        namespace: str = "datacenter",
        registry: Any = None,
    ) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self._namespace = namespace
        self._initialized = True
        
        if PROMETHEUS_AVAILABLE:
            self._registry = registry or REGISTRY
            self._setup_prometheus_metrics()
        else:
            self._registry = None
            self._counters: dict[str, int] = {}
            self._gauges: dict[str, float] = {}
            self._histograms: dict[str, list[float]] = {}
    
    def _setup_prometheus_metrics(self) -> None:
        """Set up Prometheus metrics."""
        ns = self._namespace
        
        self._collection_total = Counter(
            f"{ns}_collection_total",
            "Total number of data collections",
            ["source", "data_type", "status"],
            registry=self._registry,
        )
        
        self._collection_records = Counter(
            f"{ns}_collection_records_total",
            "Total number of records collected",
            ["source", "data_type"],
            registry=self._registry,
        )
        
        self._collection_duration = Histogram(
            f"{ns}_collection_duration_seconds",
            "Duration of data collection in seconds",
            ["source", "data_type"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
            registry=self._registry,
        )
        
        self._collection_errors = Counter(
            f"{ns}_collection_errors_total",
            "Total number of collection errors",
            ["source", "data_type", "error_type"],
            registry=self._registry,
        )
        
        self._task_total = Counter(
            f"{ns}_task_total",
            "Total number of tasks",
            ["task_type", "status"],
            registry=self._registry,
        )
        
        self._task_duration = Histogram(
            f"{ns}_task_duration_seconds",
            "Duration of task execution in seconds",
            ["task_type"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self._registry,
        )
        
        self._task_queue_size = Gauge(
            f"{ns}_task_queue_size",
            "Current size of task queue",
            ["queue_name"],
            registry=self._registry,
        )
        
        self._task_running = Gauge(
            f"{ns}_task_running",
            "Number of currently running tasks",
            registry=self._registry,
        )
        
        self._quality_score = Gauge(
            f"{ns}_quality_score",
            "Data quality score",
            ["source", "data_type", "dimension"],
            registry=self._registry,
        )
        
        self._quality_issues = Counter(
            f"{ns}_quality_issues_total",
            "Total number of quality issues",
            ["source", "data_type", "severity"],
            registry=self._registry,
        )
        
        self._pipeline_total = Counter(
            f"{ns}_pipeline_total",
            "Total number of pipeline executions",
            ["pipeline_name", "status"],
            registry=self._registry,
        )
        
        self._pipeline_duration = Histogram(
            f"{ns}_pipeline_duration_seconds",
            "Duration of pipeline execution in seconds",
            ["pipeline_name"],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
            registry=self._registry,
        )
        
        self._adapter_requests = Counter(
            f"{ns}_adapter_requests_total",
            "Total number of adapter requests",
            ["adapter_id", "status"],
            registry=self._registry,
        )
        
        self._adapter_latency = Histogram(
            f"{ns}_adapter_latency_seconds",
            "Adapter request latency in seconds",
            ["adapter_id"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self._registry,
        )
    
    def record_collection(self, metrics: CollectionMetrics) -> None:
        """Record collection metrics."""
        status = "success" if metrics.success else "failure"
        
        if PROMETHEUS_AVAILABLE:
            self._collection_total.labels(
                source=metrics.source,
                data_type=metrics.data_type,
                status=status,
            ).inc()
            
            self._collection_records.labels(
                source=metrics.source,
                data_type=metrics.data_type,
            ).inc(metrics.records_collected)
            
            self._collection_duration.labels(
                source=metrics.source,
                data_type=metrics.data_type,
            ).observe(metrics.duration_seconds)
            
            if not metrics.success and metrics.error_message:
                error_type = type(metrics.error_message).__name__
                self._collection_errors.labels(
                    source=metrics.source,
                    data_type=metrics.data_type,
                    error_type=error_type,
                ).inc()
        else:
            key = f"collection_{metrics.source}_{metrics.data_type}"
            self._counters[key] = self._counters.get(key, 0) + 1
    
    def record_task(self, metrics: TaskMetrics) -> None:
        """Record task metrics."""
        if PROMETHEUS_AVAILABLE:
            self._task_total.labels(
                task_type=metrics.task_type,
                status=metrics.status,
            ).inc()
            
            self._task_duration.labels(
                task_type=metrics.task_type,
            ).observe(metrics.duration_ms / 1000)
        else:
            key = f"task_{metrics.task_type}"
            self._counters[key] = self._counters.get(key, 0) + 1
    
    def record_quality(self, metrics: QualityMetrics) -> None:
        """Record quality metrics."""
        if PROMETHEUS_AVAILABLE:
            dimensions = {
                "completeness": metrics.completeness_score,
                "accuracy": metrics.accuracy_score,
                "timeliness": metrics.timeliness_score,
                "overall": metrics.overall_score,
            }
            
            for dimension, score in dimensions.items():
                self._quality_score.labels(
                    source=metrics.data_source,
                    data_type=metrics.data_type,
                    dimension=dimension,
                ).set(score)
            
            self._quality_issues.labels(
                source=metrics.data_source,
                data_type=metrics.data_type,
                severity="critical",
            ).inc(metrics.critical_issues)
    
    def set_queue_size(self, queue_name: str, size: int) -> None:
        """Set current queue size."""
        if PROMETHEUS_AVAILABLE:
            self._task_queue_size.labels(queue_name=queue_name).set(size)
        else:
            self._gauges[f"queue_{queue_name}"] = float(size)
    
    def set_running_tasks(self, count: int) -> None:
        """Set number of running tasks."""
        if PROMETHEUS_AVAILABLE:
            self._task_running.set(count)
        else:
            self._gauges["running_tasks"] = float(count)
    
    def record_pipeline(
        self,
        pipeline_name: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record pipeline execution."""
        if PROMETHEUS_AVAILABLE:
            self._pipeline_total.labels(
                pipeline_name=pipeline_name,
                status=status,
            ).inc()
            
            self._pipeline_duration.labels(
                pipeline_name=pipeline_name,
            ).observe(duration_seconds)
        else:
            key = f"pipeline_{pipeline_name}"
            self._counters[key] = self._counters.get(key, 0) + 1
    
    def record_adapter_request(
        self,
        adapter_id: str,
        success: bool,
        latency_seconds: float,
    ) -> None:
        """Record adapter request."""
        status = "success" if success else "failure"
        
        if PROMETHEUS_AVAILABLE:
            self._adapter_requests.labels(
                adapter_id=adapter_id,
                status=status,
            ).inc()
            
            self._adapter_latency.labels(
                adapter_id=adapter_id,
            ).observe(latency_seconds)
    
    @contextmanager
    def track_collection(self, source: str, data_type: str):
        """Context manager to track collection duration."""
        start_time = datetime.now()
        success = True
        error = None
        
        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            self.record_collection(CollectionMetrics(
                source=source,
                data_type=data_type,
                duration_seconds=duration,
                success=success,
                error_message=error,
            ))
    
    @contextmanager
    def track_task(self, task_type: str, task_id: str):
        """Context manager to track task execution."""
        start_time = datetime.now()
        status = "completed"
        error = None
        
        try:
            yield
        except Exception as e:
            status = "failed"
            error = str(e)
            raise
        finally:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.record_task(TaskMetrics(
                task_id=task_id,
                task_type=task_type,
                status=status,
                duration_ms=duration_ms,
                error=error,
            ))
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(self._registry).decode("utf-8")
        else:
            lines = []
            for key, value in self._counters.items():
                lines.append(f"{key}: {value}")
            for key, value in self._gauges.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
    
    def start_server(self, port: int = 9090) -> None:
        """Start Prometheus metrics server."""
        if PROMETHEUS_AVAILABLE:
            start_http_server(port, registry=self._registry)
            logger.info(f"Started metrics server on port {port}")
        else:
            logger.warning("Cannot start metrics server: prometheus_client not installed")


def start_metrics_server(port: int = 9090) -> MetricsCollector:
    """
    Start the metrics server and return the collector.
    
    Args:
        port: Port to expose metrics on
    
    Returns:
        MetricsCollector instance
    """
    collector = MetricsCollector()
    collector.start_server(port)
    return collector


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return MetricsCollector()
