"""
Extended Data Center API Routes.

Provides additional endpoints for:
- Task DAG management (using unified DAGEngine)
- Canvas visualization data
- Monitoring and alerts
- Company preloading

This module uses the unified DAGEngine from task/dag_engine.py
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.datacenter.task.dag_engine import (
    DAGEngine,
    DAG,
    DAGBuilder,
    DAGNode,
    TaskStatus,
    TaskPriority,
    NodeType,
)
from openfinance.datacenter.task.monitoring import (
    TaskMonitor,
    AlertSeverity,
    AlertStatus,
    MetricType,
    create_default_alert_rules,
)
from openfinance.datacenter.task.enhanced_scheduler import (
    EnhancedScheduler,
    ScheduleConfig,
    ScheduleType,
    create_default_scheduled_tasks,
)
from openfinance.datacenter.collector.implementations.company_preloader import CompanyPreloader
from openfinance.datacenter.collector.implementations.stock_batch_collector import StockBatchCollector, DataType

logger = get_logger(__name__)

router = APIRouter(prefix="/datacenter", tags=["datacenter-extended"])

_dag_engine: DAGEngine | None = None
_monitor: TaskMonitor | None = None
_scheduler: EnhancedScheduler | None = None


def get_dag_engine() -> DAGEngine:
    """Get or create the DAG engine singleton."""
    global _dag_engine
    if _dag_engine is None:
        _dag_engine = DAGEngine()
    return _dag_engine


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


class CreateDAGRequest(BaseModel):
    """Request to create a new DAG."""
    
    name: str = Field(..., description="DAG name")
    description: str = Field(default="", description="DAG description")
    tasks: list[dict[str, Any]] = Field(default_factory=list, description="DAG tasks")


class ExecuteDAGRequest(BaseModel):
    """Request to execute a DAG."""
    
    dag_id: str = Field(..., description="DAG ID to execute")
    context: dict[str, Any] | None = Field(default=None, description="Execution context")


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


# ==================== DAG Management ====================

@router.get("/dags")
async def list_dags() -> dict[str, Any]:
    """List all DAGs."""
    engine = get_dag_engine()
    dags = engine.list_dags()
    
    return {
        "success": True,
        "dags": dags,
        "total": len(dags),
    }


@router.post("/dags")
async def create_dag(request: CreateDAGRequest) -> dict[str, Any]:
    """Create a new DAG."""
    engine = get_dag_engine()
    
    builder = DAGBuilder(request.name)
    if request.description:
        builder.description(request.description)
    
    for task_data in request.tasks:
        priority = TaskPriority(task_data.get("priority", 2))
        builder.add_task(
            task_id=task_data.get("task_id", ""),
            name=task_data.get("name", ""),
            task_type=task_data.get("task_type", "generic"),
            params=task_data.get("params", {}),
            depends_on=task_data.get("depends_on", []),
            priority=priority,
            timeout=task_data.get("timeout", 300.0),
        )
    
    dag = builder.build()
    
    try:
        engine.register_dag(dag)
        return {
            "success": True,
            "dagId": dag.dag_id,
            "name": dag.name,
            "totalNodes": len(dag.nodes),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dags/{dag_id}")
async def get_dag(dag_id: str) -> dict[str, Any]:
    """Get DAG details."""
    engine = get_dag_engine()
    status = engine.get_dag_status(dag_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return {
        "success": True,
        **status,
    }


@router.post("/dags/{dag_id}/execute")
async def execute_dag(dag_id: str, request: ExecuteDAGRequest | None = None) -> dict[str, Any]:
    """Execute a DAG."""
    engine = get_dag_engine()
    
    dag = engine.get_dag(dag_id)
    if not dag:
        raise HTTPException(status_code=404, detail=f"DAG not found: {dag_id}")
    
    context = request.context if request else {}
    
    result = await engine.execute_dag(dag_id, context)
    
    return {
        "success": True,
        **result,
    }


@router.get("/dags/{dag_id}/canvas")
async def get_dag_canvas(dag_id: str) -> dict[str, Any]:
    """Get Canvas data for a specific DAG."""
    engine = get_dag_engine()
    canvas_data = engine.get_dag_canvas(dag_id)
    
    if "error" in canvas_data:
        raise HTTPException(status_code=404, detail=canvas_data["error"])
    
    return {
        "success": True,
        **canvas_data,
    }


@router.get("/dags/{dag_id}/mermaid")
async def get_dag_mermaid(dag_id: str) -> dict[str, Any]:
    """Get Mermaid diagram for a specific DAG."""
    engine = get_dag_engine()
    dag = engine.get_dag(dag_id)
    
    if not dag:
        raise HTTPException(status_code=404, detail=f"DAG not found: {dag_id}")
    
    return {
        "success": True,
        "dagId": dag_id,
        "mermaid": dag.to_mermaid(),
    }


# ==================== Canvas Data ====================

@router.get("/canvas/data")
async def get_canvas_data() -> dict[str, Any]:
    """Get data for Canvas visualization."""
    engine = get_dag_engine()
    monitor = get_monitor()
    
    dags = engine.list_dags()
    
    all_nodes = []
    all_edges = []
    
    for dag_data in dags:
        dag_id = dag_data.get("dagId", dag_data.get("id", ""))
        canvas = engine.get_dag_canvas(dag_id)
        
        if "error" not in canvas:
            for node in canvas.get("nodes", []):
                node["id"] = f"{dag_id}_{node['id']}"
                node["data"]["dagId"] = dag_id
                all_nodes.append(node)
            
            for edge in canvas.get("edges", []):
                edge["source"] = f"{dag_id}_{edge['source']}"
                edge["target"] = f"{dag_id}_{edge['target']}"
                all_edges.append(edge)
    
    summary = monitor.get_summary()
    
    return {
        "nodes": all_nodes,
        "edges": all_edges,
        "dags": dags,
        "summary": summary,
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
        logger.error(f"Company preload failed: {e}")
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
        logger.error(f"Stock data collection failed: {e}")
        return {
            "success": False,
            "message": f"Stock data collection failed: {str(e)}",
        }
    finally:
        await collector.close()


@router.get("/stocks")
async def list_stocks(
    limit: int = 100,
    offset: int = 0,
    industry: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """List stocks from database."""
    try:
        from sqlalchemy import select
        from openfinance.datacenter.models.orm import StockBasicModel
        from openfinance.infrastructure.database.database import async_session_maker
        
        async with async_session_maker() as session:
            query = select(StockBasicModel)
            
            if industry:
                query = query.where(StockBasicModel.industry == industry)
            
            if search:
                query = query.where(
                    (StockBasicModel.code.contains(search)) |
                    (StockBasicModel.name.contains(search))
                )
            
            query = query.order_by(StockBasicModel.code).limit(limit).offset(offset)
            
            result = await session.execute(query)
            stocks = result.scalars().all()
            
            count_query = select(StockBasicModel)
            if industry:
                count_query = count_query.where(StockBasicModel.industry == industry)
            if search:
                count_query = count_query.where(
                    (StockBasicModel.code.contains(search)) |
                    (StockBasicModel.name.contains(search))
                )
            
            count_result = await session.execute(count_query)
            total = len(count_result.scalars().all())
            
            return {
                "stocks": [
                    {
                        "code": stock.code,
                        "name": stock.name,
                        "industry": getattr(stock, 'industry', None),
                        "market": getattr(stock, 'market', None),
                        "listing_date": stock.listing_date.isoformat() if stock.listing_date else None,
                    }
                    for stock in stocks
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        return {
            "stocks": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }
