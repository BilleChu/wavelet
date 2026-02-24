"""
Integration Tests for Data Center Modules.

Tests the interaction between SourceRegistry, UnifiedMonitor, and DAGEngine.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from openfinance.datacenter.collector.source import (
    SourceRegistry,
    SourceConfig,
    SourceType,
    SourceStatus,
    CollectionRule,
    ConnectionConfig,
    get_source_registry,
)
from openfinance.datacenter.observability.monitoring.unified_monitor import (
    UnifiedMonitor,
    AlertSeverity,
    AlertStatus,
    AlertRule,
    MetricType,
    get_unified_monitor,
)
from openfinance.datacenter.task.dag_engine import (
    DAGEngine,
    DAG,
    DAGNode,
    DAGBuilder,
    TaskStatus,
    TaskPriority,
)


class TestSourceConfigMonitorIntegration:
    """Integration tests for SourceRegistry and UnifiedMonitor."""

    @pytest.fixture
    def registry(self):
        return SourceRegistry()

    @pytest.fixture
    def monitor(self):
        return UnifiedMonitor()

    @pytest.mark.asyncio
    async def test_connection_failure_creates_alert(self, registry, monitor):
        config = SourceConfig(
            source_id="failing_source",
            name="Failing Source",
            source_type=SourceType.API,
            connection=ConnectionConfig(
                base_url="https://nonexistent.example.com",
                timeout=1.0,
            ),
        )
        registry.register_source(config)
        
        source = registry.get_source("failing_source")
        assert source is not None
        assert source.name == "Failing Source"

    @pytest.mark.asyncio
    async def test_health_tracking_with_monitoring(self, registry, monitor):
        config = SourceConfig(
            source_id="monitored_source",
            name="Monitored Source",
            source_type=SourceType.API,
        )
        registry.register_source(config)
        
        source = registry.get_source("monitored_source")
        assert source is not None
        assert source.name == "Monitored Source"

    @pytest.mark.asyncio
    async def test_collection_rule_with_source(self, registry):
        config = SourceConfig(
            source_id="tushare",
            name="Tushare API",
            source_type=SourceType.API,
            connection=ConnectionConfig(base_url="https://api.tushare.pro"),
        )
        registry.register_source(config)
        
        rule = CollectionRule(
            rule_id="daily_quote",
            name="Daily Stock Quote",
            source_id="tushare",
            data_type="stock_daily",
            params={"ts_code": "600000.SH"},
            field_mapping={"ts_code": "code", "trade_date": "date"},
        )
        registry.register_rule(rule)
        
        rules = registry.get_rules_for_source("tushare")
        assert len(rules) == 1
        assert rules[0].name == "Daily Stock Quote"


class TestDAGExecutionWithMonitoring:
    """Integration tests for DAGEngine with UnifiedMonitor."""

    @pytest.fixture
    def engine(self):
        return DAGEngine(max_concurrent_tasks=3)

    @pytest.fixture
    def monitor(self):
        return UnifiedMonitor()

    @pytest.mark.asyncio
    async def test_dag_execution_records_metrics(self, engine, monitor):
        dag = (DAGBuilder("metrics_test_dag")
            .add_task("task_1", "Task 1", "test_task", {"value": 10})
            .build())
        
        execution_count = 0
        
        async def test_executor(params, context):
            nonlocal execution_count
            execution_count += 1
            started_at = datetime.now()
            await asyncio.sleep(0.1)
            
            await monitor.record_task_execution(
                task_id="task_1",
                task_name="Task 1",
                task_type="test_task",
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(),
                records_processed=params["value"],
            )
            
            return {"result": params["value"]}
        
        engine.register_executor("test_task", test_executor)
        engine.register_dag(dag)
        
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "completed"
        assert execution_count == 1
        
        stats = monitor.get_task_stats("task_1")
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1

    @pytest.mark.asyncio
    async def test_dag_failure_creates_alerts(self, engine, monitor):
        dag = (DAGBuilder("failing_dag")
            .add_task("failing_task", "Failing Task", "fail_task", {})
            .build())
        
        async def failing_executor(params, context):
            started_at = datetime.now()
            
            await monitor.record_task_execution(
                task_id="failing_task",
                task_name="Failing Task",
                task_type="fail_task",
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(),
                error_message="Intentional test failure",
            )
            
            raise Exception("Intentional test failure")
        
        engine.register_executor("fail_task", failing_executor)
        engine.register_dag(dag)
        
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "failed"
        
        alerts = monitor.get_alerts()
        assert len(alerts) > 0
        assert any(a.alert_type == "task_failure" for a in alerts)

    @pytest.mark.asyncio
    async def test_parallel_execution_with_monitoring(self, engine, monitor):
        dag = (DAGBuilder("parallel_dag")
            .add_task("start", "Start", "test_task", {"id": "start"})
            .add_task("parallel_1", "Parallel 1", "test_task", {"id": "p1"}, depends_on=["start"])
            .add_task("parallel_2", "Parallel 2", "test_task", {"id": "p2"}, depends_on=["start"])
            .add_task("parallel_3", "Parallel 3", "test_task", {"id": "p3"}, depends_on=["start"])
            .add_task("end", "End", "test_task", {"id": "end"}, depends_on=["parallel_1", "parallel_2", "parallel_3"])
            .build())
        
        execution_order = []
        
        async def tracking_executor(params, context):
            execution_order.append(params["id"])
            started_at = datetime.now()
            await asyncio.sleep(0.05)
            
            await monitor.record_task_execution(
                task_id=params["id"],
                task_name=params["id"],
                task_type="test_task",
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(),
            )
            
            return {"id": params["id"]}
        
        engine.register_executor("test_task", tracking_executor)
        engine.register_dag(dag)
        
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "completed"
        assert execution_order[0] == "start"
        assert execution_order[-1] == "end"
        
        summary = monitor.get_summary()
        assert summary["total_task_executions"] == 5


class TestFullPipelineIntegration:
    """Full pipeline integration tests."""

    @pytest.fixture
    def registry(self):
        return SourceRegistry()

    @pytest.fixture
    def monitor(self):
        return UnifiedMonitor()

    @pytest.fixture
    def engine(self):
        return DAGEngine()

    @pytest.mark.asyncio
    async def test_complete_data_collection_workflow(self, registry, monitor, engine):
        config = SourceConfig(
            source_id="test_api",
            name="Test API",
            source_type=SourceType.API,
            connection=ConnectionConfig(base_url="https://api.test.com"),
        )
        registry.register_source(config)
        
        rule = CollectionRule(
            rule_id="collect_stocks",
            name="Collect Stock Data",
            source_id="test_api",
            data_type="stock_list",
            params={"market": "SH"},
        )
        registry.register_rule(rule)
        
        dag = (DAGBuilder("stock_collection_pipeline")
            .description("Complete stock data collection pipeline")
            .add_task("fetch_list", "Fetch Stock List", "fetch_task", {"source": "test_api"}, priority=TaskPriority.HIGH)
            .add_task("validate", "Validate Data", "validate_task", {}, depends_on=["fetch_list"])
            .add_task("transform", "Transform Data", "transform_task", {}, depends_on=["validate"])
            .add_task("store", "Store Data", "store_task", {}, depends_on=["transform"])
            .build())
        
        async def fetch_executor(params, context):
            started_at = datetime.now()
            await asyncio.sleep(0.1)
            
            stocks = [{"code": "600000", "name": "Pudong Development Bank"}]
            
            await monitor.record_collection_result(
                source_id=params["source"],
                collection_type="stock_list",
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(),
                records_collected=len(stocks),
                quality_score=1.0,
            )
            
            return {"stocks": stocks}
        
        async def validate_executor(params, context):
            return {"valid": True, "count": 1}
        
        async def transform_executor(params, context):
            return {"transformed": [{"symbol": "600000", "name": "Pudong Development Bank"}]}
        
        async def store_executor(params, context):
            return {"stored": 1}
        
        engine.register_executor("fetch_task", fetch_executor)
        engine.register_executor("validate_task", validate_executor)
        engine.register_executor("transform_task", transform_executor)
        engine.register_executor("store_task", store_executor)
        
        engine.register_dag(dag)
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "completed"
        assert result["completed_nodes"] == 4
        
        summary = monitor.get_summary()
        assert summary["total_collection_results"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_and_retry(self, registry, monitor, engine):
        attempt_count = 0
        
        async def flaky_executor(params, context):
            nonlocal attempt_count
            attempt_count += 1
            
            started_at = datetime.now()
            
            if attempt_count < 3:
                await monitor.record_task_execution(
                    task_id="flaky_task",
                    task_name="Flaky Task",
                    task_type="flaky",
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(),
                    error_message="Temporary failure",
                    retry_count=attempt_count - 1,
                )
                raise Exception("Temporary failure")
            
            await monitor.record_task_execution(
                task_id="flaky_task",
                task_name="Flaky Task",
                task_type="flaky",
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(),
                retry_count=2,
            )
            
            return {"success": True}
        
        dag = (DAGBuilder("retry_dag")
            .add_task("flaky_task", "Flaky Task", "flaky", {}, max_retries=5)
            .build())
        
        engine.register_executor("flaky", flaky_executor)
        engine.register_dag(dag)
        
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "completed"
        assert attempt_count >= 3
        
        stats = monitor.get_task_stats("flaky_task")
        assert stats["total_executions"] >= 3


class TestAlertRulesIntegration:
    """Integration tests for alert rules."""

    @pytest.fixture
    def monitor(self):
        monitor = UnifiedMonitor()
        
        for rule in [
            AlertRule(
                rule_id="slow_task",
                name="Slow Task Alert",
                metric_type=MetricType.TASK_EXECUTION,
                condition="> threshold",
                threshold=5.0,
                severity=AlertSeverity.WARNING,
                cooldown_minutes=1,
            ),
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate",
                metric_type=MetricType.ERROR_RATE,
                condition="> threshold",
                threshold=0.1,
                severity=AlertSeverity.ERROR,
            ),
        ]:
            monitor.add_rule(rule)
        
        return monitor

    @pytest.mark.asyncio
    async def test_slow_task_triggers_alert(self, monitor):
        await monitor.record_task_execution(
            task_id="slow_task_1",
            task_name="Slow Task",
            task_type="heavy_compute",
            status="completed",
            started_at=datetime.now() - timedelta(seconds=10),
            completed_at=datetime.now(),
        )
        
        await asyncio.sleep(0.1)
        
        alerts = monitor.get_alerts()
        assert len(alerts) > 0

    @pytest.mark.asyncio
    async def test_alert_cooldown(self, monitor):
        await monitor.record_task_execution(
            task_id="slow_1",
            task_name="Slow Task 1",
            task_type="test",
            status="completed",
            started_at=datetime.now() - timedelta(seconds=10),
            completed_at=datetime.now(),
        )
        
        await asyncio.sleep(0.1)
        
        first_alerts = monitor.get_alerts()
        
        await monitor.record_task_execution(
            task_id="slow_2",
            task_name="Slow Task 2",
            task_type="test",
            status="completed",
            started_at=datetime.now() - timedelta(seconds=10),
            completed_at=datetime.now(),
        )
        
        await asyncio.sleep(0.1)
        
        second_alerts = monitor.get_alerts()
        
        assert len(second_alerts) >= len(first_alerts)


class TestSingletonInstances:
    """Test singleton instances work correctly."""

    def test_source_registry_singleton(self):
        registry1 = get_source_registry()
        registry2 = get_source_registry()
        
        assert registry1 is registry2

    def test_unified_monitor_singleton(self):
        monitor1 = get_unified_monitor()
        monitor2 = get_unified_monitor()
        
        assert monitor1 is monitor2

    def test_singleton_state_persistence(self):
        registry = get_source_registry()
        
        config = SourceConfig(
            source_id="singleton_test",
            name="Singleton Test",
            source_type=SourceType.API,
        )
        
        registry.register_source(config)
        
        same_registry = get_source_registry()
        retrieved = same_registry.get_source("singleton_test")
        
        assert retrieved is not None
        assert retrieved.name == "Singleton Test"
