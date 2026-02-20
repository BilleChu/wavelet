"""
Data Center API Routes.

Provides comprehensive data management interface:
- Data source management
- Task management (create, start, pause, cancel)
- Trigger management
- Real-time monitoring
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger
from openfinance.datacenter.collector.core.base_collector import DataSource, DataType, DataCategory
from openfinance.datacenter.task import (
    TaskManager,
    TaskDefinition,
    TaskStatus,
    TaskPriority,
    TriggerManager,
    TriggerType,
)
from openfinance.datacenter.task.handlers import HANDLERS, get_handler

logger = get_logger(__name__)

router = APIRouter(prefix="/datacenter", tags=["datacenter"])

_task_manager: TaskManager | None = None


async def execute_collection_task(task: TaskDefinition, params: dict[str, Any]) -> dict[str, Any]:
    """Execute a data collection task."""
    handler = get_handler(task.task_type)
    if not handler:
        raise ValueError(f"No handler for task type: {task.task_type}")
    return await handler.execute(task, params)


def get_task_manager() -> TaskManager:
    """Get or create the task manager singleton."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(max_concurrent=5)
        
        for task_type in HANDLERS:
            _task_manager.register_task_handler(task_type, execute_collection_task)
        
        logger.info_with_context(
            "TaskManager initialized with handlers",
            context={"handlers": list(HANDLERS.keys())}
        )
    return _task_manager


class DataSourceInfo(BaseModel):
    """Data source information."""
    
    source_id: str = Field(..., description="Source ID")
    name: str = Field(..., description="Display name")
    category: str = Field(..., description="Data category")
    is_available: bool = Field(default=True, description="Whether source is available")
    description: str = Field(default="", description="Source description")


class CreateTaskRequest(BaseModel):
    """Request to create a new task."""
    
    name: str = Field(..., description="Task name")
    task_type: str = Field(default="collection", description="Task type")
    data_source: str | None = Field(default=None, description="Data source")
    data_type: str | None = Field(default=None, description="Data type")
    params: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    priority: str = Field(default="normal", description="Task priority")
    include_in_global_start: bool = Field(default=True, description="Include in global start")
    max_retries: int = Field(default=3, description="Max retries")
    timeout_seconds: float = Field(default=300.0, description="Timeout in seconds")


class CreateTriggerRequest(BaseModel):
    """Request to create a new trigger."""
    
    name: str = Field(..., description="Trigger name")
    trigger_type: str = Field(default="interval", description="Trigger type")
    task_name: str = Field(..., description="Task name template")
    task_type: str = Field(default="collection", description="Task type")
    task_params: dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    interval_seconds: int | None = Field(default=None, description="Interval for interval triggers")
    cron_expression: str | None = Field(default=None, description="Cron expression")
    scheduled_time: datetime | None = Field(default=None, description="Scheduled time")
    condition_type: str | None = Field(default=None, description="Condition type")
    condition_value: str | list[str] | None = Field(default=None, description="Condition value")


class TaskResponse(BaseModel):
    """Response for task operations."""
    
    success: bool
    task_id: str | None = None
    message: str
    task: dict[str, Any] | None = None


class TriggerResponse(BaseModel):
    """Response for trigger operations."""
    
    success: bool
    trigger_id: str | None = None
    message: str
    trigger: dict[str, Any] | None = None


@router.get("/overview")
async def get_overview() -> dict[str, Any]:
    """Get data center overview statistics."""
    manager = get_task_manager()
    return manager.get_overview()


@router.get("/sources")
async def list_data_sources() -> dict[str, Any]:
    """List all available data sources."""
    sources = []
    
    for source in DataSource:
        category = "market"
        if source.value in ["TUSHARE", "AKSHARE", "WIND"]:
            category = "api"
        elif source.value in ["EASTMONEY", "JINSHI", "CLS", "SINA", "XUEQIU"]:
            category = "web"
        elif source.value in ["SHFE", "DCE", "CZCE", "CFFEX"]:
            category = "exchange"
        
        sources.append(DataSourceInfo(
            source_id=source.value,
            name=source.value.replace("_", " ").title(),
            category=category,
            is_available=True,
        ))
    
    return {
        "sources": [s.model_dump() for s in sources],
        "total": len(sources),
    }


