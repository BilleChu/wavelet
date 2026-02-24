"""
Pipeline API Routes - REST API for data collection pipeline management.

Provides endpoints for:
- DAG management and execution
- Task monitoring
- Alert management
- Knowledge graph integration
- Canvas visualization support
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from openfinance.datacenter.task.dag_engine import (
    DAG,
    DAGEngine,
    DAGBuilder,
    DAGNode,
    TaskStatus,
    TaskPriority,
    NodeType,
)
from openfinance.datacenter.task.pipeline import (
    PipelineConfig,
    PipelineRegistry,
    get_pipeline,
    get_all_pipelines,
    PipelineManager,
    get_pipeline_manager,
    PipelineBuilder,
    build_dag_from_config,
)
from openfinance.datacenter.task.pipeline_monitor import (
    PipelineMonitor,
    AlertSeverity,
    AlertType,
    LogAlertChannel,
    WebhookAlertChannel,
)
from openfinance.infrastructure.database.database import get_db
from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

_dag_engine: DAGEngine | None = None
_pipeline_monitor: PipelineMonitor | None = None


def get_dag_engine() -> DAGEngine:
    """Get or create DAG engine instance."""
    global _dag_engine
    
    if _dag_engine is None:
        _dag_engine = DAGEngine(max_concurrent_tasks=5)
        _register_default_executors(_dag_engine)
        _initialize_default_dags(_dag_engine)
    
    return _dag_engine


async def _default_executor(params: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default executor using the task registry."""
    from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
    import uuid
    
    task_type = params.get("task_type") or context.get("task_type", "unknown")
    logger.info(f"Executing task: {task_type}")
    
    executor = TaskRegistry.get_executor(task_type)
    if not executor:
        logger.warning(f"No executor found for task type: {task_type}")
        return {"success": False, "task_type": task_type, "error": f"Unknown task type: {task_type}"}
    
    progress = TaskProgress(task_id=str(uuid.uuid4()))
    result = await executor.execute(params, progress)
    
    return result


def _register_executors_from_registry(engine: DAGEngine) -> None:
    """Register executors from the task registry."""
    from openfinance.datacenter.task.registry import TaskRegistry
    from openfinance.datacenter.task.executors import register_all_executors
    
    register_all_executors()
    
    for task_type in TaskRegistry._executors.keys():
        engine.register_executor(task_type, _default_executor)
        logger.info(f"Registered executor from registry: {task_type}")


def _register_default_executors(engine: DAGEngine) -> None:
    """Register default executors from the task registry."""
    _register_executors_from_registry(engine)


def _initialize_default_dags(engine: DAGEngine) -> None:
    """Initialize DAG configurations from pipelines.yaml."""
    from openfinance.datacenter.task.pipeline import get_all_pipelines, reload_pipelines
    
    reload_pipelines()
    pipelines = get_all_pipelines()
    
    if not pipelines:
        _initialize_fallback_dags(engine)
        return
    
    for config in pipelines:
        if not config.enabled:
            continue
            
        builder = DAGBuilder(config.pipeline_id)
        if config.description:
            builder.description(config.description)
        
        for task in config.tasks:
            priority = TaskPriority.NORMAL
            if task.priority == "critical":
                priority = TaskPriority.CRITICAL
            elif task.priority == "high":
                priority = TaskPriority.HIGH
            elif task.priority == "low":
                priority = TaskPriority.LOW
            
            builder.add_task(
                task_id=task.task_id,
                name=task.name,
                task_type=task.task_type,
                params=task.params or {},
                depends_on=task.dependencies or [],
                priority=priority,
                timeout=task.timeout_seconds or 300.0,
            )
        
        dag = builder.build()
        try:
            engine.register_dag(dag)
            logger.info(f"Initialized DAG from config: {config.name} ({config.pipeline_id})")
        except ValueError as e:
            logger.warning(f"Failed to register DAG {config.pipeline_id}: {e}")


