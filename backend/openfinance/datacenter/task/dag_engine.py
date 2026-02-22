"""
Unified DAG Engine for Data Center.

Consolidates task chain engine, DAG manager, and pipeline builder into a single,
cohesive module for DAG-based task orchestration.

Features:
- Task dependency management
- Parallel execution of independent tasks
- Condition branching support
- State tracking and persistence
- Failure handling with retry
- Visualization export (Mermaid, JSON for Canvas)
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """Status of a task or chain."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    SKIPPED = "skipped"


class NodeType(str, Enum):
    """Types of DAG nodes."""
    
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    START = "start"
    END = "end"


class TaskPriority(int, Enum):
    """Task priority levels."""
    
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class DAGNode:
    """A node in the DAG."""
    
    node_id: str
    name: str
    node_type: NodeType = NodeType.TASK
    task_type: str | None = None
    task_params: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    
    timeout_seconds: float = 300.0
    max_retries: int = 3
    
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: float = 0.0
    
    position: dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    
    def is_ready(self, completed_nodes: set[str]) -> bool:
        """Check if all dependencies are satisfied."""
        return all(dep in completed_nodes for dep in self.dependencies)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "name": self.name,
            "type": self.node_type.value,
            "taskType": self.task_type,
            "params": self.task_params,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "retryCount": self.retry_count,
            "error": self.error,
            "progress": self.progress,
            "position": self.position,
        }
    
    def to_canvas_node(self) -> dict[str, Any]:
        """Convert to canvas display format."""
        return {
            "id": self.node_id,
            "type": "taskNode",
            "position": self.position,
            "data": {
                "label": self.name,
                "status": self.status.value,
                "taskType": self.task_type,
                "progress": self.progress,
                "error": self.error,
            },
        }


@dataclass
class DAGEdge:
    """An edge connecting two nodes in the DAG."""
    
    edge_id: str
    source_id: str
    target_id: str
    label: str = ""
    condition: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.edge_id,
            "source": self.source_id,
            "target": self.target_id,
            "label": self.label,
            "condition": self.condition,
        }
    
    def to_canvas_edge(self) -> dict[str, Any]:
        """Convert to canvas display format."""
        return {
            "id": self.edge_id,
            "source": self.source_id,
            "target": self.target_id,
            "label": self.label,
            "animated": True,
            "style": {"stroke": "#1890ff"},
        }


