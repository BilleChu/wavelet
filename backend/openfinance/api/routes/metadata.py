"""
Metadata API Routes.

Provides REST API endpoints for metadata-driven operations.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.domain.metadata import (
    EntityTypeRegistry,
    RelationTypeRegistry,
    FactorTypeRegistry,
    StrategyTypeRegistry,
    ToolTypeRegistry,
    DataSourceRegistry,
    initialize_registries,
)
from openfinance.services.storage import EntityEngine, RelationEngine, FactorEngine, StrategyEngine
from openfinance.domain.schemas.generic_model import GenericEntityModel
from openfinance.infrastructure.database import get_db

router = APIRouter(prefix="/metadata", tags=["Metadata"])


class EntityCreateRequest(BaseModel):
    """Request for creating an entity."""
    entity_type: str = Field(..., description="Entity type ID")
    name: str = Field(..., description="Entity name")
    code: Optional[str] = Field(None, description="Entity code")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Entity attributes")


class EntitySearchRequest(BaseModel):
    """Request for searching entities."""
    entity_type: Optional[str] = None
    query: Optional[str] = None
    filters: Optional[dict[str, Any]] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class RelationCreateRequest(BaseModel):
    """Request for creating a relation."""
    relation_type: str
    source_entity_id: str
    target_entity_id: str
    attributes: Optional[dict[str, Any]] = None


# ============ Type Definition Endpoints ============

@router.get("/entity-types")
async def list_entity_types() -> dict:
    """List all entity type definitions."""
    types = EntityTypeRegistry.list_all()
    return {
        "types": [
            {
                "type_id": t.type_id,
                "display_name": t.display_name,
                "category": t.category.value,
                "description": t.description,
                "properties": list(t.properties.keys()),
            }
            for t in types
        ]
    }


@router.get("/entity-types/{type_id}")
async def get_entity_type(type_id: str) -> dict:
    """Get entity type definition."""
    definition = EntityTypeRegistry.get(type_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Entity type not found: {type_id}")
    
    return definition.to_dict()


@router.get("/relation-types")
async def list_relation_types() -> dict:
    """List all relation type definitions."""
    types = RelationTypeRegistry.list_all()
    return {
        "types": [
            {
                "type_id": t.type_id,
                "display_name": t.display_name,
                "source_types": t.source_types,
                "target_types": t.target_types,
            }
            for t in types
        ]
    }


@router.get("/relation-types/{type_id}")
async def get_relation_type(type_id: str) -> dict:
    """Get relation type definition."""
    definition = RelationTypeRegistry.get(type_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Relation type not found: {type_id}")
    
    return definition.to_dict()


@router.get("/factor-types")
async def list_factor_types() -> dict:
    """List all factor type definitions."""
    types = FactorTypeRegistry.list_all()
    return {
        "types": [
            {
                "type_id": t.type_id,
                "display_name": t.display_name,
                "factor_category": t.factor_category,
                "dependencies": t.dependencies,
            }
            for t in types
        ]
    }


@router.get("/strategy-types")
async def list_strategy_types() -> dict:
    """List all strategy type definitions."""
    types = StrategyTypeRegistry.list_all()
    return {
        "types": [
            {
                "type_id": t.type_id,
                "display_name": t.display_name,
                "strategy_category": t.strategy_category,
            }
            for t in types
        ]
    }


@router.get("/tool-types")
async def list_tool_types() -> dict:
    """List all tool type definitions."""
    types = ToolTypeRegistry.list_all()
    return {
        "types": [
            {
                "type_id": t.type_id,
                "display_name": t.display_name,
                "tool_category": t.tool_category,
            }
            for t in types
        ]
    }


@router.get("/tools/openai-schema")
async def get_openai_tools_schema() -> list[dict]:
    """Get OpenAI function calling schema for all tools."""
    return ToolTypeRegistry.get_openai_tools_schema()


@router.get("/data-sources")
async def list_data_sources() -> dict:
    """List all data source definitions."""
    sources = DataSourceRegistry.list_all()
    return {
        "sources": [
            {
                "type_id": s.type_id,
                "display_name": s.display_name,
                "source_type": s.source_type,
                "data_types": s.data_types,
            }
            for s in sources
        ]
    }


# ============ Entity CRUD Endpoints ============

@router.post("/entities")
async def create_entity(
    request: EntityCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new entity."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = EntityEngine(db)
    data = {"name": request.name, "code": request.code, **request.attributes}
    result = await engine.create(request.entity_type, data)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    await db.commit()
    return result.entity.to_dict()


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get entity by ID."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = EntityEngine(db)
    entity = await engine.get(entity_id)
    
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return entity.to_dict()


@router.get("/entities")
async def search_entities(
    entity_type: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search entities."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = EntityEngine(db)
    result = await engine.search(
        entity_type=entity_type,
        query=query,
        page=page,
        page_size=page_size,
    )
    
    return {
        "entities": [e.to_dict() for e in result.entities],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.patch("/entities/{entity_id}")
async def update_entity(
    entity_id: str,
    attributes: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update entity attributes."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = EntityEngine(db)
    result = await engine.update(entity_id, attributes)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    await db.commit()
    return result.entity.to_dict()


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete entity (soft delete)."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = EntityEngine(db)
    deleted = await engine.delete(entity_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    await db.commit()
    return {"deleted": True}


# ============ Relation Endpoints ============

@router.post("/relations")
async def create_relation(
    request: RelationCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new relation."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = RelationEngine(db)
    result = await engine.create(
        relation_type=request.relation_type,
        source_entity_id=request.source_entity_id,
        target_entity_id=request.target_entity_id,
        attributes=request.attributes,
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    await db.commit()
    return result.relation.to_dict()


@router.get("/entities/{entity_id}/relations")
async def get_entity_relations(
    entity_id: str,
    relation_type: Optional[str] = Query(None),
    direction: str = Query("both"),
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get relations for an entity."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    engine = RelationEngine(db)
    relations = await engine.get_related_entities(
        entity_id=entity_id,
        relation_type=relation_type,
        direction=direction,
        limit=limit,
    )
    
    return relations


# ============ Admin Endpoints ============

@router.post("/reload")
async def reload_metadata() -> dict:
    """Reload all metadata from configuration files."""
    try:
        EntityTypeRegistry.clear()
        RelationTypeRegistry.clear()
        FactorTypeRegistry.clear()
        StrategyTypeRegistry.clear()
        ToolTypeRegistry.clear()
        DataSourceRegistry.clear()
        
        initialize_registries()
        
        return {
            "success": True,
            "counts": {
                "entity_types": len(EntityTypeRegistry.list_all()),
                "relation_types": len(RelationTypeRegistry.list_all()),
                "factor_types": len(FactorTypeRegistry.list_all()),
                "strategy_types": len(StrategyTypeRegistry.list_all()),
                "tool_types": len(ToolTypeRegistry.list_all()),
                "data_sources": len(DataSourceRegistry.list_all()),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_metadata_stats() -> dict:
    """Get metadata statistics."""
    return {
        "entity_types": len(EntityTypeRegistry.list_all()),
        "relation_types": len(RelationTypeRegistry.list_all()),
        "factor_types": len(FactorTypeRegistry.list_all()),
        "strategy_types": len(StrategyTypeRegistry.list_all()),
        "tool_types": len(ToolTypeRegistry.list_all()),
        "data_sources": len(DataSourceRegistry.list_all()),
    }
