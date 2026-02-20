"""
Entity Engine - Metadata-driven entity management.

Provides high-level operations for creating, updating, and querying entities
with automatic validation based on metadata definitions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..metadata.registry import EntityTypeRegistry, EntityTypeDefinition
from ..metadata.base import ValidationResult
from ..storage.repository import EntityRepository
from ..storage.generic_model import GenericEntityModel

logger = logging.getLogger(__name__)


@dataclass
class EntityCreateResult:
    """Result of entity creation."""
    success: bool
    entity: GenericEntityModel | None = None
    validation: ValidationResult | None = None
    error: str | None = None


@dataclass
class EntitySearchResult:
    """Result of entity search."""
    entities: list[GenericEntityModel]
    total: int
    page: int
    page_size: int


class EntityEngine:
    """
    Entity Engine - Metadata-driven entity management.
    
    Provides:
    - Create/update with automatic validation
    - Search with type-aware filtering
    - Type definition lookup
    - Quality rule checking
    """
    
    def __init__(
        self,
        session: AsyncSession,
        registry: EntityTypeRegistry | None = None,
    ):
        self.session = session
        self.registry = registry or EntityTypeRegistry()
        self.repository = EntityRepository(session)
    
    async def create(
        self,
        entity_type: str,
        data: dict[str, Any],
        validate: bool = True,
        upsert: bool = True,
    ) -> EntityCreateResult:
        """
        Create a new entity with validation.
        
        Args:
            entity_type: Entity type ID
            data: Entity data
            validate: Whether to validate against type definition
            upsert: Whether to update if entity already exists
        
        Returns:
            EntityCreateResult with entity or error
        """
        definition = self.registry.get(entity_type)
        if definition is None:
            return EntityCreateResult(
                success=False,
                error=f"Unknown entity type: {entity_type}",
            )
        
        if validate:
            validation = definition.validate_data(data, self.registry)
            if not validation.valid:
                return EntityCreateResult(
                    success=False,
                    validation=validation,
                    error=f"Validation failed: {validation.errors}",
                )
        
        name = data.get("name", "")
        code = data.get("code")
        
        core_fields = {"name", "code", "entity_type"}
        attributes = {k: v for k, v in data.items() if k not in core_fields}
        
        try:
            if upsert:
                entity = await self.repository.upsert_entity(
                    entity_type=entity_type,
                    name=name,
                    code=code,
                    attributes=attributes,
                    source=data.get("_source"),
                    confidence=data.get("_confidence"),
                )
            else:
                entity = await self.repository.create_entity(
                    entity_type=entity_type,
                    name=name,
                    code=code,
                    attributes=attributes,
                    source=data.get("_source"),
                    confidence=data.get("_confidence"),
                )
            
            return EntityCreateResult(
                success=True,
                entity=entity,
                validation=validation if validate else None,
            )
        except Exception as e:
            logger.error(f"Failed to create entity: {e}")
            return EntityCreateResult(
                success=False,
                error=str(e),
            )
    
    async def get(self, entity_id: str) -> GenericEntityModel | None:
        """Get entity by entity_id."""
        return await self.repository.get_by_entity_id(entity_id)
    
    async def get_by_code(
        self, 
        entity_type: str, 
        code: str
    ) -> GenericEntityModel | None:
        """Get entity by type and code."""
        return await self.repository.get_by_type_and_code(entity_type, code)
    
    async def update(
        self,
        entity_id: str,
        data: dict[str, Any],
        validate: bool = True,
    ) -> EntityCreateResult:
        """Update an existing entity."""
        entity = await self.get(entity_id)
        if entity is None:
            return EntityCreateResult(
                success=False,
                error=f"Entity not found: {entity_id}",
            )
        
        definition = self.registry.get(entity.entity_type)
        
        if validate and definition:
            validation = definition.validate_data(data, self.registry)
            if not validation.valid:
                return EntityCreateResult(
                    success=False,
                    validation=validation,
                    error=f"Validation failed: {validation.errors}",
                )
        
        core_fields = {"name", "code", "entity_type"}
        update_data = {}
        
        if "name" in data:
            update_data["name"] = data["name"]
        if "code" in data:
            update_data["code"] = data["code"]
        
        attributes = {k: v for k, v in data.items() if k not in core_fields}
        if attributes:
            entity.attributes.update(attributes)
        
        if update_data:
            for key, value in update_data.items():
                setattr(entity, key, value)
        
        entity.updated_at = datetime.utcnow()
        await self.session.flush()
        
        return EntityCreateResult(
            success=True,
            entity=entity,
        )
    
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity (soft delete by setting is_active=False)."""
        entity = await self.get(entity_id)
        if entity is None:
            return False
        
        entity.is_active = False
        entity.updated_at = datetime.utcnow()
        await self.session.flush()
        return True
    
    async def search(
        self,
        entity_type: str | None = None,
        query: str | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> EntitySearchResult:
        """
        Search entities with pagination.
        
        Args:
            entity_type: Filter by entity type
            query: Search query for name/code
            filters: Additional attribute filters
            page: Page number (1-based)
            page_size: Items per page
        
        Returns:
            EntitySearchResult with entities and pagination info
        """
        offset = (page - 1) * page_size
        
        entities = await self.repository.search(
            entity_type=entity_type,
            query=query,
            filters=filters,
            limit=page_size,
            offset=offset,
        )
        
        total = await self.repository.count(
            entity_type=entity_type,
            query=query,
        )
        
        return EntitySearchResult(
            entities=entities,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    def get_type_definition(self, entity_type: str) -> EntityTypeDefinition | None:
        """Get the type definition for an entity type."""
        return self.registry.get(entity_type)
    
    def list_types(self) -> list[EntityTypeDefinition]:
        """List all registered entity types."""
        return self.registry.list_all()
    
    def validate(
        self,
        entity_type: str,
        data: dict[str, Any],
    ) -> ValidationResult:
        """Validate data against entity type definition."""
        definition = self.registry.get(entity_type)
        if definition is None:
            return ValidationResult(
                valid=False,
                errors=[f"Unknown entity type: {entity_type}"],
            )
        
        return definition.validate_data(data, self.registry)
    
    async def check_quality(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """
        Check entity against quality rules.
        
        Returns list of quality issues found.
        """
        entity = await self.get(entity_id)
        if entity is None:
            return [{"error": "Entity not found"}]
        
        definition = self.registry.get(entity.entity_type)
        if definition is None or not definition.quality_rules:
            return []
        
        issues = []
        data = entity.to_dict()
        
        for rule in definition.quality_rules:
            try:
                condition_met = eval(rule.condition, {"__builtins__": {}}, data)
                if not condition_met:
                    issues.append({
                        "rule": rule.name,
                        "severity": rule.severity.value,
                        "message": rule.message,
                    })
            except Exception as e:
                logger.warning(f"Failed to evaluate quality rule {rule.name}: {e}")
        
        return issues
