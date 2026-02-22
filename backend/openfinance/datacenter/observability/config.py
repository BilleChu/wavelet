"""
Observability Configuration - Load and manage observability settings.

Configuration is loaded from observability.yaml and can be customized at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class QualityThresholds:
    """Quality threshold configuration."""
    completeness: float = 0.95
    accuracy: float = 0.99
    timeliness_hours: int = 24


@dataclass
class MetricsConfig:
    """Metrics collection configuration."""
    enabled: bool = True
    port: int = 9090
    namespace: str = "datacenter"


@dataclass
class AlertChannelConfig:
    """Alert channel configuration."""
    type: str = "log"
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRuleConfig:
    """Alert rule configuration."""
    rule_id: str
    name: str
    description: str = ""
    condition: str = ""
    severity: str = "warning"
    cooldown_minutes: int = 5
    enabled: bool = True


@dataclass
class ObservabilityConfig:
    """Complete observability configuration."""
    
    quality_thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    enabled_dimensions: list[str] = field(default_factory=lambda: [
        "completeness", "accuracy", "timeliness", 
        "consistency", "uniqueness", "validity"
    ])
    
    max_alerts: int = 10000
    max_metrics: int = 100000
    max_records: int = 10000
    
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    alert_channels: list[AlertChannelConfig] = field(default_factory=list)
    alert_rules: list[AlertRuleConfig] = field(default_factory=list)
    
    lineage_enabled: bool = True
    lineage_max_depth: int = 10
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObservabilityConfig":
        """Create config from dictionary."""
        quality_data = data.get("quality", {})
        thresholds_data = quality_data.get("default_thresholds", {})
        
        monitoring_data = data.get("monitoring", {})
        metrics_data = monitoring_data.get("metrics", {})
        
        alerts_data = data.get("alerts", {})
        channels_data = alerts_data.get("channels", [])
        rules_data = alerts_data.get("rules", [])
        
        lineage_data = data.get("lineage", {})
        
        return cls(
            quality_thresholds=QualityThresholds(
                completeness=thresholds_data.get("completeness", 0.95),
                accuracy=thresholds_data.get("accuracy", 0.99),
                timeliness_hours=thresholds_data.get("timeliness_hours", 24),
            ),
            enabled_dimensions=quality_data.get("enabled_dimensions", [
                "completeness", "accuracy", "timeliness",
                "consistency", "uniqueness", "validity"
            ]),
            max_alerts=monitoring_data.get("max_alerts", 10000),
            max_metrics=monitoring_data.get("max_metrics", 100000),
            max_records=monitoring_data.get("max_records", 10000),
            metrics=MetricsConfig(
                enabled=metrics_data.get("enabled", True),
                port=metrics_data.get("port", 9090),
                namespace=metrics_data.get("namespace", "datacenter"),
            ),
            alert_channels=[
                AlertChannelConfig(
                    type=ch.get("type", "log"),
                    enabled=ch.get("enabled", True),
                    config=ch.get("config", {}),
                )
                for ch in channels_data
            ],
            alert_rules=[
                AlertRuleConfig(
                    rule_id=rule.get("rule_id", ""),
                    name=rule.get("name", ""),
                    description=rule.get("description", ""),
                    condition=rule.get("condition", ""),
                    severity=rule.get("severity", "warning"),
                    cooldown_minutes=rule.get("cooldown_minutes", 5),
                    enabled=rule.get("enabled", True),
                )
                for rule in rules_data
            ],
            lineage_enabled=lineage_data.get("enabled", True),
            lineage_max_depth=lineage_data.get("max_depth", 10),
        )


_config: ObservabilityConfig | None = None
_config_path: Path | None = None


def load_config(config_path: str | Path | None = None) -> ObservabilityConfig:
    """Load observability configuration from file."""
    global _config, _config_path
    
    if config_path:
        _config_path = Path(config_path)
    elif _config_path is None:
        _config_path = Path(__file__).parent / "observability.yaml"
    
    if not _config_path.exists():
        logger.warning(f"Observability config file not found: {_config_path}")
        _config = ObservabilityConfig()
        return _config
    
    try:
        with open(_config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        _config = ObservabilityConfig.from_dict(data or {})
        logger.info(f"Loaded observability config from {_config_path}")
        return _config
        
    except Exception as e:
        logger.error(f"Failed to load observability config: {e}")
        _config = ObservabilityConfig()
        return _config


def get_config() -> ObservabilityConfig:
    """Get current observability configuration."""
    global _config
    if _config is None:
        return load_config()
    return _config


def reload_config() -> ObservabilityConfig:
    """Reload configuration from file."""
    global _config
    _config = None
    return load_config()
