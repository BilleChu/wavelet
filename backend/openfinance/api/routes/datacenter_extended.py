"""
Extended Data Center API Routes.

Provides additional endpoints for:
- Task chain management
- Canvas visualization data
- Monitoring and alerts
- Company preloading
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.datacenter.task.chain_engine import (
    TaskChainEngine,
    TaskChain,
    ChainNode,
    ChainStatus,
    NodeType,
    create_default_chain,
)
from openfinance.datacenter.task.monitoring import (
    TaskMonitor,
    MonitoringConfig,
    AlertSeverity,
    AlertStatus,
    MetricType,
    create_default_alert_rules,
)
from openfinance.datacenter.task.enhanced_scheduler import (
    EnhancedScheduler,
    ScheduleConfig,
    TaskPriority,
    ScheduleType,
    create_default_scheduled_tasks,
)
from openfinance.datacenter.collector.implementations.company_preloader import CompanyPreloader
from openfinance.datacenter.collector.implementations.stock_batch_collector import StockBatchCollector, DataType

logger = get_logger(__name__)

router = APIRouter(prefix="/datacenter", tags=["datacenter-extended"])

_chain_engine: TaskChainEngine | None = None
_monitor: TaskMonitor | None = None
_scheduler: EnhancedScheduler | None = None


def get_chain_engine() -> TaskChainEngine:
    """Get or create the chain engine singleton."""
    global _chain_engine
    if _chain_engine is None:
        _chain_engine = TaskChainEngine()
    return _chain_engine


def get_monitor() -> TaskMonitor:
    """Get or create the monitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = TaskMonitor()
        for rule in create_default_alert_rules():
            _monitor.add_rule(rule)
    return _monitor


