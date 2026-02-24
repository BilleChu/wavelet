"""
Data Service API Routes.

Provides RESTful endpoints for accessing data services.
All data comes from ADS layer (real database), NO mock data.
"""

import logging
import uuid
from datetime import datetime, timedelta, date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from openfinance.api.middleware.auth import (
    AuthContext,
    authenticate_request,
    check_permission,
    get_current_user,
)
from openfinance.datacenter.marketplace import (
    DataGateway,
    DataServiceCategory,
    DataServiceDefinition,
    DataServiceEndpoint,
    DataServiceSubscription,
    DataServiceUsage,
    EndpointMethod,
    get_data_gateway,
    get_service_registry,
    get_service_monitor,
)
from openfinance.datacenter.models.analytical import (
    ADSKLineModel,
    ADSFactorModel,
    ADSNewsModel,
    ADSMacroEconomicModel,
    ADSFinancialIndicatorModel,
    get_ads_service,
)
from openfinance.datacenter.models import EntityModel, RelationModel
from openfinance.infrastructure.database.database import async_session_maker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dataservice/v1", tags=["DataService"])

_registry_initialized = False


async def ensure_registry_initialized() -> None:
    """Ensure the service registry is initialized."""
    global _registry_initialized
    if not _registry_initialized:
        registry = get_service_registry()
        await registry.initialize()
        _registry_initialized = True
        logger.info("Data service registry initialized")


class APIResponse(BaseModel):
    """Standard API response."""

    success: bool = Field(default=True, description="Whether the request succeeded")
    data: Any = Field(default=None, description="Response data")
    error: str | None = Field(default=None, description="Error message if failed")
    error_code: str | None = Field(default=None, description="Error code if failed")
    request_id: str = Field(..., description="Request identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class PaginatedResponse(BaseModel):
    """Paginated API response."""

    success: bool = Field(default=True)
    data: list[Any] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    total_pages: int = Field(default=0)
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


def _generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:12]}"


