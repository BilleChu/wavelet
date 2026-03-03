"""
Economic Calendar API Routes.

Provides endpoints for fetching and managing economic calendar events.
Uses the project's TaskExecutor pattern for high cohesion.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
from openfinance.datacenter.task.calendar_executors import register_calendar_executors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar", tags=["economic_calendar"])

register_calendar_executors()


class CalendarEvent(BaseModel):
    """Single calendar event."""
    
    event_id: str
    date: str
    time: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    importance: str = "low"
    event: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    source: str = "investing.com"


class CalendarResponse(BaseModel):
    """Response for calendar events."""
    
    total: int
    past_events: list[dict]
    future_events: list[dict]
    source: str
    fetched_at: str


_calendar_cache: dict = {}
_cache_time: Optional[datetime] = None
CACHE_TTL_MINUTES = 30


async def _execute_calendar_task(
    past_days: int = 7,
    future_days: int = 30,
    countries: Optional[list[str]] = None,
    importances: Optional[list[str]] = None,
    strategy: str = "auto",
) -> dict:
    """Execute calendar collection task using the registered executor."""
    executor = TaskRegistry.get_executor("economic_calendar")
    
    if not executor:
        raise RuntimeError("Economic calendar executor not registered")
    
    progress = TaskProgress(task_id=f"calendar_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    params = {
        "past_days": past_days,
        "future_days": future_days,
        "countries": countries,
        "importances": importances,
        "strategy": strategy,
    }
    
    result = await executor.execute(params, progress)
    
    return {
        "success": result.get("success", False),
        "records_saved": result.get("records_saved", 0),
        "errors": result.get("error"),
    }


async def _get_events_from_db(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    countries: Optional[list[str]] = None,
    importances: Optional[list[str]] = None,
    limit: int = 500
) -> list[dict]:
    """Get events from database using persistence layer."""
    from openfinance.datacenter.persistence import persistence
    from sqlalchemy import text
    
    try:
        conditions = []
        params = {}
        
        if start_date:
            conditions.append("event_date >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            conditions.append("event_date <= :end_date")
            params["end_date"] = end_date
        
        if countries:
            conditions.append("(country = ANY(:countries) OR currency = ANY(:countries))")
            params["countries"] = [c.upper() for c in countries]
        
        if importances:
            conditions.append("importance = ANY(:importances)")
            params["importances"] = importances
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        async with persistence.session_maker() as session:
            query = text(f"""
                SELECT event_id, event_date, event_time, country, currency, importance,
                       event_name, actual, forecast, previous, source
                FROM openfinance.economic_calendar_events
                WHERE {where_clause}
                ORDER BY event_date, event_time
                LIMIT :limit
            """)
            params["limit"] = limit
            
            result = await session.execute(query, params)
            rows = result.fetchall()
            
            events = []
            for row in rows:
                events.append({
                    "event_id": row[0],
                    "date": str(row[1]),
                    "time": row[2],
                    "country": row[3],
                    "currency": row[4],
                    "importance": row[5],
                    "event": row[6],
                    "actual": row[7],
                    "forecast": row[8],
                    "previous": row[9],
                    "source": row[10],
                })
            
            return events
            
    except Exception as e:
        logger.error(f"Database query error: {e}")
        return []


@router.get("/events")
async def get_calendar_events(
    countries: Optional[str] = Query(None, description="Comma-separated country list"),
    importances: Optional[str] = Query(None, description="Comma-separated importance levels"),
    past_days: int = Query(7, ge=0, le=365, description="Days to look back"),
    future_days: int = Query(30, ge=0, le=365, description="Days to look forward"),
    use_cache: bool = Query(True, description="Use cached data if available"),
    source: str = Query("db", description="Data source: 'db' or 'scraper'"),
):
    """
    Get economic calendar events.
    
    - source='db': Query from database (fast, may not have latest)
    - source='scraper': Fetch from Investing.com (slower, fresh data)
    """
    global _calendar_cache, _cache_time
    
    country_list = [c.strip() for c in countries.split(',')] if countries else None
    importance_list = [i.strip() for i in importances.split(',')] if importances else None
    
    today = date.today()
    start_date = today - timedelta(days=past_days)
    end_date = today + timedelta(days=future_days)
    
    if source == "db":
        events = await _get_events_from_db(
            start_date=start_date,
            end_date=end_date,
            countries=country_list,
            importances=importance_list
        )
        
        past_events = [e for e in events if e['date'] < str(today)]
        future_events = [e for e in events if e['date'] >= str(today)]
        
        return {
            "total": len(events),
            "past_events": past_events,
            "future_events": future_events,
            "source": "database",
            "fetched_at": datetime.now().isoformat(),
        }
    
    cache_key = f"{countries}_{importances}_{past_days}_{future_days}"
    
    if use_cache and _calendar_cache.get(cache_key) and _cache_time:
        if datetime.now() - _cache_time < timedelta(minutes=CACHE_TTL_MINUTES):
            logger.info("Returning cached calendar data")
            return _calendar_cache[cache_key]
    
    try:
        result = await _execute_calendar_task(
            past_days=past_days,
            future_days=future_days,
            countries=country_list,
            importances=importance_list,
        )
        
        events = await _get_events_from_db(
            start_date=start_date,
            end_date=end_date,
            countries=country_list,
            importances=importance_list
        )
        
        past_events = [e for e in events if e['date'] < str(today)]
        future_events = [e for e in events if e['date'] >= str(today)]
        
        response = {
            "total": len(events),
            "past_events": past_events,
            "future_events": future_events,
            "source": "scraper",
            "fetched_at": datetime.now().isoformat(),
            "records_saved": result.get("records_saved", 0),
        }
        
        _calendar_cache[cache_key] = response
        _cache_time = datetime.now()
        
        return response
        
    except Exception as e:
        logger.exception(f"Failed to fetch calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/today")
async def get_today_events(
    countries: Optional[str] = Query(None, description="Comma-separated country list"),
    importances: Optional[str] = Query(None, description="Comma-separated importance levels"),
):
    """Get today's economic calendar events."""
    country_list = [c.strip() for c in countries.split(',')] if countries else None
    importance_list = [i.strip() for i in importances.split(',')] if importances else None
    
    today = date.today()
    
    events = await _get_events_from_db(
        start_date=today,
        end_date=today,
        countries=country_list,
        importances=importance_list
    )
    
    return {
        "date": str(today),
        "total": len(events),
        "events": events,
        "source": "database",
        "fetched_at": datetime.now().isoformat(),
    }


