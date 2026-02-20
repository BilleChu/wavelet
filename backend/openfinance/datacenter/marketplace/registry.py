"""
Data Service Registry.

Provides service registration, discovery, and health management
for the data service marketplace.
"""

import logging
from datetime import datetime
from typing import Any, Callable

from .models import (
    DataServiceCategory,
    DataServiceDefinition,
    DataServiceEndpoint,
    DataServiceStatus,
    DataServiceSubscription,
    DataServiceUsage,
    EndpointMethod,
    QuotaConfig,
    RateLimitConfig,
    ServiceHealth,
    SubscriptionPlan,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)


class DataServiceRegistry:
    """
    Data service registry for managing service definitions.

    Provides functionality for:
    - Service registration and deregistration
    - Service discovery by category, tags, or ID
    - Health monitoring and status management
    - Subscription management
    """

    def __init__(self) -> None:
        self._services: dict[str, DataServiceDefinition] = {}
        self._subscriptions: dict[str, DataServiceSubscription] = {}
        self._health: dict[str, ServiceHealth] = {}
        self._handlers: dict[str, Callable] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the registry with default services."""
        if self._initialized:
            return

        await self._register_default_services()
        self._initialized = True
        logger.info("Data service registry initialized")

    async def _register_default_services(self) -> None:
        """Register default data services for the three ADS layers."""

        analysis_service = DataServiceDefinition(
            service_id="analysis-service",
            name="智能分析服务",
            description="提供宏观经济分析、政策分析、公司洞察和技术信号等智能分析数据服务",
            category=DataServiceCategory.ANALYSIS,
            version="1.0.0",
            endpoints=[
                DataServiceEndpoint(
                    path="/macro",
                    method=EndpointMethod.GET,
                    description="获取宏观经济指标数据",
                    parameters={
                        "indicators": {"type": "array", "description": "指标代码列表"},
                        "start_date": {"type": "string", "description": "开始日期"},
                        "end_date": {"type": "string", "description": "结束日期"},
                    },
                    response_schema={
                        "indicators": {"type": "array"},
                        "last_updated": {"type": "string"},
                    },
                ),
                DataServiceEndpoint(
                    path="/policy",
                    method=EndpointMethod.GET,
                    description="获取政策分析数据",
                    parameters={
                        "category": {"type": "string", "description": "政策类别"},
                        "limit": {"type": "integer", "description": "返回数量"},
                    },
                ),
                DataServiceEndpoint(
                    path="/company/{code}",
                    method=EndpointMethod.GET,
                    description="获取公司洞察数据",
                    parameters={
                        "code": {"type": "string", "description": "股票代码"},
                    },
                ),
                DataServiceEndpoint(
                    path="/tech/{code}",
                    method=EndpointMethod.GET,
                    description="获取技术信号数据",
                    parameters={
                        "code": {"type": "string", "description": "股票代码"},
                    },
                ),
            ],
            tags=["分析", "宏观", "政策", "技术"],
        )

        graph_service = DataServiceDefinition(
            service_id="graph-service",
            name="知识图谱服务",
            description="提供实体、关系、事件、新闻等知识图谱数据服务",
            category=DataServiceCategory.GRAPH,
            version="1.0.0",
            endpoints=[
                DataServiceEndpoint(
                    path="/entities",
                    method=EndpointMethod.GET,
                    description="查询实体数据",
                    parameters={
                        "entity_types": {"type": "array", "description": "实体类型列表"},
                        "keywords": {"type": "string", "description": "搜索关键词"},
                        "limit": {"type": "integer", "description": "返回数量"},
                    },
                ),
                DataServiceEndpoint(
                    path="/relations",
                    method=EndpointMethod.GET,
                    description="查询关系数据",
                    parameters={
                        "entity_id": {"type": "string", "description": "实体ID"},
                        "relation_types": {"type": "array", "description": "关系类型"},
                    },
                ),
                DataServiceEndpoint(
                    path="/events",
                    method=EndpointMethod.GET,
                    description="查询事件数据",
                    parameters={
                        "event_types": {"type": "array", "description": "事件类型"},
                        "start_date": {"type": "string", "description": "开始日期"},
                        "end_date": {"type": "string", "description": "结束日期"},
                    },
                ),
                DataServiceEndpoint(
                    path="/news",
                    method=EndpointMethod.GET,
                    description="查询新闻数据",
                    parameters={
                        "source": {"type": "string", "description": "新闻来源"},
                        "keywords": {"type": "string", "description": "关键词"},
                        "limit": {"type": "integer", "description": "返回数量"},
                    },
                ),
            ],
            tags=["知识图谱", "实体", "关系", "事件", "新闻"],
        )

        quant_service = DataServiceDefinition(
            service_id="quant-service",
            name="量化分析服务",
            description="提供因子数据、回测结果、交易信号、投资组合等量化分析数据服务",
            category=DataServiceCategory.QUANT,
            version="1.0.0",
            endpoints=[
                DataServiceEndpoint(
                    path="/factors",
                    method=EndpointMethod.GET,
                    description="获取因子数据",
                    parameters={
                        "factor_ids": {"type": "array", "description": "因子ID列表"},
                        "codes": {"type": "array", "description": "股票代码列表"},
                        "start_date": {"type": "string", "description": "开始日期"},
                        "end_date": {"type": "string", "description": "结束日期"},
                    },
                ),
                DataServiceEndpoint(
                    path="/backtest",
                    method=EndpointMethod.POST,
                    description="运行回测",
                    parameters={
                        "strategy_id": {"type": "string", "description": "策略ID"},
                        "start_date": {"type": "string", "description": "开始日期"},
                        "end_date": {"type": "string", "description": "结束日期"},
                        "initial_capital": {"type": "number", "description": "初始资金"},
                    },
                ),
                DataServiceEndpoint(
                    path="/signals",
                    method=EndpointMethod.GET,
                    description="获取交易信号",
                    parameters={
                        "signal_type": {"type": "string", "description": "信号类型"},
                        "codes": {"type": "array", "description": "股票代码列表"},
                    },
                ),
                DataServiceEndpoint(
                    path="/portfolio",
                    method=EndpointMethod.GET,
                    description="获取投资组合",
                    parameters={
                        "portfolio_id": {"type": "string", "description": "组合ID"},
                    },
                ),
            ],
            tags=["量化", "因子", "回测", "信号", "组合"],
        )

        for service in [analysis_service, graph_service, quant_service]:
            self._services[service.service_id] = service
            self._health[service.service_id] = ServiceHealth(
                service_id=service.service_id,
                status="healthy",
                uptime_seconds=0.0,
            )

    def register_service(self, service: DataServiceDefinition) -> bool:
        """Register a new data service."""
        if service.service_id in self._services:
            logger.warning(f"Service {service.service_id} already registered, updating...")
        
        self._services[service.service_id] = service
        self._health[service.service_id] = ServiceHealth(
            service_id=service.service_id,
            status="healthy",
        )
        logger.info(f"Registered service: {service.service_id}")
        return True

    def deregister_service(self, service_id: str) -> bool:
        """Deregister a data service."""
        if service_id not in self._services:
            logger.warning(f"Service {service_id} not found")
            return False
        
        del self._services[service_id]
        if service_id in self._health:
            del self._health[service_id]
        logger.info(f"Deregistered service: {service_id}")
        return True

    def get_service(self, service_id: str) -> DataServiceDefinition | None:
        """Get a service by ID."""
        return self._services.get(service_id)

    def get_services_by_category(
        self, category: DataServiceCategory
    ) -> list[DataServiceDefinition]:
        """Get services by category."""
        return [
            s for s in self._services.values()
            if s.category == category and s.status == DataServiceStatus.ACTIVE
        ]

    def get_services_by_tags(self, tags: list[str]) -> list[DataServiceDefinition]:
        """Get services by tags."""
        return [
            s for s in self._services.values()
            if any(tag in s.tags for tag in tags)
            and s.status == DataServiceStatus.ACTIVE
        ]

    def list_services(
        self,
        status: DataServiceStatus | None = None,
        category: DataServiceCategory | None = None,
    ) -> list[DataServiceDefinition]:
        """List all services with optional filtering."""
        services = list(self._services.values())
        
        if status:
            services = [s for s in services if s.status == status]
        if category:
            services = [s for s in services if s.category == category]
        
        return services

    def update_service_status(
        self, service_id: str, status: DataServiceStatus
    ) -> bool:
        """Update service status."""
        service = self._services.get(service_id)
        if not service:
            return False
        
        service.status = status
        service.updated_at = datetime.now()
        logger.info(f"Updated service {service_id} status to {status}")
        return True

    def register_handler(
        self, service_id: str, endpoint: str, handler: Callable
    ) -> None:
        """Register a handler for a service endpoint."""
        key = f"{service_id}:{endpoint}"
        self._handlers[key] = handler
        logger.info(f"Registered handler for {key}")

    def get_handler(self, service_id: str, endpoint: str) -> Callable | None:
        """Get handler for a service endpoint."""
        key = f"{service_id}:{endpoint}"
        return self._handlers.get(key)

    def create_subscription(
        self,
        service_id: str,
        user_id: str,
        plan: SubscriptionPlan = SubscriptionPlan.FREE,
    ) -> DataServiceSubscription | None:
        """Create a subscription for a service."""
        if service_id not in self._services:
            logger.warning(f"Service {service_id} not found")
            return None
        
        import uuid
        subscription = DataServiceSubscription(
            subscription_id=str(uuid.uuid4()),
            service_id=service_id,
            user_id=user_id,
            plan=plan,
            quota=self._get_quota_for_plan(plan),
        )
        
        self._subscriptions[subscription.subscription_id] = subscription
        logger.info(f"Created subscription {subscription.subscription_id}")
        return subscription

    def _get_quota_for_plan(self, plan: SubscriptionPlan) -> QuotaConfig:
        """Get quota configuration for a plan."""
        quotas = {
            SubscriptionPlan.FREE: QuotaConfig(
                max_requests=1000,
                max_data_volume=100000,
                max_concurrent=2,
            ),
            SubscriptionPlan.BASIC: QuotaConfig(
                max_requests=10000,
                max_data_volume=1000000,
                max_concurrent=5,
            ),
            SubscriptionPlan.PROFESSIONAL: QuotaConfig(
                max_requests=100000,
                max_data_volume=10000000,
                max_concurrent=10,
            ),
            SubscriptionPlan.ENTERPRISE: QuotaConfig(
                max_requests=1000000,
                max_data_volume=100000000,
                max_concurrent=50,
            ),
        }
        return quotas.get(plan, quotas[SubscriptionPlan.FREE])

    def get_subscription(self, subscription_id: str) -> DataServiceSubscription | None:
        """Get a subscription by ID."""
        return self._subscriptions.get(subscription_id)

    def get_user_subscriptions(self, user_id: str) -> list[DataServiceSubscription]:
        """Get all subscriptions for a user."""
        return [
            s for s in self._subscriptions.values()
            if s.user_id == user_id and s.status == SubscriptionStatus.ACTIVE
        ]

    def update_health(
        self,
        service_id: str,
        success: bool,
        response_time_ms: float,
    ) -> None:
        """Update service health metrics."""
        health = self._health.get(service_id)
        if not health:
            return
        
        health.total_requests += 1
        if success:
            health.successful_requests += 1
        else:
            health.failed_requests += 1
        
        total = health.total_requests
        health.avg_response_time_ms = (
            (health.avg_response_time_ms * (total - 1) + response_time_ms) / total
        )
        health.last_check = datetime.now()

    def get_health(self, service_id: str) -> ServiceHealth | None:
        """Get service health status."""
        return self._health.get(service_id)

    def get_all_health(self) -> list[ServiceHealth]:
        """Get health status for all services."""
        return list(self._health.values())


_registry: DataServiceRegistry | None = None


def get_service_registry() -> DataServiceRegistry:
    """Get the global service registry instance."""
    global _registry
    if _registry is None:
        _registry = DataServiceRegistry()
    return _registry
