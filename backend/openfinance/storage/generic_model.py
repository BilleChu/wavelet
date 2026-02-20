"""
Generic storage models for metadata-driven architecture.

Provides flexible ORM models that store dynamic attributes as JSONB,
allowing schema evolution without database migrations.

Fully compatible with legacy models in orm.py:
- EntityModel -> GenericEntityModel
- RelationModel -> GenericRelationModel
- FactorDataModel -> GenericFactorModel
- Strategy (Pydantic) -> GenericStrategyModel
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any

from sqlalchemy import String, Text, DateTime, Date, Float, Index, Boolean, ForeignKey, Integer, BigInteger, DECIMAL, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class GenericEntityModel(Base):
    """Generic entity model with dynamic attributes.
    
    Fully compatible with legacy EntityModel in orm.py.
    All original fields preserved with same names and types.
    """
    
    __tablename__ = "metadata_entities"
    __table_args__ = (
        Index("ix_metadata_entities_type_code", "entity_type", "code"),
        Index("ix_metadata_entities_type_name", "entity_type", "name"),
        Index("ix_metadata_entities_attributes", "attributes", postgresql_using="gin"),
        {"schema": "openfinance"},
    )
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    entity_id: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True,
        nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=[])
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    
    industry: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    market: Mapped[str | None] = mapped_column(String(50), nullable=True)
    market_cap: Mapped[float | None] = mapped_column(DECIMAL(20, 2), nullable=True)
    
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, 
        default={},
        doc="Dynamic attributes stored as JSON (alias for properties)"
    )
    
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    outgoing_relations: Mapped[list["GenericRelationModel"]] = relationship(
        "GenericRelationModel",
        foreign_keys="GenericRelationModel.source_entity_id",
        back_populates="source_entity",
        lazy="selectin",
    )
    incoming_relations: Mapped[list["GenericRelationModel"]] = relationship(
        "GenericRelationModel",
        foreign_keys="GenericRelationModel.target_entity_id",
        back_populates="target_entity",
        lazy="selectin",
    )
    
    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default) or self.properties.get(key, default)
    
    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value
        self.properties[key] = value
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "aliases": self.aliases,
            "description": self.description,
            "code": self.code,
            "industry": self.industry,
            "market": self.market,
            "market_cap": float(self.market_cap) if self.market_cap else None,
            "properties": self.properties,
            "source": self.source,
            "confidence": float(self.confidence) if self.confidence else None,
            "schema_version": self.schema_version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        result.update(self.attributes)
        return result
    
    @classmethod
    def from_dict(
        cls, 
        data: dict[str, Any], 
        entity_type: str | None = None
    ) -> GenericEntityModel:
        core_fields = {
            "id", "entity_id", "entity_type", "name", "code",
            "aliases", "description", "industry", "market", "market_cap",
            "properties", "source", "confidence",
            "schema_version", "is_active",
            "created_at", "updated_at"
        }
        
        core_data = {k: v for k, v in data.items() if k in core_fields}
        if entity_type:
            core_data["entity_type"] = entity_type
        
        if "entity_id" not in core_data:
            code = data.get("code", "")
            etype = core_data.get("entity_type", "entity")
            core_data["entity_id"] = f"{etype}_{code}" if code else f"{etype}_{uuid.uuid4().hex[:8]}"
        
        attributes = {k: v for k, v in data.items() if k not in core_fields}
        
        return cls(**core_data, attributes=attributes)


class GenericRelationModel(Base):
    """Generic relation model with dynamic attributes.
    
    Fully compatible with legacy RelationModel in orm.py.
    All original fields preserved with same names and types.
    """
    
    __tablename__ = "metadata_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relation_type",
            name="uq_metadata_relation",
        ),
        Index("ix_metadata_relations_type_source", "relation_type", "source_entity_id"),
        Index("ix_metadata_relations_type_target", "relation_type", "target_entity_id"),
        Index("ix_metadata_relations_source_target", "source_entity_id", "target_entity_id"),
        {"schema": "openfinance"},
    )
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    relation_id: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True,
        nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    source_entity_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("openfinance.metadata_entities.entity_id", ondelete="CASCADE"),
        index=True, 
        nullable=False
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(255), 
        ForeignKey("openfinance.metadata_entities.entity_id", ondelete="CASCADE"),
        index=True, 
        nullable=False
    )
    
    weight: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    confidence: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.0)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, 
        default={},
        doc="Dynamic attributes stored as JSON (alias for properties)"
    )
    
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    source_entity: Mapped["GenericEntityModel"] = relationship(
        "GenericEntityModel", 
        foreign_keys=[source_entity_id], 
        back_populates="outgoing_relations"
    )
    target_entity: Mapped["GenericEntityModel"] = relationship(
        "GenericEntityModel", 
        foreign_keys=[target_entity_id], 
        back_populates="incoming_relations"
    )
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "relation_id": self.relation_id,
            "relation_type": self.relation_type,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "weight": float(self.weight) if self.weight else 1.0,
            "confidence": float(self.confidence) if self.confidence else 1.0,
            "evidence": self.evidence,
            "properties": self.properties,
            "source": self.source,
            "schema_version": self.schema_version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        result.update(self.attributes)
        return result


class GenericFactorModel(Base):
    """Generic factor model for storing factor data.
    
    Fully compatible with legacy FactorDataModel in orm.py.
    All original fields preserved with same names and types.
    
    Original FactorDataModel fields:
    - id: BigInteger, autoincrement
    - factor_id: String(50), index
    - factor_name: String(100)
    - factor_category: String(50), index
    - code: String(10), index
    - trade_date: Date, index
    - factor_value: DECIMAL(20, 8)
    - factor_rank: Integer
    - factor_percentile: DECIMAL(8, 4)
    - neutralized: Boolean, default=False
    - collected_at: TIMESTAMP(timezone=True)
    """
    
    __tablename__ = "metadata_factors"
    __table_args__ = (
        UniqueConstraint("factor_id", "code", "trade_date", name="uq_metadata_factor_data"),
        Index("ix_metadata_factors_date", "trade_date"),
        Index("ix_metadata_factors_symbol_date", "code", "trade_date"),
        Index("ix_metadata_factors_type_symbol_date", "factor_category", "code", "trade_date"),
        Index("ix_metadata_factors_attributes", "attributes", postgresql_using="gin"),
        {"schema": "openfinance"},
    )
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    factor_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    factor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    factor_category: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    
    code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    
    factor_value: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    factor_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    factor_percentile: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    neutralized: Mapped[bool] = mapped_column(Boolean, default=False)
    
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, 
        default={},
        doc="Dynamic attributes for extended factor data"
    )
    
    collected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    
    @property
    def factor_type(self) -> str | None:
        """Alias for factor_category for compatibility."""
        return self.factor_category
    
    @factor_type.setter
    def factor_type(self, value: str | None) -> None:
        self.factor_category = value
    
    @property
    def symbol(self) -> str:
        """Alias for code for compatibility."""
        return self.code
    
    @symbol.setter
    def symbol(self, value: str) -> None:
        self.code = value
    
    @property
    def value(self) -> float | None:
        """Alias for factor_value for compatibility."""
        return float(self.factor_value) if self.factor_value is not None else None
    
    @value.setter
    def value(self, val: float | None) -> None:
        if val is not None:
            self.factor_value = val
    
    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "factor_id": self.factor_id,
            "factor_name": self.factor_name,
            "factor_category": self.factor_category,
            "factor_type": self.factor_category,
            "code": self.code,
            "symbol": self.code,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "factor_value": float(self.factor_value) if self.factor_value is not None else None,
            "value": float(self.factor_value) if self.factor_value is not None else None,
            "factor_rank": self.factor_rank,
            "factor_percentile": float(self.factor_percentile) if self.factor_percentile else None,
            "neutralized": self.neutralized,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
        }
        result.update(self.attributes)
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenericFactorModel:
        core_fields = {
            "id", "factor_id", "factor_name", "factor_category", "factor_type",
            "code", "symbol", "trade_date", "factor_value", "value",
            "factor_rank", "factor_percentile", "neutralized", "collected_at"
        }
        
        core_data = {}
        for k, v in data.items():
            if k in core_fields:
                if k == "factor_type":
                    core_data["factor_category"] = v
                elif k == "symbol":
                    core_data["code"] = v
                elif k == "value":
                    core_data["factor_value"] = v
                else:
                    core_data[k] = v
        
        attributes = {k: v for k, v in data.items() if k not in core_fields}
        core_data["attributes"] = attributes
        
        return cls(**core_data)


class GenericStrategyModel(Base):
    """Generic strategy model for storing strategy configurations.
    
    Fully compatible with Strategy Pydantic model in models/quant.py.
    All original fields preserved with same names and types.
    
    Original Strategy fields:
    - strategy_id: str
    - name: str
    - code: str (unique identifier)
    - description: str
    - strategy_type: StrategyType enum
    - factors: list[str]
    - factor_weights: dict[str, float]
    - weight_method: WeightMethod enum
    - parameters: dict[str, Any]
    - rebalance_freq: str
    - max_positions: int
    - position_size: float
    - stop_loss: float | None
    - take_profit: float | None
    - status: FactorStatus enum
    - version: int
    - created_at: datetime
    - updated_at: datetime
    - created_by: str | None
    - metadata: dict[str, Any]
    """
    
    __tablename__ = "metadata_strategies"
    __table_args__ = (
        Index("ix_metadata_strategies_type", "strategy_type"),
        Index("ix_metadata_strategies_status", "status"),
        Index("ix_metadata_strategies_attributes", "attributes", postgresql_using="gin"),
        {"schema": "openfinance"},
    )
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    strategy_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    strategy_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    
    factors: Mapped[list[str]] = mapped_column(JSONB, default=[])
    factor_weights: Mapped[dict[str, float]] = mapped_column(JSONB, default={})
    weight_method: Mapped[str] = mapped_column(String(50), default="equal")
    
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    
    rebalance_freq: Mapped[str] = mapped_column(String(20), default="monthly")
    max_positions: Mapped[int] = mapped_column(Integer, default=50)
    position_size: Mapped[float] = mapped_column(DECIMAL(8, 4), default=0.02)
    stop_loss: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    take_profit: Mapped[float | None] = mapped_column(DECIMAL(8, 4), nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, 
        default={},
        doc="Dynamic attributes for extended strategy data"
    )
    
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    @property
    def strategy_metadata(self) -> dict[str, Any]:
        """Alias for attributes for compatibility with Strategy Pydantic model."""
        return self.attributes
    
    @strategy_metadata.setter
    def strategy_metadata(self, value: dict[str, Any]) -> None:
        self.attributes = value
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "factors": self.factors,
            "factor_weights": self.factor_weights,
            "weight_method": self.weight_method,
            "parameters": self.parameters,
            "config": self.config,
            "rebalance_freq": self.rebalance_freq,
            "max_positions": self.max_positions,
            "position_size": float(self.position_size) if self.position_size else 0.02,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "status": self.status,
            "version": self.version,
            "metadata": self.attributes,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenericStrategyModel:
        core_fields = {
            "id", "strategy_id", "code", "name", "description",
            "strategy_type", "factors", "factor_weights", "weight_method",
            "parameters", "config", "rebalance_freq",
            "max_positions", "position_size", "stop_loss", "take_profit",
            "status", "version", "created_by", "created_at", "updated_at",
            "metadata", "attributes"
        }
        
        core_data = {}
        for k, v in data.items():
            if k in core_fields:
                if k == "metadata":
                    core_data["attributes"] = v
                else:
                    core_data[k] = v
        
        extra_attrs = {k: v for k, v in data.items() if k not in core_fields}
        if extra_attrs:
            if "attributes" not in core_data:
                core_data["attributes"] = {}
            core_data["attributes"].update(extra_attrs)
        
        return cls(**core_data)
