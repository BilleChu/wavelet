"""
Task Chain Engine for Data Center.

Provides DAG-based task orchestration with:
- Task dependency management
- Parallel execution of independent tasks
- Condition branching support
- Chain state tracking
- Failure handling and rollback
"""

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from openfinance.core.logging_config import get_logger
from openfinance.datacenter.task.queue import TaskDefinition, TaskStatus

logger = get_logger(__name__)


class ChainStatus(str, Enum):
    """Status of a task chain."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeType(str, Enum):
    """Types of chain nodes."""
    
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"


@dataclass
class ChainNode:
    """A node in the task chain."""
    
    node_id: str
    name: str
    node_type: NodeType = NodeType.TASK
    task_type: str | None = None
    task_params: dict[str, Any] = field(default_factory=dict)
    condition: Callable[[dict], bool] | None = None
    timeout_seconds: float = 300.0
    retry_count: int = 0
    max_retries: int = 3
    
    status: ChainStatus = ChainStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "task_type": self.task_type,
            "task_params": self.task_params,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class ChainEdge:
    """An edge connecting two nodes in the chain."""
    
    edge_id: str
    source_id: str
    target_id: str
    condition: Callable[[dict], bool] | None = None
    label: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
        }


@dataclass
class DataTarget:
    """Represents a data distribution target."""
    
    target_id: str
    target_type: str
    target_name: str
    target_location: str
    status: str = "pending"
    records_synced: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "target_name": self.target_name,
            "target_location": self.target_location,
            "status": self.status,
            "records_synced": self.records_synced,
        }


class TaskChain(BaseModel):
    """Definition of a task chain."""
    
    chain_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = Field(..., description="Chain name")
    description: str = Field(default="", description="Chain description")
    
    nodes: dict[str, ChainNode] = Field(default_factory=dict)
    edges: list[ChainEdge] = Field(default_factory=list)
    
    status: ChainStatus = Field(default=ChainStatus.PENDING)
    
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    
    context: dict[str, Any] = Field(default_factory=dict)
    data_targets: list[DataTarget] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "context": self.context,
            "data_targets": [t.to_dict() for t in self.data_targets],
        }


@dataclass
class ChainResult:
    """Result of chain execution."""
    
    chain_id: str
    status: ChainStatus
    nodes_executed: int
    nodes_succeeded: int
    nodes_failed: int
    total_duration_ms: float
    context: dict[str, Any]
    errors: list[str] = field(default_factory=list)


class TaskChainEngine:
    """
    DAG-based task chain execution engine.
    
    Features:
    - DAG task orchestration
    - Parallel execution of independent tasks
    - Condition branching
    - State tracking and persistence
    - Failure handling
    
    Usage:
        engine = TaskChainEngine()
        
        chain = TaskChain(name="Daily Data Collection")
        
        engine.add_node(chain, ChainNode(
            node_id="preload_companies",
            name="Preload Companies",
            task_type="company_preload",
        ))
        
        engine.add_node(chain, ChainNode(
            node_id="collect_klines",
            name="Collect K-lines",
            task_type="kline_collection",
        ))
        
        engine.add_edge(chain, "preload_companies", "collect_klines")
        
        result = await engine.execute_chain(chain, handler)
    """
    
    def __init__(self) -> None:
        self._chains: dict[str, TaskChain] = {}
        self._handlers: dict[str, Callable[[ChainNode, dict], Awaitable[dict]]] = {}
    
    def register_handler(
        self,
        task_type: str,
        handler: Callable[[ChainNode, dict], Awaitable[dict]],
    ) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler
    
    def add_node(self, chain: TaskChain, node: ChainNode) -> None:
        """Add a node to the chain."""
        chain.nodes[node.node_id] = node
    
    def add_edge(
        self,
        chain: TaskChain,
        source_id: str,
        target_id: str,
        condition: Callable[[dict], bool] | None = None,
        label: str = "",
    ) -> None:
        """Add an edge between two nodes."""
        edge = ChainEdge(
            edge_id=str(uuid.uuid4())[:8],
            source_id=source_id,
            target_id=target_id,
            condition=condition,
            label=label,
        )
        chain.edges.append(edge)
    
    def add_data_target(
        self,
        chain: TaskChain,
        target_type: str,
        target_name: str,
        target_location: str,
    ) -> DataTarget:
        """Add a data distribution target."""
        target = DataTarget(
            target_id=str(uuid.uuid4())[:8],
            target_type=target_type,
            target_name=target_name,
            target_location=target_location,
        )
        chain.data_targets.append(target)
        return target
    
    def validate_dag(self, chain: TaskChain) -> bool:
        """Validate that the chain is a valid DAG (no cycles)."""
        visited = set()
        rec_stack = set()
        
        adj = defaultdict(list)
        for edge in chain.edges:
            adj[edge.source_id].append(edge.target_id)
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in adj[node_id]:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in chain.nodes:
            if node_id not in visited:
                if has_cycle(node_id):
                    return False
        
        return True
    
    def get_dependencies(self, chain: TaskChain, node_id: str) -> list[str]:
        """Get all dependencies of a node."""
        deps = []
        for edge in chain.edges:
            if edge.target_id == node_id:
                deps.append(edge.source_id)
        return deps
    
    def get_dependents(self, chain: TaskChain, node_id: str) -> list[str]:
        """Get all nodes that depend on this node."""
        dependents = []
        for edge in chain.edges:
            if edge.source_id == node_id:
                dependents.append(edge.target_id)
        return dependents
    
    def get_ready_nodes(self, chain: TaskChain) -> list[str]:
        """Get nodes that are ready to execute (all dependencies completed)."""
        ready = []
        for node_id, node in chain.nodes.items():
            if node.status != ChainStatus.PENDING:
                continue
            
            deps = self.get_dependencies(chain, node_id)
            if not deps:
                ready.append(node_id)
                continue
            
            all_deps_completed = all(
                chain.nodes[dep].status == ChainStatus.COMPLETED
                for dep in deps
            )
            
            if all_deps_completed:
                ready.append(node_id)
        
        return ready
    
    async def execute_node(
        self,
        chain: TaskChain,
        node: ChainNode,
    ) -> dict[str, Any]:
        """Execute a single node."""
        node.status = ChainStatus.RUNNING
        node.started_at = datetime.now()
        
        try:
            handler = self._handlers.get(node.task_type)
            if not handler:
                raise ValueError(f"No handler for task type: {node.task_type}")
            
            result = await asyncio.wait_for(
                handler(node, chain.context),
                timeout=node.timeout_seconds,
            )
            
            node.result = result
            node.status = ChainStatus.COMPLETED
            node.completed_at = datetime.now()
            
            if result:
                chain.context.update(result)
            
            logger.info_with_context(
                "Node completed",
                context={
                    "chain_id": chain.chain_id,
                    "node_id": node.node_id,
                    "node_name": node.name,
                }
            )
            
            return result
            
        except asyncio.TimeoutError:
            node.error = f"Node timed out after {node.timeout_seconds}s"
            node.status = ChainStatus.FAILED
            node.completed_at = datetime.now()
            raise
            
        except Exception as e:
            node.retry_count += 1
            if node.retry_count < node.max_retries:
                node.status = ChainStatus.PENDING
                logger.warning_with_context(
                    "Node failed, will retry",
                    context={
                        "chain_id": chain.chain_id,
                        "node_id": node.node_id,
                        "error": str(e),
                        "retry_count": node.retry_count,
                    }
                )
                raise
            
            node.error = str(e)
            node.status = ChainStatus.FAILED
            node.completed_at = datetime.now()
            raise
    
    async def execute_chain(
        self,
        chain: TaskChain,
        stop_on_failure: bool = True,
    ) -> ChainResult:
        """
        Execute the entire chain.
        
        Args:
            chain: The task chain to execute
            stop_on_failure: Whether to stop on first failure
            
        Returns:
            ChainResult with execution statistics
        """
        if not self.validate_dag(chain):
            return ChainResult(
                chain_id=chain.chain_id,
                status=ChainStatus.FAILED,
                nodes_executed=0,
                nodes_succeeded=0,
                nodes_failed=0,
                total_duration_ms=0,
                context=chain.context,
                errors=["Chain contains cycles, not a valid DAG"],
            )
        
        chain.status = ChainStatus.RUNNING
        chain.started_at = datetime.now()
        
        self._chains[chain.chain_id] = chain
        
        nodes_executed = 0
        nodes_succeeded = 0
        nodes_failed = 0
        errors: list[str] = []
        
        start_time = datetime.now()
        
        try:
            while True:
                ready_nodes = self.get_ready_nodes(chain)
                
                if not ready_nodes:
                    break
                
                tasks = [
                    self.execute_node(chain, chain.nodes[node_id])
                    for node_id in ready_nodes
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for node_id, result in zip(ready_nodes, results):
                    nodes_executed += 1
                    if isinstance(result, Exception):
                        nodes_failed += 1
                        errors.append(f"{node_id}: {str(result)}")
                        if stop_on_failure:
                            chain.status = ChainStatus.FAILED
                            break
                    else:
                        nodes_succeeded += 1
                
                if chain.status == ChainStatus.FAILED:
                    break
            
            if chain.status == ChainStatus.RUNNING:
                chain.status = ChainStatus.COMPLETED
            
        except Exception as e:
            chain.status = ChainStatus.FAILED
            errors.append(str(e))
        
        chain.completed_at = datetime.now()
        duration_ms = (chain.completed_at - start_time).total_seconds() * 1000
        
        for target in chain.data_targets:
            target.status = "synced" if chain.status == ChainStatus.COMPLETED else "failed"
        
        return ChainResult(
            chain_id=chain.chain_id,
            status=chain.status,
            nodes_executed=nodes_executed,
            nodes_succeeded=nodes_succeeded,
            nodes_failed=nodes_failed,
            total_duration_ms=duration_ms,
            context=chain.context,
            errors=errors,
        )
    
    def get_chain(self, chain_id: str) -> TaskChain | None:
        """Get a chain by ID."""
        return self._chains.get(chain_id)
    
    def get_chain_status(self, chain_id: str) -> dict[str, Any] | None:
        """Get the status of a chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return None
        return chain.to_dict()
    
    def list_chains(self) -> list[dict[str, Any]]:
        """List all chains."""
        return [chain.to_dict() for chain in self._chains.values()]
    
    async def cancel_chain(self, chain_id: str) -> bool:
        """Cancel a running chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return False
        
        chain.status = ChainStatus.CANCELLED
        chain.completed_at = datetime.now()
        
        for node in chain.nodes.values():
            if node.status == ChainStatus.RUNNING:
                node.status = ChainStatus.CANCELLED
                node.completed_at = datetime.now()
        
        return True


def create_default_chain() -> TaskChain:
    """Create a default daily data collection chain."""
    chain = TaskChain(
        chain_id="default_daily",
        name="Daily Data Collection",
        description="Daily stock data collection workflow",
    )
    
    chain.nodes = {
        "preload_companies": ChainNode(
            node_id="preload_companies",
            name="Preload Companies",
            node_type=NodeType.TASK,
            task_type="company_preload",
        ),
        "collect_klines": ChainNode(
            node_id="collect_klines",
            name="Collect K-lines",
            node_type=NodeType.TASK,
            task_type="kline_collection",
        ),
        "collect_financial": ChainNode(
            node_id="collect_financial",
            name="Collect Financial Indicators",
            node_type=NodeType.TASK,
            task_type="financial_collection",
        ),
        "collect_money_flow": ChainNode(
            node_id="collect_money_flow",
            name="Collect Money Flow",
            node_type=NodeType.TASK,
            task_type="money_flow_collection",
        ),
        "sync_to_graph": ChainNode(
            node_id="sync_to_graph",
            name="Sync to Knowledge Graph",
            node_type=NodeType.TASK,
            task_type="graph_sync",
        ),
    }
    
    chain.edges = [
        ChainEdge(edge_id="e1", source_id="preload_companies", target_id="collect_klines"),
        ChainEdge(edge_id="e2", source_id="preload_companies", target_id="collect_financial"),
        ChainEdge(edge_id="e3", source_id="preload_companies", target_id="collect_money_flow"),
        ChainEdge(edge_id="e4", source_id="collect_klines", target_id="sync_to_graph"),
        ChainEdge(edge_id="e5", source_id="collect_financial", target_id="sync_to_graph"),
        ChainEdge(edge_id="e6", source_id="collect_money_flow", target_id="sync_to_graph"),
    ]
    
    chain.data_targets = [
        DataTarget(
            target_id="pg_main",
            target_type="postgresql",
            target_name="Main Database",
            target_location="openfinance.stock_*",
        ),
        DataTarget(
            target_id="neo4j_graph",
            target_type="neo4j",
            target_name="Knowledge Graph",
            target_location="entities, relations",
        ),
        DataTarget(
            target_id="redis_cache",
            target_type="redis",
            target_name="Cache Layer",
            target_location="realtime:*",
        ),
    ]
    
    return chain


class ChainVisualizer:
    """
    Visualizer for task chains.
    
    Provides methods to generate visual representations
    of DAG task chains for monitoring and debugging.
    """
    
    @staticmethod
    def to_dagre(chain: TaskChain) -> dict[str, Any]:
        """
        Export chain to Dagre.js format for frontend visualization.
        
        Returns:
            Dict with nodes and edges in Dagre format
        """
        nodes = []
        for node_id, node in chain.nodes.items():
            nodes.append({
                "id": node_id,
                "label": node.name,
                "type": node.node_type.value,
                "status": node.status.value,
                "taskType": node.task_type,
                "config": {
                    "x": 0,
                    "y": 0,
                },
                "data": {
                    "startedAt": node.started_at.isoformat() if node.started_at else None,
                    "completedAt": node.completed_at.isoformat() if node.completed_at else None,
                    "error": node.error,
                    "result": node.result,
                },
            })
        
        edges = []
        for edge in chain.edges:
            edges.append({
                "id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.label,
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "config": {
                "rankdir": "TB",
                "align": "UL",
                "nodeSep": 50,
                "edgeSep": 10,
                "rankSep": 100,
            },
        }
    
    @staticmethod
    def to_mermaid(chain: TaskChain) -> str:
        """
        Export chain to Mermaid diagram format.
        
        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]
        
        for node_id, node in chain.nodes.items():
            status_color = {
                ChainStatus.PENDING: "",
                ChainStatus.RUNNING: ":::running",
                ChainStatus.COMPLETED: ":::completed",
                ChainStatus.FAILED: ":::failed",
                ChainStatus.CANCELLED: ":::cancelled",
            }.get(node.status, "")
            
            lines.append(f'    {node_id}["{node.name}"]{status_color}')
        
        for edge in chain.edges:
            label = f"|{edge.label}|" if edge.label else ""
            lines.append(f"    {edge.source_id} -->{label} {edge.target_id}")
        
        lines.append("")
        lines.append("    classDef running fill:#ffd700,stroke:#333")
        lines.append("    classDef completed fill:#90ee90,stroke:#333")
        lines.append("    classDef failed fill:#ff6b6b,stroke:#333")
        lines.append("    classDef cancelled fill:#d3d3d3,stroke:#333")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_dot(chain: TaskChain) -> str:
        """
        Export chain to Graphviz DOT format.
        
        Returns:
            DOT format string
        """
        lines = ["digraph TaskChain {"]
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box, style=filled];")
        lines.append("")
        
        status_colors = {
            ChainStatus.PENDING: "lightgray",
            ChainStatus.RUNNING: "gold",
            ChainStatus.COMPLETED: "lightgreen",
            ChainStatus.FAILED: "lightcoral",
            ChainStatus.CANCELLED: "gray",
        }
        
        for node_id, node in chain.nodes.items():
            color = status_colors.get(node.status, "white")
            lines.append(f'    "{node_id}" [label="{node.name}", fillcolor={color}];')
        
        lines.append("")
        for edge in chain.edges:
            label = f' [label="{edge.label}"]' if edge.label else ""
            lines.append(f'    "{edge.source_id}" -> "{edge.target_id}"{label};')
        
        lines.append("}")
        return "\n".join(lines)


