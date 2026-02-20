"""
Knowledge Graph API Routes for OpenFinance.

Provides graph visualization, traversal, and management endpoints.
Uses database as single source of truth for data consistency.
"""

import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, and_, distinct, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from openfinance.infrastructure.database import get_db
from openfinance.datacenter.models import (
    EntityModel,
    RelationModel,
    StockBasicModel,
)
from openfinance.domain.metadata.compat import (
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
    ENTITY_TYPE_LABELS,
    RELATION_TYPE_LABELS,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class GraphNode(BaseModel):
    id: str
    name: str
    type: str
    properties: dict[str, Any] = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    weight: float = 1.0
    properties: dict[str, Any] = {}


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    total_edges: int


class EntityCreateRequest(BaseModel):
    entity_type: str
    name: str
    code: Optional[str] = None
    aliases: list[str] = []
    description: Optional[str] = None
    industry: Optional[str] = None
    properties: dict[str, Any] = {}
    confidence: float = 1.0


class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    aliases: Optional[list[str]] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    properties: Optional[dict[str, Any]] = None
    reason: Optional[str] = None


class RelationCreateRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relation_type: str
    weight: float = 1.0
    confidence: float = 1.0
    evidence: Optional[str] = None
    properties: dict[str, Any] = {}


class DataQualityReport(BaseModel):
    total_entities: int
    total_relations: int
    entity_type_distribution: dict[str, int]
    relation_type_distribution: dict[str, int]
    isolated_entities: int
    entities_without_industry: int
    entities_without_code: int
    stock_entities_without_basic: int
    dangling_relations: int
    consistency_score: float
    issues: list[dict[str, Any]]


def entity_to_dict(e: EntityModel) -> dict[str, Any]:
    return {
        "id": e.entity_id,
        "name": e.name,
        "type": e.entity_type,
        "code": e.code,
        "industry": e.industry,
        "description": e.description,
        "aliases": e.aliases or [],
        "properties": e.properties or {},
        "confidence": float(e.confidence) if e.confidence else 1.0,
        "source": e.source,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


def entity_to_node(e: EntityModel) -> GraphNode:
    return GraphNode(
        id=e.entity_id,
        name=e.name,
        type=e.entity_type,
        properties={
            "code": e.code,
            "industry": e.industry,
            "description": e.description,
            **(e.properties or {}),
        },
    )


def relation_to_edge(r: RelationModel) -> GraphEdge:
    return GraphEdge(
        id=r.relation_id,
        source=r.source_entity_id,
        target=r.target_entity_id,
        type=r.relation_type,
        weight=float(r.weight) if r.weight else 1.0,
        properties={
            "evidence": r.evidence,
            "confidence": float(r.confidence) if r.confidence else 1.0,
            **(r.properties or {}),
        },
    )


@router.get("/graph/default", response_model=GraphData)
async def get_default_graph(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> GraphData:
    if db is None:
        logger.warning("Database not available, returning empty graph")
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)
    
    try:
        query = (
            select(EntityModel)
            .options(selectinload(EntityModel.outgoing_relations))
            .limit(limit)
        )
        result = await db.execute(query)
        entities = result.scalars().all()
        
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        
        for entity in entities:
            nodes[entity.entity_id] = entity_to_node(entity)
            
            for rel in entity.outgoing_relations:
                edges[rel.relation_id] = relation_to_edge(rel)
                
                if rel.target_entity_id not in nodes:
                    target_query = select(EntityModel).where(
                        EntityModel.entity_id == rel.target_entity_id
                    )
                    target_result = await db.execute(target_query)
                    target = target_result.scalar_one_or_none()
                    if target:
                        nodes[target.entity_id] = entity_to_node(target)
        
        return GraphData(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            total_nodes=len(nodes),
            total_edges=len(edges),
        )
    except Exception as e:
        logger.warning(f"Database error in get_default_graph: {e}")
        return GraphData(nodes=[], edges=[], total_nodes=0, total_edges=0)


@router.get("/graph/entity/{entity_id}", response_model=GraphData)
async def get_entity_graph(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3),
    db: AsyncSession = Depends(get_db),
) -> GraphData:
    center_query = select(EntityModel).where(EntityModel.entity_id == entity_id)
    center_result = await db.execute(center_query)
    center = center_result.scalar_one_or_none()
    
    if not center:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    
    nodes: dict[str, GraphNode] = {center.entity_id: entity_to_node(center)}
    edges: dict[str, GraphEdge] = {}
    
    current_level = [center.entity_id]
    visited = {center.entity_id}
    
    for _ in range(depth):
        next_level = []
        
        for eid in current_level:
            rel_query = (
                select(RelationModel)
                .where(
                    or_(
                        RelationModel.source_entity_id == eid,
                        RelationModel.target_entity_id == eid,
                    )
                )
            )
            rel_result = await db.execute(rel_query)
            relations = rel_result.scalars().all()
            
            for rel in relations:
                edges[rel.relation_id] = relation_to_edge(rel)
                
                neighbor_id = (
                    rel.target_entity_id 
                    if rel.source_entity_id == eid 
                    else rel.source_entity_id
                )
                
                if neighbor_id not in visited:
                    neighbor_query = select(EntityModel).where(
                        EntityModel.entity_id == neighbor_id
                    )
                    neighbor_result = await db.execute(neighbor_query)
                    neighbor = neighbor_result.scalar_one_or_none()
                    
                    if neighbor:
                        nodes[neighbor.entity_id] = entity_to_node(neighbor)
                        visited.add(neighbor.entity_id)
                        next_level.append(neighbor.entity_id)
        
        current_level = next_level
        if not current_level:
            break
    
    return GraphData(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


@router.get("/graph/search", response_model=GraphData)
async def search_graph(
    keyword: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> GraphData:
    search_term = f"%{keyword}%"
    query = select(EntityModel).where(
        or_(
            EntityModel.name.ilike(search_term),
            EntityModel.code.ilike(search_term),
            EntityModel.description.ilike(search_term),
        )
    ).limit(limit)
    
    result = await db.execute(query)
    entities = result.scalars().all()
    
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    
    for entity in entities:
        nodes[entity.entity_id] = entity_to_node(entity)
        
        rel_query = select(RelationModel).where(
            or_(
                RelationModel.source_entity_id == entity.entity_id,
                RelationModel.target_entity_id == entity.entity_id,
            )
        )
        rel_result = await db.execute(rel_query)
        relations = rel_result.scalars().all()
        
        for rel in relations:
            edges[rel.relation_id] = relation_to_edge(rel)
            
            neighbor_id = (
                rel.target_entity_id 
                if rel.source_entity_id == entity.entity_id 
                else rel.source_entity_id
            )
            
            if neighbor_id not in nodes:
                neighbor_query = select(EntityModel).where(
                    EntityModel.entity_id == neighbor_id
                )
                neighbor_result = await db.execute(neighbor_query)
                neighbor = neighbor_result.scalar_one_or_none()
                if neighbor:
                    nodes[neighbor.entity_id] = entity_to_node(neighbor)
    
    return GraphData(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        total_nodes=len(nodes),
        total_edges=len(edges),
    )


@router.get("/graph/path")
async def find_path(
    start_id: str = Query(...),
    end_id: str = Query(...),
    max_depth: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    for eid, label in [(start_id, "Start"), (end_id, "End")]:
        query = select(EntityModel).where(EntityModel.entity_id == eid)
        result = await db.execute(query)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"{label} entity not found: {eid}")
    
    queue = deque([(start_id, [start_id])])
    visited = {start_id}
    
    while queue:
        current_id, path = queue.popleft()
        
        if current_id == end_id:
            path_entities = []
            for eid in path:
                query = select(EntityModel).where(EntityModel.entity_id == eid)
                result = await db.execute(query)
                entity = result.scalar_one_or_none()
                if entity:
                    path_entities.append({
                        "id": entity.entity_id,
                        "name": entity.name,
                        "type": entity.entity_type,
                    })
            
            return {
                "found": True,
                "path": path_entities,
                "length": len(path) - 1,
            }
        
        if len(path) > max_depth:
            continue
        
        rel_query = select(RelationModel).where(
            or_(
                RelationModel.source_entity_id == current_id,
                RelationModel.target_entity_id == current_id,
            )
        )
        rel_result = await db.execute(rel_query)
        relations = rel_result.scalars().all()
        
        for rel in relations:
            neighbor_id = (
                rel.target_entity_id 
                if rel.source_entity_id == current_id 
                else rel.source_entity_id
            )
            
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                queue.append((neighbor_id, path + [neighbor_id]))
    
    return {
        "found": False,
        "path": [],
        "length": 0,
        "message": f"No path found within {max_depth} hops",
    }


@router.get("/stats")
async def get_graph_stats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if db is None:
        logger.warning("Database not available, returning empty stats")
        return {
            "total_entities": 0,
            "total_relations": 0,
            "entity_types": {},
            "relation_types": {},
        }
    
    try:
        entity_count_query = select(func.count(EntityModel.id))
        entity_count = await db.scalar(entity_count_query) or 0
        
        relation_count_query = select(func.count(RelationModel.id))
        relation_count = await db.scalar(relation_count_query) or 0
        
        entity_type_query = (
            select(EntityModel.entity_type, func.count(EntityModel.id))
            .group_by(EntityModel.entity_type)
        )
        entity_type_result = await db.execute(entity_type_query)
        entity_types = {row[0]: row[1] for row in entity_type_result.all()}
        
        relation_type_query = (
            select(RelationModel.relation_type, func.count(RelationModel.id))
            .group_by(RelationModel.relation_type)
        )
        relation_type_result = await db.execute(relation_type_query)
        relation_types = {row[0]: row[1] for row in relation_type_result.all()}
        
        return {
            "total_entities": entity_count,
            "total_relations": relation_count,
            "entity_types": entity_types,
            "relation_types": relation_types,
        }
    except Exception as e:
        logger.warning(f"Database error in get_graph_stats: {e}")
        return {
            "total_entities": 0,
            "total_relations": 0,
            "entity_types": {},
            "relation_types": {},
        }


@router.get("/entities")
async def list_entities(
    entity_type: Optional[str] = None,
    keyword: Optional[str] = None,
    industry: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if db is None:
        logger.warning("Database not available, returning empty entities")
        return {"entities": [], "total": 0, "page": 1, "page_size": limit, "has_more": False}
    
    try:
        query = select(EntityModel)
        
        if entity_type:
            query = query.where(EntityModel.entity_type == entity_type)
        
        if keyword:
            search_term = f"%{keyword}%"
            query = query.where(
                or_(
                    EntityModel.name.ilike(search_term),
                    EntityModel.code.ilike(search_term),
                )
            )
        
        if industry:
            query = query.where(EntityModel.industry == industry)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0
        
        query = query.offset(offset).limit(limit).order_by(EntityModel.created_at.desc())
        result = await db.execute(query)
        entities = result.scalars().all()
        
        return {
            "entities": [entity_to_dict(e) for e in entities],
            "total": total,
            "page": (offset // limit) + 1,
            "page_size": limit,
            "has_more": offset + limit < total,
        }
    except Exception as e:
        logger.warning(f"Database error in list_entities: {e}")
        return {"entities": [], "total": 0, "page": 1, "page_size": limit, "has_more": False}


@router.get("/entities/{entity_id}")
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = (
        select(EntityModel)
        .where(EntityModel.entity_id == entity_id)
        .options(
            selectinload(EntityModel.outgoing_relations),
            selectinload(EntityModel.incoming_relations),
        )
    )
    
    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    
    outgoing = []
    incoming = []
    
    for rel in entity.outgoing_relations:
        target_query = select(EntityModel).where(
            EntityModel.entity_id == rel.target_entity_id
        )
        target_result = await db.execute(target_query)
        target = target_result.scalar_one_or_none()
        
        outgoing.append({
            "id": rel.relation_id,
            "type": rel.relation_type,
            "weight": float(rel.weight) if rel.weight else 1.0,
            "confidence": float(rel.confidence) if rel.confidence else 1.0,
            "evidence": rel.evidence,
            "target": {
                "id": target.entity_id,
                "name": target.name,
                "type": target.entity_type,
            } if target else None,
        })
    
    for rel in entity.incoming_relations:
        source_query = select(EntityModel).where(
            EntityModel.entity_id == rel.source_entity_id
        )
        source_result = await db.execute(source_query)
        source = source_result.scalar_one_or_none()
        
        incoming.append({
            "id": rel.relation_id,
            "type": rel.relation_type,
            "weight": float(rel.weight) if rel.weight else 1.0,
            "confidence": float(rel.confidence) if rel.confidence else 1.0,
            "evidence": rel.evidence,
            "source": {
                "id": source.entity_id,
                "name": source.name,
                "type": source.entity_type,
            } if source else None,
        })
    
    return {
        **entity_to_dict(entity),
        "relations": {
            "outgoing": outgoing,
            "incoming": incoming,
            "total": len(outgoing) + len(incoming),
        },
    }


@router.post("/entities")
async def create_entity(
    request: EntityCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if request.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid entity type: {request.entity_type}. Valid types: {VALID_ENTITY_TYPES}"
        )
    
    if request.code:
        existing_query = select(EntityModel).where(EntityModel.code == request.code)
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail=f"Entity with code '{request.code}' already exists"
            )
    
    entity_id = f"{request.entity_type}_{uuid.uuid4().hex[:8]}"
    
    entity = EntityModel(
        id=str(uuid.uuid4()),
        entity_id=entity_id,
        entity_type=request.entity_type,
        name=request.name,
        code=request.code,
        aliases=request.aliases,
        description=request.description,
        industry=request.industry,
        properties=request.properties,
        confidence=request.confidence,
        source="manual",
    )
    
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    
    return {
        "id": entity.entity_id,
        "name": entity.name,
        "type": entity.entity_type,
        "created": True,
    }


@router.put("/entities/{entity_id}")
async def update_entity(
    entity_id: str,
    request: EntityUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(EntityModel).where(EntityModel.entity_id == entity_id)
    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    
    if request.name is not None:
        entity.name = request.name
    if request.aliases is not None:
        entity.aliases = request.aliases
    if request.description is not None:
        entity.description = request.description
    if request.industry is not None:
        entity.industry = request.industry
    if request.properties is not None:
        entity.properties = request.properties
    
    entity.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(entity)
    
    return {
        "id": entity.entity_id,
        "name": entity.name,
        "updated": True,
    }


@router.delete("/entities/{entity_id}")
async def delete_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(EntityModel).where(EntityModel.entity_id == entity_id)
    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    
    delete_rels_query = delete(RelationModel).where(
        or_(
            RelationModel.source_entity_id == entity_id,
            RelationModel.target_entity_id == entity_id,
        )
    )
    await db.execute(delete_rels_query)
    
    await db.delete(entity)
    await db.commit()
    
    return {"id": entity_id, "deleted": True}


@router.post("/relations")
async def create_relation(
    request: RelationCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if request.relation_type not in VALID_RELATION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid relation type: {request.relation_type}. Valid types: {VALID_RELATION_TYPES}"
        )
    
    for eid in [request.source_entity_id, request.target_entity_id]:
        query = select(EntityModel).where(EntityModel.entity_id == eid)
        result = await db.execute(query)
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Entity not found: {eid}")
    
    existing_query = select(RelationModel).where(
        and_(
            RelationModel.source_entity_id == request.source_entity_id,
            RelationModel.target_entity_id == request.target_entity_id,
            RelationModel.relation_type == request.relation_type,
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Relation already exists"
        )
    
    relation_id = f"rel_{uuid.uuid4().hex[:8]}"
    
    relation = RelationModel(
        id=str(uuid.uuid4()),
        relation_id=relation_id,
        source_entity_id=request.source_entity_id,
        target_entity_id=request.target_entity_id,
        relation_type=request.relation_type,
        weight=request.weight,
        confidence=request.confidence,
        evidence=request.evidence,
        properties=request.properties,
    )
    
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    
    return {
        "id": relation.relation_id,
        "type": relation.relation_type,
        "created": True,
    }


@router.get("/entities/types/list")
async def list_entity_types(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if db is None:
        logger.warning("Database not available, returning empty types")
        return {"types": [{"type": t, "display_name": ENTITY_TYPE_LABELS.get(t, t), "count": 0} for t in VALID_ENTITY_TYPES]}
    
    try:
        query = (
            select(EntityModel.entity_type, func.count(EntityModel.id))
            .group_by(EntityModel.entity_type)
        )
        result = await db.execute(query)
        type_counts = {row[0]: row[1] for row in result.all()}
        
        types = []
        for t in VALID_ENTITY_TYPES:
            types.append({
                "type": t,
                "display_name": ENTITY_TYPE_LABELS.get(t, t),
                "count": type_counts.get(t, 0),
            })
        
        return {"types": types}
    except Exception as e:
        logger.warning(f"Database error in list_entity_types: {e}")
        return {"types": [{"type": t, "display_name": ENTITY_TYPE_LABELS.get(t, t), "count": 0} for t in VALID_ENTITY_TYPES]}


@router.get("/entities/industries/list")
async def list_industries(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if db is None:
        logger.warning("Database not available, returning empty industries")
        return {"industries": []}
    
    try:
        query = (
            select(EntityModel.industry, func.count(EntityModel.id))
            .where(EntityModel.industry.isnot(None))
            .group_by(EntityModel.industry)
        )
        result = await db.execute(query)
        industries = [{"name": row[0], "count": row[1]} for row in result.all()]
        
        return {"industries": industries}
    except Exception as e:
        logger.warning(f"Database error in list_industries: {e}")
        return {"industries": []}


@router.get("/quality", response_model=DataQualityReport)
async def get_data_quality(db: AsyncSession = Depends(get_db)) -> DataQualityReport:
    issues: list[dict[str, Any]] = []
    
    entity_count = await db.scalar(select(func.count(EntityModel.id))) or 0
    relation_count = await db.scalar(select(func.count(RelationModel.id))) or 0
    
    entity_type_query = (
        select(EntityModel.entity_type, func.count(EntityModel.id))
        .group_by(EntityModel.entity_type)
    )
    entity_type_result = await db.execute(entity_type_query)
    entity_type_dist = {row[0]: row[1] for row in entity_type_result.all()}
    
    relation_type_query = (
        select(RelationModel.relation_type, func.count(RelationModel.id))
        .group_by(RelationModel.relation_type)
    )
    relation_type_result = await db.execute(relation_type_query)
    relation_type_dist = {row[0]: row[1] for row in relation_type_result.all()}
    
    entities_with_relations_query = (
        select(distinct(RelationModel.source_entity_id))
        .union(select(distinct(RelationModel.target_entity_id)))
    )
    entities_with_relations_result = await db.execute(entities_with_relations_query)
    entities_with_relations = set(entities_with_relations_result.scalars().all())
    
    all_entities_query = select(EntityModel.entity_id)
    all_entities_result = await db.execute(all_entities_query)
    all_entity_ids = set(all_entities_result.scalars().all())
    
    isolated_count = len(all_entity_ids - entities_with_relations)
    if isolated_count > 0:
        issues.append({
            "type": "isolated_entities",
            "severity": "warning",
            "message": f"发现 {isolated_count} 个孤立实体（无任何关系）",
            "count": isolated_count,
        })
    
    no_industry_query = select(func.count(EntityModel.id)).where(
        and_(
            EntityModel.industry.is_(None),
            EntityModel.entity_type.in_(["stock", "company"]),
        )
    )
    no_industry_count = await db.scalar(no_industry_query) or 0
    if no_industry_count > 0:
        issues.append({
            "type": "missing_industry",
            "severity": "info",
            "message": f"发现 {no_industry_count} 个股票/公司实体缺少行业信息",
            "count": no_industry_count,
        })
    
    no_code_query = select(func.count(EntityModel.id)).where(
        and_(
            EntityModel.code.is_(None),
            EntityModel.entity_type.in_(["stock", "company"]),
        )
    )
    no_code_count = await db.scalar(no_code_query) or 0
    if no_code_count > 0:
        issues.append({
            "type": "missing_code",
            "severity": "info",
            "message": f"发现 {no_code_count} 个股票/公司实体缺少代码",
            "count": no_code_count,
        })
    
    stock_entities_query = select(EntityModel.code).where(
        EntityModel.entity_type == "stock"
    )
    stock_entities_result = await db.execute(stock_entities_query)
    stock_codes = [row[0] for row in stock_entities_result.fetchall() if row[0]]
    
    if stock_codes:
        basic_query = select(func.count(StockBasicModel.code)).where(
            StockBasicModel.code.in_(stock_codes)
        )
        basic_count = await db.scalar(basic_query) or 0
        missing_basic = len(stock_codes) - basic_count
        if missing_basic > 0:
            issues.append({
                "type": "missing_basic_data",
                "severity": "warning",
                "message": f"发现 {missing_basic} 个股票实体在基础数据表中不存在",
                "count": missing_basic,
            })
    
    dangling_query = select(RelationModel).where(
        or_(
            ~RelationModel.source_entity_id.in_(select(EntityModel.entity_id)),
            ~RelationModel.target_entity_id.in_(select(EntityModel.entity_id)),
        )
    )
    dangling_result = await db.execute(dangling_query)
    dangling_relations = dangling_result.scalars().all()
    if dangling_relations:
        issues.append({
            "type": "dangling_relations",
            "severity": "error",
            "message": f"发现 {len(dangling_relations)} 个悬空关系（引用不存在的实体）",
            "count": len(dangling_relations),
        })
    
    total_checks = 5
    passed_checks = total_checks - sum(1 for i in issues if i["severity"] == "error")
    consistency_score = passed_checks / total_checks
    
    return DataQualityReport(
        total_entities=entity_count,
        total_relations=relation_count,
        entity_type_distribution=entity_type_dist,
        relation_type_distribution=relation_type_dist,
        isolated_entities=isolated_count,
        entities_without_industry=no_industry_count,
        entities_without_code=no_code_count,
        stock_entities_without_basic=missing_basic if stock_codes else 0,
        dangling_relations=len(dangling_relations),
        consistency_score=consistency_score,
        issues=issues,
    )


@router.get("/entity/{entity_id}/news")
async def get_entity_news(
    entity_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(EntityModel).where(EntityModel.entity_id == entity_id)
    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    
    sample_news = [
        {
            "id": f"news_{i}",
            "title": f"{entity.name}相关新闻{i+1}",
            "summary": f"这是关于{entity.name}的新闻摘要...",
            "source": "财经资讯",
            "published_at": "2024-01-15",
            "sentiment": "positive" if i % 2 == 0 else "neutral",
        }
        for i in range(min(limit, 5))
    ]
    
    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "news": sample_news,
        "total": len(sample_news),
    }


@router.get("/entity/{entity_id}/sources")
async def get_entity_sources(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(EntityModel).where(EntityModel.entity_id == entity_id)
    result = await db.execute(query)
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity not found: {entity_id}")
    
    sources = []
    if entity.source:
        sources.append({
            "type": "primary",
            "name": entity.source,
            "confidence": float(entity.confidence) if entity.confidence else 1.0,
        })
    
    sources.append({
        "type": "created",
        "timestamp": entity.created_at.isoformat() if entity.created_at else None,
    })
    
    if entity.updated_at and entity.updated_at != entity.created_at:
        sources.append({
            "type": "updated",
            "timestamp": entity.updated_at.isoformat(),
        })
    
    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "sources": sources,
    }


@router.get("/relation-types/list")
async def list_relation_types() -> dict[str, Any]:
    return {
        "types": [
            {
                "type": t,
                "display_name": RELATION_TYPE_LABELS.get(t, t),
            }
            for t in VALID_RELATION_TYPES
        ]
    }