class DAG(BaseModel):
    """Definition of a DAG (Directed Acyclic Graph)."""
    
    dag_id: str = Field(default_factory=lambda: f"dag_{uuid.uuid4().hex[:8]}")
    name: str = Field(..., description="DAG name")
    description: str = Field(default="", description="DAG description")
    
    nodes: dict[str, DAGNode] = Field(default_factory=dict)
    edges: list[DAGEdge] = Field(default_factory=list)
    
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True
    
    def add_node(self, node: DAGNode) -> None:
        """Add a node to the DAG."""
        self.nodes[node.node_id] = node
        
        for dep_id in node.dependencies:
            if dep_id in self.nodes:
                self.nodes[dep_id].dependents.append(node.node_id)
        
        self._invalidate_cache()
    
    def add_edge(self, source_id: str, target_id: str, label: str = "") -> DAGEdge:
        """Add an edge between two nodes."""
        edge_id = f"edge_{source_id}_{target_id}"
        edge = DAGEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            label=label,
        )
        self.edges.append(edge)
        
        if source_id in self.nodes and target_id in self.nodes:
            if target_id not in self.nodes[source_id].dependents:
                self.nodes[source_id].dependents.append(target_id)
            if source_id not in self.nodes[target_id].dependencies:
                self.nodes[target_id].dependencies.append(source_id)
        
        self._invalidate_cache()
        return edge
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate the DAG for cycles and missing dependencies."""
        errors = []
        
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    errors.append(f"Node {node_id} depends on missing node {dep_id}")
        
        if self._has_cycle():
            errors.append("DAG contains a cycle")
        
        return len(errors) == 0, errors
    
    def _has_cycle(self) -> bool:
        """Check if the DAG has a cycle using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {node_id: WHITE for node_id in self.nodes}
        
        def dfs(node_id: str) -> bool:
            colors[node_id] = GRAY
            
            for dep_id in self.nodes[node_id].dependencies:
                if dep_id not in colors:
                    continue
                
                if colors[dep_id] == GRAY:
                    return True
                if colors[dep_id] == WHITE and dfs(dep_id):
                    return True
            
            colors[node_id] = BLACK
            return False
        
        for node_id in self.nodes:
            if colors[node_id] == WHITE:
                if dfs(node_id):
                    return True
        
        return False
    
    _execution_order: list[str] | None = None
    
    def _invalidate_cache(self) -> None:
        """Invalidate cached execution order."""
        self._execution_order = None
    
    def get_execution_order(self) -> list[str]:
        """Get topological order for execution."""
        if self._execution_order:
            return self._execution_order
        
        in_degree = {node_id: len(node.dependencies) for node_id, node in self.nodes.items()}
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        
        order = []
        while queue:
            queue.sort(key=lambda n: self.nodes[n].priority.value)
            node_id = queue.pop(0)
            order.append(node_id)
            
            for dependent_id in self.nodes[node_id].dependents:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        self._execution_order = order
        return order
    
    def get_ready_nodes(self, completed: set[str], running: set[str]) -> list[str]:
        """Get nodes that are ready to execute."""
        ready = []
        for node_id, node in self.nodes.items():
            if node.status == TaskStatus.PENDING and node.is_ready(completed):
                ready.append(node_id)
        
        ready.sort(key=lambda n: self.nodes[n].priority.value)
        return ready
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dagId": self.dag_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "createdAt": self.created_at.isoformat(),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }
    
    def to_canvas_format(self) -> dict[str, Any]:
        """Convert to format for frontend canvas display."""
        self._auto_layout()
        
        return {
            "nodes": [node.to_canvas_node() for node in self.nodes.values()],
            "edges": [edge.to_canvas_edge() for edge in self.edges],
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "metadata": {
                "dagId": self.dag_id,
                "name": self.name,
                "description": self.description,
                "status": self.status.value,
                "totalNodes": len(self.nodes),
                "totalEdges": len(self.edges),
            },
        }
    
    def to_mermaid(self) -> str:
        """Export DAG to Mermaid diagram format."""
        lines = ["graph TD"]
        
        for node_id, node in self.nodes.items():
            status_color = {
                TaskStatus.PENDING: "",
                TaskStatus.RUNNING: ":::running",
                TaskStatus.COMPLETED: ":::completed",
                TaskStatus.FAILED: ":::failed",
                TaskStatus.SKIPPED: ":::skipped",
            }.get(node.status, "")
            
            lines.append(f"    {node_id}[\"{node.name}\"]{status_color}")
        
        for edge in self.edges:
            label = f"|{edge.label}|" if edge.label else ""
            lines.append(f"    {edge.source_id} -->{label} {edge.target_id}")
        
        lines.append("")
        lines.append("    classDef running fill:#1890ff,color:#fff")
        lines.append("    classDef completed fill:#52c41a,color:#fff")
        lines.append("    classDef failed fill:#ff4d4f,color:#fff")
        lines.append("    classDef skipped fill:#d9d9d9,color:#666")
        
        return "\n".join(lines)
    
    def _auto_layout(self) -> None:
        """Auto-layout nodes for display."""
        levels: dict[str, int] = {}
        
        def get_level(node_id: str) -> int:
            if node_id in levels:
                return levels[node_id]
            
            node = self.nodes.get(node_id)
            if not node or not node.dependencies:
                levels[node_id] = 0
                return 0
            
            max_dep_level = max(get_level(dep) for dep in node.dependencies)
            levels[node_id] = max_dep_level + 1
            return levels[node_id]
        
        for node_id in self.nodes:
            get_level(node_id)
        
        level_nodes: dict[int, list[str]] = defaultdict(list)
        for node_id, level in levels.items():
            level_nodes[level].append(node_id)
        
        max_level = max(levels.values()) if levels else 0
        node_height = 100
        node_width = 200
        start_x = 100
        start_y = 100
        
        for level, node_ids in level_nodes.items():
            y = start_y + level * node_height
            total_width = len(node_ids) * node_width
            start_x_level = start_x - total_width / 2
            
            for i, node_id in enumerate(node_ids):
                self.nodes[node_id].position = {
                    "x": start_x_level + i * node_width + node_width / 2,
                    "y": y,
                }


