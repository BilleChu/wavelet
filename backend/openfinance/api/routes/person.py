"""
Person API Routes.

Provides person profile data services:
- List persons with filters and pagination
- Get person details with scores
- Get person activities timeline
- Get person knowledge graph
- Get person scores by industry
- Person rankings
"""

import logging
from datetime import datetime, date
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from openfinance.infrastructure.database.database import async_session_maker
from openfinance.datacenter.models.orm import (
    EntityModel,
    RelationModel,
    PersonProfileModel,
    PersonActivityModel,
    PersonIndustryScoreModel,
    PersonScoreHistoryModel,
)
from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/persons", tags=["persons"])


PERSON_TYPE_LABELS = {
    "investment_manager": "投资经理",
    "kol": "KOL",
    "entrepreneur": "企业家",
    "analyst": "分析师",
    "executive": "企业高管",
    "investor": "投资人",
}


class PersonResponse(BaseModel):
    """Person list item response."""
    
    entity_id: str
    name: str
    person_type: str | None = None
    person_type_label: str | None = None
    title: str | None = None
    company: str | None = None
    industry: str | None = None
    avatar_url: str | None = None
    verified: bool = False
    
    total_score: float = 0
    influence_score: float = 0
    activity_score: float = 0
    accuracy_score: float = 0
    network_score: float = 0
    
    followers_count: int = 0
    news_mentions: int = 0
    report_count: int = 0
    
    industry_scores: dict[str, Any] = {}


class PersonListResponse(BaseModel):
    """Person list response."""
    
    persons: list[PersonResponse]
    total: int
    page: int
    page_size: int


class PersonDetailResponse(BaseModel):
    """Person detail response."""
    
    entity_id: str
    name: str
    person_type: str | None = None
    person_type_label: str | None = None
    title: str | None = None
    company: str | None = None
    industry: str | None = None
    avatar_url: str | None = None
    verified: bool = False
    biography: str | None = None
    
    certifications: list[str] = []
    social_links: dict[str, str] = {}
    work_history: list[dict[str, Any]] = []
    education: list[dict[str, Any]] = []
    focus_industries: list[dict[str, Any]] = []
    managed_assets: float | None = None
    investment_style: str | None = None
    
    total_score: float = 0
    influence_score: float = 0
    activity_score: float = 0
    accuracy_score: float = 0
    network_score: float = 0
    industry_score: float = 0
    
    followers_count: int = 0
    news_mentions: int = 0
    report_count: int = 0
    
    industry_scores: dict[str, Any] = {}
    
    created_at: str | None = None
    updated_at: str | None = None


class PersonActivityResponse(BaseModel):
    """Person activity response."""
    
    activity_id: str
    activity_type: str
    title: str
    content: str | None = None
    source: str | None = None
    source_url: str | None = None
    industry: str | None = None
    sentiment_score: float | None = None
    impact_score: float | None = None
    related_codes: list[str] = []
    related_entities: list[str] = []
    activity_date: str | None = None


class PersonActivityListResponse(BaseModel):
    """Person activity list response."""
    
    activities: list[PersonActivityResponse]
    total: int
    page: int
    page_size: int


class PersonIndustryScoreResponse(BaseModel):
    """Person industry score response."""
    
    industry: str
    total_score: float
    expertise_score: float | None = None
    influence_score: float | None = None
    accuracy_score: float | None = None
    metrics: dict[str, Any] = {}


class PersonStatsResponse(BaseModel):
    """Person statistics response."""
    
    total_persons: int
    by_type: dict[str, int]
    by_industry: dict[str, int]
    avg_score: float
    top_scored_count: int


class PersonScoreHistoryResponse(BaseModel):
    """Person score history response."""
    
    score_date: str
    total_score: float | None = None
    influence_score: float | None = None
    activity_score: float | None = None
    accuracy_score: float | None = None
    network_score: float | None = None
    industry_score: float | None = None


async def get_db():
    """Get database session."""
    async with async_session_maker() as session:
        yield session


