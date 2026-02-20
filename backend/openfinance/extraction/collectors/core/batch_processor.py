"""
Batch Processor Framework.

Provides a generic, high-performance batch processing framework with:
- Concurrent processing with configurable limits
- Checkpoint/resume support for fault tolerance
- Error isolation (single item failure doesn't affect batch)
- Progress tracking and callbacks
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeVar, Callable, Awaitable

from pydantic import BaseModel, Field

from openfinance.core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class BatchStatus(str, Enum):
    """Status of a batch processing operation."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ProcessResult(Generic[R]):
    """Result of processing a single item."""
    
    success: bool
    item_id: str
    data: R | None = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult(Generic[R]):
    """Result of processing a batch of items."""
    
    batch_id: str
    status: BatchStatus
    total_items: int
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ProcessResult[R]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    checkpoint: dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return self.successful / self.total_items


class BatchConfig(BaseModel):
    """Configuration for batch processing."""
    
    batch_size: int = Field(default=100, description="Items per batch")
    max_concurrent: int = Field(default=5, description="Max concurrent batches")
    max_retries: int = Field(default=3, description="Max retries per item")
    retry_delay_seconds: float = Field(default=1.0, description="Base retry delay")
    retry_backoff_factor: float = Field(default=2.0, description="Exponential backoff factor")
    timeout_seconds: float = Field(default=300.0, description="Batch timeout")
    checkpoint_enabled: bool = Field(default=True, description="Enable checkpointing")
    checkpoint_dir: str = Field(default="data/checkpoints", description="Checkpoint directory")
    fail_fast: bool = Field(default=False, description="Stop on first error")
    progress_callback: bool = Field(default=True, description="Enable progress callbacks")


class CheckpointManager:
    """Manages checkpoints for batch processing."""
    
    def __init__(self, checkpoint_dir: str, job_id: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.job_id = job_id
        self.checkpoint_file = self.checkpoint_dir / f"{job_id}.json"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, processed_ids: list[str], metadata: dict[str, Any]) -> None:
        checkpoint = {
            "job_id": self.job_id,
            "processed_ids": processed_ids,
            "metadata": metadata,
            "updated_at": datetime.now().isoformat(),
        }
        with open(self.checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2)
    
    def load(self) -> dict[str, Any] | None:
        if not self.checkpoint_file.exists():
            return None
        try:
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def clear(self) -> None:
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
    
    def exists(self) -> bool:
        return self.checkpoint_file.exists()


