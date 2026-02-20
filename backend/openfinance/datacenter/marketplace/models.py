"""
Data Service Marketplace Models.

Defines the core data structures for the data service marketplace,
including service definitions, endpoints, subscriptions, and usage tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataServiceCategory(str, Enum):
    """Data service category enumeration."""

    ANALYSIS = "analysis"
    GRAPH = "graph"
    QUANT = "quant"
    MARKET = "market"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"


class DataServiceStatus(str, Enum):
    """Data service status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class EndpointMethod(str, Enum):
    """HTTP method enumeration."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SubscriptionPlan(str, Enum):
    """Subscription plan enumeration."""

    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PricingModel(str, Enum):
    """Pricing model enumeration."""

    FREE = "free"
    PER_REQUEST = "per_request"
    PER_MONTH = "per_month"
    PER_VOLUME = "per_volume"
    TIERED = "tiered"


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests_per_minute: int = Field(default=60, description="Requests per minute")
    requests_per_hour: int = Field(default=1000, description="Requests per hour")
    requests_per_day: int = Field(default=10000, description="Requests per day")
    burst_limit: int = Field(default=10, description="Burst limit")


class QuotaConfig(BaseModel):
    """Quota configuration."""

    max_requests: int = Field(default=10000, description="Maximum requests")
    max_data_volume: int = Field(default=1000000, description="Maximum data volume in bytes")
    max_concurrent: int = Field(default=5, description="Maximum concurrent requests")
    reset_period: str = Field(default="monthly", description="Reset period")


class DataServiceEndpoint(BaseModel):
    """Data service endpoint definition."""

    path: str = Field(..., description="Endpoint path")
    method: EndpointMethod = Field(..., description="HTTP method")
    description: str = Field(default="", description="Endpoint description")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters schema")
    response_schema: dict[str, Any] = Field(default_factory=dict, description="Response schema")
    cache_ttl_seconds: int = Field(default=0, description="Cache TTL in seconds")
    requires_auth: bool = Field(default=True, description="Requires authentication")
    deprecated: bool = Field(default=False, description="Whether deprecated")
    deprecation_message: str | None = Field(default=None, description="Deprecation message")


class DataServiceDefinition(BaseModel):
    """Data service definition."""

    service_id: str = Field(..., description="Unique service identifier")
    name: str = Field(..., description="Service name")
    description: str = Field(default="", description="Service description")
    category: DataServiceCategory = Field(..., description="Service category")
    provider: str = Field(default="openfinance", description="Service provider")
    version: str = Field(default="1.0.0", description="Service version")
    endpoints: list[DataServiceEndpoint] = Field(default_factory=list, description="Service endpoints")
    pricing_model: PricingModel = Field(default=PricingModel.FREE, description="Pricing model")
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig, description="Rate limit config")
    status: DataServiceStatus = Field(default=DataServiceStatus.ACTIVE, description="Service status")
    tags: list[str] = Field(default_factory=list, description="Service tags")
    documentation_url: str | None = Field(default=None, description="Documentation URL")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Update timestamp")


class DataServiceSubscription(BaseModel):
    """Data service subscription."""

    subscription_id: str = Field(..., description="Unique subscription identifier")
    service_id: str = Field(..., description="Service identifier")
    user_id: str = Field(..., description="User identifier")
    plan: SubscriptionPlan = Field(default=SubscriptionPlan.FREE, description="Subscription plan")
    quota: QuotaConfig = Field(default_factory=QuotaConfig, description="Quota configuration")
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE, description="Subscription status")
    started_at: datetime = Field(default_factory=datetime.now, description="Start timestamp")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class DataServiceUsage(BaseModel):
    """Data service usage record."""

    usage_id: str = Field(..., description="Unique usage identifier")
    subscription_id: str = Field(..., description="Subscription identifier")
    service_id: str = Field(..., description="Service identifier")
    user_id: str = Field(..., description="User identifier")
    endpoint: str = Field(..., description="Endpoint used")
    method: EndpointMethod = Field(..., description="HTTP method")
    request_size: int = Field(default=0, description="Request size in bytes")
    response_size: int = Field(default=0, description="Response size in bytes")
    response_time_ms: float = Field(default=0.0, description="Response time in milliseconds")
    status_code: int = Field(default=200, description="HTTP status code")
    success: bool = Field(default=True, description="Whether request succeeded")
    error_message: str | None = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Usage timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DataRequest(BaseModel):
    """Data service request."""

    request_id: str = Field(..., description="Unique request identifier")
    service_id: str = Field(..., description="Service identifier")
    endpoint: str = Field(..., description="Endpoint path")
    method: EndpointMethod = Field(default=EndpointMethod.GET, description="HTTP method")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Request parameters")
    headers: dict[str, str] = Field(default_factory=dict, description="Request headers")
    user_id: str | None = Field(default=None, description="User identifier")
    api_key: str | None = Field(default=None, description="API key")
    timestamp: datetime = Field(default_factory=datetime.now, description="Request timestamp")


class DataResponse(BaseModel):
    """Data service response."""

    request_id: str = Field(..., description="Request identifier")
    success: bool = Field(default=True, description="Whether request succeeded")
    data: Any = Field(default=None, description="Response data")
    error_code: str | None = Field(default=None, description="Error code if failed")
    error_message: str | None = Field(default=None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ServiceHealth(BaseModel):
    """Service health status."""

    service_id: str = Field(..., description="Service identifier")
    status: str = Field(default="healthy", description="Health status")
    uptime_seconds: float = Field(default=0.0, description="Uptime in seconds")
    total_requests: int = Field(default=0, description="Total requests")
    successful_requests: int = Field(default=0, description="Successful requests")
    failed_requests: int = Field(default=0, description="Failed requests")
    avg_response_time_ms: float = Field(default=0.0, description="Average response time")
    last_check: datetime = Field(default_factory=datetime.now, description="Last health check")


class AnalysisDataObject(BaseModel):
    """Analysis layer data object."""

    object_type: str = Field(..., description="Object type")
    object_id: str = Field(..., description="Object identifier")
    data: dict[str, Any] = Field(default_factory=dict, description="Object data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Object metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")


class GraphDataObject(BaseModel):
    """Knowledge graph layer data object."""

    object_type: str = Field(..., description="Object type: entity, relation, event, news")
    object_id: str = Field(..., description="Object identifier")
    data: dict[str, Any] = Field(default_factory=dict, description="Object data")
    relations: list[dict[str, Any]] = Field(default_factory=list, description="Related objects")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Object metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")


class QuantDataObject(BaseModel):
    """Quantitative analysis layer data object."""

    object_type: str = Field(..., description="Object type: factor, backtest, signal, portfolio")
    object_id: str = Field(..., description="Object identifier")
    data: dict[str, Any] = Field(default_factory=dict, description="Object data")
    metrics: dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Object metadata")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