@router.get("/events/important")
async def get_important_events(
    days: int = Query(7, ge=1, le=30, description="Days to look ahead"),
):
    """Get high-importance economic events for the next N days."""
    today = date.today()
    end_date = today + timedelta(days=days)
    
    events = await _get_events_from_db(
        start_date=today,
        end_date=end_date,
        importances=['high']
    )
    
    return {
        "period": f"Next {days} days",
        "total": len(events),
        "events": events,
        "source": "database",
        "fetched_at": datetime.now().isoformat(),
    }


@router.get("/events/date/{event_date}")
async def get_events_by_date(
    event_date: str,
    countries: Optional[str] = Query(None, description="Comma-separated country list"),
    importances: Optional[str] = Query(None, description="Comma-separated importance levels"),
):
    """Get events for a specific date (YYYY-MM-DD format)."""
    try:
        target_date = datetime.strptime(event_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    country_list = [c.strip() for c in countries.split(',')] if countries else None
    importance_list = [i.strip() for i in importances.split(',')] if importances else None
    
    events = await _get_events_from_db(
        start_date=target_date,
        end_date=target_date,
        countries=country_list,
        importances=importance_list
    )
    
    return {
        "date": event_date,
        "total": len(events),
        "events": events,
        "fetched_at": datetime.now().isoformat(),
    }


@router.get("/events/range")
async def get_events_by_range(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    countries: Optional[str] = Query(None, description="Comma-separated country list"),
    importances: Optional[str] = Query(None, description="Comma-separated importance levels"),
):
    """Get events within a date range."""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    country_list = [c.strip() for c in countries.split(',')] if countries else None
    importance_list = [i.strip() for i in importances.split(',')] if importances else None
    
    events = await _get_events_from_db(
        start_date=start,
        end_date=end,
        countries=country_list,
        importances=importance_list
    )
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total": len(events),
        "events": events,
        "fetched_at": datetime.now().isoformat(),
    }