class ChainBuilder:
    """
    Fluent builder for creating task chains.
    
    Usage:
        chain = (ChainBuilder("my_chain")
            .add_task("fetch", "data_fetcher")
            .add_task("process", "data_processor")
            .depends_on("fetch")
            .add_task("save", "data_sink")
            .depends_on("process")
            .build())
    """
    
    def __init__(self, name: str, description: str = "") -> None:
        self._chain = TaskChain(
            name=name,
            description=description,
        )
        self._current_node: str | None = None
        self._node_counter = 0
        self._edge_counter = 0
    
    def add_task(
        self,
        name: str,
        task_type: str,
        params: dict[str, Any] | None = None,
        timeout_seconds: float = 300.0,
        max_retries: int = 3,
    ) -> "ChainBuilder":
        """Add a task node to the chain."""
        self._node_counter += 1
        node_id = f"node_{self._node_counter}"
        
        node = ChainNode(
            node_id=node_id,
            name=name,
            node_type=NodeType.TASK,
            task_type=task_type,
            task_params=params or {},
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        
        self._chain.nodes[node_id] = node
        self._current_node = node_id
        
        return self
    
    def add_parallel(
        self,
        name: str,
        tasks: list[dict[str, Any]],
    ) -> "ChainBuilder":
        """
        Add a parallel execution node.
        
        Args:
            name: Node name
            tasks: List of task definitions to execute in parallel
        """
        self._node_counter += 1
        node_id = f"node_{self._node_counter}"
        
        node = ChainNode(
            node_id=node_id,
            name=name,
            node_type=NodeType.PARALLEL,
            task_params={"tasks": tasks},
        )
        
        self._chain.nodes[node_id] = node
        self._current_node = node_id
        
        return self
    
    def add_condition(
        self,
        name: str,
        condition_type: str,
        branches: dict[str, str],
    ) -> "ChainBuilder":
        """
        Add a conditional branch node.
        
        Args:
            name: Node name
            condition_type: Type of condition to evaluate
            branches: Dict mapping condition results to target node names
        """
        self._node_counter += 1
        node_id = f"node_{self._node_counter}"
        
        node = ChainNode(
            node_id=node_id,
            name=name,
            node_type=NodeType.CONDITION,
            task_params={
                "condition_type": condition_type,
                "branches": branches,
            },
        )
        
        self._chain.nodes[node_id] = node
        self._current_node = node_id
        
        return self
    
    def depends_on(self, *node_names: str) -> "ChainBuilder":
        """Set dependencies for the current node."""
        if self._current_node is None:
            raise ValueError("No current node to set dependencies for")
        
        for node_name in node_names:
            source_id = self._find_node_by_name(node_name)
            if source_id:
                self._edge_counter += 1
                edge = ChainEdge(
                    edge_id=f"edge_{self._edge_counter}",
                    source_id=source_id,
                    target_id=self._current_node,
                )
                self._chain.edges.append(edge)
        
        return self
    
    def with_data_target(
        self,
        target_type: str,
        target_name: str,
        target_location: str,
    ) -> "ChainBuilder":
        """Add a data target to the chain."""
        target = DataTarget(
            target_id=f"target_{len(self._chain.data_targets) + 1}",
            target_type=target_type,
            target_name=target_name,
            target_location=target_location,
        )
        self._chain.data_targets.append(target)
        return self
    
    def with_context(self, key: str, value: Any) -> "ChainBuilder":
        """Add context data to the chain."""
        self._chain.context[key] = value
        return self
    
    def _find_node_by_name(self, name: str) -> str | None:
        """Find a node ID by name."""
        for node_id, node in self._chain.nodes.items():
            if node.name == name:
                return node_id
        return None
    
    def build(self) -> TaskChain:
        """Build and validate the chain."""
        engine = TaskChainEngine()
        if not engine.validate_dag(self._chain):
            raise ValueError("Chain contains cycles, not a valid DAG")
        return self._chain


def chain_from_dict(data: dict[str, Any]) -> TaskChain:
    """
    Create a TaskChain from a dictionary configuration.
    
    Args:
        data: Dictionary with chain configuration
        
    Returns:
        TaskChain instance
    """
    chain = TaskChain(
        chain_id=data.get("chain_id", str(uuid.uuid4())[:8]),
        name=data["name"],
        description=data.get("description", ""),
    )
    
    for node_data in data.get("nodes", []):
        node = ChainNode(
            node_id=node_data["id"],
            name=node_data["name"],
            node_type=NodeType(node_data.get("type", "task")),
            task_type=node_data.get("task_type"),
            task_params=node_data.get("params", {}),
            timeout_seconds=node_data.get("timeout_seconds", 300.0),
            max_retries=node_data.get("max_retries", 3),
        )
        chain.nodes[node.node_id] = node
    
    for edge_data in data.get("edges", []):
        edge = ChainEdge(
            edge_id=edge_data.get("id", str(uuid.uuid4())[:8]),
            source_id=edge_data["source"],
            target_id=edge_data["target"],
            label=edge_data.get("label", ""),
        )
        chain.edges.append(edge)
    
    for target_data in data.get("data_targets", []):
        target = DataTarget(
            target_id=target_data.get("id", str(uuid.uuid4())[:8]),
            target_type=target_data["type"],
            target_name=target_data["name"],
            target_location=target_data["location"],
        )
        chain.data_targets.append(target)
    
    chain.context = data.get("context", {})
    
    return chain
