"""
Source Config - Configuration models for data sources.

Provides Pydantic models for data source configuration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, SecretStr

from openfinance.datacenter.collector.source.types import SourceType, SourceStatus, AuthType


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    
    requests_per_minute: int | None = Field(default=None, description="Requests per minute")
    requests_per_second: float | None = Field(default=None, description="Requests per second")
    burst_size: int | None = Field(default=None, description="Burst size for rate limiting")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "requests_per_minute": self.requests_per_minute,
            "requests_per_second": self.requests_per_second,
            "burst_size": self.burst_size,
        }


class RetryConfig(BaseModel):
    """Retry configuration."""
    
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    exponential_backoff: bool = Field(default=True, description="Use exponential backoff")
    max_delay: float = Field(default=60.0, description="Maximum delay between retries")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "exponential_backoff": self.exponential_backoff,
            "max_delay": self.max_delay,
        }


class AuthConfig(BaseModel):
    """Authentication configuration."""
    
    auth_type: AuthType = Field(default=AuthType.NONE, description="Authentication type")
    api_key: SecretStr | None = Field(default=None, description="API key")
    api_secret: SecretStr | None = Field(default=None, description="API secret")
    username: str | None = Field(default=None, description="Username for basic auth")
    password: SecretStr | None = Field(default=None, description="Password for basic auth")
    bearer_token: SecretStr | None = Field(default=None, description="Bearer token")
    oauth_config: dict[str, Any] = Field(default_factory=dict, description="OAuth configuration")
    custom_headers: dict[str, str] = Field(default_factory=dict, description="Custom auth headers")
    
    def to_dict(self, include_secrets: bool = False) -> dict[str, Any]:
        result = {
            "auth_type": self.auth_type.value,
            "oauth_config": self.oauth_config,
            "custom_headers": self.custom_headers,
        }
        
        if include_secrets:
            result.update({
                "api_key": self.api_key.get_secret_value() if self.api_key else None,
                "api_secret": self.api_secret.get_secret_value() if self.api_secret else None,
                "username": self.username,
                "password": self.password.get_secret_value() if self.password else None,
                "bearer_token": self.bearer_token.get_secret_value() if self.bearer_token else None,
            })
        
        return result


class ConnectionConfig(BaseModel):
    """Connection configuration."""
    
    base_url: str | None = Field(default=None, description="Base URL for API sources")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    connect_timeout: float = Field(default=10.0, description="Connection timeout in seconds")
    pool_size: int = Field(default=10, description="Connection pool size")
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates")
    proxy: str | None = Field(default=None, description="Proxy URL")
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "connect_timeout": self.connect_timeout,
            "pool_size": self.pool_size,
            "ssl_verify": self.ssl_verify,
            "proxy": self.proxy,
        }


class SourceConfig(BaseModel):
    """Complete configuration for a data source."""
    
    source_id: str = Field(..., description="Unique identifier for the source")
    name: str = Field(..., description="Human-readable name")
    source_type: SourceType = Field(default=SourceType.API, description="Type of data source")
    
    connection: ConnectionConfig = Field(
        default_factory=ConnectionConfig,
        description="Connection configuration"
    )
    
    auth: AuthConfig = Field(
        default_factory=AuthConfig,
        description="Authentication configuration"
    )
    
    rate_limit: RateLimitConfig = Field(
        default_factory=RateLimitConfig,
        description="Rate limit configuration"
    )
    
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry configuration"
    )
    
    enabled: bool = Field(default=True, description="Whether source is enabled")
    status: SourceStatus = Field(default=SourceStatus.UNKNOWN, description="Current status")
    
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    def to_dict(self, include_secrets: bool = False) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "source_type": self.source_type.value,
            "connection": self.connection.to_dict(),
            "auth": self.auth.to_dict(include_secrets=include_secrets),
            "rate_limit": self.rate_limit.to_dict(),
            "retry": self.retry.to_dict(),
            "enabled": self.enabled,
            "status": self.status.value,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CollectionRule(BaseModel):
    """Rule for data collection from a source."""
    
    rule_id: str = Field(..., description="Unique identifier for the rule")
    name: str = Field(..., description="Human-readable name")
    source_id: str = Field(..., description="Associated source ID")
    
    data_type: str = Field(..., description="Type of data to collect")
    endpoint: str | None = Field(default=None, description="Specific endpoint")
    
    params: dict[str, Any] = Field(default_factory=dict, description="Collection parameters")
    filters: dict[str, Any] = Field(default_factory=dict, description="Data filters")
    
    field_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping from source fields to target fields"
    )
    
    transform_rules: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Data transformation rules"
    )
    
    validation_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Data validation rules"
    )
    
    enabled: bool = Field(default=True)
    
    class Config:
        use_enum_values = True
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "source_id": self.source_id,
            "data_type": self.data_type,
            "endpoint": self.endpoint,
            "params": self.params,
            "filters": self.filters,
            "field_mapping": self.field_mapping,
            "transform_rules": self.transform_rules,
            "validation_rules": self.validation_rules,
            "enabled": self.enabled,
        }
