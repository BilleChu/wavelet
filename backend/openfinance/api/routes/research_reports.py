"""
Research Report API Routes.

Provides research report data services:
- Search reports from Elasticsearch
- List reports from PostgreSQL
- Get report details
- Statistics
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/research-reports", tags=["research-reports"])


class ResearchReportResponse(BaseModel):
    """Research report response model."""
    
    report_id: str
    title: str
    summary: Optional[str] = None
    source: str
    institution: Optional[str] = None
    analyst: Optional[str] = None
    rating: Optional[str] = None
    target_price: Optional[float] = None
    related_codes: list[str] = []
    related_names: list[str] = []
    industry: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    publish_date: Optional[str] = None
    report_type: Optional[str] = None
    source_url: Optional[str] = None


class ResearchReportListResponse(BaseModel):
    """Research report list response."""
    
    reports: list[ResearchReportResponse]
    total: int
    page: int
    page_size: int


class ResearchReportSearchRequest(BaseModel):
    """Research report search request."""
    
    query: str = Field(..., description="Search query")
    codes: list[str] | None = Field(default=None, description="Filter by stock codes")
    institution: str | None = Field(default=None, description="Filter by institution")
    rating: str | None = Field(default=None, description="Filter by rating")
    industry: str | None = Field(default=None, description="Filter by industry")
    start_date: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="End date (YYYY-MM-DD)")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=10, description="Page size")


class ResearchReportStatsResponse(BaseModel):
    """Research report statistics response."""
    
    total_reports: int
    by_source: dict[str, int]
    by_rating: dict[str, int]
    by_institution: dict[str, int]
    recent_count: int


@router.get("", response_model=ResearchReportListResponse)
async def list_research_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    code: str | None = None,
    institution: str | None = None,
    rating: str | None = None,
    source: str | None = None,
) -> ResearchReportListResponse:
    """List research reports with pagination and filters."""
    from openfinance.infrastructure.database.database import async_session_maker
    from openfinance.datacenter.models.orm import ResearchReportModel
    from sqlalchemy import select, func, or_
    
    async with async_session_maker() as session:
        query = select(ResearchReportModel)
        count_query = select(func.count()).select_from(ResearchReportModel)
        
        if code:
            query = query.where(ResearchReportModel.related_codes.contains([code]))
            count_query = count_query.where(ResearchReportModel.related_codes.contains([code]))
        if institution:
            query = query.where(ResearchReportModel.institution == institution)
            count_query = count_query.where(ResearchReportModel.institution == institution)
        if rating:
            query = query.where(ResearchReportModel.rating == rating)
            count_query = count_query.where(ResearchReportModel.rating == rating)
        if source:
            query = query.where(ResearchReportModel.source == source)
            count_query = count_query.where(ResearchReportModel.source == source)
        
        total = await session.scalar(count_query) or 0
        
        query = query.order_by(ResearchReportModel.publish_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await session.execute(query)
        reports = result.scalars().all()
        
        return ResearchReportListResponse(
            reports=[
                ResearchReportResponse(
                    report_id=r.report_id,
                    title=r.title,
                    summary=r.summary[:200] + "..." if r.summary and len(r.summary) > 200 else r.summary,
                    source=r.source,
                    institution=r.institution,
                    analyst=r.analyst,
                    rating=r.rating,
                    target_price=float(r.target_price) if r.target_price else None,
                    related_codes=r.related_codes or [],
                    related_names=r.related_names or [],
                    industry=r.industry,
                    sentiment_score=float(r.sentiment_score) if r.sentiment_score else None,
                    sentiment_label=r.sentiment_label,
                    publish_date=r.publish_date.isoformat() if r.publish_date else None,
                    report_type=r.report_type,
                    source_url=r.source_url,
                )
                for r in reports
            ],
            total=total,
            page=page,
            page_size=page_size,
        )


@router.get("/search")
async def search_research_reports(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """Search research reports using Elasticsearch."""
    try:
        from openfinance.infrastructure.search import (
            init_es_client,
            get_research_report_index,
        )
        
        await init_es_client()
        index = get_research_report_index()
        
        result = await index.search_reports(
            query=q,
            size=page_size,
            from_=(page - 1) * page_size,
        )
        
        return {
            "reports": result.get("hits", []),
            "total": result.get("total", 0),
            "page": page,
            "page_size": page_size,
        }
        
    except Exception as e:
        logger.warning(f"Elasticsearch search failed, falling back to database: {e}")
        
        from openfinance.infrastructure.database.database import async_session_maker
        from openfinance.datacenter.models.orm import ResearchReportModel
        from sqlalchemy import select, or_
        
        async with async_session_maker() as session:
            query = select(ResearchReportModel).where(
                or_(
                    ResearchReportModel.title.ilike(f"%{q}%"),
                    ResearchReportModel.summary.ilike(f"%{q}%"),
                )
            ).order_by(ResearchReportModel.publish_date.desc())
            
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            result = await session.execute(query)
            reports = result.scalars().all()
            
            return {
                "reports": [
                    {
                        "report_id": r.report_id,
                        "title": r.title,
                        "summary": r.summary[:200] + "..." if r.summary and len(r.summary) > 200 else r.summary,
                        "source": r.source,
                        "institution": r.institution,
                        "analyst": r.analyst,
                        "rating": r.rating,
                        "related_codes": r.related_codes or [],
                        "related_names": r.related_names or [],
                        "publish_date": r.publish_date.isoformat() if r.publish_date else None,
                    }
                    for r in reports
                ],
                "total": len(reports),
                "page": page,
                "page_size": page_size,
            }


@router.get("/stats", response_model=ResearchReportStatsResponse)
async def get_research_report_stats() -> ResearchReportStatsResponse:
    """Get research report statistics."""
    from openfinance.infrastructure.database.database import async_session_maker
    from openfinance.datacenter.models.orm import ResearchReportModel
    from sqlalchemy import select, func
    
    async with async_session_maker() as session:
        total = await session.scalar(
            select(func.count()).select_from(ResearchReportModel)
        ) or 0
        
        source_result = await session.execute(
            select(ResearchReportModel.source, func.count())
            .group_by(ResearchReportModel.source)
        )
        by_source = {row[0]: row[1] for row in source_result.all()}
        
        rating_result = await session.execute(
            select(ResearchReportModel.rating, func.count())
            .where(ResearchReportModel.rating.isnot(None))
            .group_by(ResearchReportModel.rating)
        )
        by_rating = {row[0]: row[1] for row in rating_result.all()}
        
        institution_result = await session.execute(
            select(ResearchReportModel.institution, func.count())
            .where(ResearchReportModel.institution.isnot(None))
            .group_by(ResearchReportModel.institution)
            .order_by(func.count().desc())
            .limit(10)
        )
        by_institution = {row[0]: row[1] for row in institution_result.all()}
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = await session.scalar(
            select(func.count()).select_from(ResearchReportModel)
            .where(ResearchReportModel.publish_date >= week_ago)
        ) or 0
        
        return ResearchReportStatsResponse(
            total_reports=total,
            by_source=by_source,
            by_rating=by_rating,
            by_institution=by_institution,
            recent_count=recent_count,
        )


@router.get("/{report_id}")
async def get_research_report(report_id: str) -> dict[str, Any]:
    """Get research report details by ID."""
    from openfinance.infrastructure.database.database import async_session_maker
    from openfinance.datacenter.models.orm import ResearchReportModel
    from sqlalchemy import select
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(ResearchReportModel).where(
                ResearchReportModel.report_id == report_id
            )
        )
        report = result.scalar_one_or_none()
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
        
        return {
            "report_id": report.report_id,
            "title": report.title,
            "summary": report.summary,
            "content": report.content,
            "source": report.source,
            "source_url": report.source_url,
            "related_codes": report.related_codes or [],
            "related_names": report.related_names or [],
            "industry": report.industry,
            "institution": report.institution,
            "analyst": report.analyst,
            "rating": report.rating,
            "target_price": float(report.target_price) if report.target_price else None,
            "sentiment_score": float(report.sentiment_score) if report.sentiment_score else None,
            "sentiment_label": report.sentiment_label,
            "extracted_entities": report.extracted_entities,
            "extracted_relations": report.extracted_relations,
            "publish_date": report.publish_date.isoformat() if report.publish_date else None,
            "report_type": report.report_type,
            "collected_at": report.collected_at.isoformat() if report.collected_at else None,
        }


@router.get("/code/{code}")
async def get_reports_by_code(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """Get research reports by stock code."""
    from openfinance.infrastructure.database.database import async_session_maker
    from openfinance.datacenter.models.orm import ResearchReportModel
    from sqlalchemy import select, func
    
    async with async_session_maker() as session:
        count_query = select(func.count()).select_from(ResearchReportModel).where(
            ResearchReportModel.related_codes.contains([code])
        )
        total = await session.scalar(count_query) or 0
        
        query = select(ResearchReportModel).where(
            ResearchReportModel.related_codes.contains([code])
        ).order_by(ResearchReportModel.publish_date.desc())
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await session.execute(query)
        reports = result.scalars().all()
        
        return {
            "code": code,
            "reports": [
                {
                    "report_id": r.report_id,
                    "title": r.title,
                    "summary": r.summary[:200] + "..." if r.summary and len(r.summary) > 200 else r.summary,
                    "institution": r.institution,
                    "analyst": r.analyst,
                    "rating": r.rating,
                    "publish_date": r.publish_date.isoformat() if r.publish_date else None,
                }
                for r in reports
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get("/institution/{institution}")
async def get_reports_by_institution(
    institution: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """Get research reports by institution."""
    from openfinance.infrastructure.database.database import async_session_maker
    from openfinance.datacenter.models.orm import ResearchReportModel
    from sqlalchemy import select, func
    
    async with async_session_maker() as session:
        count_query = select(func.count()).select_from(ResearchReportModel).where(
            ResearchReportModel.institution == institution
        )
        total = await session.scalar(count_query) or 0
        
        query = select(ResearchReportModel).where(
            ResearchReportModel.institution == institution
        ).order_by(ResearchReportModel.publish_date.desc())
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await session.execute(query)
        reports = result.scalars().all()
        
        return {
            "institution": institution,
            "reports": [
                {
                    "report_id": r.report_id,
                    "title": r.title,
                    "related_codes": r.related_codes or [],
                    "related_names": r.related_names or [],
                    "analyst": r.analyst,
                    "rating": r.rating,
                    "publish_date": r.publish_date.isoformat() if r.publish_date else None,
                }
                for r in reports
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