def _initialize_fallback_dags(engine: DAGEngine) -> None:
    """Initialize fallback DAG configurations if config file not found."""
    default_dags = [
        {
            "name": "daily_basic_sync",
            "description": "每日基础数据同步",
            "tasks": [
                {"task_id": "sync_stock_basic", "name": "股票基础信息同步", "task_type": "stock_basic_info", "priority": 0},
                {"task_id": "sync_industry", "name": "行业数据同步", "task_type": "industry_classify", "priority": 1, "depends_on": ["sync_stock_basic"]},
                {"task_id": "sync_concept", "name": "概念数据同步", "task_type": "concept_classify", "priority": 1, "depends_on": ["sync_stock_basic"]},
            ],
        },
        {
            "name": "intraday_collection",
            "description": "日内实时数据采集",
            "tasks": [
                {"task_id": "collect_realtime", "name": "实时行情采集", "task_type": "market_realtime", "priority": 1},
                {"task_id": "collect_tick", "name": "Tick数据采集", "task_type": "tick_data", "priority": 2, "depends_on": ["collect_realtime"]},
            ],
        },
        {
            "name": "daily_post_market",
            "description": "每日收盘后数据处理",
            "tasks": [
                {"task_id": "collect_daily_quotes", "name": "日行情采集", "task_type": "daily_quotes", "priority": 1},
                {"task_id": "collect_financial_indicator", "name": "财务指标采集", "task_type": "financial_indicator", "priority": 2, "depends_on": ["collect_daily_quotes"]},
                {"task_id": "collect_income", "name": "利润表采集", "task_type": "income_statement", "priority": 2, "depends_on": ["collect_daily_quotes"]},
                {"task_id": "collect_balance", "name": "资产负债表采集", "task_type": "balance_sheet", "priority": 2, "depends_on": ["collect_daily_quotes"]},
            ],
        },
        {
            "name": "knowledge_graph_sync",
            "description": "知识图谱数据同步",
            "tasks": [
                {"task_id": "sync_company_entities", "name": "公司实体同步", "task_type": "sync_company_entities", "priority": 1},
                {"task_id": "sync_stock_entities", "name": "股票实体同步", "task_type": "sync_stock_entities", "priority": 2, "depends_on": ["sync_company_entities"]},
                {"task_id": "sync_industry_entities", "name": "行业实体同步", "task_type": "sync_industry_entities", "priority": 3, "depends_on": ["sync_company_entities"]},
                {"task_id": "sync_concept_entities", "name": "概念实体同步", "task_type": "sync_concept_entities", "priority": 3, "depends_on": ["sync_company_entities"]},
            ],
        },
    ]
    
    for dag_config in default_dags:
        builder = DAGBuilder(dag_config["name"])
        if dag_config.get("description"):
            builder.description(dag_config["description"])
        
        for task in dag_config["tasks"]:
            priority = TaskPriority(task.get("priority", 2))
            builder.add_task(
                task_id=task["task_id"],
                name=task["name"],
                task_type=task["task_type"],
                params=task.get("params", {}),
                depends_on=task.get("depends_on", []),
                priority=priority,
                timeout=task.get("timeout", 300.0),
            )
        
        dag = builder.build()
        try:
            engine.register_dag(dag)
            logger.info(f"Initialized fallback DAG: {dag_config['name']}")
        except ValueError as e:
            logger.warning(f"Failed to register fallback DAG {dag_config['name']}: {e}")


def get_pipeline_monitor() -> PipelineMonitor:
    """Get or create pipeline monitor instance."""
    global _pipeline_monitor
    
    if _pipeline_monitor is None:
        channels = [LogAlertChannel()]
        _pipeline_monitor = PipelineMonitor(alert_channels=channels)
    
    return _pipeline_monitor


class DAGCreateRequest(BaseModel):
    """Request to create a new DAG."""
    
    name: str = Field(..., description="DAG name")
    description: str | None = Field(default=None, description="DAG description")
    tasks: list[dict[str, Any]] = Field(default_factory=list, description="Task definitions")


class DAGExecuteRequest(BaseModel):
    """Request to execute a DAG."""
    
    dag_id: str = Field(..., description="ID of the DAG to execute")
    context: dict[str, Any] | None = Field(default=None, description="Execution context")


class TaskAddRequest(BaseModel):
    """Request to add a task to DAG."""
    
    task_id: str = Field(..., description="Task ID")
    name: str = Field(..., description="Task name")
    task_type: str = Field(..., description="Task type")
    params: dict[str, Any] | None = Field(default=None, description="Task parameters")
    depends_on: list[str] | None = Field(default=None, description="Dependencies")
    priority: int = Field(default=2, description="Priority (0=Critical, 1=High, 2=Normal, 3=Low)")
    timeout: float = Field(default=300.0, description="Timeout in seconds")