@router.get("/data-types")
async def list_data_types() -> dict[str, Any]:
    """List all available data types."""
    types = []
    
    for data_type in DataType:
        category = "market"
        if "FUNDAMENTAL" in data_type.value or "FINANCIAL" in data_type.value:
            category = "fundamental"
        elif "OPTION" in data_type.value or "FUTURE" in data_type.value:
            category = "derivative"
        elif "MACRO" in data_type.value:
            category = "macro"
        elif "KG" in data_type.value:
            category = "knowledge_graph"
        elif "FACTOR" in data_type.value:
            category = "factor"
        
        types.append({
            "type_id": data_type.value,
            "name": data_type.value.replace("_", " ").title(),
            "category": category,
        })
    
    return {
        "data_types": types,
        "total": len(types),
    }


@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    task_type: str | None = None,
) -> dict[str, Any]:
    """List tasks with optional filters."""
    manager = get_task_manager()
    
    task_status = TaskStatus(status) if status else None
    
    tasks = manager.list_tasks(status=task_status, task_type=task_type)
    
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "name": t.name,
                "task_type": t.task_type,
                "status": t.status.value,
                "priority": t.priority.name,
                "progress": t.progress,
                "progress_message": t.progress_message,
                "data_source": t.data_source,
                "data_type": t.data_type,
                "created_at": t.created_at.isoformat(),
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "error": t.error,
                "include_in_global_start": t.include_in_global_start,
            }
            for t in tasks
        ],
        "total": len(tasks),
    }


@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest) -> TaskResponse:
    """Create a new task."""
    manager = get_task_manager()
    
    priority_map = {
        "critical": TaskPriority.CRITICAL,
        "high": TaskPriority.HIGH,
        "normal": TaskPriority.NORMAL,
        "low": TaskPriority.LOW,
        "background": TaskPriority.BACKGROUND,
    }
    
    task = manager.create_task(
        name=request.name,
        task_type=request.task_type,
        params=request.params,
        priority=priority_map.get(request.priority, TaskPriority.NORMAL),
        data_source=request.data_source,
        data_type=request.data_type,
        include_in_global_start=request.include_in_global_start,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds,
    )
    
    task_id = manager.enqueue_task(task)
    
    logger.info_with_context(
        f"Task created via API: {request.name}",
        context={"task_id": task_id, "task_type": request.task_type}
    )
    
    return TaskResponse(
        success=True,
        task_id=task_id,
        message=f"Task created successfully",
        task={"task_id": task_id, "name": task.name, "status": task.status.value},
    )


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    """Get task details."""
    manager = get_task_manager()
    task = manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return {
        "task_id": task.task_id,
        "name": task.name,
        "task_type": task.task_type,
        "status": task.status.value,
        "priority": task.priority.name,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "data_source": task.data_source,
        "data_type": task.data_type,
        "params": task.params,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result": task.result,
        "error": task.error,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "include_in_global_start": task.include_in_global_start,
        "dependencies": task.dependencies,
    }