@router.post("/fetch")
async def fetch_and_save_events(
    background_tasks: BackgroundTasks,
    past_days: int = Query(7, ge=0, le=365, description="Days to look back"),
    future_days: int = Query(30, ge=0, le=365, description="Days to look forward"),
    countries: Optional[str] = Query(None, description="Comma-separated country list"),
    importances: Optional[str] = Query(None, description="Comma-separated importance levels"),
):
    """Fetch events from source and save to database (background task)."""
    country_list = [c.strip() for c in countries.split(',')] if countries else None
    importance_list = [i.strip() for i in importances.split(',')] if importances else None
    
    async def fetch_task():
        await _execute_calendar_task(
            past_days=past_days,
            future_days=future_days,
            countries=country_list,
            importances=importance_list,
        )
    
    background_tasks.add_task(fetch_task)
    
    return {
        "message": "Fetch task started in background",
        "date_range": {
            "from": str(date.today() - timedelta(days=past_days)),
            "to": str(date.today() + timedelta(days=future_days))
        }
    }


@router.get("/countries")
async def get_available_countries():
    """Get list of available countries for filtering."""
    return {
        "countries": [
            {"code": "united states", "name": "美国", "currency": "USD"},
            {"code": "china", "name": "中国", "currency": "CNY"},
            {"code": "euro zone", "name": "欧元区", "currency": "EUR"},
            {"code": "japan", "name": "日本", "currency": "JPY"},
            {"code": "united kingdom", "name": "英国", "currency": "GBP"},
            {"code": "germany", "name": "德国", "currency": "EUR"},
            {"code": "france", "name": "法国", "currency": "EUR"},
            {"code": "australia", "name": "澳大利亚", "currency": "AUD"},
            {"code": "canada", "name": "加拿大", "currency": "CAD"},
            {"code": "new zealand", "name": "新西兰", "currency": "NZD"},
            {"code": "switzerland", "name": "瑞士", "currency": "CHF"},
            {"code": "india", "name": "印度", "currency": "INR"},
            {"code": "brazil", "name": "巴西", "currency": "BRL"},
            {"code": "russia", "name": "俄罗斯", "currency": "RUB"},
            {"code": "south korea", "name": "韩国", "currency": "KRW"},
        ]
    }


@router.get("/importance-levels")
async def get_importance_levels():
    """Get list of importance levels."""
    return {
        "levels": [
            {"code": "high", "name": "高", "description": "通常对市场影响较大", "emoji": "🔴"},
            {"code": "medium", "name": "中", "description": "中等市场影响", "emoji": "🟡"},
            {"code": "low", "name": "低", "description": "较小市场影响", "emoji": "🟢"},
        ]
    }


@router.post("/refresh-cache")
async def refresh_cache():
    """Clear the calendar cache and force fresh data fetch."""
    global _calendar_cache, _cache_time
    
    _calendar_cache = {}
    _cache_time = None
    
    return {"message": "Cache cleared successfully"}


@router.get("/stats")
async def get_calendar_stats():
    """Get statistics about stored calendar events."""
    from openfinance.datacenter.persistence import persistence
    from sqlalchemy import text
    
    try:
        async with persistence.session_maker() as session:
            total = await session.execute(
                text("SELECT COUNT(*) FROM openfinance.economic_calendar_events")
            )
            total_count = total.scalar() or 0
            
            by_importance = await session.execute(text("""
                SELECT importance, COUNT(*) as count
                FROM openfinance.economic_calendar_events
                GROUP BY importance
            """))
            importance_rows = by_importance.fetchall()
            
            by_country = await session.execute(text("""
                SELECT country, COUNT(*) as count
                FROM openfinance.economic_calendar_events
                GROUP BY country
                ORDER BY count DESC
                LIMIT 10
            """))
            country_rows = by_country.fetchall()
            
            date_range = await session.execute(text("""
                SELECT MIN(event_date) as min_date, MAX(event_date) as max_date
                FROM openfinance.economic_calendar_events
            """))
            date_row = date_range.fetchone()
            
            return {
                "total_events": total_count,
                "by_importance": {row[0]: row[1] for row in importance_rows},
                "by_country": {row[0]: row[1] for row in country_rows},
                "date_range": {
                    "start": str(date_row[0]) if date_row[0] else None,
                    "end": str(date_row[1]) if date_row[1] else None,
                },
                "fetched_at": datetime.now().isoformat(),
            }
            
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {
            "total_events": 0,
            "error": str(e),
        }


@router.get("/tasks")
async def get_calendar_tasks():
    """Get registered calendar task types."""
    from openfinance.datacenter.task.registry import get_task_info
    
    tasks = []
    for task_type in ["economic_calendar", "economic_calendar_important", "economic_calendar_daily"]:
        info = get_task_info(task_type)
        if info:
            tasks.append(info)
    
    return {
        "tasks": tasks,
        "total": len(tasks),
    }
