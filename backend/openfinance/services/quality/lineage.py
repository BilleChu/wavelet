"""
Data Lineage Tracking for Data Center.

Provides comprehensive data lineage tracking with:
- Source tracking
- Transformation tracking
- Dependency tracking
- Impact analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from collections import defaultdict

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LineageNodeType(str, Enum):
    """Types of lineage nodes."""
    
    SOURCE = "source"
    TRANSFORM = "transform"
    SINK = "sink"
    DATASET = "dataset"
    TABLE = "table"
    COLUMN = "column"
    JOB = "job"
    PIPELINE = "pipeline"


class LineageEdgeType(str, Enum):
    """Types of lineage edges."""
    
    DERIVES_FROM = "derives_from"
    TRANSFORMS = "transforms"
    CONSUMES = "consumes"
    PRODUCES = "produces"
    DEPENDS_ON = "depends_on"


@dataclass
class LineageNode:
    """A node in the lineage graph."""
    
    node_id: str
    name: str
    node_type: LineageNodeType
    
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class LineageEdge:
    """An edge in the lineage graph."""
    
    edge_id: str
    source_id: str
    target_id: str
    edge_type: LineageEdgeType
    
    description: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }


class LineagePath(BaseModel):
    """A path in the lineage graph."""
    
    path_id: str = Field(..., description="Unique path identifier")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    
    nodes: list[str] = Field(default_factory=list, description="Node IDs in path")
    edges: list[str] = Field(default_factory=list, description="Edge IDs in path")
    
    depth: int = Field(default=0, description="Path depth")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "nodes": self.nodes,
            "edges": self.edges,
            "depth": self.depth,
        }


class DataLineage(BaseModel):
    """Complete data lineage graph."""
    
    lineage_id: str = Field(..., description="Unique lineage identifier")
    name: str = Field(..., description="Lineage name")
    description: str = Field(default="", description="Lineage description")
    
    nodes: dict[str, LineageNode] = Field(default_factory=dict)
    edges: dict[str, LineageEdge] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "name": self.name,
            "description": self.description,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LineageTracker:
    """
    Tracker for data lineage.
    
    Provides:
    - Lineage recording
    - Upstream/downstream analysis
    - Impact analysis
    - Lineage visualization
    
    Usage:
        tracker = LineageTracker()
        
        # Record lineage
        tracker.record_source("eastmoney_api", "EastMoney API", {"type": "rest_api"})
        tracker.record_transform("parse_quotes", "Parse Quotes", "eastmoney_api")
        tracker.record_sink("stock_quotes_table", "Stock Quotes Table", "parse_quotes")
        
        # Get lineage
        lineage = tracker.get_lineage("stock_quotes_table")
        
        # Analyze impact
        impact = tracker.analyze_impact("eastmoney_api")
    """
    
    def __init__(self) -> None:
        self._lineages: dict[str, DataLineage] = {}
        self._node_index: dict[str, str] = {}
        self._edge_counter = 0
    
    def create_lineage(
        self,
        lineage_id: str,
        name: str,
        description: str = "",
    ) -> DataLineage:
        """Create a new lineage graph."""
        lineage = DataLineage(
            lineage_id=lineage_id,
            name=name,
            description=description,
        )
        self._lineages[lineage_id] = lineage
        logger.info(f"Created lineage: {lineage_id}")
        return lineage
    
    def record_source(
        self,
        node_id: str,
        name: str,
        properties: dict[str, Any] | None = None,
        lineage_id: str = "default",
    ) -> LineageNode:
        """Record a data source."""
        lineage = self._get_or_create_lineage(lineage_id)
        
        node = LineageNode(
            node_id=node_id,
            name=name,
            node_type=LineageNodeType.SOURCE,
            properties=properties or {},
        )
        
        lineage.nodes[node_id] = node
        self._node_index[node_id] = lineage_id
        
        logger.info(f"Recorded source: {node_id}")
        return node
    
    def record_transform(
        self,
        node_id: str,
        name: str,
        input_node_ids: str | list[str],
        properties: dict[str, Any] | None = None,
        lineage_id: str = "default",
    ) -> LineageNode:
        """Record a data transformation."""
        lineage = self._get_or_create_lineage(lineage_id)
        
        node = LineageNode(
            node_id=node_id,
            name=name,
            node_type=LineageNodeType.TRANSFORM,
            properties=properties or {},
        )
        
        lineage.nodes[node_id] = node
        self._node_index[node_id] = lineage_id
        
        if isinstance(input_node_ids, str):
            input_node_ids = [input_node_ids]
        
        for input_id in input_node_ids:
            self._add_edge(
                lineage,
                input_id,
                node_id,
                LineageEdgeType.TRANSFORMS,
            )
        
        logger.info(f"Recorded transform: {node_id}")
        return node
    
    def record_sink(
        self,
        node_id: str,
        name: str,
        input_node_ids: str | list[str],
        properties: dict[str, Any] | None = None,
        lineage_id: str = "default",
    ) -> LineageNode:
        """Record a data sink."""
        lineage = self._get_or_create_lineage(lineage_id)
        
        node = LineageNode(
            node_id=node_id,
            name=name,
            node_type=LineageNodeType.SINK,
            properties=properties or {},
        )
        
        lineage.nodes[node_id] = node
        self._node_index[node_id] = lineage_id
        
        if isinstance(input_node_ids, str):
            input_node_ids = [input_node_ids]
        
        for input_id in input_node_ids:
            self._add_edge(
                lineage,
                input_id,
                node_id,
                LineageEdgeType.PRODUCES,
            )
        
        logger.info(f"Recorded sink: {node_id}")
        return node
    
    def record_dataset(
        self,
        node_id: str,
        name: str,
        source_node_id: str | None = None,
        properties: dict[str, Any] | None = None,
        lineage_id: str = "default",
    ) -> LineageNode:
        """Record a dataset."""
        lineage = self._get_or_create_lineage(lineage_id)
        
        node = LineageNode(
            node_id=node_id,
            name=name,
            node_type=LineageNodeType.DATASET,
            properties=properties or {},
        )
        
        lineage.nodes[node_id] = node
        self._node_index[node_id] = lineage_id
        
        if source_node_id:
            self._add_edge(
                lineage,
                source_node_id,
                node_id,
                LineageEdgeType.DERIVES_FROM,
            )
        
        logger.info(f"Recorded dataset: {node_id}")
        return node
    
    def get_lineage(self, lineage_id: str = "default") -> DataLineage | None:
        """Get a lineage graph by ID."""
        return self._lineages.get(lineage_id)
    
    def get_node(self, node_id: str) -> LineageNode | None:
        """Get a node by ID."""
        lineage_id = self._node_index.get(node_id)
        if lineage_id:
            lineage = self._lineages.get(lineage_id)
            if lineage:
                return lineage.nodes.get(node_id)
        return None
    
    def get_upstream(
        self,
        node_id: str,
        depth: int = -1,
    ) -> list[LineageNode]:
        """
        Get upstream nodes (data sources).
        
        Args:
            node_id: Starting node ID
            depth: Maximum depth (-1 for unlimited)
        
        Returns:
            List of upstream nodes
        """
        lineage_id = self._node_index.get(node_id)
        if not lineage_id:
            return []
        
        lineage = self._lineages.get(lineage_id)
        if not lineage:
            return []
        
        upstream = []
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_depth > 0:
                node = lineage.nodes.get(current_id)
                if node:
                    upstream.append(node)
            
            if depth == -1 or current_depth < depth:
                for edge in lineage.edges.values():
                    if edge.target_id == current_id:
                        queue.append((edge.source_id, current_depth + 1))
        
        return upstream
    
    def get_downstream(
        self,
        node_id: str,
        depth: int = -1,
    ) -> list[LineageNode]:
        """
        Get downstream nodes (data consumers).
        
        Args:
            node_id: Starting node ID
            depth: Maximum depth (-1 for unlimited)
        
        Returns:
            List of downstream nodes
        """
        lineage_id = self._node_index.get(node_id)
        if not lineage_id:
            return []
        
        lineage = self._lineages.get(lineage_id)
        if not lineage:
            return []
        
        downstream = []
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_depth > 0:
                node = lineage.nodes.get(current_id)
                if node:
                    downstream.append(node)
            
            if depth == -1 or current_depth < depth:
                for edge in lineage.edges.values():
                    if edge.source_id == current_id:
                        queue.append((edge.target_id, current_depth + 1))
        
        return downstream
    
    def analyze_impact(
        self,
        node_id: str,
    ) -> dict[str, Any]:
        """
        Analyze impact of changes to a node.
        
        Args:
            node_id: Node ID to analyze
        
        Returns:
            Impact analysis result
        """
        node = self.get_node(node_id)
        if not node:
            return {"error": f"Node not found: {node_id}"}
        
        downstream = self.get_downstream(node_id)
        
        impact_by_type: dict[str, int] = defaultdict(int)
        for n in downstream:
            impact_by_type[n.node_type.value] += 1
        
        return {
            "node_id": node_id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "total_impact": len(downstream),
            "impact_by_type": dict(impact_by_type),
            "affected_nodes": [n.node_id for n in downstream],
        }
    
    def trace_path(
        self,
        source_id: str,
        target_id: str,
    ) -> LineagePath | None:
        """
        Trace path between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
        
        Returns:
            LineagePath if found, None otherwise
        """
        lineage_id = self._node_index.get(source_id)
        if not lineage_id:
            return None
        
        lineage = self._lineages.get(lineage_id)
        if not lineage:
            return None
        
        visited = set()
        queue = [(source_id, [source_id], [])]
        
        while queue:
            current_id, path_nodes, path_edges = queue.pop(0)
            
            if current_id == target_id:
                return LineagePath(
                    path_id=f"path_{source_id}_{target_id}",
                    source_node_id=source_id,
                    target_node_id=target_id,
                    nodes=path_nodes,
                    edges=path_edges,
                    depth=len(path_nodes) - 1,
                )
            
            if current_id in visited:
                continue
            visited.add(current_id)
            
            for edge in lineage.edges.values():
                if edge.source_id == current_id:
                    queue.append((
                        edge.target_id,
                        path_nodes + [edge.target_id],
                        path_edges + [edge.edge_id],
                    ))
        
        return None
    
    def to_d3_format(self, lineage_id: str = "default") -> dict[str, Any]:
        """
        Export lineage to D3.js format for visualization.
        
        Args:
            lineage_id: Lineage to export
        
        Returns:
            Dict with nodes and links for D3.js
        """
        lineage = self._lineages.get(lineage_id)
        if not lineage:
            return {"nodes": [], "links": []}
        
        nodes = []
        for node in lineage.nodes.values():
            nodes.append({
                "id": node.node_id,
                "name": node.name,
                "type": node.node_type.value,
                "properties": node.properties,
            })
        
        links = []
        for edge in lineage.edges.values():
            links.append({
                "source": edge.source_id,
                "target": edge.target_id,
                "type": edge.edge_type.value,
            })
        
        return {"nodes": nodes, "links": links}
    
    def _get_or_create_lineage(self, lineage_id: str) -> DataLineage:
        """Get or create a lineage graph."""
        if lineage_id not in self._lineages:
            return self.create_lineage(
                lineage_id=lineage_id,
                name=f"Lineage {lineage_id}",
            )
        return self._lineages[lineage_id]
    
    def _add_edge(
        self,
        lineage: DataLineage,
        source_id: str,
        target_id: str,
        edge_type: LineageEdgeType,
    ) -> LineageEdge:
        """Add an edge to the lineage."""
        self._edge_counter += 1
        edge_id = f"edge_{self._edge_counter}"
        
        edge = LineageEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
        )
        
        lineage.edges[edge_id] = edge
        lineage.updated_at = datetime.now()
        
        return edge
    
    def get_stats(self) -> dict[str, Any]:
        """Get lineage statistics."""
        total_nodes = sum(len(l.nodes) for l in self._lineages.values())
        total_edges = sum(len(l.edges) for l in self._lineages.values())
        
        return {
            "lineages_count": len(self._lineages),
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "lineages": [
                {
                    "lineage_id": l.lineage_id,
                    "name": l.name,
                    "nodes": len(l.nodes),
                    "edges": len(l.edges),
                }
                for l in self._lineages.values()
            ],
        }