@router.get("", response_model=PersonListResponse)
async def list_persons(
    person_type: str | None = Query(None, description="Filter by person type"),
    industry: str | None = Query(None, description="Filter by industry"),
    company: str | None = Query(None, description="Filter by company"),
    min_score: float | None = Query(None, description="Minimum total score"),
    keyword: str | None = Query(None, description="Search keyword"),
    sort_by: str = Query("total_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PersonListResponse:
    """List persons with filters and pagination."""
    
    query = (
        select(EntityModel, PersonProfileModel)
        .outerjoin(
            PersonProfileModel, 
            EntityModel.entity_id == PersonProfileModel.entity_id
        )
        .where(EntityModel.entity_type == "person")
    )
    
    count_query = (
        select(func.count())
        .select_from(EntityModel)
        .where(EntityModel.entity_type == "person")
    )
    
    if person_type:
        query = query.where(EntityModel.properties["person_type"].astext == person_type)
        count_query = count_query.where(EntityModel.properties["person_type"].astext == person_type)
    
    if industry:
        query = query.where(EntityModel.industry == industry)
        count_query = count_query.where(EntityModel.industry == industry)
    
    if company:
        query = query.where(EntityModel.properties["company"].astext.ilike(f"%{company}%"))
        count_query = count_query.where(EntityModel.properties["company"].astext.ilike(f"%{company}%"))
    
    if keyword:
        keyword_filter = or_(
            EntityModel.name.ilike(f"%{keyword}%"),
            EntityModel.properties["company"].astext.ilike(f"%{keyword}%"),
            EntityModel.properties["title"].astext.ilike(f"%{keyword}%"),
        )
        query = query.where(keyword_filter)
        count_query = count_query.where(keyword_filter)
    
    if min_score is not None:
        query = query.where(PersonProfileModel.total_score >= min_score)
        count_query = count_query.outerjoin(
            PersonProfileModel, 
            EntityModel.entity_id == PersonProfileModel.entity_id
        ).where(PersonProfileModel.total_score >= min_score)
    
    total = await db.scalar(count_query) or 0
    
    sort_column = getattr(PersonProfileModel, sort_by, PersonProfileModel.total_score)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    persons = []
    for entity, profile in rows:
        props = entity.properties or {}
        person_type_val = props.get("person_type")
        
        persons.append(PersonResponse(
            entity_id=entity.entity_id,
            name=entity.name,
            person_type=person_type_val,
            person_type_label=PERSON_TYPE_LABELS.get(person_type_val),
            title=props.get("title"),
            company=props.get("company"),
            industry=entity.industry,
            avatar_url=props.get("avatar_url"),
            verified=props.get("verified", False),
            total_score=float(profile.total_score) if profile else 0,
            influence_score=float(profile.influence_score) if profile else 0,
            activity_score=float(profile.activity_score) if profile else 0,
            accuracy_score=float(profile.accuracy_score) if profile else 0,
            network_score=float(profile.network_score) if profile else 0,
            followers_count=profile.followers_count if profile else 0,
            news_mentions=profile.news_mentions if profile else 0,
            report_count=profile.report_count if profile else 0,
            industry_scores=profile.industry_scores if profile else {},
        ))
    
    return PersonListResponse(
        persons=persons,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=PersonStatsResponse)
async def get_person_stats(
    db: AsyncSession = Depends(get_db),
) -> PersonStatsResponse:
    """Get person statistics."""
    
    total_query = select(func.count()).select_from(EntityModel).where(
        EntityModel.entity_type == "person"
    )
    total = await db.scalar(total_query) or 0
    
    all_persons_query = select(EntityModel).where(EntityModel.entity_type == "person")
    result = await db.execute(all_persons_query)
    persons = result.scalars().all()
    
    by_type: dict[str, int] = {}
    for p in persons:
        props = p.properties or {}
        ptype = props.get("person_type", "unknown") or "unknown"
        by_type[ptype] = by_type.get(ptype, 0) + 1
    
    by_industry: dict[str, int] = {}
    for p in persons:
        if p.industry:
            by_industry[p.industry] = by_industry.get(p.industry, 0) + 1
    
    avg_query = select(func.avg(PersonProfileModel.total_score))
    avg_score = await db.scalar(avg_query) or 0
    
    top_count_query = select(func.count()).select_from(PersonProfileModel).where(
        PersonProfileModel.total_score >= 80
    )
    top_scored_count = await db.scalar(top_count_query) or 0
    
    return PersonStatsResponse(
        total_persons=total,
        by_type=by_type,
        by_industry=by_industry,
        avg_score=float(avg_score),
        top_scored_count=top_scored_count,
    )


@router.get("/types")
async def get_person_types() -> dict[str, str]:
    """Get available person types."""
    return PERSON_TYPE_LABELS


@router.get("/rankings")
async def get_person_rankings(
    person_type: str | None = Query(None, description="Filter by person type"),
    industry: str | None = Query(None, description="Filter by industry"),
    sort_by: str = Query("total_score", description="Sort field"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PersonListResponse:
    """Get person rankings."""
    
    return await list_persons(
        person_type=person_type,
        industry=industry,
        sort_by=sort_by,
        sort_order="desc",
        page=page,
        page_size=page_size,
        db=db,
    )


@router.get("/{entity_id}", response_model=PersonDetailResponse)
async def get_person(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> PersonDetailResponse:
    """Get person details by entity ID."""
    
    query = (
        select(EntityModel, PersonProfileModel)
        .outerjoin(
            PersonProfileModel, 
            EntityModel.entity_id == PersonProfileModel.entity_id
        )
        .where(
            EntityModel.entity_type == "person",
            EntityModel.entity_id == entity_id,
        )
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Person not found: {entity_id}")
    
    entity, profile = row
    props = entity.properties or {}
    person_type_val = props.get("person_type")
    
    return PersonDetailResponse(
        entity_id=entity.entity_id,
        name=entity.name,
        person_type=person_type_val,
        person_type_label=PERSON_TYPE_LABELS.get(person_type_val),
        title=props.get("title"),
        company=props.get("company"),
        industry=entity.industry,
        avatar_url=props.get("avatar_url"),
        verified=props.get("verified", False),
        biography=props.get("biography") or entity.description,
        certifications=props.get("certifications", []),
        social_links=props.get("social_links", {}),
        work_history=props.get("work_history", []),
        education=props.get("education", []),
        focus_industries=props.get("focus_industries", []),
        managed_assets=float(profile.managed_assets) if profile and profile.managed_assets else None,
        investment_style=props.get("investment_style"),
        total_score=float(profile.total_score) if profile else 0,
        influence_score=float(profile.influence_score) if profile else 0,
        activity_score=float(profile.activity_score) if profile else 0,
        accuracy_score=float(profile.accuracy_score) if profile else 0,
        network_score=float(profile.network_score) if profile else 0,
        industry_score=float(profile.industry_score) if profile else 0,
        followers_count=profile.followers_count if profile else 0,
        news_mentions=profile.news_mentions if profile else 0,
        report_count=profile.report_count if profile else 0,
        industry_scores=profile.industry_scores if profile else {},
        created_at=entity.created_at.isoformat() if entity.created_at else None,
        updated_at=entity.updated_at.isoformat() if entity.updated_at else None,
    )


@router.get("/{entity_id}/activities", response_model=PersonActivityListResponse)
async def get_person_activities(
    entity_id: str,
    activity_type: str | None = Query(None, description="Filter by activity type"),
    industry: str | None = Query(None, description="Filter by industry"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PersonActivityListResponse:
    """Get person activities timeline."""
    
    count_query = (
        select(func.count())
        .select_from(PersonActivityModel)
        .where(PersonActivityModel.entity_id == entity_id)
    )
    
    query = (
        select(PersonActivityModel)
        .where(PersonActivityModel.entity_id == entity_id)
    )
    
    if activity_type:
        query = query.where(PersonActivityModel.activity_type == activity_type)
        count_query = count_query.where(PersonActivityModel.activity_type == activity_type)
    
    if industry:
        query = query.where(PersonActivityModel.industry == industry)
        count_query = count_query.where(PersonActivityModel.industry == industry)
    
    total = await db.scalar(count_query) or 0
    
    query = query.order_by(desc(PersonActivityModel.activity_date))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    return PersonActivityListResponse(
        activities=[
            PersonActivityResponse(
                activity_id=a.activity_id,
                activity_type=a.activity_type,
                title=a.title,
                content=a.content,
                source=a.source,
                source_url=a.source_url,
                industry=a.industry,
                sentiment_score=float(a.sentiment_score) if a.sentiment_score else None,
                impact_score=float(a.impact_score) if a.impact_score else None,
                related_codes=a.related_codes or [],
                related_entities=a.related_entities or [],
                activity_date=a.activity_date.isoformat() if a.activity_date else None,
            )
            for a in activities
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{entity_id}/industry-scores")
async def get_person_industry_scores(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PersonIndustryScoreResponse]:
    """Get person scores by industry."""
    
    profile_query = select(PersonProfileModel).where(
        PersonProfileModel.entity_id == entity_id
    )
    profile_result = await db.execute(profile_query)
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        return []
    
    industry_scores = profile.industry_scores or {}
    
    return [
        PersonIndustryScoreResponse(
            industry=industry,
            total_score=score_data.get("total_score", 0),
            expertise_score=score_data.get("expertise_score"),
            influence_score=score_data.get("influence_score"),
            accuracy_score=score_data.get("accuracy_score"),
            metrics=score_data.get("metrics", {}),
        )
        for industry, score_data in industry_scores.items()
    ]


@router.get("/{entity_id}/score-history")
async def get_person_score_history(
    entity_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db),
) -> list[PersonScoreHistoryResponse]:
    """Get person score history."""
    
    query = (
        select(PersonScoreHistoryModel)
        .where(PersonScoreHistoryModel.entity_id == entity_id)
        .order_by(desc(PersonScoreHistoryModel.score_date))
        .limit(days)
    )
    
    result = await db.execute(query)
    history = result.scalars().all()
    
    return [
        PersonScoreHistoryResponse(
            score_date=h.score_date.isoformat(),
            total_score=float(h.total_score) if h.total_score else None,
            influence_score=float(h.influence_score) if h.influence_score else None,
            activity_score=float(h.activity_score) if h.activity_score else None,
            accuracy_score=float(h.accuracy_score) if h.accuracy_score else None,
            network_score=float(h.network_score) if h.network_score else None,
            industry_score=float(h.industry_score) if h.industry_score else None,
        )
        for h in history
    ]


@router.get("/{entity_id}/graph")
async def get_person_graph(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3, description="Graph traversal depth"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get person knowledge graph with related entities."""
    
    nodes = []
    edges = []
    visited_nodes = set()
    visited_edges = set()
    
    person = await db.scalar(
        select(EntityModel).where(
            EntityModel.entity_type == "person",
            EntityModel.entity_id == entity_id,
        )
    )
    
    if not person:
        raise HTTPException(status_code=404, detail=f"Person not found: {entity_id}")
    
    nodes.append({
        "id": person.entity_id,
        "name": person.name,
        "type": "person",
        "category": "person",
        "properties": person.properties or {},
    })
    visited_nodes.add(person.entity_id)
    
    current_level = [entity_id]
    
    for _ in range(depth):
        next_level = []
        
        for source_id in current_level:
            relations = await db.execute(
                select(RelationModel).where(
                    or_(
                        RelationModel.source_entity_id == source_id,
                        RelationModel.target_entity_id == source_id,
                    )
                )
            )
            
            for rel in relations.scalars():
                target_id = rel.target_entity_id if rel.source_entity_id == source_id else rel.source_entity_id
                
                edge_key = f"{rel.source_entity_id}-{rel.relation_type}-{rel.target_entity_id}"
                if edge_key not in visited_edges:
                    edges.append({
                        "id": rel.relation_id,
                        "source": rel.source_entity_id,
                        "target": rel.target_entity_id,
                        "type": rel.relation_type,
                        "weight": float(rel.weight) if rel.weight else 1.0,
                        "properties": rel.properties or {},
                    })
                    visited_edges.add(edge_key)
                
                if target_id not in visited_nodes:
                    target_entity = await db.scalar(
                        select(EntityModel).where(EntityModel.entity_id == target_id)
                    )
                    
                    if target_entity:
                        nodes.append({
                            "id": target_entity.entity_id,
                            "name": target_entity.name,
                            "type": target_entity.entity_type,
                            "category": target_entity.entity_type,
                            "properties": target_entity.properties or {},
                            "code": target_entity.code,
                            "industry": target_entity.industry,
                        })
                        visited_nodes.add(target_id)
                        next_level.append(target_id)
        
        current_level = next_level
    
    return {
        "nodes": nodes,
        "edges": edges,
        "center": entity_id,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }
