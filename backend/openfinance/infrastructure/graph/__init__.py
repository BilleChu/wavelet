"""
Graph Infrastructure - System-level components.

Provides low-level infrastructure for graph storage:
- Connection management (pooling, lifecycle)
- Transaction management (two-phase commit)
- Consistency guarantees (WAL, sync)
"""

from openfinance.infrastructure.graph.connection import (
    ConnectionPool,
    ConnectionManager,
)
from openfinance.infrastructure.graph.transaction import (
    TransactionManager,
    TwoPhaseCommitCoordinator,
)
from openfinance.infrastructure.graph.consistency import (
    WriteAheadLog,
    SyncCoordinator,
)

__all__ = [
    "ConnectionPool",
    "ConnectionManager",
    "TransactionManager",
    "TwoPhaseCommitCoordinator",
    "WriteAheadLog",
    "SyncCoordinator",
]
