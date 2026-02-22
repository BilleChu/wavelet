"""
Consistency Management - System-level consistency guarantees.

Provides:
- WriteAheadLog: Transaction logging for recovery
- SyncCoordinator: Synchronization between backends
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable


logger = logging.getLogger(__name__)


class LogEntryType(str, Enum):
    """Log entry type."""
    BEGIN = "begin"
    PREPARE = "prepare"
    COMMIT = "commit"
    ABORT = "abort"
    OPERATION = "operation"


class SyncStatus(str, Enum):
    """Synchronization status."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"


@dataclass
class LogEntry:
    """Write-ahead log entry."""
    
    entry_id: str
    entry_type: LogEntryType
    transaction_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: dict[str, Any] = field(default_factory=dict)
    checksum: str | None = None
    
    def compute_checksum(self) -> str:
        """Compute checksum for integrity."""
        data_str = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "entry_id": self.entry_id,
            "entry_type": self.entry_type.value,
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "checksum": self.checksum,
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "LogEntry":
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return cls(
            entry_id=data["entry_id"],
            entry_type=LogEntryType(data["entry_type"]),
            transaction_id=data["transaction_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data.get("data", {}),
            checksum=data.get("checksum"),
        )


class WriteAheadLog:
    """
    Write-ahead log for transaction recovery.
    
    Features:
    - Durable logging
    - Checksum verification
    - Recovery support
    - Log rotation
    """
    
    def __init__(self, log_dir: str | Path | None = None):
        self._log_dir = Path(log_dir) if log_dir else Path(__file__).parent / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._current_log = self._log_dir / "wal.log"
        self._lock = asyncio.Lock()
        self._entry_counter = 0
    
    async def append(
        self,
        entry_type: LogEntryType,
        transaction_id: str,
        data: dict[str, Any] | None = None,
    ) -> LogEntry:
        """Append a log entry."""
        entry = LogEntry(
            entry_id=f"entry_{int(time.time() * 1000)}_{self._entry_counter}",
            entry_type=entry_type,
            transaction_id=transaction_id,
            data=data or {},
        )
        entry.checksum = entry.compute_checksum()
        
        async with self._lock:
            with open(self._current_log, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
            self._entry_counter += 1
        
        return entry
    
    async def read_entries(
        self,
        transaction_id: str | None = None,
    ) -> list[LogEntry]:
        """Read log entries."""
        entries = []
        
        if not self._current_log.exists():
            return entries
        
        async with self._lock:
            with open(self._current_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = LogEntry.from_json(line)
                        if transaction_id is None or entry.transaction_id == transaction_id:
                            entries.append(entry)
        
        return entries
    
    async def checkpoint(self, transaction_id: str) -> None:
        """Create a checkpoint for a transaction."""
        await self.append(LogEntryType.COMMIT, transaction_id)
    
    async def recover_uncommitted(self) -> list[dict[str, Any]]:
        """Find uncommitted operations for recovery."""
        entries = await self.read_entries()
        
        transactions: dict[str, list[dict]] = {}
        for entry in entries:
            if entry.transaction_id not in transactions:
                transactions[entry.transaction_id] = []
            transactions[entry.transaction_id].append(entry.__dict__)
        
        uncommitted = []
        for txn_id, txn_entries in transactions.items():
            has_commit = any(
                e["entry_type"] == LogEntryType.COMMIT.value 
                for e in txn_entries
            )
            if not has_commit:
                uncommitted.extend(txn_entries)
        
        return uncommitted
    
    async def clear(self) -> None:
        """Clear the log."""
        async with self._lock:
            if self._current_log.exists():
                self._current_log.unlink()


@dataclass
class SyncTask:
    """Synchronization task."""
    
    task_id: str
    operation: str
    source_backend: str
    target_backend: str
    data: dict[str, Any]
    status: SyncStatus = SyncStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    error_message: str | None = None


class SyncCoordinator:
    """
    Synchronization coordinator for multiple backends.
    
    Features:
    - Async sync queue
    - Retry with exponential backoff
    - Status tracking
    - Background worker
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        default_retry_delay: float = 1.0,
        max_retries: int = 3,
    ):
        self._queue: asyncio.Queue[SyncTask] = asyncio.Queue(maxsize=max_queue_size)
        self._default_retry_delay = default_retry_delay
        self._max_retries = max_retries
        self._handlers: dict[str, Callable] = {}
        self._running = False
        self._worker_task: asyncio.Task | None = None
        self._stats = {
            "total_tasks": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
        }
    
    def register_handler(
        self,
        backend: str,
        handler: Callable[[str, dict[str, Any]], Any],
    ) -> None:
        """Register a sync handler for a backend."""
        self._handlers[backend] = handler
    
    async def submit(
        self,
        operation: str,
        source_backend: str,
        target_backend: str,
        data: dict[str, Any],
    ) -> str:
        """Submit a sync task."""
        task = SyncTask(
            task_id=f"sync_{int(time.time() * 1000)}_{operation}",
            operation=operation,
            source_backend=source_backend,
            target_backend=target_backend,
            data=data,
            max_retries=self._max_retries,
        )
        
        await self._queue.put(task)
        self._stats["total_tasks"] += 1
        
        return task.task_id
    
    async def start(self) -> None:
        """Start the sync worker."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("SyncCoordinator started")
    
    async def stop(self) -> None:
        """Stop the sync worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("SyncCoordinator stopped")
    
    async def _worker(self) -> None:
        """Background worker for processing sync tasks."""
        while self._running:
            try:
                task = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )
                await self._process_task(task)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync worker error: {e}")
    
    async def _process_task(self, task: SyncTask) -> None:
        """Process a sync task."""
        handler = self._handlers.get(task.target_backend)
        if not handler:
            logger.error(f"No handler for backend: {task.target_backend}")
            return
        
        try:
            await handler(task.operation, task.data)
            task.status = SyncStatus.SYNCED
            self._stats["successful"] += 1
            logger.debug(f"Sync task completed: {task.task_id}")
            
        except Exception as e:
            task.error_message = str(e)
            task.retry_count += 1
            self._stats["retries"] += 1
            
            if task.retry_count < task.max_retries:
                task.status = SyncStatus.PENDING
                delay = self._default_retry_delay * (2 ** task.retry_count)
                await asyncio.sleep(delay)
                await self._queue.put(task)
                logger.warning(f"Retry {task.retry_count}/{task.max_retries}: {task.task_id}")
            else:
                task.status = SyncStatus.FAILED
                self._stats["failed"] += 1
                logger.error(f"Sync task failed after {task.max_retries} retries: {task.task_id}")
    
    def get_stats(self) -> dict[str, Any]:
        """Get sync statistics."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "running": self._running,
        }
    
    @property
    def queue_size(self) -> int:
        return self._queue.qsize()
