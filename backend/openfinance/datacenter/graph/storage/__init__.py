"""
Graph Storage - Business-level storage implementations.
"""

from openfinance.datacenter.graph.storage.base import (
    GraphStorage,
    StorageBackend,
    QueryResult,
    PathResult,
    SubgraphResult,
)
from openfinance.datacenter.graph.storage.postgres import PostgresGraphStorage
from openfinance.datacenter.graph.storage.neo4j import Neo4jGraphStorage
from openfinance.datacenter.graph.storage.dual import DualWriteCoordinator
from openfinance.datacenter.graph.storage.factory import get_graph_storage

__all__ = [
    "GraphStorage",
    "StorageBackend",
    "QueryResult",
    "PathResult",
    "SubgraphResult",
    "PostgresGraphStorage",
    "Neo4jGraphStorage",
    "DualWriteCoordinator",
    "get_graph_storage",
]
