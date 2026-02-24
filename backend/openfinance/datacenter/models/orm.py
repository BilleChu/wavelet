"""
SQLAlchemy models for entities and relations.

Entity and relation types are dynamically loaded from YAML configuration.
See: domain/metadata/config/entity_types.yaml and relation_types.yaml
"""

from datetime import datetime
from typing import Any, Literal, Optional

from sqlalchemy import (
    ARRAY,
    JSON,
    DECIMAL,
    BigInteger,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    ForeignKey,
    Index,
    Date,
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from openfinance.infrastructure.database.database import Base


def _get_entity_types_from_registry() -> list[str]:
    """Dynamically get entity types from metadata registry."""
    try:
        from openfinance.domain.metadata.loader import MetadataLoader
        from openfinance.domain.metadata.registry import EntityTypeRegistry
        from pathlib import Path
        
        if not EntityTypeRegistry.get_type_ids():
            config_dir = Path(__file__).parent.parent.parent / "domain" / "metadata" / "config"
            loader = MetadataLoader(config_dir)
            loader.load_entity_types()
        
        types = EntityTypeRegistry.get_type_ids()
        if types:
            return types
    except Exception:
        pass
    
    return [
        "company", "industry", "concept", "person", "stock",
        "fund", "event", "sector", "index", "investor",
    ]


def _get_relation_types_from_registry() -> list[str]:
    """Dynamically get relation types from metadata registry."""
    try:
        from openfinance.domain.metadata.loader import MetadataLoader
        from openfinance.domain.metadata.registry import RelationTypeRegistry
        from pathlib import Path
        
        if not RelationTypeRegistry.get_type_ids():
            config_dir = Path(__file__).parent.parent.parent / "domain" / "metadata" / "config"
            loader = MetadataLoader(config_dir)
            loader.load_relation_types()
        
        types = RelationTypeRegistry.get_type_ids()
        if types:
            return types
    except Exception:
        pass
    
    return [
        "belongs_to", "has_concept", "competes_with", "supplies_to",
        "invests_in", "affects", "works_for", "manages", "owns",
        "parent_of", "subsidiary_of", "ceo_of", "director_of",
        "founded", "acquired", "merged_with", "operates_in",
        "regulated_by", "related_to", "listed_on",
    ]


def _get_entity_labels_from_registry() -> dict[str, str]:
    """Dynamically get entity type labels from metadata registry."""
    try:
        from openfinance.domain.metadata.loader import MetadataLoader
        from openfinance.domain.metadata.registry import EntityTypeRegistry
        from pathlib import Path
        
        if not EntityTypeRegistry.get_type_ids():
            config_dir = Path(__file__).parent.parent.parent / "domain" / "metadata" / "config"
            loader = MetadataLoader(config_dir)
            loader.load_entity_types()
        
        labels = {
            type_id: defn.display_name
            for type_id, defn in EntityTypeRegistry._types.items()
        }
        if labels:
            return labels
    except Exception:
        pass
    
    return {
        "company": "公司",
        "industry": "行业",
        "concept": "概念",
        "person": "人物",
        "stock": "股票",
        "fund": "基金",
        "event": "事件",
        "sector": "板块",
        "index": "指数",
        "investor": "投资者",
    }


def _get_relation_labels_from_registry() -> dict[str, str]:
    """Dynamically get relation type labels from metadata registry."""
    try:
        from openfinance.domain.metadata.loader import MetadataLoader
        from openfinance.domain.metadata.registry import RelationTypeRegistry
        from pathlib import Path
        
        if not RelationTypeRegistry.get_type_ids():
            config_dir = Path(__file__).parent.parent.parent / "domain" / "metadata" / "config"
            loader = MetadataLoader(config_dir)
            loader.load_relation_types()
        
        labels = {
            type_id: defn.display_name
            for type_id, defn in RelationTypeRegistry._types.items()
        }
        if labels:
            return labels
    except Exception:
        pass
    
    return {
        "belongs_to": "属于",
        "has_concept": "具有概念",
        "competes_with": "竞争",
        "supplies_to": "供应",
        "invests_in": "投资",
        "affects": "影响",
        "works_for": "任职",
        "manages": "管理",
        "owns": "拥有",
        "parent_of": "母公司",
        "subsidiary_of": "子公司",
        "ceo_of": "CEO",
        "director_of": "董事",
        "founded": "创立",
        "acquired": "收购",
        "merged_with": "合并",
        "operates_in": "运营于",
        "regulated_by": "受监管",
        "related_to": "相关",
        "listed_on": "上市于",
    }


VALID_ENTITY_TYPES = _get_entity_types_from_registry()
VALID_RELATION_TYPES = _get_relation_types_from_registry()
ENTITY_TYPE_LABELS = _get_entity_labels_from_registry()
RELATION_TYPE_LABELS = _get_relation_labels_from_registry()


def _create_entity_type_literal():
    """Dynamically create EntityTypeLiteral."""
    types = _get_entity_types_from_registry()
    return Literal[tuple(types)]


def _create_relation_type_literal():
    """Dynamically create RelationTypeLiteral."""
    types = _get_relation_types_from_registry()
    return Literal[tuple(types)]


EntityTypeLiteral = _create_entity_type_literal()
RelationTypeLiteral = _create_relation_type_literal()


class EntityModel(Base):
    """Entity database model."""

    __tablename__ = "entities"
    __table_args__ = {"schema": "openfinance"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[])
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    outgoing_relations: Mapped[list["RelationModel"]] = relationship(
        "RelationModel",
        foreign_keys="RelationModel.source_entity_id",
        back_populates="source_entity",
        lazy="selectin",
    )
    incoming_relations: Mapped[list["RelationModel"]] = relationship(
        "RelationModel",
        foreign_keys="RelationModel.target_entity_id",
        back_populates="target_entity",
        lazy="selectin",
    )


class TaskChainModel(Base):
    """Task chain model for DAG task orchestration."""

    __tablename__ = "task_chains"
    __table_args__ = {"schema": "openfinance"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    chain_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    nodes: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=[])
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    data_targets: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class TaskExecutionModel(Base):
    """Task execution record model."""

    __tablename__ = "task_executions"
    __table_args__ = (
        Index("ix_task_executions_task_id", "task_id"),
        Index("ix_task_executions_chain_id", "chain_id"),
        Index("ix_task_executions_started_at", "started_at"),
        {"schema": "openfinance"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    execution_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    task_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    chain_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoints: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    data_targets: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=[])
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class MonitoringMetricModel(Base):
    """Monitoring metric model for performance tracking."""

    __tablename__ = "monitoring_metrics"
    __table_args__ = (
        Index("ix_monitoring_metrics_type", "metric_type"),
        Index("ix_monitoring_metrics_recorded", "recorded_at"),
        {"schema": "openfinance"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    metric_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(DECIMAL(20, 6), nullable=False)
    labels: Mapped[dict[str, str]] = mapped_column(JSON, default={})
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class AlertModel(Base):
    """Alert model for monitoring alerts."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_created", "created_at"),
        {"schema": "openfinance"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    chain_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    alert_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ScheduledTaskModel(Base):
    """Scheduled task model for task scheduling."""

    __tablename__ = "scheduled_tasks"
    __table_args__ = {"schema": "openfinance"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cron_expression: Mapped[str | None] = mapped_column(String(100), nullable=True)
    daily_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_strategy: Mapped[str] = mapped_column(String(20), default="exponential")
    retry_delay_seconds: Mapped[float] = mapped_column(DECIMAL(10, 2), default=5.0)
    timeout_seconds: Mapped[float] = mapped_column(DECIMAL(10, 2), default=300.0)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=[])
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    last_run: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    next_run: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class RelationModel(Base):
    """Relation database model."""

    __tablename__ = "relations"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relation_type",
            name="uq_relation",
        ),
        {"schema": "openfinance"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    relation_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_entity_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("openfinance.entities.entity_id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("openfinance.entities.entity_id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    confidence: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    source_entity: Mapped["EntityModel"] = relationship(
        "EntityModel", foreign_keys=[source_entity_id], back_populates="outgoing_relations"
    )
    target_entity: Mapped["EntityModel"] = relationship(
        "EntityModel", foreign_keys=[target_entity_id], back_populates="incoming_relations"
    )


class StockBasicModel(Base):
    """Stock basic information model."""

    __tablename__ = "stock_basic"
    __table_args__ = {"schema": "openfinance"}

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    market: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    list_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    total_shares: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    circulating_shares: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default={})
    collected_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class StockDailyQuoteModel(Base):
    """Stock daily quote model."""

    __tablename__ = "stock_daily_quote"
    __table_args__ = (
        {"schema": "openfinance"},
    )

    code: Mapped[str] = mapped_column(String(10), primary_key=True, nullable=False)
    trade_date: Mapped[datetime] = mapped_column(Date, primary_key=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    open: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    change_pct: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    amplitude: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    circulating_market_cap: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class StockFinancialIndicatorModel(Base):
    """Stock financial indicator model."""

    __tablename__ = "stock_financial_indicator"
    __table_args__ = (
        UniqueConstraint("code", "report_date", name="uq_financial_indicator"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    report_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    eps: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    bps: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    roe: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    roa: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    net_margin: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    debt_ratio: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    current_ratio: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    quick_ratio: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    revenue: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    net_profit: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    revenue_yoy: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    net_profit_yoy: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class StockMoneyFlowModel(Base):
    """Stock money flow model."""

    __tablename__ = "stock_money_flow"
    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uq_money_flow"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    main_net_inflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    main_net_inflow_pct: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    super_large_net_inflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    large_net_inflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    medium_net_inflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    small_net_inflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    north_net_inflow: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class OptionQuoteModel(Base):
    """Option quote model."""

    __tablename__ = "option_quote"
    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uq_option_quote"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    underlying: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    strike_price: Mapped[float] = mapped_column(DECIMAL(12, 4), nullable=False)
    expiry_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    option_type: Mapped[str] = mapped_column(String(10), nullable=False)
    last_price: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    bid_price: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    ask_price: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    open_interest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    implied_volatility: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    delta: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    gamma: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    theta: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    vega: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    rho: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class FutureQuoteModel(Base):
    """Future quote model."""

    __tablename__ = "future_quote"
    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uq_future_quote"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    delivery_month: Mapped[str | None] = mapped_column(String(10), nullable=True)
    open: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    pre_settlement: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    settlement: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(DECIMAL(12, 4), nullable=True)
    change_pct: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amount: Mapped[float | None] = mapped_column(DECIMAL(20, 4), nullable=True)
    open_interest: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class FactorDataModel(Base):
    """Factor data model for quantitative analysis."""

    __tablename__ = "factor_data"
    __table_args__ = (
        UniqueConstraint("factor_id", "code", "trade_date", name="uq_factor_data"),
        Index("ix_factor_date", "trade_date"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    factor_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    factor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    factor_category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    factor_value: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    factor_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    factor_percentile: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    neutralized: Mapped[bool] = mapped_column(default=False)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class NewsModel(Base):
    """News data model."""

    __tablename__ = "news"
    __table_args__ = (
        Index("ix_news_published", "published_at"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    news_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[])
    sentiment: Mapped[float | None] = mapped_column(DECIMAL(4, 3), nullable=True)
    published_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, index=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class MacroEconomicModel(Base):
    """Macro economic data model."""

    __tablename__ = "macro_economic"
    __table_args__ = (
        UniqueConstraint("indicator_code", "period", name="uq_macro_data"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    indicator_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(DECIMAL(20, 4), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(10), default="CN")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class ESGRatingModel(Base):
    """ESG rating data model."""

    __tablename__ = "esg_rating"
    __table_args__ = (
        UniqueConstraint("code", "rating_agency", "rating_date", name="uq_esg_rating"),
        {"schema": "openfinance"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rating_agency: Mapped[str] = mapped_column(String(50), nullable=False)
    esg_score: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    e_score: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    s_score: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    g_score: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    esg_rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rating_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class EventModel(Base):
    """Event model for knowledge graph."""

    __tablename__ = "events"
    __table_args__ = {"schema": "openfinance"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_entities: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[])
    event_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    impact_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sentiment: Mapped[float | None] = mapped_column(DECIMAL(4, 3), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class IncomeStatementModel(Base):
    """Income statement model - unified with ADS naming."""

    __tablename__ = "income_statement"
    __table_args__ = {"schema": "openfinance"}

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    report_date: Mapped[datetime] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(10), default="annual")
    
    total_revenue: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    operating_revenue: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    other_revenue: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    total_operating_cost: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cost_of_goods_sold: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    selling_expenses: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    admin_expenses: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    rd_expenses: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    finance_expenses: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    operating_profit: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    total_profit: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    net_profit: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    net_profit_attr_parent: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    net_profit_attr_minority: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    income_tax: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    interest_expense: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    basic_eps: Mapped[Optional[DECIMAL(10, 4)]] = mapped_column(Numeric(10, 4), nullable=True)
    diluted_eps: Mapped[Optional[DECIMAL(10, 4)]] = mapped_column(Numeric(10, 4), nullable=True)
    
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class BalanceSheetModel(Base):
    """Balance sheet model - unified with ADS naming."""

    __tablename__ = "balance_sheet"
    __table_args__ = {"schema": "openfinance"}

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    report_date: Mapped[datetime] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(10), default="annual")
    
    total_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    total_current_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    total_non_current_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    cash: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    accounts_receivable: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    inventory: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    fixed_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    intangible_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    total_liabilities: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    total_current_liabilities: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    total_non_current_liabilities: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    short_term_debt: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    long_term_debt: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    accounts_payable: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    total_equity: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    paid_in_capital: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    retained_earnings: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class CashFlowModel(Base):
    """Cash flow statement model - unified with ADS naming."""

    __tablename__ = "cash_flow"
    __table_args__ = {"schema": "openfinance"}

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    report_date: Mapped[datetime] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(10), default="annual")
    
    net_cash_from_operating: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    net_cash_from_investing: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    net_cash_from_financing: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    net_cash_increase: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_at_beginning: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_at_end: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    cash_received_from_sales: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_paid_for_goods: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_paid_to_employees: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    taxes_paid: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    cash_paid_for_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_received_from_assets: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_paid_for_investments: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    cash_received_from_financing: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    cash_paid_for_debt: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    dividends_paid: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    free_cash_flow: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class DividendDataModel(Base):
    """Dividend data model."""

    __tablename__ = "dividend_data"
    __table_args__ = {"schema": "openfinance"}

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    report_year: Mapped[str] = mapped_column(String(4), primary_key=True)
    
    ex_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    dividend_per_share: Mapped[Optional[DECIMAL(10, 4)]] = mapped_column(Numeric(10, 4), nullable=True)
    bonus_per_share: Mapped[Optional[DECIMAL(10, 4)]] = mapped_column(Numeric(10, 4), nullable=True)
    transfer_per_share: Mapped[Optional[DECIMAL(10, 4)]] = mapped_column(Numeric(10, 4), nullable=True)
    total_dividend: Mapped[Optional[DECIMAL(20, 8)]] = mapped_column(Numeric(20, 8), nullable=True)
    dividend_yield: Mapped[Optional[DECIMAL(10, 4)]] = mapped_column(Numeric(10, 4), nullable=True)
    
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