class DAGExecutionLog(BaseModel):
    """Log entry for DAG execution."""
    
    log_id: str = Field(default_factory=lambda: f"log_{uuid.uuid4().hex[:12]}")
    dag_id: str
    node_id: str | None = None
    event: str
    status: TaskStatus
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class DAGEngine:
    """
    Unified DAG Engine for task orchestration.
    
    Features:
    - DAG validation and execution
    - Parallel execution with concurrency control
    - Retry with exponential backoff
    - State persistence
    - Real-time progress tracking
    - Canvas visualization support
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        default_timeout: int = 300,
        enable_persistence: bool = False,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.enable_persistence = enable_persistence
        
        self._dags: dict[str, DAG] = {}
        self._executors: dict[str, Callable] = {}
        self._logs: list[DAGExecutionLog] = []
        self._execution_history: dict[str, list[dict]] = defaultdict(list)
    
    def register_dag(self, dag: DAG) -> None:
        """Register a DAG for execution."""
        is_valid, errors = dag.validate()
        if not is_valid:
            raise ValueError(f"Invalid DAG: {errors}")
        
        self._dags[dag.dag_id] = dag
        logger.info(f"Registered DAG: {dag.name} ({dag.dag_id}) with {len(dag.nodes)} nodes")
    
    def register_executor(self, task_type: str, executor: Callable) -> None:
        """Register an executor function for a task type."""
        self._executors[task_type] = executor
    
    async def execute_dag(
        self,
        dag_id: str,
        context: dict[str, Any] | None = None,
        on_progress: Callable[[str, str, float], None] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a DAG with all its nodes.
        
        Args:
            dag_id: ID of the DAG to execute
            context: Execution context shared across tasks
            on_progress: Callback for progress updates (dag_id, node_id, progress)
        
        Returns:
            Execution result with status and metrics
        """
        if dag_id not in self._dags:
            raise ValueError(f"DAG not found: {dag_id}")
        
        dag = self._dags[dag_id]
        context = context or {}
        
        dag.status = TaskStatus.RUNNING
        dag.started_at = datetime.now()
        
        self._log(dag_id, None, "dag_started", TaskStatus.RUNNING, f"DAG {dag.name} started")
        
        completed: set[str] = set()
        running: set[str] = set()
        failed: set[str] = set()
        results: dict[str, Any] = {}
        
        while len(completed) + len(failed) < len(dag.nodes):
            ready_nodes = dag.get_ready_nodes(completed, running)
            
            while len(running) < self.max_concurrent_tasks and ready_nodes:
                node_id = ready_nodes.pop(0)
                node = dag.nodes[node_id]
                node.status = TaskStatus.RUNNING
                node.started_at = datetime.now()
                running.add(node_id)
                
                self._log(dag_id, node_id, "node_started", TaskStatus.RUNNING, f"Node {node.name} started")
                
                asyncio.create_task(
                    self._execute_node(dag_id, node_id, context, results, completed, running, failed, on_progress)
                )
            
            if running:
                await asyncio.sleep(0.1)
            else:
                break
        
        dag.completed_at = datetime.now()
        
        if failed:
            dag.status = TaskStatus.FAILED
            self._log(dag_id, None, "dag_failed", TaskStatus.FAILED, f"DAG failed with {len(failed)} failed nodes")
        else:
            dag.status = TaskStatus.COMPLETED
            self._log(dag_id, None, "dag_completed", TaskStatus.COMPLETED, f"DAG completed successfully")
        
        duration_ms = int((dag.completed_at - dag.started_at).total_seconds() * 1000)
        
        return {
            "dag_id": dag_id,
            "status": dag.status.value,
            "completed_nodes": len(completed),
            "failed_nodes": len(failed),
            "total_nodes": len(dag.nodes),
            "duration_ms": duration_ms,
            "results": results,
        }
    
    async def _execute_node(
        self,
        dag_id: str,
        node_id: str,
        context: dict[str, Any],
        results: dict[str, Any],
        completed: set[str],
        running: set[str],
        failed: set[str],
        on_progress: Callable | None,
    ) -> None:
        """Execute a single node with retry logic."""
        dag = self._dags[dag_id]
        node = dag.nodes[node_id]
        
        try:
            executor = self._executors.get(node.task_type)
            if not executor:
                raise ValueError(f"No executor for task type: {node.task_type}")
            
            node_context = {**context, "task_type": node.task_type}
            node_params = {**node.task_params, "task_type": node.task_type}
            
            if asyncio.iscoroutinefunction(executor):
                result = await asyncio.wait_for(
                    executor(node_params, node_context),
                    timeout=node.timeout_seconds
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, executor, node_params, node_context
                )
            
            node.status = TaskStatus.COMPLETED
            node.completed_at = datetime.now()
            node.result = result
            node.progress = 1.0
            results[node_id] = result
            
            completed.add(node_id)
            
            self._log(dag_id, node_id, "node_completed", TaskStatus.COMPLETED, f"Node {node.name} completed")
            
            if on_progress:
                on_progress(dag_id, node_id, 1.0)
            
        except asyncio.TimeoutError:
            error_msg = f"Node timeout after {node.timeout_seconds}s"
            await self._handle_node_failure(dag, node, error_msg, failed)
            
        except Exception as e:
            error_msg = str(e)
            await self._handle_node_failure(dag, node, error_msg, failed)
        
        finally:
            running.discard(node_id)
    
    async def _handle_node_failure(
        self,
        dag: DAG,
        node: DAGNode,
        error_msg: str,
        failed: set[str],
    ) -> None:
        """Handle node failure with retry logic."""
        node.retry_count += 1
        
        if node.retry_count < node.max_retries:
            backoff = min(2 ** node.retry_count, 60)
            logger.warning(f"Node {node.node_id} failed, retrying in {backoff}s")
            
            await asyncio.sleep(backoff)
            
            node.status = TaskStatus.PENDING
            node.error = None
        else:
            node.status = TaskStatus.FAILED
            node.completed_at = datetime.now()
            node.error = error_msg
            failed.add(node.node_id)
            
            self._log(dag.dag_id, node.node_id, "node_failed", TaskStatus.FAILED, error_msg)
            
            logger.error(f"Node {node.node_id} failed after {node.retry_count} retries: {error_msg}")
    
    def _log(
        self,
        dag_id: str,
        node_id: str | None,
        event: str,
        status: TaskStatus,
        message: str | None = None,
    ) -> None:
        """Add execution log entry."""
        log = DAGExecutionLog(
            dag_id=dag_id,
            node_id=node_id,
            event=event,
            status=status,
            message=message,
        )
        self._logs.append(log)
    
    def get_dag(self, dag_id: str) -> DAG | None:
        """Get a registered DAG."""
        return self._dags.get(dag_id)
    
    def get_dag_status(self, dag_id: str) -> dict[str, Any]:
        """Get current status of a DAG."""
        dag = self._dags.get(dag_id)
        if not dag:
            return {"error": "DAG not found"}
        
        status_counts = defaultdict(int)
        for node in dag.nodes.values():
            status_counts[node.status.value] += 1
        
        return {
            "id": dag_id,
            "dagId": dag_id,
            "name": dag.name,
            "description": dag.description,
            "status": dag.status.value,
            "totalTasks": len(dag.nodes),
            "totalNodes": len(dag.nodes),
            "statusCounts": dict(status_counts),
            "executionOrder": dag.get_execution_order(),
            "schedule": dag.metadata.get("schedule"),
            "timezone": dag.metadata.get("timezone", "Asia/Shanghai"),
        }
    
    def get_dag_canvas(self, dag_id: str) -> dict[str, Any]:
        """Get DAG in canvas display format."""
        dag = self._dags.get(dag_id)
        if not dag:
            return {"error": "DAG not found"}
        
        return dag.to_canvas_format()
    
    def get_logs(
        self,
        dag_id: str | None = None,
        node_id: str | None = None,
        limit: int = 100,
    ) -> list[DAGExecutionLog]:
        """Get execution logs with filtering."""
        logs = self._logs
        
        if dag_id:
            logs = [l for l in logs if l.dag_id == dag_id]
        if node_id:
            logs = [l for l in logs if l.node_id == node_id]
        
        return logs[-limit:]
    
    def list_dags(self) -> list[dict[str, Any]]:
        """List all registered DAGs."""
        return [self.get_dag_status(dag_id) for dag_id in self._dags]