@router.put("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(task_id: str) -> TaskResponse:
    """Start a task."""
    manager = get_task_manager()
    
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    if task.status == TaskStatus.PAUSED:
        success = manager.resume_task(task_id)
    else:
        task.status = TaskStatus.QUEUED
        success = True
    
    return TaskResponse(
        success=success,
        task_id=task_id,
        message=f"Task started" if success else "Failed to start task",
    )


@router.put("/tasks/{task_id}/pause", response_model=TaskResponse)
async def pause_task(task_id: str) -> TaskResponse:
    """Pause a running task."""
    manager = get_task_manager()
    
    success = manager.pause_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause task")
    
    return TaskResponse(
        success=True,
        task_id=task_id,
        message="Task paused",
    )


@router.put("/tasks/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str) -> TaskResponse:
    """Cancel a task."""
    manager = get_task_manager()
    
    success = manager.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel task")
    
    return TaskResponse(
        success=True,
        task_id=task_id,
        message="Task cancelled",
    )


@router.put("/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(task_id: str) -> TaskResponse:
    """Retry a failed task."""
    manager = get_task_manager()
    
    success = manager.retry_task(task_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot retry task")
    
    return TaskResponse(
        success=True,
        task_id=task_id,
        message="Task retry initiated",
    )


@router.post("/tasks/start-all")
async def start_all_tasks() -> dict[str, Any]:
    """Start all tasks that have include_in_global_start=True."""
    manager = get_task_manager()
    return await manager.start_all()


@router.post("/tasks/pause-all")
async def pause_all_tasks() -> dict[str, Any]:
    """Pause all running tasks."""
    manager = get_task_manager()
    return await manager.pause_all()


@router.get("/queue")
async def get_queue_status() -> dict[str, Any]:
    """Get task queue status."""
    manager = get_task_manager()
    stats = manager.task_queue.get_stats()
    
    return {
        "queue_size": manager.task_queue.get_queue_size(),
        "running_count": manager.task_queue.get_running_count(),
        "stats": stats,
    }


@router.get("/executions")
async def get_executions(
    task_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Get task execution history."""
    manager = get_task_manager()
    executions = manager.get_task_executions(task_id=task_id, limit=limit)
    
    return {
        "executions": [
            {
                "execution_id": e.execution_id,
                "task_id": e.task_id,
                "status": e.status.value,
                "started_at": e.started_at.isoformat(),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "duration_ms": e.duration_ms,
                "records_processed": e.records_processed,
                "records_failed": e.records_failed,
                "error": e.error,
            }
            for e in executions
        ],
        "total": len(executions),
    }


@router.get("/triggers")
async def list_triggers(
    trigger_type: str | None = None,
) -> dict[str, Any]:
    """List triggers with optional filters."""
    manager = get_task_manager()
    
    t_type = TriggerType(trigger_type) if trigger_type else None
    triggers = manager.list_triggers(trigger_type=t_type)
    
    return {
        "triggers": [
            {
                "trigger_id": t.trigger_id,
                "name": t.name,
                "trigger_type": t.trigger_type.value,
                "status": t.status.value,
                "last_triggered": t.last_triggered.isoformat() if t.last_triggered else None,
                "next_trigger": t.next_trigger.isoformat() if t.next_trigger else None,
                "trigger_count": t.trigger_count,
                "error_count": t.error_count,
            }
            for t in triggers
        ],
        "total": len(triggers),
    }


@router.post("/triggers", response_model=TriggerResponse)
async def create_trigger(request: CreateTriggerRequest) -> TriggerResponse:
    """Create a new trigger."""
    manager = get_task_manager()
    
    trigger_type_map = {
        "interval": TriggerType.INTERVAL,
        "cron": TriggerType.CRON,
        "once": TriggerType.ONCE,
        "condition": TriggerType.CONDITION,
        "manual": TriggerType.MANUAL,
    }
    
    task_template = manager.create_task(
        name=request.task_name,
        task_type=request.task_type,
        params=request.task_params,
    )
    
    trigger = manager.create_trigger(
        name=request.name,
        trigger_type=trigger_type_map.get(request.trigger_type, TriggerType.INTERVAL),
        task_template=task_template,
        interval_seconds=request.interval_seconds,
        cron_expression=request.cron_expression,
        scheduled_time=request.scheduled_time,
        condition_type=request.condition_type,
        condition_value=request.condition_value,
    )
    
    return TriggerResponse(
        success=True,
        trigger_id=trigger.trigger_id,
        message="Trigger created successfully",
        trigger={"trigger_id": trigger.trigger_id, "name": trigger.name},
    )


@router.put("/triggers/{trigger_id}/enable")
async def enable_trigger(trigger_id: str) -> dict[str, Any]:
    """Enable a trigger."""
    manager = get_task_manager()
    
    success = manager.enable_trigger(trigger_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    return {"success": True, "message": "Trigger enabled"}


@router.put("/triggers/{trigger_id}/disable")
async def disable_trigger(trigger_id: str) -> dict[str, Any]:
    """Disable a trigger."""
    manager = get_task_manager()
    
    success = manager.disable_trigger(trigger_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    return {"success": True, "message": "Trigger disabled"}


@router.post("/triggers/{trigger_id}/execute")
async def execute_trigger(trigger_id: str) -> dict[str, Any]:
    """Manually execute a trigger."""
    manager = get_task_manager()
    
    task_id = await manager.manual_trigger(trigger_id)
    
    if not task_id:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Trigger executed, task created",
    }


@router.get("/monitoring")
async def get_monitoring_data() -> dict[str, Any]:
    """Get real-time monitoring data."""
    manager = get_task_manager()
    
    queue_stats = manager.task_queue.get_stats()
    trigger_stats = manager.trigger_manager.get_stats()
    
    tasks = manager.list_tasks()
    running_tasks = [t for t in tasks if t.status == TaskStatus.RUNNING]
    
    return {
        "timestamp": datetime.now().isoformat(),
        "queue": queue_stats,
        "triggers": trigger_stats,
        "running_tasks": [
            {
                "task_id": t.task_id,
                "name": t.name,
                "progress": t.progress,
                "progress_message": t.progress_message,
                "started_at": t.started_at.isoformat() if t.started_at else None,
            }
            for t in running_tasks
        ],
        "recent_errors": [
            {
                "task_id": t.task_id,
                "name": t.name,
                "error": t.error,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
            if t.status == TaskStatus.FAILED
        ][:5],
    }


@router.post("/init-default-tasks")
async def init_default_tasks() -> dict[str, Any]:
    """
    Initialize default data collection tasks.
    
    Creates the following tasks:
    1. stock_list - Fetch all A-share stocks
    2. realtime_quote - Fetch real-time quotes
    3. index_quote - Fetch index quotes
    4. north_money - Fetch north-bound money flow
    5. etf_quote - Fetch ETF quotes
    6. industry_quote - Fetch industry sector quotes
    7. concept_quote - Fetch concept sector quotes
    8. financial_indicator - Fetch financial indicators
    """
    manager = get_task_manager()
    
    default_tasks = [
        {
            "name": "A股股票列表采集",
            "task_type": "stock_list",
            "description": "采集全部A股股票列表，包括代码、名称、市值等信息",
            "priority": TaskPriority.CRITICAL,
            "data_source": "eastmoney",
            "data_type": "stock_list",
        },
        {
            "name": "实时行情采集",
            "task_type": "realtime_quote",
            "description": "采集A股实时行情数据，包括价格、涨跌幅、成交量等",
            "priority": TaskPriority.HIGH,
            "data_source": "eastmoney",
            "data_type": "stock_quote_realtime",
        },
        {
            "name": "指数行情采集",
            "task_type": "index_quote",
            "description": "采集主要指数行情数据，包括上证指数、深证成指等",
            "priority": TaskPriority.HIGH,
            "data_source": "eastmoney",
            "data_type": "index_quote",
        },
        {
            "name": "北向资金采集",
            "task_type": "north_money",
            "description": "采集北向资金流入流出数据",
            "priority": TaskPriority.HIGH,
            "data_source": "eastmoney",
            "data_type": "north_money",
        },
        {
            "name": "ETF行情采集",
            "task_type": "etf_quote",
            "description": "采集全部ETF基金行情数据",
            "priority": TaskPriority.NORMAL,
            "data_source": "eastmoney",
            "data_type": "etf_quote",
        },
        {
            "name": "行业板块行情采集",
            "task_type": "industry_quote",
            "description": "采集行业板块涨跌幅、领涨股等数据",
            "priority": TaskPriority.NORMAL,
            "data_source": "eastmoney",
            "data_type": "industry_data",
        },
        {
            "name": "概念板块行情采集",
            "task_type": "concept_quote",
            "description": "采集概念板块涨跌幅、领涨股等数据",
            "priority": TaskPriority.NORMAL,
            "data_source": "eastmoney",
            "data_type": "concept_data",
        },
        {
            "name": "财务指标采集",
            "task_type": "financial_indicator",
            "description": "采集股票财务指标数据，包括PE、PB、市值等",
            "priority": TaskPriority.LOW,
            "data_source": "eastmoney",
            "data_type": "stock_financial_indicator",
        },
        {
            "name": "上市公司档案采集与知识图谱构建",
            "task_type": "company_profile",
            "description": "采集上市公司完整档案信息，构建知识图谱实体和关系",
            "priority": TaskPriority.HIGH,
            "data_source": "eastmoney",
            "data_type": "company_profile",
        },
    ]
    
    created_tasks = []
    existing_tasks = manager.list_tasks()
    existing_types = {t.task_type for t in existing_tasks}
    
    for task_config in default_tasks:
        if task_config["task_type"] in existing_types:
            continue
            
        task = manager.create_task(
            name=task_config["name"],
            task_type=task_config["task_type"],
            params={},
            priority=task_config["priority"],
            data_source=task_config.get("data_source"),
            data_type=task_config.get("data_type"),
            dependencies=task_config.get("dependencies", []),
            timeout_seconds=task_config.get("timeout_seconds", 300.0),
        )
        
        task_id = manager.enqueue_task(task)
        created_tasks.append({
            "task_id": task_id,
            "name": task_config["name"],
            "task_type": task_config["task_type"],
        })
        
        logger.info_with_context(
            f"Default task created: {task_config['name']}",
            context={"task_id": task_id, "task_type": task_config["task_type"]}
        )
    
    return {
        "success": True,
        "created_count": len(created_tasks),
        "skipped_count": len(default_tasks) - len(created_tasks),
        "tasks": created_tasks,
        "message": f"Created {len(created_tasks)} tasks, skipped {len(default_tasks) - len(created_tasks)} existing tasks",
    }


@router.get("/task-types")
async def list_task_types() -> dict[str, Any]:
    """List all available task types."""
    return {
        "task_types": [
            {
                "type": "stock_list",
                "name": "股票列表采集",
                "description": "采集全部A股股票列表",
                "data_source": "akshare",
            },
            {
                "type": "realtime_quote",
                "name": "实时行情采集",
                "description": "采集A股实时行情数据",
                "data_source": "eastmoney",
            },
            {
                "type": "index_quote",
                "name": "指数行情采集",
                "description": "采集主要指数行情数据",
                "data_source": "eastmoney",
            },
            {
                "type": "north_money",
                "name": "北向资金采集",
                "description": "采集北向资金流入流出数据",
                "data_source": "eastmoney",
            },
            {
                "type": "etf_quote",
                "name": "ETF行情采集",
                "description": "采集全部ETF基金行情数据",
                "data_source": "eastmoney",
            },
            {
                "type": "industry_quote",
                "name": "行业板块行情采集",
                "description": "采集行业板块涨跌幅数据",
                "data_source": "eastmoney",
            },
            {
                "type": "concept_quote",
                "name": "概念板块行情采集",
                "description": "采集概念板块涨跌幅数据",
                "data_source": "eastmoney",
            },
            {
                "type": "financial_indicator",
                "name": "财务指标采集",
                "description": "采集股票财务指标数据，包括PE、PB、市值等",
                "data_source": "eastmoney",
            },
            {
                "type": "company_profile",
                "name": "上市公司档案采集与知识图谱构建",
                "description": "采集上市公司完整档案信息，构建知识图谱",
                "data_source": "eastmoney",
            },
        ],
        "total": len(HANDLERS),
    }


@router.post("/queue/start")
async def start_queue() -> dict[str, Any]:
    """Start the task queue processor."""
    manager = get_task_manager()
    await manager.start()
    
    logger.info_with_context("Task queue started", context={})
    
    return {
        "success": True,
        "message": "Task queue started",
    }


@router.post("/queue/stop")
async def stop_queue() -> dict[str, Any]:
    """Stop the task queue processor."""
    manager = get_task_manager()
    await manager.stop()
    
    logger.info_with_context("Task queue stopped", context={})
    
    return {
        "success": True,
        "message": "Task queue stopped",
    }


@router.post("/init-daily-triggers")
async def init_daily_triggers() -> dict[str, Any]:
    """
    Initialize daily scheduled triggers for data collection.
    
    Creates triggers for:
    - Daily company profile collection at 9:00 AM
    - Daily quote collection at 15:30 PM
    - Weekly full data sync on Sunday
    """
    manager = get_task_manager()
    trigger_manager = manager._trigger_manager
    
    if not trigger_manager:
        raise HTTPException(status_code=500, detail="Trigger manager not initialized")
    
    daily_triggers = [
        {
            "name": "每日上市公司档案采集",
            "trigger_type": TriggerType.CRON,
            "task_name": "上市公司档案采集",
            "task_type": "company_profile",
            "task_params": {"limit": 500},
            "cron_expression": "0 9 * * *",
            "description": "每天9:00执行上市公司档案采集与知识图谱构建",
        },
        {
            "name": "每日行情数据采集",
            "trigger_type": TriggerType.CRON,
            "task_name": "每日行情采集",
            "task_type": "realtime_quote",
            "task_params": {},
            "cron_expression": "30 15 * * 1-5",
            "description": "工作日15:30执行行情数据采集",
        },
        {
            "name": "每日指数数据采集",
            "trigger_type": TriggerType.CRON,
            "task_name": "每日指数采集",
            "task_type": "index_quote",
            "task_params": {},
            "cron_expression": "30 15 * * 1-5",
            "description": "工作日15:30执行指数数据采集",
        },
        {
            "name": "每周完整数据同步",
            "trigger_type": TriggerType.CRON,
            "task_name": "每周完整同步",
            "task_type": "company_profile",
            "task_params": {"limit": 0},
            "cron_expression": "0 8 * * 0",
            "description": "每周日8:00执行完整数据同步",
        },
    ]
    
    created_triggers = []
    existing_triggers = trigger_manager.list_triggers()
    existing_names = {t.name for t in existing_triggers}
    
    for trigger_config in daily_triggers:
        if trigger_config["name"] in existing_names:
            continue
        
        trigger = trigger_manager.create_trigger(
            name=trigger_config["name"],
            trigger_type=trigger_config["trigger_type"],
            task_name=trigger_config["task_name"],
            task_type=trigger_config["task_type"],
            task_params=trigger_config["task_params"],
            cron_expression=trigger_config.get("cron_expression"),
        )
        
        if trigger:
            created_triggers.append({
                "trigger_id": trigger.trigger_id,
                "name": trigger_config["name"],
                "trigger_type": trigger_config["trigger_type"].value,
                "cron_expression": trigger_config.get("cron_expression", ""),
            })
            
            logger.info_with_context(
                f"Daily trigger created: {trigger_config['name']}",
                context={"trigger_id": trigger.trigger_id}
            )
    
    return {
        "success": True,
        "created_count": len(created_triggers),
        "skipped_count": len(daily_triggers) - len(created_triggers),
        "triggers": created_triggers,
        "message": f"Created {len(created_triggers)} triggers, skipped {len(daily_triggers) - len(created_triggers)} existing triggers",
    }


@router.get("/knowledge-graph/stats")
async def get_knowledge_graph_stats() -> dict[str, Any]:
    """Get knowledge graph statistics."""
    graph_dir = DATA_DIR / "knowledge_graph"
    
    stats = {
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "total_entities": 0,
        "total_relations": 0,
    }
    
    if graph_dir.exists():
        for file in graph_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                file_stats = {
                    "file": file.name,
                    "timestamp": data.get("timestamp", ""),
                    "entity_count": data.get("statistics", {}).get("entity_count", 0),
                    "relation_count": data.get("statistics", {}).get("relation_count", 0),
                    "entity_types": data.get("statistics", {}).get("entity_types", {}),
                    "relation_types": data.get("statistics", {}).get("relation_types", {}),
                }
                stats["files"].append(file_stats)
                stats["total_entities"] += file_stats["entity_count"]
                stats["total_relations"] += file_stats["relation_count"]
                
            except Exception as e:
                logger.warning(f"Failed to read graph file {file}: {e}")
    
    return stats


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