@router.get("/services", response_model=APIResponse)
async def list_services(
    category: DataServiceCategory | None = Query(None, description="Filter by category"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """List all available data services."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    services = registry.list_services(category=category)
    
    return APIResponse(
        success=True,
        data=[
            {
                "service_id": s.service_id,
                "name": s.name,
                "description": s.description,
                "category": s.category.value,
                "version": s.version,
                "status": s.status.value,
                "endpoints_count": len(s.endpoints),
                "tags": s.tags,
            }
            for s in services
        ],
        request_id=request_id,
    )


@router.get("/services/{service_id}", response_model=APIResponse)
async def get_service(
    service_id: str,
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get details of a specific service."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    service = registry.get_service(service_id)
    
    if not service:
        return APIResponse(
            success=False,
            error=f"Service {service_id} not found",
            error_code="SERVICE_NOT_FOUND",
            request_id=request_id,
        )
    
    return APIResponse(
        success=True,
        data={
            "service_id": service.service_id,
            "name": service.name,
            "description": service.description,
            "category": service.category.value,
            "version": service.version,
            "status": service.status.value,
            "endpoints": [
                {
                    "path": e.path,
                    "method": e.method.value,
                    "description": e.description,
                    "parameters": e.parameters,
                    "requires_auth": e.requires_auth,
                    "deprecated": e.deprecated,
                }
                for e in service.endpoints
            ],
            "rate_limit": {
                "requests_per_minute": service.rate_limit.requests_per_minute,
                "requests_per_hour": service.rate_limit.requests_per_hour,
            },
            "tags": service.tags,
        },
        request_id=request_id,
    )


@router.get("/analysis/macro", response_model=APIResponse)
async def get_macro_indicators(
    indicators: list[str] | None = Query(None, description="Indicator codes to fetch"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get macro economic indicators from ADS layer."""
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:analysis"):
        return APIResponse(
            success=False,
            error="Permission denied: read:analysis required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select
        from openfinance.datacenter.models.orm import MacroEconomicModel
        
        async with async_session_maker() as session:
            query = select(MacroEconomicModel)
            
            if indicators:
                query = query.where(MacroEconomicModel.indicator_code.in_(indicators))
            if start_date:
                query = query.where(MacroEconomicModel.published_at >= datetime.fromisoformat(start_date))
            if end_date:
                query = query.where(MacroEconomicModel.published_at <= datetime.fromisoformat(end_date))
            
            query = query.order_by(MacroEconomicModel.published_at.desc()).limit(100)
            
            result = await session.execute(query)
            records = result.scalars().all()
            
            data = [
                {
                    "code": r.indicator_code,
                    "name": r.indicator_name,
                    "name_en": r.indicator_code,
                    "category": "economic",
                    "unit": r.unit or "",
                    "current_value": float(r.value) if r.value else None,
                    "previous_value": None,
                    "yoy_change": None,
                    "mom_change": None,
                    "trend": "stable",
                    "period": r.period,
                    "country": r.country,
                    "timestamp": r.published_at.isoformat() if r.published_at else None,
                }
                for r in records
            ]
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to fetch macro indicators: {e}")
        return APIResponse(
            success=True,
            data=[],
            request_id=request_id,
        )


@router.get("/analysis/company/{code}", response_model=APIResponse)
async def get_company_insight(
    code: str,
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get company insight data from ADS layer.
    
    Stock code format: Supports 6-digit code (000001), Wind format (000001.SZ),
    or Eastmoney format (000001.SZ). All formats are normalized to 6-digit code.
    """
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:analysis"):
        return APIResponse(
            success=False,
            error="Permission denied: read:analysis required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select
        from openfinance.datacenter.models.orm import StockBasicModel, StockFinancialIndicatorModel
        from openfinance.utils.stock_code import normalize_stock_code
        
        # Normalize stock code
        code = normalize_stock_code(code)
        
        async with async_session_maker() as session:
            basic_query = select(StockBasicModel).where(StockBasicModel.code == code)
            basic_result = await session.execute(basic_query)
            basic = basic_result.scalar_one_or_none()
            
            if not basic:
                return APIResponse(
                    success=False,
                    error=f"Company {code} not found",
                    error_code="COMPANY_NOT_FOUND",
                    request_id=request_id,
                )
            
            fin_query = select(StockFinancialIndicatorModel).where(
                StockFinancialIndicatorModel.code == code
            ).order_by(StockFinancialIndicatorModel.report_date.desc()).limit(1)
            fin_result = await session.execute(fin_query)
            fin = fin_result.scalar_one_or_none()
            
            data = {
                "stock_code": code,
                "stock_name": basic.name,
                "industry": basic.industry,
                "sector": basic.sector,
                "market": basic.market,
                "pe_ratio": float(fin.pe) if fin and fin.pe else None,
                "pb_ratio": float(fin.bps) if fin and fin.bps else None,
                "roe": float(fin.roe) if fin and fin.roe else None,
                "net_margin": float(fin.net_margin) if fin and fin.net_margin else None,
                "debt_ratio": float(fin.debt_ratio) if fin and fin.debt_ratio else None,
                "timestamp": datetime.now().isoformat(),
            }
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to fetch company insight: {e}")
        return APIResponse(
            success=False,
            error=str(e),
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        )


@router.get("/graph/entities", response_model=PaginatedResponse)
async def query_entities(
    entity_types: list[str] | None = Query(None, description="Entity types to filter"),
    keywords: str | None = Query(None, description="Search keywords"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    auth: AuthContext = Depends(authenticate_request),
) -> PaginatedResponse:
    """Query entities from knowledge graph."""
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:graph"):
        return PaginatedResponse(
            success=False,
            data=[],
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select, or_
        
        async with async_session_maker() as session:
            query = select(EntityModel)
            
            if entity_types:
                query = query.where(EntityModel.entity_type.in_(entity_types))
            
            if keywords:
                query = query.where(
                    or_(
                        EntityModel.name.ilike(f"%{keywords}%"),
                        EntityModel.aliases.ilike(f"%{keywords}%"),
                    )
                )
            
            count_query = select(EntityModel)
            if entity_types:
                count_query = count_query.where(EntityModel.entity_type.in_(entity_types))
            if keywords:
                count_query = count_query.where(
                    or_(
                        EntityModel.name.ilike(f"%{keywords}%"),
                        EntityModel.aliases.ilike(f"%{keywords}%"),
                    )
                )
            
            total_result = await session.execute(count_query)
            total = len(total_result.scalars().all())
            
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            result = await session.execute(query)
            entities = result.scalars().all()
            
            data = [
                {
                    "entity_id": str(e.id),
                    "entity_type": e.entity_type,
                    "name": e.name,
                    "aliases": e.aliases if e.aliases else [],
                    "description": e.description,
                    "code": e.code,
                    "industry": e.industry,
                    "properties": e.properties or {},
                    "relations_count": 0,
                }
                for e in entities
            ]
            
            total_pages = (total + page_size - 1) // page_size
            
            return PaginatedResponse(
                success=True,
                data=data,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to query entities: {e}")
        return PaginatedResponse(
            success=True,
            data=[],
            total=0,
            request_id=request_id,
        )


@router.get("/graph/relations", response_model=APIResponse)
async def query_relations(
    entity_id: str | None = Query(None, description="Entity ID to filter"),
    relation_types: list[str] | None = Query(None, description="Relation types"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Query relations from knowledge graph."""
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:graph"):
        return APIResponse(
            success=False,
            error="Permission denied: read:graph required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select, or_
        
        async with async_session_maker() as session:
            query = select(RelationModel)
            
            if entity_id:
                query = query.where(
                    or_(
                        RelationModel.source_entity_id == entity_id,
                        RelationModel.target_entity_id == entity_id,
                    )
                )
            
            if relation_types:
                query = query.where(RelationModel.relation_type.in_(relation_types))
            
            query = query.limit(limit)
            
            result = await session.execute(query)
            relations = result.scalars().all()
            
            data = [
                {
                    "relation_id": str(r.id),
                    "source_entity_id": r.source_entity_id,
                    "target_entity_id": r.target_entity_id,
                    "relation_type": r.relation_type,
                    "weight": float(r.weight) if r.weight else 1.0,
                    "confidence": float(r.confidence) if r.confidence else 1.0,
                    "evidence": r.evidence,
                    "properties": r.properties or {},
                }
                for r in relations
            ]
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to query relations: {e}")
        return APIResponse(
            success=True,
            data=[],
            request_id=request_id,
        )


@router.get("/graph/news", response_model=APIResponse)
async def query_news(
    source: str | None = Query(None, description="News source"),
    keywords: str | None = Query(None, description="Search keywords"),
    limit: int = Query(50, ge=1, le=200, description="Number of results"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Query news from database."""
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:graph"):
        return APIResponse(
            success=False,
            error="Permission denied: read:graph required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select, or_
        from openfinance.datacenter.models.orm import NewsModel
        
        async with async_session_maker() as session:
            query = select(NewsModel)
            
            if source:
                query = query.where(NewsModel.source == source)
            
            if keywords:
                query = query.where(
                    or_(
                        NewsModel.title.ilike(f"%{keywords}%"),
                        NewsModel.content.ilike(f"%{keywords}%"),
                    )
                )
            
            query = query.order_by(NewsModel.published_at.desc()).limit(limit)
            
            result = await session.execute(query)
            news_list = result.scalars().all()
            
            data = [
                {
                    "news_id": str(n.id),
                    "news_code": n.news_id,
                    "title": n.title,
                    "content": n.content[:500] if n.content and len(n.content) > 500 else n.content,
                    "source": n.source,
                    "category": n.category,
                    "keywords": n.keywords if n.keywords else [],
                    "sentiment": float(n.sentiment) if n.sentiment else None,
                    "published_at": n.published_at.isoformat() if n.published_at else None,
                }
                for n in news_list
            ]
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to query news: {e}")
        return APIResponse(
            success=True,
            data=[],
            request_id=request_id,
        )


@router.get("/quant/factors", response_model=APIResponse)
async def get_factor_data(
    factor_ids: list[str] | None = Query(None, description="Factor IDs"),
    codes: list[str] | None = Query(None, description="Stock codes"),
    start_date: str | None = Query(None, description="Start date"),
    end_date: str | None = Query(None, description="End date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get factor data from ADS layer."""
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:quant"):
        return APIResponse(
            success=False,
            error="Permission denied: read:quant required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select
        from openfinance.datacenter.models.orm import FactorDataModel
        
        async with async_session_maker() as session:
            query = select(FactorDataModel)
            
            if factor_ids:
                query = query.where(FactorDataModel.factor_id.in_(factor_ids))
            if codes:
                query = query.where(FactorDataModel.code.in_(codes))
            if start_date:
                query = query.where(FactorDataModel.trade_date >= date.fromisoformat(start_date))
            if end_date:
                query = query.where(FactorDataModel.trade_date <= date.fromisoformat(end_date))
            
            query = query.order_by(FactorDataModel.trade_date.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            result = await session.execute(query)
            factors = result.scalars().all()
            
            data = [
                {
                    "factor_id": f.factor_id,
                    "factor_name": f.factor_name,
                    "factor_category": f.factor_category,
                    "code": f.code,
                    "trade_date": f.trade_date.isoformat() if f.trade_date else None,
                    "factor_value": float(f.factor_value) if f.factor_value else None,
                    "factor_rank": f.factor_rank,
                    "factor_percentile": float(f.factor_percentile) if f.factor_percentile else None,
                }
                for f in factors
            ]
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to fetch factor data: {e}")
        return APIResponse(
            success=True,
            data=[],
            request_id=request_id,
        )


@router.get("/market/kline/{code}", response_model=APIResponse)
async def get_kline_data(
    code: str,
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500, description="Number of records"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get K-Line data from ADS layer.
    
    Stock code format: Supports 6-digit code (000001), Wind format (000001.SZ),
    or Eastmoney format (000001.SZ). All formats are normalized to 6-digit code.
    """
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:market"):
        return APIResponse(
            success=False,
            error="Permission denied: read:market required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select
        from openfinance.datacenter.models.orm import StockDailyQuoteModel
        from openfinance.utils.stock_code import normalize_stock_code
        
        # Normalize stock code
        code = normalize_stock_code(code)
        
        async with async_session_maker() as session:
            query = select(StockDailyQuoteModel).where(StockDailyQuoteModel.code == code)
            
            if start_date:
                query = query.where(StockDailyQuoteModel.trade_date >= date.fromisoformat(start_date))
            if end_date:
                query = query.where(StockDailyQuoteModel.trade_date <= date.fromisoformat(end_date))
            
            query = query.order_by(StockDailyQuoteModel.trade_date.desc()).limit(limit)
            
            result = await session.execute(query)
            klines = result.scalars().all()
            
            data = [
                {
                    "code": k.code,
                    "trade_date": k.trade_date.isoformat() if k.trade_date else None,
                    "open": float(k.open) if k.open else None,
                    "high": float(k.high) if k.high else None,
                    "low": float(k.low) if k.low else None,
                    "close": float(k.close) if k.close else None,
                    "volume": int(k.volume) if k.volume else None,
                    "amount": float(k.amount) if k.amount else None,
                    "turnover_rate": float(k.turnover_rate) if k.turnover_rate else None,
                }
                for k in klines
            ]
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to fetch kline data: {e}")
        return APIResponse(
            success=True,
            data=[],
            request_id=request_id,
        )


@router.get("/market/financial/{code}", response_model=APIResponse)
async def get_financial_data(
    code: str,
    report_date: str | None = Query(None, description="Report date (YYYY-MM-DD)"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get financial indicators from ADS layer.
    
    Stock code format: Supports 6-digit code (000001), Wind format (000001.SZ),
    or Eastmoney format (000001.SZ). All formats are normalized to 6-digit code.
    """
    request_id = _generate_request_id()
    
    if not check_permission(auth, "read:market"):
        return APIResponse(
            success=False,
            error="Permission denied: read:market required",
            error_code="PERMISSION_DENIED",
            request_id=request_id,
        )
    
    try:
        from sqlalchemy import select
        from openfinance.datacenter.models.orm import StockFinancialIndicatorModel
        from openfinance.utils.stock_code import normalize_stock_code
        
        # Normalize stock code
        code = normalize_stock_code(code)
        
        async with async_session_maker() as session:
            query = select(StockFinancialIndicatorModel).where(
                StockFinancialIndicatorModel.code == code
            )
            
            if report_date:
                query = query.where(StockFinancialIndicatorModel.report_date == date.fromisoformat(report_date))
            
            query = query.order_by(StockFinancialIndicatorModel.report_date.desc()).limit(10)
            
            result = await session.execute(query)
            records = result.scalars().all()
            
            data = [
                {
                    "code": r.code,
                    "report_date": r.report_date.isoformat() if r.report_date else None,
                    "eps": float(r.eps) if r.eps else None,
                    "bps": float(r.bps) if r.bps else None,
                    "roe": float(r.roe) if r.roe else None,
                    "roa": float(r.roa) if r.roa else None,
                    "gross_margin": float(r.gross_margin) if r.gross_margin else None,
                    "net_margin": float(r.net_margin) if r.net_margin else None,
                    "debt_ratio": float(r.debt_ratio) if r.debt_ratio else None,
                    "current_ratio": float(r.current_ratio) if r.current_ratio else None,
                    "quick_ratio": float(r.quick_ratio) if r.quick_ratio else None,
                    "revenue": float(r.revenue) if r.revenue else None,
                    "net_profit": float(r.net_profit) if r.net_profit else None,
                    "revenue_yoy": float(r.revenue_yoy) if r.revenue_yoy else None,
                    "net_profit_yoy": float(r.net_profit_yoy) if r.net_profit_yoy else None,
                }
                for r in records
            ]
            
            return APIResponse(
                success=True,
                data=data,
                request_id=request_id,
            )
    except Exception as e:
        logger.error(f"Failed to fetch financial data: {e}")
        return APIResponse(
            success=True,
            data=[],
            request_id=request_id,
        )


@router.get("/health", response_model=APIResponse)
async def health_check() -> APIResponse:
    """Health check endpoint."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    monitor = get_service_monitor()
    
    services_health = []
    for service in registry.list_services():
        health = registry.get_health(service.service_id)
        if health:
            services_health.append({
                "service_id": service.service_id,
                "status": health.status,
                "total_requests": health.total_requests,
                "success_rate": (
                    health.successful_requests / health.total_requests
                    if health.total_requests > 0
                    else 1.0
                ),
            })
    
    return APIResponse(
        success=True,
        data={
            "status": "healthy",
            "services": services_health,
            "alerts_count": len(monitor.get_alerts(severity="critical")),
        },
        request_id=request_id,
    )


@router.get("/docs", response_model=APIResponse)
async def get_api_documentation(
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Get complete API documentation."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    services = registry.list_services()
    
    category_counts: dict[str, int] = {}
    documented_services = []
    
    for service in services:
        category = service.category.value
        category_counts[category] = category_counts.get(category, 0) + 1
        
        endpoints_docs = []
        for endpoint in service.endpoints:
            endpoints_docs.append({
                "path": endpoint.path,
                "method": endpoint.method.value,
                "description": endpoint.description,
                "parameters": endpoint.parameters,
                "response_schema": endpoint.response_schema,
                "requires_auth": endpoint.requires_auth,
                "deprecated": endpoint.deprecated,
                "cache_ttl_seconds": endpoint.cache_ttl_seconds,
            })
        
        documented_services.append({
            "service_id": service.service_id,
            "name": service.name,
            "description": service.description,
            "category": service.category.value,
            "version": service.version,
            "status": service.status.value,
            "endpoints": endpoints_docs,
            "tags": service.tags,
            "rate_limit": {
                "requests_per_minute": service.rate_limit.requests_per_minute,
                "requests_per_hour": service.rate_limit.requests_per_hour,
            },
        })
    
    categories = [
        {"id": cat, "name": _get_category_name(cat), "count": count}
        for cat, count in category_counts.items()
    ]
    
    return APIResponse(
        success=True,
        data={
            "services": documented_services,
            "total": len(documented_services),
            "categories": categories,
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
        },
        request_id=request_id,
    )


def _get_category_name(category: str) -> str:
    """Get display name for a category."""
    names = {
        "analysis": "智能分析",
        "graph": "知识图谱",
        "quant": "量化分析",
        "market": "市场数据",
        "fundamental": "基本面数据",
        "alternative": "另类数据",
    }
    return names.get(category, category)


@router.get("/search", response_model=APIResponse)
async def search_endpoints(
    q: str = Query(..., description="Search query"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """Search endpoints by query."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    services = registry.list_services()
    
    results = []
    query_lower = q.lower()
    
    for service in services:
        for endpoint in service.endpoints:
            if (
                query_lower in endpoint.path.lower()
                or query_lower in endpoint.description.lower()
                or query_lower in service.name.lower()
                or any(query_lower in tag.lower() for tag in service.tags)
            ):
                results.append({
                    "service": {
                        "service_id": service.service_id,
                        "name": service.name,
                        "category": service.category.value,
                    },
                    "endpoint": {
                        "path": endpoint.path,
                        "method": endpoint.method.value,
                        "description": endpoint.description,
                    },
                })
    
    return APIResponse(
        success=True,
        data={
            "results": results[:50],
            "total": len(results),
        },
        request_id=request_id,
    )


@router.get("/marketplace/services", response_model=APIResponse)
async def marketplace_list_services(
    category: str | None = Query(None, description="Service category"),
    auth: AuthContext = Depends(authenticate_request),
) -> APIResponse:
    """List services in the marketplace."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    services = registry.list_services()
    
    result = []
    for s in services:
        health = registry.get_health(s.service_id)
        result.append({
            "service_id": s.service_id,
            "name": s.name,
            "description": s.description,
            "category": s.category.value,
            "status": s.status.value,
            "pricing_model": s.pricing_model.value,
            "health": {
                "status": health.status if health else "unknown",
                "success_rate": (
                    health.successful_requests / health.total_requests
                    if health and health.total_requests > 0
                    else 1.0
                ),
            } if health else None,
        })
    
    if category:
        result = [s for s in result if s["category"] == category]
    
    return APIResponse(
        success=True,
        data=result,
        request_id=request_id,
    )


@router.post("/marketplace/subscribe/{service_id}", response_model=APIResponse)
async def subscribe_service(
    service_id: str,
    auth: AuthContext = Depends(get_current_user),
) -> APIResponse:
    """Subscribe to a service."""
    request_id = _generate_request_id()
    
    await ensure_registry_initialized()
    registry = get_service_registry()
    subscription = registry.create_subscription(
        service_id=service_id,
        user_id=auth.user_id or "anonymous",
    )
    
    if not subscription:
        return APIResponse(
            success=False,
            error=f"Failed to subscribe to service {service_id}",
            error_code="SUBSCRIPTION_FAILED",
            request_id=request_id,
        )
    
    return APIResponse(
        success=True,
        data={
            "subscription_id": subscription.subscription_id,
            "service_id": subscription.service_id,
            "plan": subscription.plan.value,
            "status": subscription.status.value,
            "quota": {
                "max_requests": subscription.quota.max_requests,
                "max_concurrent": subscription.quota.max_concurrent,
            },
        },
        request_id=request_id,
    )


@router.get("/marketplace/usage", response_model=APIResponse)
async def get_usage_stats(
    service_id: str | None = Query(None, description="Service ID"),
    auth: AuthContext = Depends(get_current_user),
) -> APIResponse:
    """Get usage statistics."""
    request_id = _generate_request_id()
    
    gateway = get_data_gateway()
    stats = gateway.get_usage_stats(
        service_id=service_id,
        user_id=auth.user_id,
    )
    
    return APIResponse(
        success=True,
        data=stats,
        request_id=request_id,
    )
