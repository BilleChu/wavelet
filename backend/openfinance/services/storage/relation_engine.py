"""
Relation Engine - Metadata-driven relation management.

Provides high-level operations for creating and querying relations
between entities with type-aware validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.domain.metadata.registry import RelationTypeRegistry, RelationTypeDefinition
from openfinance.domain.metadata.base import ValidationResult
from .repository import RelationRepository, EntityRepository
from openfinance.domain.schemas.generic_model import GenericRelationModel

logger = logging.getLogger(__name__)


@dataclass
class RelationCreateResult:
    """Result of relation creation."""
    success: bool
    relation: GenericRelationModel | None = None
    error: str | None = None


class RelationEngine:
    """
    Relation Engine - Metadata-driven relation management.
    
    Provides:
    - Create relations with type validation
    - Query relations by entity
    - Validate source/target type compatibility
    """
    
    def __init__(
        self,
        session: AsyncSession,
        registry: RelationTypeRegistry | None = None,
    ):
        self.session = session
        self.registry = registry or RelationTypeRegistry()
        self.repository = RelationRepository(session)
        self.entity_repository = EntityRepository(session)
    
    async def create(
        self,
        relation_type: str,
        source_entity_id: str,
        target_entity_id: str,
        attributes: dict[str, Any] | None = None,
        validate_types: bool = True,
    ) -> RelationCreateResult:
        """
        Create a new relation.
        
        Args:
            relation_type: Relation type ID
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            attributes: Relation attributes
            validate_types: Whether to validate source/target types
        
        Returns:
            RelationCreateResult
        """
        definition = self.registry.get(relation_type)
        if definition is None:
            return RelationCreateResult(
                success=False,
                error=f"Unknown relation type: {relation_type}",
            )
        
        if validate_types:
            source_entity = await self.entity_repository.get_by_entity_id(source_entity_id)
            target_entity = await self.entity_repository.get_by_entity_id(target_entity_id)
            
            if source_entity is None:
                return RelationCreateResult(
                    success=False,
                    error=f"Source entity not found: {source_entity_id}",
                )
            
            if target_entity is None:
                return RelationCreateResult(
                    success=False,
                    error=f"Target entity not found: {target_entity_id}",
                )
            
            if not definition.is_valid_for(source_entity.entity_type, target_entity.entity_type):
                return RelationCreateResult(
                    success=False,
                    error=f"Relation {relation_type} not valid between {source_entity.entity_type} and {target_entity.entity_type}",
                )
        
        try:
            relation = await self.repository.create_relation(
                relation_type=relation_type,
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                attributes=attributes,
            )
            
            return RelationCreateResult(
                success=True,
                relation=relation,
            )
        except Exception as e:
            logger.error(f"Failed to create relation: {e}")
            return RelationCreateResult(
                success=False,
                error=str(e),
            )
    
    async def get(self, relation_id: str) -> GenericRelationModel | None:
        """Get relation by ID."""
        return await self.repository.get_by_relation_id(relation_id)
    
    async def get_relations_for_entity(
        self,
        entity_id: str,
        relation_type: str | None = None,
        as_source: bool = True,
        as_target: bool = True,
        limit: int = 100,
    ) -> list[GenericRelationModel]:
        """
        Get all relations for an entity.
        
        Args:
            entity_id: Entity ID
            relation_type: Filter by relation type
            as_source: Include relations where entity is source
            as_target: Include relations where entity is target
            limit: Maximum number of relations
        
        Returns:
            List of relations
        """
        return await self.repository.get_relations_for_entity(
            entity_id=entity_id,
            relation_type=relation_type,
            as_source=as_source,
            as_target=as_target,
            limit=limit,
        )
    
    async def get_related_entities(
        self,
        entity_id: str,
        relation_type: str | None = None,
        direction: str = "both",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get entities related to the given entity.
        
        Args:
            entity_id: Entity ID
            relation_type: Filter by relation type
            direction: "outgoing", "incoming", or "both"
            limit: Maximum number of results
        
        Returns:
            List of related entities with relation info
        """
        as_source = direction in ("outgoing", "both")
        as_target = direction in ("incoming", "both")
        
        relations = await self.get_relations_for_entity(
            entity_id=entity_id,
            relation_type=relation_type,
            as_source=as_source,
            as_target=as_target,
            limit=limit,
        )
        
        results = []
        for rel in relations:
            related_id = (
                rel.target_entity_id 
                if rel.source_entity_id == entity_id 
                else rel.source_entity_id
            )
            
            related_entity = await self.entity_repository.get_by_entity_id(related_id)
            if related_entity:
                results.append({
                    "relation_id": rel.relation_id,
                    "relation_type": rel.relation_type,
                    "entity": related_entity.to_dict(),
                    "direction": "outgoing" if rel.source_entity_id == entity_id else "incoming",
                    "attributes": rel.attributes,
                })
        
        return results
    
    async def delete(self, relation_id: str) -> bool:
        """Delete a relation."""
        return await self.repository.delete(relation_id)
    
    async def delete_for_entity(
        self,
        entity_id: str,
        relation_type: str | None = None,
    ) -> int:
        """Delete all relations for an entity."""
        return await self.repository.delete_relations_for_entity(
            entity_id=entity_id,
            relation_type=relation_type,
        )
    
    def get_type_definition(self, relation_type: str) -> RelationTypeDefinition | None:
        """Get the type definition for a relation type."""
        return self.registry.get(relation_type)
    
    def list_types(self) -> list[RelationTypeDefinition]:
        """List all registered relation types."""
        return self.registry.list_all()
    
    def get_valid_relation_types(
        self,
        source_type: str,
        target_type: str,
    ) -> list[RelationTypeDefinition]:
        """Get valid relation types between two entity types."""
        return self.registry.get_valid_relations(source_type, target_type)