class BatchProcessor(ABC, Generic[T, R]):
    """
    Abstract base class for batch processing.
    
    Features:
    - Generic type support for any item and result types
    - Configurable concurrency and batch size
    - Checkpoint/resume support
    - Error isolation with retry logic
    - Progress callbacks
    
    Usage:
        class MyProcessor(BatchProcessor[MyItem, MyResult]):
            async def process_item(self, item: MyItem) -> ProcessResult[MyResult]:
                # Process single item
                result = await do_something(item)
                return ProcessResult(success=True, item_id=item.id, data=result)
        
        processor = MyProcessor(config=BatchConfig(batch_size=50))
        results = await processor.process_all(items)
    """
    
    def __init__(self, config: BatchConfig | None = None) -> None:
        self.config = config or BatchConfig()
        self._job_id = str(uuid.uuid4())[:8]
        self._checkpoint_manager: CheckpointManager | None = None
        self._processed_ids: list[str] = []
        self._is_running = False
        self._is_paused = False
        self._progress_callback: Callable[[int, int], Awaitable[None]] | None = None
        
        if self.config.checkpoint_enabled:
            self._checkpoint_manager = CheckpointManager(
                self.config.checkpoint_dir, self._job_id
            )
    
    @abstractmethod
    async def process_item(self, item: T) -> ProcessResult[R]:
        """
        Process a single item. Must be implemented by subclasses.
        
        Args:
            item: The item to process
            
        Returns:
            ProcessResult containing success status and optional data
        """
        pass
    
    def get_item_id(self, item: T) -> str:
        """Get unique identifier for an item. Override for custom ID logic."""
        return str(hash(item))
    
    async def on_batch_start(self, batch: list[T]) -> None:
        """Hook called before processing a batch. Override for custom logic."""
        pass
    
    async def on_batch_complete(self, result: BatchResult[R]) -> None:
        """Hook called after processing a batch. Override for custom logic."""
        pass
    
    async def on_error(self, item: T, error: Exception) -> None:
        """Hook called when an item processing fails. Override for custom logic."""
        pass
    
    def set_progress_callback(self, callback: Callable[[int, int], Awaitable[None]]) -> None:
        """Set callback for progress updates: callback(processed_count, total_count)."""
        self._progress_callback = callback
    
    async def _process_with_retry(self, item: T) -> ProcessResult[R]:
        """Process item with retry logic."""
        item_id = self.get_item_id(item)
        last_error: Exception | None = None
        delay = self.config.retry_delay_seconds
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    self.process_item(item),
                    timeout=self.config.timeout_seconds
                )
                result.duration_ms = (time.time() - start_time) * 1000
                return result
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Item {item_id} timed out after {self.config.timeout_seconds}s")
            except Exception as e:
                last_error = e
            
            if attempt < self.config.max_retries:
                await asyncio.sleep(delay)
                delay *= self.config.retry_backoff_factor
        
        await self.on_error(item, last_error or Exception("Unknown error"))
        return ProcessResult(
            success=False,
            item_id=item_id,
            error=str(last_error),
        )
    
    async def process_batch(self, batch: list[T]) -> BatchResult[R]:
        """
        Process a batch of items.
        
        Args:
            batch: List of items to process
            
        Returns:
            BatchResult with processing statistics
        """
        batch_id = str(uuid.uuid4())[:8]
        result = BatchResult[R](
            batch_id=batch_id,
            status=BatchStatus.RUNNING,
            total_items=len(batch),
            started_at=datetime.now(),
        )
        
        await self.on_batch_start(batch)
        
        try:
            for item in batch:
                if self._is_paused:
                    result.status = BatchStatus.PAUSED
                    break
                
                item_result = await self._process_with_retry(item)
                result.results.append(item_result)
                
                if item_result.success:
                    result.successful += 1
                    self._processed_ids.append(item_result.item_id)
                else:
                    result.failed += 1
                    if self.config.fail_fast:
                        result.status = BatchStatus.FAILED
                        break
            
            if result.status == BatchStatus.RUNNING:
                result.status = BatchStatus.COMPLETED
            
        except Exception as e:
            result.status = BatchStatus.FAILED
            logger.error_with_context(
                "Batch processing failed",
                context={"batch_id": batch_id, "error": str(e)}
            )
        
        result.completed_at = datetime.now()
        result.duration_ms = (result.completed_at - result.started_at).total_seconds() * 1000
        
        if self._checkpoint_manager:
            result.checkpoint = {
                "processed_count": len(self._processed_ids),
                "last_batch_id": batch_id,
            }
            self._checkpoint_manager.save(self._processed_ids, result.checkpoint)
        
        await self.on_batch_complete(result)
        
        return result
    
    async def process_all(
        self,
        items: list[T],
        resume: bool = True,
    ) -> list[BatchResult[R]]:
        """
        Process all items in batches.
        
        Args:
            items: All items to process
            resume: Whether to resume from checkpoint if available
            
        Returns:
            List of BatchResults for each batch
        """
        self._is_running = True
        self._is_paused = False
        total_items = len(items)
        processed_count = 0
        
        if resume and self._checkpoint_manager and self._checkpoint_manager.exists():
            checkpoint = self._checkpoint_manager.load()
            if checkpoint:
                self._processed_ids = checkpoint.get("processed_ids", [])
                processed_count = len(self._processed_ids)
                logger.info_with_context(
                    "Resuming from checkpoint",
                    context={"job_id": self._job_id, "processed": processed_count}
                )
        
        results: list[BatchResult[R]] = []
        batches = [
            items[i:i + self.config.batch_size]
            for i in range(0, len(items), self.config.batch_size)
        ]
        
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def process_with_semaphore(batch: list[T], batch_idx: int) -> BatchResult[R]:
            async with semaphore:
                result = await self.process_batch(batch)
                if self._progress_callback:
                    await self._progress_callback(
                        min((batch_idx + 1) * self.config.batch_size, total_items),
                        total_items
                    )
                return result
        
        tasks = [
            process_with_semaphore(batch, idx)
            for idx, batch in enumerate(batches)
        ]
        
        results = await asyncio.gather(*tasks)
        
        self._is_running = False
        
        if self._checkpoint_manager:
            self._checkpoint_manager.clear()
        
        logger.info_with_context(
            "Batch processing completed",
            context={
                "job_id": self._job_id,
                "total_items": total_items,
                "total_batches": len(batches),
                "total_successful": sum(r.successful for r in results),
                "total_failed": sum(r.failed for r in results),
            }
        )
        
        return results
    
    def pause(self) -> None:
        """Pause processing."""
        self._is_paused = True
    
    def resume_processing(self) -> None:
        """Resume processing."""
        self._is_paused = False
    
    def stop(self) -> None:
        """Stop processing."""
        self._is_running = False
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def processed_count(self) -> int:
        return len(self._processed_ids)