class AlertAcknowledgeRequest(BaseModel):
    """Request to acknowledge an alert."""
    
    alert_id: str = Field(..., description="ID of the alert to acknowledge")
    acknowledged_by: str = Field(..., description="User acknowledging the alert")


class StockSyncRequest(BaseModel):
    """Request to sync stock data to knowledge graph."""
    
    stock_data: list[dict[str, Any]] = Field(..., description="Stock data to sync")
    upsert: bool = Field(default=True, description="Update existing entities")


@router.get("/dags")
async def list_dags() -> dict[str, Any]:
    """List all registered DAGs."""
    engine = get_dag_engine()
    
    dags = engine.list_dags()
    
    return {
        "success": True,
        "dags": dags,
        "total": len(dags),
    }


@router.post("/dags")
async def create_dag(request: DAGCreateRequest) -> dict[str, Any]:
    """Create a new DAG with tasks."""
    engine = get_dag_engine()
    
    builder = DAGBuilder(request.name)
    
    if request.description:
        builder.description(request.description)
    
    for task in request.tasks:
        priority = TaskPriority(task.get("priority", 2))
        builder.add_task(
            task_id=task["task_id"],
            name=task.get("name", task["task_id"]),
            task_type=task.get("task_type", "generic"),
            params=task.get("params"),
            depends_on=task.get("depends_on"),
            priority=priority,
            timeout=task.get("timeout", 300.0),
        )
    
    dag = builder.build()
    
    try:
        engine.register_dag(dag)
        return {
            "success": True,
            "dagId": dag.dag_id,
            "name": dag.name,
            "totalNodes": len(dag.nodes),
            "executionOrder": dag.get_execution_order(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dags/{dag_id}")
async def get_dag_status(dag_id: str) -> dict[str, Any]:
    """Get status of a specific DAG."""
    engine = get_dag_engine()
    status = engine.get_dag_status(dag_id)
    
    if "error" in status:
        raise HTTPException(status_code=404, detail=status["error"])
    
    return {
        "success": True,
        **status,
    }


@router.get("/dags/{dag_id}/canvas")
async def get_dag_canvas(dag_id: str) -> dict[str, Any]:
    """Get DAG in canvas display format for frontend visualization."""
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
    """Get DAG in Mermaid diagram format."""
    engine = get_dag_engine()
    dag = engine.get_dag(dag_id)
    
    if not dag:
        raise HTTPException(status_code=404, detail="DAG not found")
    
    return {
        "success": True,
        "dagId": dag_id,
        "mermaid": dag.to_mermaid(),
    }


@router.post("/dags/{dag_id}/execute")
async def execute_dag(
    dag_id: str,
    background_tasks: BackgroundTasks,
    request: DAGExecuteRequest | None = None,
) -> dict[str, Any]:
    """Execute a DAG."""
    engine = get_dag_engine()
    monitor = get_pipeline_monitor()
    
    dag = engine.get_dag(dag_id)
    if not dag:
        raise HTTPException(status_code=404, detail=f"DAG not found: {dag_id}")
    
    context = request.context if request else {}
    
    async def run_dag():
        try:
            def on_progress(dag_id: str, node_id: str, progress: float):
                logger.info(f"DAG {dag_id} node {node_id}: {progress*100:.0f}%")
            
            await engine.execute_dag(dag_id, context, on_progress)
        except Exception as e:
            logger.error(f"DAG execution failed: {e}")
    
    background_tasks.add_task(run_dag)
    
    return {
        "success": True,
        "message": f"DAG {dag_id} execution started",
        "dagId": dag_id,
    }


@router.get("/dags/{dag_id}/logs")
async def get_dag_logs(
    dag_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Get execution logs for a DAG."""
    engine = get_dag_engine()
    
    logs = engine.get_logs(dag_id=dag_id, limit=limit)
    
    return {
        "success": True,
        "dagId": dag_id,
        "logs": [log.model_dump() for log in logs],
        "total": len(logs),
    }


@router.post("/dags/daily/create")
async def create_daily_dag() -> dict[str, Any]:
    """Create the standard daily data collection DAG."""
    engine = get_dag_engine()
    
    builder = DAGBuilder("daily_data_collection")
    builder.description("每日数据采集任务链")
    
    tasks = [
        ("stock_basic_info", "股票基础信息采集", "data_collection", [], TaskPriority.CRITICAL),
        ("stock_daily_quote", "股票日线行情采集", "data_collection", ["stock_basic_info"], TaskPriority.HIGH),
        ("stock_financial_indicator", "财务指标采集", "data_collection", ["stock_basic_info"], TaskPriority.HIGH),
        ("index_daily_quote", "指数日线行情采集", "data_collection", [], TaskPriority.HIGH),
        ("macro_economic_data", "宏观经济数据采集", "data_collection", [], TaskPriority.NORMAL),
        ("factor_pe_ratio", "PE因子计算", "factor_compute", ["stock_daily_quote"], TaskPriority.NORMAL),
        ("factor_pb_ratio", "PB因子计算", "factor_compute", ["stock_daily_quote"], TaskPriority.NORMAL),
        ("financial_news", "财经新闻采集", "data_collection", [], TaskPriority.LOW),
    ]
    
    for task_id, name, task_type, deps, priority in tasks:
        builder.add_task(
            task_id=task_id,
            name=name,
            task_type=task_type,
            depends_on=deps,
            priority=priority,
        )
    
    dag = builder.build()
    
    try:
        engine.register_dag(dag)
        return {
            "success": True,
            "dagId": dag.dag_id,
            "name": dag.name,
            "totalNodes": len(dag.nodes),
            "executionOrder": dag.get_execution_order(),
            "mermaid": dag.to_mermaid(),
            "canvas": dag.to_canvas_format(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dags/load-config")
async def load_dags_from_config() -> dict[str, Any]:
    """Load all DAGs from pipeline configuration file."""
    from openfinance.datacenter.task.pipeline.pipeline_config import reload_pipelines
    
    engine = get_dag_engine()
    builder = PipelineBuilder(engine)
    
    try:
        reload_pipelines()
        pipelines = get_all_pipelines()
        
        loaded = []
        for config in pipelines:
            try:
                dag = builder.build_and_register(config)
                loaded.append({
                    "id": config.pipeline_id,
                    "name": config.name,
                    "totalNodes": len(dag.nodes),
                })
            except ValueError as e:
                logger.warning(f"Failed to register DAG {config.pipeline_id}: {e}")
        
        return {
            "success": True,
            "loaded": loaded,
            "total": len(loaded),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/config/summary")
async def get_dag_config_summary() -> dict[str, Any]:
    """Get summary of all pipeline configurations."""
    try:
        pipelines = get_all_pipelines()
        
        summaries = []
        for config in pipelines:
            summaries.append({
                "id": config.pipeline_id,
                "name": config.name,
                "description": config.description,
                "totalTasks": len(config.tasks),
                "schedule": config.schedule.to_dict() if config.schedule else None,
                "enabled": config.enabled,
            })
        
        return {
            "success": True,
            "dags": summaries,
            "total": len(summaries),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines")
async def list_pipelines() -> dict[str, Any]:
    """List all registered pipelines."""
    pipelines = get_all_pipelines()
    
    return {
        "success": True,
        "pipelines": [p.to_dict() for p in pipelines],
        "total": len(pipelines),
    }


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline_config(pipeline_id: str) -> dict[str, Any]:
    """Get pipeline configuration."""
    config = get_pipeline(pipeline_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")
    
    return {
        "success": True,
        "pipeline": config.to_dict(),
    }


@router.post("/pipelines/{pipeline_id}/execute")
async def execute_pipeline(
    pipeline_id: str,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Execute a pipeline."""
    config = get_pipeline(pipeline_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")
    
    manager = get_pipeline_manager()
    
    async def run_pipeline():
        try:
            await manager.execute_pipeline_config(config)
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
    
    background_tasks.add_task(run_pipeline)
    
    return {
        "success": True,
        "message": f"Pipeline {pipeline_id} execution started",
        "pipelineId": pipeline_id,
    }


@router.get("/tasks/templates")
async def get_task_templates() -> dict[str, Any]:
    """Get available task templates."""
    from openfinance.datacenter.task.registry import get_all_task_types
    
    task_types = get_all_task_types()
    
    return {
        "success": True,
        "templates": {tt: {"task_type": tt} for tt in task_types},
    }


@router.get("/monitor/dashboard")
async def get_monitor_dashboard() -> dict[str, Any]:
    """Get monitoring dashboard data."""
    monitor = get_pipeline_monitor()
    
    return {
        "success": True,
        "dashboard": monitor.get_dashboard_data(),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/alerts")
async def get_alerts(
    severity: str | None = None,
    alert_type: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Get alerts with filtering."""
    monitor = get_pipeline_monitor()
    
    sev = AlertSeverity(severity) if severity else None
    typ = AlertType(alert_type) if alert_type else None
    
    alerts = monitor.alert_manager.get_alerts(
        severity=sev,
        alert_type=typ,
        limit=limit,
    )
    
    return {
        "success": True,
        "alerts": [a.to_dict() for a in alerts],
        "total": len(alerts),
    }


@router.post("/alerts/acknowledge")
async def acknowledge_alert(request: AlertAcknowledgeRequest) -> dict[str, Any]:
    """Acknowledge an alert."""
    monitor = get_pipeline_monitor()
    
    success = monitor.alert_manager.acknowledge_alert(
        request.alert_id,
        request.acknowledged_by,
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "success": True,
        "alertId": request.alert_id,
        "acknowledgedBy": request.acknowledged_by,
        "acknowledgedAt": datetime.now().isoformat(),
    }


@router.post("/knowledge-graph/sync")
async def sync_to_knowledge_graph(
    request: StockSyncRequest,
    session = Depends(get_db),
) -> dict[str, Any]:
    """Sync stock data to knowledge graph."""
    from openfinance.services.storage.entity_engine import EntityEngine
    from openfinance.domain.metadata.registry import EntityTypeRegistry
    
    entity_engine = EntityEngine(session, registry=EntityTypeRegistry())
    
    created_count = 0
    updated_count = 0
    error_count = 0
    
    for stock in request.stock_data:
        try:
            code = stock.get("ts_code") or stock.get("code")
            name = stock.get("name")
            
            if not code or not name:
                continue
            
            entity_data = {
                "code": code,
                "name": name,
                "industry": stock.get("industry"),
                "market": stock.get("market"),
                "list_date": stock.get("list_date"),
                "is_active": True,
            }
            
            result = await entity_engine.create(
                entity_type="stock",
                data=entity_data,
                validate=True,
                upsert=request.upsert,
            )
            
            if result.success:
                if result.validation and result.validation.is_new:
                    created_count += 1
                else:
                    updated_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            error_count += 1
            logger.error(f"Error syncing stock {stock.get('code')}: {e}")
    
    return {
        "success": True,
        "result": {
            "total": len(request.stock_data),
            "created": created_count,
            "updated": updated_count,
            "errors": error_count,
        },
    }


@router.get("/knowledge-graph/stocks")
async def get_stocks_from_kg(
    industry: str | None = None,
    market: str | None = None,
    use_cache: bool = True,
    session = Depends(get_db),
) -> dict[str, Any]:
    """Get stocks from knowledge graph."""
    from openfinance.services.storage.entity_engine import EntityEngine
    from openfinance.domain.metadata.registry import EntityTypeRegistry
    
    entity_engine = EntityEngine(session, registry=EntityTypeRegistry())
    
    filters = {}
    if industry:
        filters["industry"] = industry
    if market:
        filters["market"] = market
    
    results = await entity_engine.search(
        entity_type="stock",
        filters=filters if filters else None,
        limit=1000,
    )
    
    stocks = [
        {
            "entity_id": e.entity_id,
            "code": e.code,
            "name": e.name,
            "industry": e.industry,
            "market": getattr(e, "market", None),
        }
        for e in results.entities
    ]
    
    return {
        "success": True,
        "stocks": stocks,
        "total": len(stocks),
    }


@router.get("/knowledge-graph/stats")
async def get_kg_stats(
    session = Depends(get_db),
) -> dict[str, Any]:
    """Get knowledge graph statistics."""
    from openfinance.services.storage.entity_engine import EntityEngine
    from openfinance.domain.metadata.registry import EntityTypeRegistry
    from openfinance.datacenter.storage.models import EntityModel
    from sqlalchemy import select, func
    
    entity_engine = EntityEngine(session, registry=EntityTypeRegistry())
    
    counts = {}
    for entity_type in ["stock", "company", "industry", "concept", "index", "fund"]:
        result = await session.execute(
            select(func.count()).where(EntityModel.entity_type == entity_type)
        )
        counts[entity_type] = result.scalar() or 0
    
    return {
        "success": True,
        "entityCounts": counts,
    }