def get_scheduler() -> EnhancedScheduler:
    """Get or create the scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = EnhancedScheduler()
        for task in create_default_scheduled_tasks():
            _scheduler.register_task(task)
    return _scheduler


class CreateChainRequest(BaseModel):
    """Request to create a new task chain."""
    
    name: str = Field(..., description="Chain name")
    description: str = Field(default="", description="Chain description")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Chain nodes")
    edges: list[dict[str, str]] = Field(default_factory=list, description="Chain edges")


class ExecuteChainRequest(BaseModel):
    """Request to execute a chain."""
    
    chain_id: str = Field(..., description="Chain ID to execute")
    stop_on_failure: bool = Field(default=True, description="Stop on first failure")


class CreateAlertRuleRequest(BaseModel):
    """Request to create an alert rule."""
    
    name: str = Field(..., description="Rule name")
    metric_type: str = Field(..., description="Metric type")
    condition: str = Field(..., description="Condition expression")
    severity: str = Field(default="warning", description="Alert severity")
    cooldown_minutes: int = Field(default=5, description="Cooldown between alerts")


class CreateScheduleRequest(BaseModel):
    """Request to create a scheduled task."""
    
    task_name: str = Field(..., description="Task name")
    task_type: str = Field(..., description="Task type")
    schedule_type: str = Field(default="daily", description="Schedule type")
    daily_time: str | None = Field(default="09:00", description="Daily execution time")
    interval_seconds: int | None = Field(default=None, description="Interval in seconds")
    priority: str = Field(default="NORMAL", description="Task priority")
    enabled: bool = Field(default=True, description="Whether task is enabled")


# ==================== Chain Management ====================

@router.get("/chains")
async def list_chains() -> dict[str, Any]:
    """List all task chains."""
    engine = get_chain_engine()
    chains = engine.list_chains()
    
    return {
        "chains": chains,
        "total": len(chains),
    }


@router.post("/chains")
async def create_chain(request: CreateChainRequest) -> dict[str, Any]:
    """Create a new task chain."""
    engine = get_chain_engine()
    
    chain = TaskChain(
        name=request.name,
        description=request.description,
    )
    
    for node_data in request.nodes:
        node = ChainNode(
            node_id=node_data.get("node_id", ""),
            name=node_data.get("name", ""),
            node_type=NodeType(node_data.get("node_type", "task")),
            task_type=node_data.get("task_type"),
            task_params=node_data.get("params", {}),
        )
        engine.add_node(chain, node)
    
    for edge_data in request.edges:
        engine.add_edge(
            chain,
            edge_data.get("source_id", ""),
            edge_data.get("target_id", ""),
            label=edge_data.get("label", ""),
        )
    
    return chain.to_dict()


@router.get("/chains/{chain_id}")
async def get_chain(chain_id: str) -> dict[str, Any]:
    """Get chain details."""
    engine = get_chain_engine()
    chain = engine.get_chain(chain_id)
    
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain not found: {chain_id}")
    
    return chain.to_dict()


@router.post("/chains/{chain_id}/execute")
async def execute_chain(chain_id: str) -> dict[str, Any]:
    """Execute a task chain."""
    engine = get_chain_engine()
    chain = engine.get_chain(chain_id)
    
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain not found: {chain_id}")
    
    result = await engine.execute_chain(chain)
    
    return {
        "chain_id": result.chain_id,
        "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
        "nodes_executed": result.nodes_executed,
        "nodes_succeeded": result.nodes_succeeded,
        "nodes_failed": result.nodes_failed,
        "total_duration_ms": result.total_duration_ms,
        "errors": result.errors,
    }


@router.post("/chains/default")
async def create_default_task_chain() -> dict[str, Any]:
    """Create the default daily data collection chain."""
    chain = create_default_chain()
    engine = get_chain_engine()
    engine._chains[chain.chain_id] = chain
    
    return chain.to_dict()


@router.delete("/chains/{chain_id}")
async def cancel_chain(chain_id: str) -> dict[str, Any]:
    """Cancel a running chain."""
    engine = get_chain_engine()
    success = await engine.cancel_chain(chain_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Chain not found: {chain_id}")
    
    return {"success": True, "message": f"Chain {chain_id} cancelled"}


# ==================== Canvas Data ====================

@router.get("/canvas/data")
async def get_canvas_data() -> dict[str, Any]:
    """Get data for Canvas visualization."""
    engine = get_chain_engine()
    monitor = get_monitor()
    
    chains = engine.list_chains()
    
    nodes = []
    edges = []
    
    for chain_data in chains:
        chain_id = chain_data.get("chain_id", "")
        chain_nodes = chain_data.get("nodes", {})
        chain_edges = chain_data.get("edges", [])
        
        for node_id, node in chain_nodes.items():
            nodes.append({
                "id": f"{chain_id}_{node_id}",
                "type": "taskNode",
                "data": {
                    "label": node.get("name", ""),
                    "taskType": node.get("task_type", ""),
                    "status": node.get("status", "pending"),
                    "chainId": chain_id,
                },
                "position": {"x": 0, "y": 0},
            })
        
        for edge in chain_edges:
            edges.append({
                "id": edge.get("edge_id", ""),
                "source": f"{chain_id}_{edge.get('source_id', '')}",
                "target": f"{chain_id}_{edge.get('target_id', '')}",
                "animated": True,
                "label": edge.get("label", ""),
            })
    
    summary = monitor.get_summary()
    
    return {
        "nodes": nodes,
        "edges": edges,
        "chains": chains,
        "summary": summary,
    }


@router.get("/canvas/chain/{chain_id}")
async def get_chain_canvas_data(chain_id: str) -> dict[str, Any]:
    """Get Canvas data for a specific chain."""
    engine = get_chain_engine()
    chain = engine.get_chain(chain_id)
    
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain not found: {chain_id}")
    
    chain_dict = chain.to_dict()
    
    nodes = []
    edges = []
    
    for node_id, node in chain_dict.get("nodes", {}).items():
        nodes.append({
            "id": node_id,
            "type": "taskNode",
            "data": {
                "label": node.get("name", ""),
                "taskType": node.get("task_type", ""),
                "status": node.get("status", "pending"),
            },
            "position": {"x": 0, "y": 0},
        })
    
    for edge in chain_dict.get("edges", []):
        edges.append({
            "id": edge.get("edge_id", ""),
            "source": edge.get("source_id", ""),
            "target": edge.get("target_id", ""),
            "animated": True,
            "label": edge.get("label", ""),
        })
    
    data_targets = chain_dict.get("data_targets", [])
    
    return {
        "chain_id": chain_id,
        "name": chain.name,
        "nodes": nodes,
        "edges": edges,
        "data_targets": data_targets,
        "status": chain.status.value if hasattr(chain.status, 'value') else str(chain.status),
    }


# ==================== Monitoring ====================

@router.get("/monitoring/summary")
async def get_monitoring_summary() -> dict[str, Any]:
    """Get monitoring summary."""
    monitor = get_monitor()
    return monitor.get_summary()


@router.get("/monitoring/metrics")
async def get_metrics(
    metric_type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Get metrics."""
    monitor = get_monitor()
    
    m_type = MetricType(metric_type) if metric_type else None
    metrics = monitor.get_metrics(metric_type=m_type, limit=limit)
    
    return {
        "metrics": metrics,
        "total": len(metrics),
    }


@router.get("/monitoring/alerts")
async def get_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Get alerts."""
    monitor = get_monitor()
    
    a_status = AlertStatus(status) if status else None
    a_severity = AlertSeverity(severity) if severity else None
    
    alerts = monitor.get_alerts(status=a_status, severity=a_severity, limit=limit)
    
    return {
        "alerts": [a.model_dump() for a in alerts],
        "total": len(alerts),
    }


@router.put("/monitoring/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str) -> dict[str, Any]:
    """Resolve an alert."""
    monitor = get_monitor()
    success = monitor.resolve_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    
    return {"success": True, "message": f"Alert {alert_id} resolved"}


@router.put("/monitoring/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str) -> dict[str, Any]:
    """Acknowledge an alert."""
    monitor = get_monitor()
    success = monitor.acknowledge_alert(alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    
    return {"success": True, "message": f"Alert {alert_id} acknowledged"}


@router.post("/monitoring/rules")
async def create_alert_rule(request: CreateAlertRuleRequest) -> dict[str, Any]:
    """Create an alert rule."""
    from openfinance.datacenter.task.monitoring import AlertRule
    
    monitor = get_monitor()
    
    rule = AlertRule(
        name=request.name,
        metric_type=MetricType(request.metric_type),
        condition=request.condition,
        severity=AlertSeverity(request.severity),
        cooldown_minutes=request.cooldown_minutes,
    )
    
    monitor.add_rule(rule)
    
    return {
        "success": True,
        "rule_id": rule.rule_id,
        "message": "Alert rule created",
    }


@router.get("/monitoring/task/{task_id}")
async def get_task_monitoring(task_id: str) -> dict[str, Any]:
    """Get monitoring data for a specific task."""
    monitor = get_monitor()
    return monitor.get_task_stats(task_id)


# ==================== Scheduler ====================

@router.get("/scheduler/tasks")
async def list_scheduled_tasks(enabled_only: bool = False) -> dict[str, Any]:
    """List scheduled tasks."""
    scheduler = get_scheduler()
    tasks = scheduler.list_tasks(enabled_only=enabled_only)
    
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "task_name": t.task_name,
                "task_type": t.task_type,
                "schedule_type": t.schedule_type if isinstance(t.schedule_type, str) else (t.schedule_type.value if hasattr(t.schedule_type, 'value') else str(t.schedule_type)),
                "daily_time": t.daily_time,
                "enabled": t.enabled,
                "priority": TaskPriority(t.priority).name if isinstance(t.priority, int) else (t.priority.name if hasattr(t.priority, 'name') else str(t.priority)),
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "last_status": t.last_status,
                "next_run": t.next_run.isoformat() if t.next_run else None,
                "consecutive_failures": t.consecutive_failures,
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


@router.post("/scheduler/tasks")
async def create_scheduled_task(request: CreateScheduleRequest) -> dict[str, Any]:
    """Create a scheduled task."""
    scheduler = get_scheduler()
    
    priority_map = {
        "CRITICAL": TaskPriority.CRITICAL,
        "HIGH": TaskPriority.HIGH,
        "NORMAL": TaskPriority.NORMAL,
        "LOW": TaskPriority.LOW,
        "BACKGROUND": TaskPriority.BACKGROUND,
    }
    
    config = ScheduleConfig(
        task_name=request.task_name,
        task_type=request.task_type,
        schedule_type=ScheduleType(request.schedule_type),
        daily_time=request.daily_time,
        interval_seconds=request.interval_seconds,
        priority=priority_map.get(request.priority, TaskPriority.NORMAL),
        enabled=request.enabled,
    )
    
    scheduler.register_task(config)
    
    return {
        "success": True,
        "task_id": config.task_id,
        "message": "Scheduled task created",
    }


@router.post("/scheduler/start")
async def start_scheduler() -> dict[str, Any]:
    """Start the scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()
    
    return {"success": True, "message": "Scheduler started"}


@router.post("/scheduler/stop")
async def stop_scheduler() -> dict[str, Any]:
    """Stop the scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()
    
    return {"success": True, "message": "Scheduler stopped"}


@router.get("/scheduler/stats")
async def get_scheduler_stats() -> dict[str, Any]:
    """Get scheduler statistics."""
    scheduler = get_scheduler()
    return scheduler.get_stats()


# ==================== Company Preload ====================

@router.post("/companies/preload")
async def preload_companies() -> dict[str, Any]:
    """Trigger company preload."""
    from openfinance.datacenter.collector.core.batch_processor import BatchConfig
    
    preloader = CompanyPreloader(
        config=BatchConfig(batch_size=50, max_concurrent=3),
        sync_to_graph=True,
    )
    
    try:
        stats = await preloader.preload_all(resume=True)
        return {
            "success": True,
            "message": "Company preload completed",
            "stats": stats,
        }
    except Exception as e:
        logger.error_with_context(
            "Company preload failed",
            context={"error": str(e)}
        )
        return {
            "success": False,
            "message": f"Company preload failed: {str(e)}",
        }
    finally:
        await preloader.close()


# ==================== Stock Data Collection ====================

@router.post("/stocks/collect")
async def collect_stock_data(
    data_types: list[str] | None = None,
    stock_codes: list[str] | None = None,
) -> dict[str, Any]:
    """Trigger stock data collection."""
    from openfinance.datacenter.collector.core.batch_processor import BatchConfig
    
    collector = StockBatchCollector(
        config=BatchConfig(batch_size=100, max_concurrent=5),
        incremental=True,
    )
    
    types = [DataType(dt) for dt in data_types] if data_types else [DataType.KLINE_DAILY]
    
    try:
        stats = await collector.collect_all_stocks(
            data_types=types,
            stock_codes=stock_codes,
        )
        return {
            "success": True,
            "message": "Stock data collection completed",
            "stats": stats,
        }
    except Exception as e:
        logger.error_with_context(
            "Stock data collection failed",
            context={"error": str(e)}
        )
        return {
            "success": False,
            "message": f"Stock data collection failed: {str(e)}",
        }
    finally:
        await collector.close()
