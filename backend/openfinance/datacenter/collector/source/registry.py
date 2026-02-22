"""
Source Registry - Centralized data source management.

Provides:
- Source configuration CRUD
- Source discovery
- Configuration loading from YAML
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from openfinance.datacenter.collector.source.types import SourceType, SourceStatus
from openfinance.datacenter.collector.source.config import (
    SourceConfig,
    CollectionRule,
    ConnectionConfig,
    AuthConfig,
    RateLimitConfig,
    RetryConfig,
)
from openfinance.datacenter.collector.source.health import HealthChecker, SourceHealth
from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


class SourceRegistry:
    """
    Centralized registry for data source management.
    
    Features:
    - Source configuration CRUD
    - Configuration loading from YAML
    - Health monitoring integration
    - Collection rule management
    
    Usage:
        registry = SourceRegistry()
        registry.load_from_file("config/sources.yaml")
        
        source = registry.get_source("eastmoney")
        health = await registry.check_health("eastmoney")
    """
    
    _instance: "SourceRegistry | None" = None
    
    def __init__(
        self,
        config_path: str | Path | None = None,
    ):
        self._sources: dict[str, SourceConfig] = {}
        self._rules: dict[str, CollectionRule] = {}
        self._health_checker = HealthChecker()
        
        if config_path:
            self.load_from_file(config_path)
    
    @classmethod
    def get_instance(cls, **kwargs) -> "SourceRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def load_from_file(self, config_path: str | Path) -> int:
        """Load source configurations from YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            logger.warning(f"Source config file not found: {config_path}")
            return 0
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            
            if not data:
                return 0
            
            count = 0
            
            if "sources" in data:
                for source_id, source_data in data["sources"].items():
                    config = self._parse_source_config(source_id, source_data)
                    self._sources[source_id] = config
                    count += 1
            
            if "rules" in data:
                for rule_id, rule_data in data["rules"].items():
                    rule = self._parse_collection_rule(rule_id, rule_data)
                    self._rules[rule_id] = rule
            
            logger.info(f"Loaded {count} source configurations from {config_path}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to load source config: {e}")
            return 0
    
    def _parse_source_config(
        self,
        source_id: str,
        data: dict[str, Any],
    ) -> SourceConfig:
        """Parse source configuration from dict."""
        from openfinance.datacenter.collector.source.types import AuthType
        
        conn_data = data.get("connection", {})
        auth_data = data.get("auth", {})
        rate_data = data.get("rate_limit", {})
        retry_data = data.get("retry", {})
        
        connection = ConnectionConfig(
            base_url=conn_data.get("base_url") or data.get("base_url"),
            timeout=conn_data.get("timeout", data.get("timeout", 30.0)),
            connect_timeout=conn_data.get("connect_timeout", 10.0),
            pool_size=conn_data.get("pool_size", 10),
            ssl_verify=conn_data.get("ssl_verify", True),
            proxy=conn_data.get("proxy"),
        )
        
        auth = AuthConfig(
            auth_type=AuthType(auth_data.get("type", "none")),
            api_key=auth_data.get("api_key"),
            api_secret=auth_data.get("api_secret"),
            username=auth_data.get("username"),
            password=auth_data.get("password"),
            bearer_token=auth_data.get("bearer_token"),
            custom_headers=auth_data.get("headers", {}),
        )
        
        rate_limit = RateLimitConfig(
            requests_per_minute=rate_data.get("requests_per_minute") or data.get("rate_limit"),
            requests_per_second=rate_data.get("requests_per_second"),
            burst_size=rate_data.get("burst_size"),
        )
        
        retry = RetryConfig(
            max_retries=retry_data.get("max_retries", data.get("max_retries", 3)),
            retry_delay=retry_data.get("retry_delay", data.get("retry_delay", 1.0)),
            exponential_backoff=retry_data.get("exponential_backoff", True),
            max_delay=retry_data.get("max_delay", 60.0),
        )
        
        return SourceConfig(
            source_id=source_id,
            name=data.get("name", source_id),
            source_type=SourceType(data.get("type", "api")),
            connection=connection,
            auth=auth,
            rate_limit=rate_limit,
            retry=retry,
            enabled=data.get("enabled", True),
            status=SourceStatus(data.get("status", "unknown")),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
    
    def _parse_collection_rule(
        self,
        rule_id: str,
        data: dict[str, Any],
    ) -> CollectionRule:
        """Parse collection rule from dict."""
        return CollectionRule(
            rule_id=rule_id,
            name=data.get("name", rule_id),
            source_id=data.get("source_id", ""),
            data_type=data.get("data_type", ""),
            endpoint=data.get("endpoint"),
            params=data.get("params", {}),
            filters=data.get("filters", {}),
            field_mapping=data.get("field_mapping", {}),
            transform_rules=data.get("transform_rules", []),
            validation_rules=data.get("validation_rules", {}),
            enabled=data.get("enabled", True),
        )
    
    def register_source(self, config: SourceConfig) -> None:
        """Register a data source configuration."""
        config.updated_at = datetime.now()
        self._sources[config.source_id] = config
        logger.info(f"Registered source: {config.source_id}")
    
    def unregister_source(self, source_id: str) -> bool:
        """Unregister a data source."""
        if source_id in self._sources:
            del self._sources[source_id]
            logger.info(f"Unregistered source: {source_id}")
            return True
        return False
    
    def get_source(self, source_id: str) -> SourceConfig | None:
        """Get a source configuration by ID."""
        return self._sources.get(source_id)
    
    def get_sources(
        self,
        source_type: SourceType | None = None,
        enabled_only: bool = False,
        tags: list[str] | None = None,
    ) -> list[SourceConfig]:
        """Get source configurations with filtering."""
        sources = list(self._sources.values())
        
        if source_type:
            sources = [s for s in sources if s.source_type == source_type]
        
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        
        if tags:
            sources = [s for s in sources if any(t in s.tags for t in tags)]
        
        return sources
    
    def get_source_names(self) -> list[str]:
        """Get all source IDs."""
        return list(self._sources.keys())
    
    async def check_health(self, source_id: str) -> dict[str, Any]:
        """Check health of a data source."""
        config = self._sources.get(source_id)
        if not config:
            return {"error": f"Source not found: {source_id}"}
        
        result = await self._health_checker.check_health(config)
        return result.to_dict()
    
    async def check_all_health(self) -> dict[str, dict[str, Any]]:
        """Check health of all data sources."""
        results = {}
        for source_id, config in self._sources.items():
            if config.enabled:
                result = await self._health_checker.check_health(config)
                results[source_id] = result.to_dict()
        return results
    
    def get_health(self, source_id: str) -> SourceHealth | None:
        """Get health status for a source."""
        return self._health_checker.get_health(source_id)
    
    def get_all_health(self) -> dict[str, SourceHealth]:
        """Get health status for all sources."""
        return self._health_checker.get_all_health()
    
    def register_rule(self, rule: CollectionRule) -> None:
        """Register a collection rule."""
        self._rules[rule.rule_id] = rule
        logger.info(f"Registered collection rule: {rule.rule_id}")
    
    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a collection rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    def get_rule(self, rule_id: str) -> CollectionRule | None:
        """Get a collection rule by ID."""
        return self._rules.get(rule_id)
    
    def get_rules_for_source(self, source_id: str) -> list[CollectionRule]:
        """Get all collection rules for a source."""
        return [r for r in self._rules.values() if r.source_id == source_id]
    
    def get_all_rules(self) -> list[CollectionRule]:
        """Get all collection rules."""
        return list(self._rules.values())
    
    def to_dict(self) -> dict[str, Any]:
        """Export registry to dictionary."""
        return {
            "sources": {
                sid: config.to_dict(include_secrets=False)
                for sid, config in self._sources.items()
            },
            "rules": {
                rid: rule.to_dict()
                for rid, rule in self._rules.items()
            },
            "health": {
                sid: health.to_dict()
                for sid, health in self._health_checker.get_all_health().items()
            },
        }


def get_source_registry() -> SourceRegistry:
    """Get the singleton SourceRegistry instance."""
    return SourceRegistry.get_instance()
