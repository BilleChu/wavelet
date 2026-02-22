"""
Graph Storage Factory - Creates storage instances.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from openfinance.datacenter.graph.storage.base import GraphStorage, StorageBackend
from openfinance.datacenter.graph.storage.dual import DualWriteCoordinator


logger = logging.getLogger(__name__)

_storage_instance: GraphStorage | None = None


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load graph storage configuration."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "graph.yaml"
    
    config_path = Path(config_path)
    if not config_path.exists():
        return {
            "storage": {"mode": "postgres"},
            "sync": {"mode": "async"},
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_storage(
    mode: str | None = None,
    database_url: str | None = None,
    neo4j_uri: str | None = None,
    neo4j_user: str | None = None,
    neo4j_password: str | None = None,
    config: dict[str, Any] | None = None,
) -> GraphStorage:
    """Create a graph storage instance."""
    if config is None:
        config = load_config()
    
    mode = mode or config.get("storage", {}).get("mode", "postgres")
    
    if mode == "postgres" or mode == StorageBackend.POSTGRES.value:
        from openfinance.datacenter.graph.storage.postgres import PostgresGraphStorage
        return PostgresGraphStorage(database_url=database_url)
    
    elif mode == "neo4j" or mode == StorageBackend.NEO4J.value:
        from openfinance.datacenter.graph.storage.neo4j import Neo4jGraphStorage
        return Neo4jGraphStorage(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
        )
    
    elif mode == "hybrid" or mode == StorageBackend.HYBRID.value:
        from openfinance.datacenter.graph.storage.postgres import PostgresGraphStorage
        from openfinance.datacenter.graph.storage.neo4j import Neo4jGraphStorage
        
        pg_storage = PostgresGraphStorage(database_url=database_url)
        neo4j_storage = Neo4jGraphStorage(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
        )
        
        sync_config = config.get("sync", {})
        
        return DualWriteCoordinator(
            primary=pg_storage,
            secondary=neo4j_storage,
            sync_mode=sync_config.get("mode", "async"),
            max_retries=sync_config.get("max_retries", 3),
        )
    
    raise ValueError(f"Unknown storage mode: {mode}")


def get_graph_storage(force_new: bool = False) -> GraphStorage:
    """Get the global graph storage instance."""
    global _storage_instance
    
    if _storage_instance is not None and not force_new:
        return _storage_instance
    
    _storage_instance = create_storage()
    return _storage_instance
