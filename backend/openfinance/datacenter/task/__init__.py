"""Task management module for Data Center."""

from openfinance.datacenter.task.queue import (
    TaskQueue,
    TaskPriority,
    TaskStatus,
    TaskDefinition,
    TaskExecution,
)
from openfinance.datacenter.task.trigger import (
    TriggerManager,
    TriggerType,
    TriggerStatus,
    TriggerDefinition,
)
from openfinance.datacenter.task.manager import TaskManager
from openfinance.datacenter.task.registry import (
    TaskExecutor,
    TaskMetadata,
    TaskProgress,
    TaskCategory,
    TaskPriority as ExecutorPriority,
    TaskParameter,
    TaskOutput,
    task_executor,
    TaskRegistry,
    get_task_info,
    get_all_task_types,
    get_tasks_by_category,
)
from openfinance.datacenter.task.executors import register_all_executors
from openfinance.datacenter.task.additional_executors import register_additional_executors
from openfinance.datacenter.task.dag_engine import (
    DAG,
    DAGEngine,
    DAGBuilder,
    DAGNode,
    DAGEdge,
    NodeType,
)
from openfinance.datacenter.task.lineage import (
    DataLineage,
    LineageNode,
    LineageEdge,
    LineageTracker,
    LineageNodeType,
    LineageEdgeType,
    LineagePath,
)

def get_handler(task_type: str):
    """Get executor for task type."""
    return TaskRegistry.get_executor(task_type)

def get_all_handlers() -> dict:
    """Get all registered handlers."""
    return TaskRegistry._executors.copy()

HANDLERS = property(get_all_handlers)

__all__ = [
    "TaskQueue",
    "TaskPriority",
    "TaskStatus",
    "TaskDefinition",
    "TaskExecution",
    "TriggerManager",
    "TriggerType",
    "TriggerStatus",
    "TriggerDefinition",
    "TaskManager",
    "TaskExecutor",
    "TaskMetadata",
    "TaskProgress",
    "TaskCategory",
    "ExecutorPriority",
    "TaskParameter",
    "TaskOutput",
    "task_executor",
    "TaskRegistry",
    "get_task_info",
    "get_all_task_types",
    "get_tasks_by_category",
    "get_handler",
    "get_all_handlers",
    "HANDLERS",
    "register_all_executors",
    "register_additional_executors",
    "DAG",
    "DAGEngine",
    "DAGBuilder",
    "DAGNode",
    "DAGEdge",
    "NodeType",
    "DataLineage",
    "LineageNode",
    "LineageEdge",
    "LineageTracker",
    "LineageNodeType",
    "LineageEdgeType",
    "LineagePath",
]
