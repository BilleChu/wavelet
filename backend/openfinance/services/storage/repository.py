"""
Repository layer for generic storage models.

Provides high-level data access methods with metadata-driven validation.
Fully compatible with legacy models in orm.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any, Generic, TypeVar

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.domain.schemas.generic_model import (
    GenericEntityModel,
    GenericRelationModel,
    GenericFactorModel,
    GenericStrategyModel,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""
    
    model_class: type
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, id: str | int) -> T | None:
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs) -> T:
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def update(self, id: str | int, **kwargs) -> T | None:
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        await self.session.flush()
        return instance
    
    async def delete(self, id: str | int) -> bool:
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        
        await self.session.delete(instance)
        await self.session.flush()
        return True


class EntityRepository(BaseRepository[GenericEntityModel]):
    """Repository for generic entities."""
    
    model_class = GenericEntityModel
    
    async def get_by_entity_id(self, entity_id: str) -> GenericEntityModel | None:
        result = await self.session.execute(
            select(GenericEntityModel).where(
                GenericEntityModel.entity_id == entity_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_type_and_code(
        self, 
        entity_type: str, 
        code: str
    ) -> GenericEntityModel | None:
        result = await self.session.execute(
            select(GenericEntityModel).where(
                and_(
                    GenericEntityModel.entity_type == entity_type,
                    GenericEntityModel.code == code,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def search(
        self,
        entity_type: str | None = None,
        query: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        is_active: bool = True,
    ) -> list[GenericEntityModel]:
        stmt = select(GenericEntityModel)
        
        if entity_type:
            stmt = stmt.where(GenericEntityModel.entity_type == entity_type)
        
        if query:
            stmt = stmt.where(
                or_(
                    GenericEntityModel.name.ilike(f"%{query}%"),
                    GenericEntityModel.code.ilike(f"%{query}%"),
                )
            )
        
        if is_active is not None:
            stmt = stmt.where(GenericEntityModel.is_active == is_active)
        
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(
                    GenericEntityModel.attributes[key].astext == str(value)
                )
        
        stmt = stmt.offset(offset).limit(limit).order_by(
            GenericEntityModel.created_at.desc()
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count(
        self,
        entity_type: str | None = None,
        query: str | None = None,
        is_active: bool = True,
    ) -> int:
        stmt = select(func.count(GenericEntityModel.id))
        
        if entity_type:
            stmt = stmt.where(GenericEntityModel.entity_type == entity_type)
        
        if query:
            stmt = stmt.where(
                or_(
                    GenericEntityModel.name.ilike(f"%{query}%"),
                    GenericEntityModel.code.ilike(f"%{query}%"),
                )
            )
        
        if is_active is not None:
            stmt = stmt.where(GenericEntityModel.is_active == is_active)
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def create_entity(
        self,
        entity_type: str,
        name: str,
        code: str | None = None,
        aliases: list[str] | None = None,
        description: str | None = None,
        industry: str | None = None,
        market: str | None = None,
        market_cap: float | None = None,
        properties: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        source: str | None = None,
        confidence: float | None = None,
    ) -> GenericEntityModel:
        entity_id = f"{entity_type}_{code}" if code else f"{entity_type}_{datetime.utcnow().timestamp()}"
        
        instance = GenericEntityModel(
            entity_id=entity_id,
            entity_type=entity_type,
            name=name,
            code=code,
            aliases=aliases or [],
            description=description,
            industry=industry,
            market=market,
            market_cap=market_cap,
            properties=properties or {},
            attributes=attributes or {},
            source=source,
            confidence=confidence or 1.0,
        )
        
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def upsert_entity(
        self,
        entity_type: str,
        name: str,
        code: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> GenericEntityModel:
        if code:
            existing = await self.get_by_type_and_code(entity_type, code)
            if existing:
                existing.name = name
                if attributes:
                    existing.attributes.update(attributes)
                    existing.properties.update(attributes)
                existing.updated_at = datetime.utcnow()
                await self.session.flush()
                return existing
        
        return await self.create_entity(
            entity_type=entity_type,
            name=name,
            code=code,
            attributes=attributes,
        )


class RelationRepository(BaseRepository[GenericRelationModel]):
    """Repository for generic relations."""
    
    model_class = GenericRelationModel
    
    async def get_by_relation_id(self, relation_id: str) -> GenericRelationModel | None:
        result = await self.session.execute(
            select(GenericRelationModel).where(
                GenericRelationModel.relation_id == relation_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_relations_for_entity(
        self,
        entity_id: str,
        relation_type: str | None = None,
        as_source: bool = True,
        as_target: bool = True,
        limit: int = 100,
    ) -> list[GenericRelationModel]:
        conditions = []
        
        if as_source:
            conditions.append(GenericRelationModel.source_entity_id == entity_id)
        if as_target:
            conditions.append(GenericRelationModel.target_entity_id == entity_id)
        
        stmt = select(GenericRelationModel).where(
            and_(
                or_(*conditions),
                GenericRelationModel.is_active == True,
            )
        )
        
        if relation_type:
            stmt = stmt.where(GenericRelationModel.relation_type == relation_type)
        
        stmt = stmt.limit(limit).order_by(GenericRelationModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_relation(
        self,
        relation_type: str,
        source_entity_id: str,
        target_entity_id: str,
        weight: float | None = None,
        confidence: float | None = None,
        evidence: str | None = None,
        properties: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> GenericRelationModel:
        relation_id = f"{relation_type}_{source_entity_id}_{target_entity_id}"
        
        instance = GenericRelationModel(
            relation_id=relation_id,
            relation_type=relation_type,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            weight=weight or 1.0,
            confidence=confidence or 1.0,
            evidence=evidence,
            properties=properties or {},
            attributes=attributes or {},
            source=source,
        )
        
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def delete_relations_for_entity(
        self,
        entity_id: str,
        relation_type: str | None = None,
    ) -> int:
        stmt = select(GenericRelationModel).where(
            or_(
                GenericRelationModel.source_entity_id == entity_id,
                GenericRelationModel.target_entity_id == entity_id,
            )
        )
        
        if relation_type:
            stmt = stmt.where(GenericRelationModel.relation_type == relation_type)
        
        result = await self.session.execute(stmt)
        relations = result.scalars().all()
        
        count = 0
        for relation in relations:
            await self.session.delete(relation)
            count += 1
        
        await self.session.flush()
        return count


class FactorRepository(BaseRepository[GenericFactorModel]):
    """Repository for factor data.
    
    Fully compatible with FactorDataModel in orm.py.
    Uses original field names: factor_id, factor_name, factor_category, code, etc.
    Also supports aliases: factor_type (-> factor_category), symbol (-> code), value (-> factor_value)
    """
    
    model_class = GenericFactorModel
    
    async def get_by_factor_id(self, factor_id: str) -> GenericFactorModel | None:
        result = await self.session.execute(
            select(GenericFactorModel).where(
                GenericFactorModel.factor_id == factor_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_factor_data(
        self,
        factor_id: str | None = None,
        factor_category: str | None = None,
        code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 1000,
    ) -> list[GenericFactorModel]:
        stmt = select(GenericFactorModel)
        
        if factor_id:
            stmt = stmt.where(GenericFactorModel.factor_id == factor_id)
        
        if factor_category:
            stmt = stmt.where(GenericFactorModel.factor_category == factor_category)
        
        if code:
            stmt = stmt.where(GenericFactorModel.code == code)
        
        if start_date:
            stmt = stmt.where(GenericFactorModel.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(GenericFactorModel.trade_date <= end_date)
        
        stmt = stmt.limit(limit).order_by(GenericFactorModel.trade_date.asc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_factor_value(
        self,
        factor_id: str,
        code: str,
    ) -> GenericFactorModel | None:
        result = await self.session.execute(
            select(GenericFactorModel)
            .where(
                and_(
                    GenericFactorModel.factor_id == factor_id,
                    GenericFactorModel.code == code,
                )
            )
            .order_by(GenericFactorModel.trade_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def save_factor_data(
        self,
        factor_id: str,
        code: str,
        trade_date: date,
        factor_value: float,
        factor_name: str | None = None,
        factor_category: str | None = None,
        factor_rank: int | None = None,
        factor_percentile: float | None = None,
        neutralized: bool = False,
        attributes: dict[str, Any] | None = None,
    ) -> GenericFactorModel:
        existing = await self.session.execute(
            select(GenericFactorModel).where(
                and_(
                    GenericFactorModel.factor_id == factor_id,
                    GenericFactorModel.code == code,
                    GenericFactorModel.trade_date == trade_date,
                )
            )
        )
        existing_instance = existing.scalar_one_or_none()
        
        if existing_instance:
            existing_instance.factor_value = factor_value
            existing_instance.factor_name = factor_name or existing_instance.factor_name
            existing_instance.factor_category = factor_category or existing_instance.factor_category
            existing_instance.factor_rank = factor_rank
            existing_instance.factor_percentile = factor_percentile
            existing_instance.neutralized = neutralized
            if attributes:
                existing_instance.attributes.update(attributes)
            existing_instance.collected_at = datetime.utcnow()
            await self.session.flush()
            return existing_instance
        
        instance = GenericFactorModel(
            factor_id=factor_id,
            factor_name=factor_name,
            factor_category=factor_category,
            code=code,
            trade_date=trade_date,
            factor_value=factor_value,
            factor_rank=factor_rank,
            factor_percentile=factor_percentile,
            neutralized=neutralized,
            attributes=attributes or {},
        )
        
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def batch_save_factor_data(
        self,
        factor_data_list: list[dict[str, Any]],
    ) -> int:
        count = 0
        for data in factor_data_list:
            await self.save_factor_data(**data)
            count += 1
        return count
    
    async def delete_factor_data(
        self,
        factor_id: str,
        code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        stmt = select(GenericFactorModel).where(
            GenericFactorModel.factor_id == factor_id
        )
        
        if code:
            stmt = stmt.where(GenericFactorModel.code == code)
        if start_date:
            stmt = stmt.where(GenericFactorModel.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(GenericFactorModel.trade_date <= end_date)
        
        result = await self.session.execute(stmt)
        factors = result.scalars().all()
        
        count = 0
        for factor in factors:
            await self.session.delete(factor)
            count += 1
        
        await self.session.flush()
        return count


class StrategyRepository(BaseRepository[GenericStrategyModel]):
    """Repository for strategy configurations.
    
    Fully compatible with Strategy Pydantic model in models/quant.py.
    All original fields preserved.
    """
    
    model_class = GenericStrategyModel
    
    async def get_by_strategy_id(self, strategy_id: str) -> GenericStrategyModel | None:
        result = await self.session.execute(
            select(GenericStrategyModel).where(
                GenericStrategyModel.strategy_id == strategy_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> GenericStrategyModel | None:
        result = await self.session.execute(
            select(GenericStrategyModel).where(
                GenericStrategyModel.code == code
            )
        )
        return result.scalar_one_or_none()
    
    async def list_by_type(
        self,
        strategy_type: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[GenericStrategyModel]:
        stmt = select(GenericStrategyModel).where(
            GenericStrategyModel.strategy_type == strategy_type
        )
        
        if status:
            stmt = stmt.where(GenericStrategyModel.status == status)
        
        stmt = stmt.limit(limit).order_by(GenericStrategyModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def list_strategies(
        self,
        strategy_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenericStrategyModel]:
        stmt = select(GenericStrategyModel)
        
        if strategy_type:
            stmt = stmt.where(GenericStrategyModel.strategy_type == strategy_type)
        
        if status:
            stmt = stmt.where(GenericStrategyModel.status == status)
        
        if search:
            stmt = stmt.where(
                or_(
                    GenericStrategyModel.name.ilike(f"%{search}%"),
                    GenericStrategyModel.code.ilike(f"%{search}%"),
                )
            )
        
        stmt = stmt.offset(offset).limit(limit).order_by(
            GenericStrategyModel.updated_at.desc()
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_strategy(
        self,
        name: str,
        code: str,
        strategy_type: str,
        description: str | None = None,
        factors: list[str] | None = None,
        factor_weights: dict[str, float] | None = None,
        weight_method: str = "equal",
        parameters: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        rebalance_freq: str = "monthly",
        max_positions: int = 50,
        position_size: float = 0.02,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        status: str = "draft",
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GenericStrategyModel:
        strategy_id = f"strat_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{code}"
        
        instance = GenericStrategyModel(
            strategy_id=strategy_id,
            code=code,
            name=name,
            description=description,
            strategy_type=strategy_type,
            factors=factors or [],
            factor_weights=factor_weights or {},
            weight_method=weight_method,
            parameters=parameters or {},
            config=config or {},
            rebalance_freq=rebalance_freq,
            max_positions=max_positions,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=status,
            created_by=created_by,
            attributes=metadata or {},
        )
        
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def update_strategy(
        self,
        strategy_id: str,
        **kwargs,
    ) -> GenericStrategyModel | None:
        instance = await self.get_by_strategy_id(strategy_id)
        if instance is None:
            return None
        
        if "metadata" in kwargs:
            kwargs["attributes"] = kwargs.pop("metadata")
        
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        instance.updated_at = datetime.utcnow()
        await self.session.flush()
        return instance
    
    async def update_status(
        self,
        strategy_id: str,
        status: str,
    ) -> GenericStrategyModel | None:
        return await self.update_strategy(strategy_id, status=status)
    
    async def delete_strategy(self, strategy_id: str) -> bool:
        instance = await self.get_by_strategy_id(strategy_id)
        if instance is None:
            return False
        
        await self.session.delete(instance)
        await self.session.flush()
        return True