class DAGBuilder:
    """
    Fluent builder for creating DAGs.
    
    Example:
        dag = (DAGBuilder("my_dag")
            .description("My data pipeline")
            .add_task("extract", "Extract Data", "data_extract", {"source": "db"})
            .add_task("transform", "Transform Data", "data_transform", {"type": "clean"}, depends_on=["extract"])
            .add_task("load", "Load Data", "data_load", {"target": "warehouse"}, depends_on=["transform"])
            .build())
    """
    
    def __init__(self, name: str):
        self._name = name
        self._description = ""
        self._nodes: list[DAGNode] = []
        self._edges: list[tuple[str, str, str]] = []
    
    def description(self, desc: str) -> "DAGBuilder":
        """Set DAG description."""
        self._description = desc
        return self
    
    def add_task(
        self,
        task_id: str,
        name: str,
        task_type: str,
        params: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 300.0,
        max_retries: int = 3,
    ) -> "DAGBuilder":
        """Add a task node to the DAG."""
        node = DAGNode(
            node_id=task_id,
            name=name,
            node_type=NodeType.TASK,
            task_type=task_type,
            task_params=params or {},
            priority=priority,
            timeout_seconds=timeout,
            max_retries=max_retries,
            dependencies=depends_on or [],
        )
        self._nodes.append(node)
        
        if depends_on:
            for dep_id in depends_on:
                self._edges.append((dep_id, task_id, ""))
        
        return self
    
    def add_condition(
        self,
        condition_id: str,
        name: str,
        condition: str,
        true_target: str,
        false_target: str,
    ) -> "DAGBuilder":
        """Add a condition node to the DAG."""
        node = DAGNode(
            node_id=condition_id,
            name=name,
            node_type=NodeType.CONDITION,
            task_params={"condition": condition},
        )
        self._nodes.append(node)
        
        self._edges.append((condition_id, true_target, "true"))
        self._edges.append((condition_id, false_target, "false"))
        
        return self
    
    def build(self, dag_id: str | None = None) -> DAG:
        """Build the DAG."""
        dag = DAG(name=self._name, description=self._description)
        
        if dag_id:
            dag.dag_id = dag_id
        
        for node in self._nodes:
            dag.add_node(node)
        
        for source_id, target_id, label in self._edges:
            if source_id in dag.nodes and target_id in dag.nodes:
                dag.add_edge(source_id, target_id, label)
        
        return dag
