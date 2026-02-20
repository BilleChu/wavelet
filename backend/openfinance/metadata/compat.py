"""
Compatibility layer for legacy code.

Provides adapters and constants that maintain backward compatibility
with the old hardcoded approach while using the new metadata-driven architecture.
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..metadata import EntityTypeRegistry, RelationTypeRegistry
from ..metadata.registry import EntityTypeDefinition, RelationTypeDefinition
from ..engine import EntityEngine, RelationEngine


VALID_ENTITY_TYPES = [
    "company", "industry", "concept", "person", "stock",
    "fund", "event", "sector", "index", "investor",
]

VALID_RELATION_TYPES = [
    "belongs_to", "has_concept", "competes_with", "supplies_to",
    "invests_in", "affects", "works_for", "manages", "owns",
    "parent_of", "subsidiary_of", "ceo_of", "director_of",
    "founded", "acquired", "merged_with", "operates_in",
    "regulated_by", "related_to", "listed_on",
]

ENTITY_TYPE_LABELS = {
    "company": "公司",
    "stock": "股票",
    "industry": "行业",
    "concept": "概念",
    "person": "人物",
    "event": "事件",
    "fund": "基金",
    "index": "指数",
    "investor": "投资者",
    "sector": "板块",
}

RELATION_TYPE_LABELS = {
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


def get_entity_type_label(entity_type: str) -> str:
    """Get display label for entity type."""
    definition = EntityTypeRegistry.get(entity_type)
    if definition:
        return definition.display_name
    return ENTITY_TYPE_LABELS.get(entity_type, entity_type)


def get_relation_type_label(relation_type: str) -> str:
    """Get display label for relation type."""
    definition = RelationTypeRegistry.get(relation_type)
    if definition:
        return definition.display_name
    return RELATION_TYPE_LABELS.get(relation_type, relation_type)


def is_valid_entity_type(entity_type: str) -> bool:
    """Check if entity type is valid."""
    return EntityTypeRegistry.exists(entity_type) or entity_type in VALID_ENTITY_TYPES


def is_valid_relation_type(relation_type: str) -> bool:
    """Check if relation type is valid."""
    return RelationTypeRegistry.exists(relation_type) or relation_type in VALID_RELATION_TYPES


class LegacyEntityAdapter:
    """
    Adapter for legacy entity operations.
    
    Provides the same interface as the old EntityModel operations
    but uses the new EntityEngine internally.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine = EntityEngine(session)
    
    async def get_entity(self, entity_id: str) -> dict | None:
        """Get entity by ID (legacy interface)."""
        entity = await self.engine.get(entity_id)
        return entity.to_dict() if entity else None
    
    async def get_entity_by_code(
        self,
        entity_type: str,
        code: str,
    ) -> dict | None:
        """Get entity by type and code (legacy interface)."""
        entity = await self.engine.get_by_code(entity_type, code)
        return entity.to_dict() if entity else None
    
    async def create_entity(
        self,
        entity_type: str,
        name: str,
        code: str | None = None,
        **kwargs
    ) -> dict:
        """Create entity (legacy interface)."""
        data = {"name": name, "code": code, **kwargs}
        result = await self.engine.create(entity_type, data, validate=False)
        
        if not result.success:
            raise ValueError(result.error)
        
        await self.session.commit()
        return result.entity.to_dict()
    
    async def update_entity(
        self,
        entity_id: str,
        **kwargs
    ) -> dict | None:
        """Update entity (legacy interface)."""
        result = await self.engine.update(entity_id, kwargs, validate=False)
        
        if not result.success:
            return None
        
        await self.session.commit()
        return result.entity.to_dict()
    
    async def search_entities(
        self,
        entity_type: str,
        keyword: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Search entities (legacy interface)."""
        page = (offset // limit) + 1
        result = await self.engine.search(
            entity_type=entity_type,
            query=keyword,
            page=page,
            page_size=limit,
        )
        return [e.to_dict() for e in result.entities]
    
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity (legacy interface)."""
        deleted = await self.engine.delete(entity_id)
        if deleted:
            await self.session.commit()
        return deleted


class LegacyRelationAdapter:
    """
    Adapter for legacy relation operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine = RelationEngine(session)
    
    async def create_relation(
        self,
        relation_type: str,
        source_id: str,
        target_id: str,
        **kwargs
    ) -> dict:
        """Create relation (legacy interface)."""
        result = await self.engine.create(
            relation_type=relation_type,
            source_entity_id=source_id,
            target_entity_id=target_id,
            attributes=kwargs if kwargs else None,
            validate_types=False,
        )
        
        if not result.success:
            raise ValueError(result.error)
        
        await self.session.commit()
        return result.relation.to_dict()
    
    async def get_relations(
        self,
        entity_id: str,
        relation_type: str | None = None,
    ) -> list[dict]:
        """Get relations for entity (legacy interface)."""
        relations = await self.engine.get_relations_for_entity(
            entity_id=entity_id,
            relation_type=relation_type,
        )
        return [r.to_dict() for r in relations]
    
    async def delete_relations(
        self,
        entity_id: str,
        relation_type: str | None = None,
    ) -> int:
        """Delete relations (legacy interface)."""
        count = await self.engine.delete_for_entity(
            entity_id=entity_id,
            relation_type=relation_type,
        )
        await self.session.commit()
        return count
