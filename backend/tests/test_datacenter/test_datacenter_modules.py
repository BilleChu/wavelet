"""
Tests for Data Center Modules.

Tests for SourceRegistry, UnifiedMonitor, and DAGEngine.
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
    AuthConfig,
    get_source_registry,
)
from openfinance.datacenter.observability.monitoring.unified_monitor import (
    UnifiedMonitor,
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertRule,
    Metric,
    MetricType,
    TaskExecutionRecord,
    CollectionResultRecord,
    get_unified_monitor,
)
from openfinance.datacenter.task.dag_engine import (
    DAGEngine,
    DAG,
    DAGNode,
    DAGEdge,
    DAGBuilder,
    DAGExecutionLog,
    TaskStatus,
    NodeType,
    TaskPriority,
)


class TestSourceRegistry:
    """Tests for SourceRegistry class."""

    @pytest.fixture
    def registry(self):
        return SourceRegistry()

    @pytest.fixture
    def sample_config(self):
        return SourceConfig(
            source_id="test_source_1",
            name="Test API Source",
            source_type=SourceType.API,
            connection=ConnectionConfig(base_url="https://api.example.com"),
        )

    def test_register_source(self, registry, sample_config):
        registry.register_source(sample_config)
        
        config = registry.get_source("test_source_1")
        assert config is not None
        assert config.name == "Test API Source"
        assert config.source_type == SourceType.API

    def test_get_source_not_found(self, registry):
        config = registry.get_source("nonexistent")
        assert config is None

    def test_unregister_source(self, registry, sample_config):
        registry.register_source(sample_config)
        
        result = registry.unregister_source("test_source_1")
        assert result is True
        
        config = registry.get_source("test_source_1")
        assert config is None

    def test_unregister_source_not_found(self, registry):
        result = registry.unregister_source("nonexistent")
        assert result is False

    def test_get_sources(self, registry):
        config1 = SourceConfig(
            source_id="source_1",
            name="Source 1",
            source_type=SourceType.API,
        )
        config2 = SourceConfig(
            source_id="source_2",
            name="Source 2",
            source_type=SourceType.DATABASE,
        )
        config3 = SourceConfig(
            source_id="source_3",
            name="Source 3",
            source_type=SourceType.API,
            enabled=False,
        )
        
        registry.register_source(config1)
        registry.register_source(config2)
        registry.register_source(config3)
        
        all_sources = registry.get_sources()
        assert len(all_sources) == 3
        
        api_sources = registry.get_sources(source_type=SourceType.API)
        assert len(api_sources) == 2
        
        enabled_sources = registry.get_sources(enabled_only=True)
        assert len(enabled_sources) == 2

    def test_collection_rule_crud(self, registry):
        rule = CollectionRule(
            rule_id="rule_1",
            name="Test Rule",
            source_id="test_source",
            data_type="stock_quote",
            params={"symbol": "600000"},
        )
        
        registry.register_rule(rule)
        
        retrieved = registry.get_rule("rule_1")
        assert retrieved is not None
        assert retrieved.name == "Test Rule"
        
        rules = registry.get_rules_for_source("test_source")
        assert len(rules) == 1
        
        result = registry.unregister_rule("rule_1")
        assert result is True
        
        retrieved = registry.get_rule("rule_1")
        assert retrieved is None

    def test_get_source_registry_singleton(self):
        registry1 = get_source_registry()
        registry2 = get_source_registry()
        assert registry1 is registry2


class TestSourceConfig:
    """Tests for SourceConfig model."""

    def test_source_config_creation(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            source_type=SourceType.API,
            connection=ConnectionConfig(base_url="https://api.example.com"),
        )
        assert config.source_id == "test"
        assert config.enabled is True
        assert config.status == SourceStatus.UNKNOWN

    def test_source_config_with_connection_params(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            connection=ConnectionConfig(
                base_url="https://api.example.com",
                timeout=60.0,
            ),
        )
        assert config.connection.base_url == "https://api.example.com"
        assert config.connection.timeout == 60.0


class TestCollectionRule:
    """Tests for CollectionRule model."""

    def test_collection_rule_creation(self):
        rule = CollectionRule(
            rule_id="rule_1",
            name="Stock Quote Collection",
            source_id="tushare",
            data_type="stock_quote",
            params={"ts_code": "600000.SH"},
            field_mapping={"ts_code": "code", "trade_date": "date"},
        )
        assert rule.rule_id == "rule_1"
        assert rule.enabled is True
        assert len(rule.field_mapping) == 2


class TestUnifiedMonitor:
    """Tests for UnifiedMonitor class."""

    @pytest.fixture
    def monitor(self):
        return UnifiedMonitor()

    @pytest.mark.asyncio
    async def test_record_task_execution_success(self, monitor):
        now = datetime.now()
        record = await monitor.record_task_execution(
            task_id="task_1",
            task_name="Test Task",
            task_type="collection",
            status="completed",
            started_at=now,
            completed_at=now + timedelta(seconds=10),
            records_processed=100,
        )
        
        assert record.task_id == "task_1"
        assert record.status == "completed"
        assert record.duration_seconds == 10.0
        assert record.records_processed == 100

    @pytest.mark.asyncio
    async def test_record_task_execution_failure(self, monitor):
        now = datetime.now()
        record = await monitor.record_task_execution(
            task_id="task_2",
            task_name="Failing Task",
            task_type="collection",
            status="failed",
            started_at=now,
            completed_at=now + timedelta(seconds=5),
            error_message="Connection timeout",
            retry_count=2,
        )
        
        assert record.status == "failed"
        assert record.error_message == "Connection timeout"
        assert record.retry_count == 2
        
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_type == "task_failure"
        assert alerts[0].severity == AlertSeverity.ERROR

    @pytest.mark.asyncio
    async def test_record_collection_result(self, monitor):
        now = datetime.now()
        record = await monitor.record_collection_result(
            source_id="tushare",
            collection_type="stock_daily",
            status="completed",
            started_at=now,
            completed_at=now + timedelta(seconds=30),
            records_collected=5000,
            records_processed=5000,
            records_stored=5000,
            quality_score=0.95,
        )
        
        assert record.source_id == "tushare"
        assert record.records_collected == 5000
        assert record.quality_score == 0.95

    @pytest.mark.asyncio
    async def test_low_quality_triggers_alert(self, monitor):
        now = datetime.now()
        await monitor.record_collection_result(
            source_id="test_source",
            collection_type="test",
            status="completed",
            started_at=now,
            quality_score=0.85,
        )
        
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0].alert_type == "data_quality"

    @pytest.mark.asyncio
    async def test_create_alert(self, monitor):
        alert = await monitor.create_alert(
            alert_type="test_alert",
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test",
            source="test_source",
        )
        
        assert alert is not None
        assert alert.alert_type == "test_alert"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_alert_deduplication(self, monitor):
        alert1 = await monitor.create_alert(
            alert_type="dup_test",
            severity=AlertSeverity.WARNING,
            title="Duplicate Test",
            message="Test",
            source="source_1",
        )
        
        alert2 = await monitor.create_alert(
            alert_type="dup_test",
            severity=AlertSeverity.WARNING,
            title="Duplicate Test",
            message="Test",
            source="source_1",
        )
        
        assert alert1 is not None
        assert alert2 is None

    def test_acknowledge_alert(self, monitor):
        monitor._alerts.append(Alert(
            alert_id="alert_1",
            alert_type="test",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            source="test",
        ))
        
        result = monitor.acknowledge_alert("alert_1", "user_1")
        assert result is True
        
        alerts = monitor.get_alerts()
        assert alerts[0].status == AlertStatus.ACKNOWLEDGED
        assert alerts[0].acknowledged_by == "user_1"

    def test_resolve_alert(self, monitor):
        monitor._alerts.append(Alert(
            alert_id="alert_2",
            alert_type="test",
            severity=AlertSeverity.WARNING,
            title="Test",
            message="Test",
            source="test",
        ))
        
        result = monitor.resolve_alert("alert_2")
        assert result is True
        
        alerts = monitor.get_alerts()
        assert alerts[0].status == AlertStatus.RESOLVED

    def test_get_alerts_with_filtering(self, monitor):
        monitor._alerts = [
            Alert(alert_id=f"alert_{i}", alert_type="test", severity=s, title=f"Alert {i}", message="Test", source=f"source_{i % 2}")
            for i, s in enumerate([AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.WARNING])
        ]
        
        all_alerts = monitor.get_alerts()
        assert len(all_alerts) == 3
        
        error_alerts = monitor.get_alerts(severity=AlertSeverity.ERROR)
        assert len(error_alerts) == 1
        
        source_0_alerts = monitor.get_alerts(source="source_0")
        assert len(source_0_alerts) == 2

    def test_get_metrics(self, monitor):
        monitor._metrics[MetricType.TASK_EXECUTION] = [
            Metric(
                metric_id=f"metric_{i}",
                metric_type=MetricType.TASK_EXECUTION,
                name=f"task.duration.{i}",
                value=float(i * 10),
                source=f"task_{i}",
            )
            for i in range(5)
        ]
        
        metrics = monitor.get_metrics(metric_type=MetricType.TASK_EXECUTION)
        assert len(metrics) == 5
        
        metrics = monitor.get_metrics(limit=3)
        assert len(metrics) == 3

    def test_get_task_stats(self, monitor):
        now = datetime.now()
        monitor._task_executions["task_1"] = [
            TaskExecutionRecord(
                task_id="task_1",
                task_name="Test",
                task_type="collection",
                status="completed",
                started_at=now,
                completed_at=now + timedelta(seconds=i * 10),
                duration_seconds=i * 10,
                records_processed=100 * i,
            )
            for i in range(1, 4)
        ]
        monitor._task_executions["task_1"].append(
            TaskExecutionRecord(
                task_id="task_1",
                task_name="Test",
                task_type="collection",
                status="failed",
                started_at=now,
                completed_at=now + timedelta(seconds=5),
                duration_seconds=5,
                records_processed=0,
            )
        )
        
        stats = monitor.get_task_stats("task_1")
        assert stats["total_executions"] == 4
        assert stats["successful_executions"] == 3
        assert stats["failed_executions"] == 1
        assert stats["success_rate"] == 0.75

    def test_get_summary(self, monitor):
        monitor._task_executions["task_1"] = [MagicMock()]
        monitor._task_executions["task_2"] = [MagicMock(), MagicMock()]
        monitor._collection_results["source_1"] = [MagicMock()]
        monitor._alerts = [
            Alert(alert_id="a1", alert_type="t1", severity=AlertSeverity.WARNING, title="A1", message="M", source="s1", status=AlertStatus.ACTIVE),
            Alert(alert_id="a2", alert_type="t2", severity=AlertSeverity.ERROR, title="A2", message="M", source="s2", status=AlertStatus.RESOLVED),
        ]
        
        summary = monitor.get_summary()
        assert summary["total_task_executions"] == 3
        assert summary["total_collection_results"] == 1
        assert summary["active_alerts"] == 1
        assert summary["unique_tasks"] == 2

    def test_alert_rule_evaluation(self, monitor):
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            metric_type=MetricType.TASK_EXECUTION,
            condition="> threshold",
            threshold=100.0,
            severity=AlertSeverity.WARNING,
        )
        monitor.add_rule(rule)
        
        assert monitor._evaluate_condition(rule, MagicMock(value=150.0)) is True
        assert monitor._evaluate_condition(rule, MagicMock(value=50.0)) is False

    def test_add_alert_handler(self, monitor):
        handler_called = []
        
        def handler(alert):
            handler_called.append(alert)
        
        monitor.add_alert_handler(handler)
        
        asyncio.run(monitor.create_alert(
            alert_type="handler_test",
            severity=AlertSeverity.INFO,
            title="Handler Test",
            message="Test",
            source="test",
        ))
        
        assert len(handler_called) == 1

    def test_get_unified_monitor_singleton(self):
        m1 = get_unified_monitor()
        m2 = get_unified_monitor()
        assert m1 is m2


class TestDAG:
    """Tests for DAG class."""

    def test_dag_creation(self):
        dag = DAG(name="test_dag", description="Test DAG")
        assert dag.name == "test_dag"
        assert dag.status == TaskStatus.PENDING
        assert len(dag.nodes) == 0

    def test_add_node(self):
        dag = DAG(name="test")
        node = DAGNode(node_id="node_1", name="Task 1", task_type="test_task")
        
        dag.add_node(node)
        
        assert "node_1" in dag.nodes
        assert dag.nodes["node_1"].name == "Task 1"

    def test_add_edge(self):
        dag = DAG(name="test")
        node1 = DAGNode(node_id="node_1", name="Task 1", task_type="test")
        node2 = DAGNode(node_id="node_2", name="Task 2", task_type="test", dependencies=["node_1"])
        
        dag.add_node(node1)
        dag.add_node(node2)
        edge = dag.add_edge("node_1", "node_2")
        
        assert len(dag.edges) == 1
        assert edge.source_id == "node_1"
        assert edge.target_id == "node_2"
        assert "node_2" in dag.nodes["node_1"].dependents

    def test_validate_no_cycle(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test"))
        dag.add_node(DAGNode(node_id="b", name="B", task_type="test", dependencies=["a"]))
        dag.add_node(DAGNode(node_id="c", name="C", task_type="test", dependencies=["b"]))
        
        is_valid, errors = dag.validate()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_with_cycle(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test", dependencies=["c"]))
        dag.add_node(DAGNode(node_id="b", name="B", task_type="test", dependencies=["a"]))
        dag.add_node(DAGNode(node_id="c", name="C", task_type="test", dependencies=["b"]))
        
        is_valid, errors = dag.validate()
        assert is_valid is False
        assert "cycle" in str(errors).lower()

    def test_validate_missing_dependency(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test", dependencies=["nonexistent"]))
        
        is_valid, errors = dag.validate()
        assert is_valid is False
        assert any("missing" in e.lower() for e in errors)

    def test_get_execution_order(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test"))
        dag.add_node(DAGNode(node_id="b", name="B", task_type="test"))
        dag.add_node(DAGNode(node_id="c", name="C", task_type="test", dependencies=["a", "b"]))
        
        order = dag.get_execution_order()
        
        assert "a" in order
        assert "b" in order
        assert "c" in order
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("c")

    def test_get_ready_nodes(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test"))
        dag.add_node(DAGNode(node_id="b", name="B", task_type="test", dependencies=["a"]))
        dag.add_node(DAGNode(node_id="c", name="C", task_type="test", dependencies=["a"]))
        
        ready = dag.get_ready_nodes(set(), set())
        assert ready == ["a"]
        
        dag.nodes["a"].status = TaskStatus.COMPLETED
        ready = dag.get_ready_nodes({"a"}, set())
        assert set(ready) == {"b", "c"}

    def test_to_dict(self):
        dag = DAG(name="test", description="Test DAG")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test"))
        
        result = dag.to_dict()
        
        assert result["name"] == "test"
        assert result["description"] == "Test DAG"
        assert len(result["nodes"]) == 1

    def test_to_canvas_format(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test"))
        dag.add_node(DAGNode(node_id="b", name="B", task_type="test", dependencies=["a"]))
        dag.add_edge("a", "b")
        
        canvas = dag.to_canvas_format()
        
        assert "nodes" in canvas
        assert "edges" in canvas
        assert len(canvas["nodes"]) == 2
        assert len(canvas["edges"]) == 1
        assert canvas["metadata"]["totalNodes"] == 2

    def test_to_mermaid(self):
        dag = DAG(name="test")
        dag.add_node(DAGNode(node_id="a", name="Task A", task_type="test"))
        dag.add_node(DAGNode(node_id="b", name="Task B", task_type="test", dependencies=["a"]))
        dag.add_edge("a", "b", "next")
        
        mermaid = dag.to_mermaid()
        
        assert "graph TD" in mermaid
        assert "a[\"Task A\"]" in mermaid
        assert "b[\"Task B\"]" in mermaid
        assert "a -->|next| b" in mermaid


class TestDAGNode:
    """Tests for DAGNode class."""

    def test_node_creation(self):
        node = DAGNode(
            node_id="test_node",
            name="Test Node",
            node_type=NodeType.TASK,
            task_type="data_collection",
            task_params={"source": "tushare"},
        )
        
        assert node.node_id == "test_node"
        assert node.status == TaskStatus.PENDING
        assert node.priority == TaskPriority.NORMAL

    def test_is_ready(self):
        node = DAGNode(
            node_id="test",
            name="Test",
            dependencies=["dep1", "dep2"],
        )
        
        assert node.is_ready({"dep1"}) is False
        assert node.is_ready({"dep1", "dep2"}) is True

    def test_to_dict(self):
        node = DAGNode(node_id="test", name="Test", task_type="test_task")
        result = node.to_dict()
        
        assert result["id"] == "test"
        assert result["name"] == "Test"
        assert result["type"] == "task"
        assert result["taskType"] == "test_task"

    def test_to_canvas_node(self):
        node = DAGNode(
            node_id="test",
            name="Test Node",
            task_type="collection",
            status=TaskStatus.RUNNING,
            progress=0.5,
        )
        node.position = {"x": 100, "y": 200}
        
        result = node.to_canvas_node()
        
        assert result["id"] == "test"
        assert result["type"] == "taskNode"
        assert result["position"] == {"x": 100, "y": 200}
        assert result["data"]["label"] == "Test Node"
        assert result["data"]["status"] == "running"
        assert result["data"]["progress"] == 0.5


class TestDAGEdge:
    """Tests for DAGEdge class."""

    def test_edge_creation(self):
        edge = DAGEdge(
            edge_id="edge_1",
            source_id="a",
            target_id="b",
            label="next",
            condition="success",
        )
        
        assert edge.edge_id == "edge_1"
        assert edge.source_id == "a"
        assert edge.target_id == "b"

    def test_to_canvas_edge(self):
        edge = DAGEdge(edge_id="e1", source_id="a", target_id="b", label="flow")
        result = edge.to_canvas_edge()
        
        assert result["id"] == "e1"
        assert result["source"] == "a"
        assert result["target"] == "b"
        assert result["animated"] is True


class TestDAGEngine:
    """Tests for DAGEngine class."""

    @pytest.fixture
    def engine(self):
        return DAGEngine(max_concurrent_tasks=3)

    @pytest.fixture
    def simple_dag(self):
        return (DAGBuilder("simple_dag")
            .description("A simple test DAG")
            .add_task("task_a", "Task A", "test_task", {"value": 1})
            .add_task("task_b", "Task B", "test_task", {"value": 2}, depends_on=["task_a"])
            .add_task("task_c", "Task C", "test_task", {"value": 3}, depends_on=["task_a"])
            .build())

    def test_register_dag(self, engine, simple_dag):
        engine.register_dag(simple_dag)
        
        assert simple_dag.dag_id in engine._dags
        assert engine.get_dag(simple_dag.dag_id) is simple_dag

    def test_register_invalid_dag(self, engine):
        dag = DAG(name="invalid")
        dag.add_node(DAGNode(node_id="a", name="A", task_type="test", dependencies=["nonexistent"]))
        
        with pytest.raises(ValueError, match="Invalid DAG"):
            engine.register_dag(dag)

    def test_register_executor(self, engine):
        async def test_executor(params, context):
            return {"result": params["value"] * 2}
        
        engine.register_executor("test_task", test_executor)
        assert "test_task" in engine._executors

    @pytest.mark.asyncio
    async def test_execute_dag_success(self, engine, simple_dag):
        async def test_executor(params, context):
            await asyncio.sleep(0.1)
            return {"result": params["value"] * 2}
        
        engine.register_executor("test_task", test_executor)
        engine.register_dag(simple_dag)
        
        result = await engine.execute_dag(simple_dag.dag_id)
        
        assert result["status"] == "completed"
        assert result["completed_nodes"] == 3
        assert result["failed_nodes"] == 0
        assert result["total_nodes"] == 3

    @pytest.mark.asyncio
    async def test_execute_dag_not_found(self, engine):
        with pytest.raises(ValueError, match="DAG not found"):
            await engine.execute_dag("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_dag_with_failure(self, engine):
        dag = (DAGBuilder("failing_dag")
            .add_task("task_a", "Task A", "test_task", {"value": 1})
            .add_task("task_b", "Task B", "failing_task", {"value": 2}, depends_on=["task_a"])
            .build())
        
        async def test_executor(params, context):
            return {"result": params["value"]}
        
        async def failing_executor(params, context):
            raise Exception("Intentional failure")
        
        engine.register_executor("test_task", test_executor)
        engine.register_executor("failing_task", failing_executor)
        engine.register_dag(dag)
        
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "failed"
        assert result["failed_nodes"] > 0

    @pytest.mark.asyncio
    async def test_execute_dag_with_retry(self, engine):
        call_count = 0
        
        async def flaky_executor(params, context):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"result": "success"}
        
        dag = (DAGBuilder("retry_dag")
            .add_task("task_a", "Task A", "flaky_task", {}, max_retries=3)
            .build())
        
        engine.register_executor("flaky_task", flaky_executor)
        engine.register_dag(dag)
        
        result = await engine.execute_dag(dag.dag_id)
        
        assert result["status"] == "completed"
        assert call_count >= 3

    def test_get_dag_status(self, engine, simple_dag):
        engine.register_dag(simple_dag)
        
        status = engine.get_dag_status(simple_dag.dag_id)
        
        assert status["name"] == "simple_dag"
        assert status["totalTasks"] == 3
        assert status["status"] == "pending"

    def test_get_dag_canvas(self, engine, simple_dag):
        engine.register_dag(simple_dag)
        
        canvas = engine.get_dag_canvas(simple_dag.dag_id)
        
        assert "nodes" in canvas
        assert "edges" in canvas
        assert len(canvas["nodes"]) == 3

    def test_get_logs(self, engine, simple_dag):
        engine.register_dag(simple_dag)
        engine._log(simple_dag.dag_id, "task_a", "test_event", TaskStatus.RUNNING, "Test message")
        
        logs = engine.get_logs(dag_id=simple_dag.dag_id)
        
        assert len(logs) == 1
        assert logs[0].event == "test_event"

    def test_list_dags(self, engine):
        dag1 = DAGBuilder("dag1").add_task("a", "A", "test").build()
        dag2 = DAGBuilder("dag2").add_task("b", "B", "test").build()
        
        engine.register_dag(dag1)
        engine.register_dag(dag2)
        
        dags = engine.list_dags()
        
        assert len(dags) == 2
        assert any(d["name"] == "dag1" for d in dags)
        assert any(d["name"] == "dag2" for d in dags)


class TestDAGBuilder:
    """Tests for DAGBuilder class."""

    def test_build_simple_dag(self):
        dag = (DAGBuilder("test_dag")
            .description("Test DAG")
            .add_task("extract", "Extract Data", "extract_task", {"source": "db"})
            .add_task("transform", "Transform Data", "transform_task", {"type": "clean"}, depends_on=["extract"])
            .add_task("load", "Load Data", "load_task", {"target": "warehouse"}, depends_on=["transform"])
            .build())
        
        assert dag.name == "test_dag"
        assert dag.description == "Test DAG"
        assert len(dag.nodes) == 3
        assert len(dag.edges) == 2

    def test_build_with_priority(self):
        dag = (DAGBuilder("priority_dag")
            .add_task("low", "Low Priority", "test", priority=TaskPriority.LOW)
            .add_task("high", "High Priority", "test", priority=TaskPriority.HIGH)
            .build())
        
        assert dag.nodes["low"].priority == TaskPriority.LOW
        assert dag.nodes["high"].priority == TaskPriority.HIGH

    def test_build_with_custom_dag_id(self):
        dag = (DAGBuilder("test")
            .add_task("a", "A", "test")
            .build(dag_id="custom_dag_id"))
        
        assert dag.dag_id == "custom_dag_id"

    def test_build_with_condition(self):
        dag = (DAGBuilder("conditional_dag")
            .add_task("start", "Start", "test")
            .add_condition("check", "Check Condition", "value > 0", "yes_path", "no_path")
            .add_task("yes_path", "Yes Path", "test")
            .add_task("no_path", "No Path", "test")
            .build())
        
        assert len(dag.nodes) == 4
        assert dag.nodes["check"].node_type == NodeType.CONDITION


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"

    def test_status_comparison(self):
        assert TaskStatus.PENDING != TaskStatus.RUNNING
        assert TaskStatus.COMPLETED == TaskStatus.COMPLETED


class TestNodeType:
    """Tests for NodeType enum."""

    def test_node_type_values(self):
        assert NodeType.TASK.value == "task"
        assert NodeType.CONDITION.value == "condition"
        assert NodeType.PARALLEL.value == "parallel"
        assert NodeType.SEQUENCE.value == "sequence"


class TestTaskPriority:
    """Tests for TaskPriority enum."""

    def test_priority_ordering(self):
        assert TaskPriority.CRITICAL < TaskPriority.HIGH
        assert TaskPriority.HIGH < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.LOW
        assert TaskPriority.LOW < TaskPriority.BACKGROUND
