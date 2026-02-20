"""
Collection Orchestrator for Data Collection Center.

Coordinates multiple collectors and manages the overall collection workflow.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from openfinance.datacenter.collector.core.base_collector import (
    BaseCollector,
    CollectionResult,
    CollectionStatus,
)

logger = logging.getLogger(__name__)


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator."""

    max_concurrent_collectors: int = Field(
        default=5,
        description="Maximum concurrent collectors",
    )
    health_check_interval_seconds: int = Field(
        default=60,
        description="Health check interval",
    )
    auto_restart_failed: bool = Field(
        default=True,
        description="Auto restart failed collectors",
    )
    restart_delay_seconds: int = Field(
        default=30,
        description="Delay before restart",
    )


class CollectorStatus(BaseModel):
    """Status of a collector in the orchestrator."""

    source: str = Field(..., description="Data source")
    is_registered: bool = Field(default=False, description="Whether registered")
    is_running: bool = Field(default=False, description="Whether running")
    last_collection: datetime | None = Field(default=None, description="Last collection time")
    total_collections: int = Field(default=0, description="Total collections")
    error_count: int = Field(default=0, description="Error count")
    last_error: str | None = Field(default=None, description="Last error message")


class OrchestratorResult(BaseModel):
    """Result from orchestrator operation."""

    operation: str = Field(..., description="Operation type")
    success: bool = Field(..., description="Whether succeeded")
    message: str = Field(..., description="Result message")
    details: dict[str, Any] = Field(default_factory=dict, description="Details")


class CollectionOrchestrator:
    """Orchestrator for managing multiple data collectors.

    Provides:
    - Collector registration and lifecycle management
    - Concurrent collection execution
    - Health monitoring and auto-recovery
    - Collection result aggregation
    """

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self._collectors: dict[str, BaseCollector] = {}
        self._statuses: dict[str, CollectorStatus] = {}
        self._results: list[CollectionResult] = []
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_collectors)
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    def register_collector(self, collector: BaseCollector) -> OrchestratorResult:
        """Register a collector."""
        source = collector.source.value

        if source in self._collectors:
            return OrchestratorResult(
                operation="register",
                success=False,
                message=f"Collector {source} already registered",
            )

        self._collectors[source] = collector
        self._statuses[source] = CollectorStatus(
            source=source,
            is_registered=True,
        )

        logger.info(f"Registered collector: {source}")
        return OrchestratorResult(
            operation="register",
            success=True,
            message=f"Collector {source} registered successfully",
        )

    def unregister_collector(self, source: str) -> OrchestratorResult:
        """Unregister a collector."""
        if source not in self._collectors:
            return OrchestratorResult(
                operation="unregister",
                success=False,
                message=f"Collector {source} not found",
            )

        del self._collectors[source]
        if source in self._statuses:
            del self._statuses[source]

        logger.info(f"Unregistered collector: {source}")
        return OrchestratorResult(
            operation="unregister",
            success=True,
            message=f"Collector {source} unregistered successfully",
        )

    async def start_all(self) -> OrchestratorResult:
        """Start all registered collectors."""
        self._running = True
        started = []
        failed = []

        for source, collector in self._collectors.items():
            try:
                await collector.start()
                self._statuses[source].is_running = True
                started.append(source)
            except Exception as e:
                logger.exception(f"Failed to start collector {source}")
                self._statuses[source].last_error = str(e)
                failed.append(source)

        return OrchestratorResult(
            operation="start_all",
            success=len(failed) == 0,
            message=f"Started {len(started)} collectors, {len(failed)} failed",
            details={"started": started, "failed": failed},
        )

    async def stop_all(self) -> OrchestratorResult:
        """Stop all running collectors."""
        self._running = False
        stopped = []
        failed = []

        for source, collector in self._collectors.items():
            if collector.is_running:
                try:
                    await collector.stop()
                    self._statuses[source].is_running = False
                    stopped.append(source)
                except Exception as e:
                    logger.exception(f"Failed to stop collector {source}")
                    failed.append(source)

        return OrchestratorResult(
            operation="stop_all",
            success=len(failed) == 0,
            message=f"Stopped {len(stopped)} collectors, {len(failed)} failed",
            details={"stopped": stopped, "failed": failed},
        )

    async def collect_from(
        self,
        source: str,
        **kwargs: Any,
    ) -> CollectionResult:
        """Collect data from a specific source."""
        collector = self._collectors.get(source)
        if not collector:
            return CollectionResult(
                task_id="",
                source=source,
                status=CollectionStatus.FAILED,
                error_message=f"Collector {source} not found",
                started_at=datetime.now(),
            )

        async with self._semaphore:
            result = await collector.collect(**kwargs)
            self._results.append(result)

            status = self._statuses.get(source)
            if status:
                status.last_collection = datetime.now()
                status.total_collections += 1
                if result.status == CollectionStatus.FAILED:
                    status.error_count += 1
                    status.last_error = result.error_message

            return result

    async def collect_all(self, **kwargs: Any) -> list[CollectionResult]:
        """Collect data from all registered sources concurrently."""
        tasks = [
            self.collect_from(source, **kwargs)
            for source in self._collectors
        ]
        return await asyncio.gather(*tasks)

    def get_collector_status(self, source: str) -> CollectorStatus | None:
        """Get status of a specific collector."""
        return self._statuses.get(source)

    def get_all_statuses(self) -> list[CollectorStatus]:
        """Get status of all collectors."""
        return list(self._statuses.values())

    def get_collection_results(
        self,
        source: str | None = None,
        limit: int = 100,
    ) -> list[CollectionResult]:
        """Get collection results."""
        results = self._results
        if source:
            results = [r for r in results if r.source.value == source]
        return results[-limit:]

    def get_summary(self) -> dict[str, Any]:
        """Get orchestrator summary."""
        total_collections = sum(s.total_collections for s in self._statuses.values())
        total_errors = sum(s.error_count for s in self._statuses.values())

        return {
            "is_running": self._running,
            "registered_collectors": len(self._collectors),
            "running_collectors": sum(1 for c in self._collectors.values() if c.is_running),
            "total_collections": total_collections,
            "total_errors": total_errors,
            "error_rate": total_errors / max(total_collections, 1),
            "collectors": [s.model_dump() for s in self._statuses.values()],
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on all collectors."""
        results = {}

        for source, collector in self._collectors.items():
            try:
                health = await collector.health_check()
                results[source] = {
                    "healthy": True,
                    "details": health,
                }
            except Exception as e:
                results[source] = {
                    "healthy": False,
                    "error": str(e),
                }

        return {
            "overall_healthy": all(r.get("healthy", False) for r in results.values()),
            "collectors": results,
            "checked_at": datetime.now().isoformat(),
        }
