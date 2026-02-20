"""
Service Registry for MCP Architecture.

Provides service registration, discovery, and load balancing.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from openfinance.datacenter.provider.mcp.server import (
    ServiceMetadata,
    ServiceStatus,
)

logger = logging.getLogger(__name__)


class RegistryConfig(BaseModel):
    """Configuration for service registry."""

    heartbeat_interval_seconds: int = Field(
        default=10,
        description="Heartbeat interval",
    )
    heartbeat_timeout_seconds: int = Field(
        default=30,
        description="Heartbeat timeout",
    )
    enable_load_balancing: bool = Field(
        default=True,
        description="Enable load balancing",
    )
    load_balance_strategy: str = Field(
        default="round_robin",
        description="Load balance strategy",
    )


class ServiceInstance(BaseModel):
    """Instance of a registered service."""

    metadata: ServiceMetadata = Field(..., description="Service metadata")
    request_count: int = Field(default=0, description="Total request count")
    error_count: int = Field(default=0, description="Total error count")
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")


class ServiceRegistry:
    """Registry for MCP services.

    Provides:
    - Service registration and discovery
    - Health monitoring
    - Load balancing
    - Service metadata management
    """

    def __init__(self, config: RegistryConfig | None = None) -> None:
        self.config = config or RegistryConfig()
        self._services: dict[str, list[ServiceInstance]] = {}
        self._round_robin_index: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def register(self, metadata: ServiceMetadata) -> bool:
        """Register a service instance."""
        async with self._lock:
            service_name = metadata.service_name
            
            if service_name not in self._services:
                self._services[service_name] = []
                self._round_robin_index[service_name] = 0

            for instance in self._services[service_name]:
                if instance.metadata.service_id == metadata.service_id:
                    instance.metadata = metadata
                    instance.metadata.last_heartbeat = datetime.now()
                    logger.info(f"Updated service: {metadata.service_id}")
                    return True

            instance = ServiceInstance(metadata=metadata)
            self._services[service_name].append(instance)
            logger.info(f"Registered service: {metadata.service_id}")
            return True

    async def unregister(self, service_id: str) -> bool:
        """Unregister a service instance."""
        async with self._lock:
            for service_name, instances in self._services.items():
                for i, instance in enumerate(instances):
                    if instance.metadata.service_id == service_id:
                        instances.pop(i)
                        logger.info(f"Unregistered service: {service_id}")
                        return True
            return False

    async def discover(
        self,
        service_name: str,
        healthy_only: bool = True,
    ) -> list[ServiceInstance]:
        """Discover service instances."""
        instances = self._services.get(service_name, [])
        
        if healthy_only:
            instances = [
                i for i in instances
                if i.metadata.status == ServiceStatus.HEALTHY
            ]
        
        return instances

    async def get_instance(
        self,
        service_name: str,
    ) -> ServiceInstance | None:
        """Get a service instance using load balancing."""
        instances = await self.discover(service_name)
        
        if not instances:
            return None

        if not self.config.enable_load_balancing:
            return instances[0]

        strategy = self.config.load_balance_strategy
        
        if strategy == "round_robin":
            return self._round_robin_select(service_name, instances)
        elif strategy == "random":
            return random.choice(instances)
        elif strategy == "least_requests":
            return min(instances, key=lambda i: i.request_count)
        else:
            return instances[0]

    def _round_robin_select(
        self,
        service_name: str,
        instances: list[ServiceInstance],
    ) -> ServiceInstance:
        """Select instance using round-robin."""
        index = self._round_robin_index.get(service_name, 0)
        instance = instances[index % len(instances)]
        self._round_robin_index[service_name] = index + 1
        return instance

    async def heartbeat(self, service_id: str) -> bool:
        """Update heartbeat for a service."""
        async with self._lock:
            for instances in self._services.values():
                for instance in instances:
                    if instance.metadata.service_id == service_id:
                        instance.metadata.last_heartbeat = datetime.now()
                        instance.metadata.status = ServiceStatus.HEALTHY
                        return True
            return False

    async def check_health(self) -> dict[str, Any]:
        """Check health of all registered services."""
        now = datetime.now()
        timeout = timedelta(seconds=self.config.heartbeat_timeout_seconds)
        results: dict[str, Any] = {}

        async with self._lock:
            for service_name, instances in self._services.items():
                healthy_count = 0
                unhealthy_count = 0

                for instance in instances:
                    if now - instance.metadata.last_heartbeat > timeout:
                        instance.metadata.status = ServiceStatus.UNHEALTHY
                        unhealthy_count += 1
                    else:
                        healthy_count += 1

                results[service_name] = {
                    "total": len(instances),
                    "healthy": healthy_count,
                    "unhealthy": unhealthy_count,
                }

        return results

    async def record_request(
        self,
        service_id: str,
        response_time_ms: float,
        success: bool,
    ) -> None:
        """Record request metrics for a service."""
        async with self._lock:
            for instances in self._services.values():
                for instance in instances:
                    if instance.metadata.service_id == service_id:
                        instance.request_count += 1
                        if not success:
                            instance.error_count += 1
                        
                        total = instance.request_count
                        old_avg = instance.avg_response_time_ms
                        instance.avg_response_time_ms = (
                            (old_avg * (total - 1) + response_time_ms) / total
                        )
                        return

    def list_services(self) -> dict[str, list[dict[str, Any]]]:
        """List all registered services."""
        return {
            name: [
                {
                    "service_id": i.metadata.service_id,
                    "status": i.metadata.status.value,
                    "host": i.metadata.host,
                    "port": i.metadata.port,
                    "request_count": i.request_count,
                    "error_count": i.error_count,
                    "avg_response_time_ms": i.avg_response_time_ms,
                }
                for i in instances
            ]
            for name, instances in self._services.items()
        }

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total_services = len(self._services)
        total_instances = sum(len(i) for i in self._services.values())
        healthy_instances = sum(
            1 for instances in self._services.values()
            for i in instances
            if i.metadata.status == ServiceStatus.HEALTHY
        )

        return {
            "total_services": total_services,
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": total_instances - healthy_instances,
        }
