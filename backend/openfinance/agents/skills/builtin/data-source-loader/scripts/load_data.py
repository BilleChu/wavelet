"""
Data Source Loader Scripts.

Provides functions for loading and managing data sources.
"""

import asyncio
import json
from typing import Any

from openfinance.infrastructure.logging.logging_config import get_logger

logger = get_logger(__name__)


async def list_sources() -> dict[str, Any]:
    """List all available data sources.
    
    Returns:
        Dictionary containing source list and metadata.
    """
    from openfinance.domain.metadata.loader import MetadataLoader
    
    loader = MetadataLoader()
    sources = loader.load_data_sources()
    
    return {
        "sources": [
            {
                "name": s.get("name"),
                "display_name": s.get("display_name"),
                "category": s.get("category"),
                "source_type": s.get("source_type"),
                "endpoint": s.get("endpoint"),
                "data_types": s.get("data_types", []),
            }
            for s in sources
        ],
        "total": len(sources),
    }


async def get_source_detail(source_name: str) -> dict[str, Any] | None:
    """Get detailed information about a specific data source.
    
    Args:
        source_name: Name of the data source.
        
    Returns:
        Source details or None if not found.
    """
    from openfinance.domain.metadata.loader import MetadataLoader
    
    loader = MetadataLoader()
    sources = loader.load_data_sources()
    
    for source in sources:
        if source.get("name") == source_name:
            return {
                "name": source.get("name"),
                "display_name": source.get("display_name"),
                "category": source.get("category"),
                "source_type": source.get("source_type"),
                "endpoint": source.get("endpoint"),
                "rate_limit": source.get("rate_limit"),
                "timeout_ms": source.get("timeout_ms"),
                "data_types": source.get("data_types", []),
                "auth_type": source.get("auth_type"),
                "description": source.get("description"),
            }
    
    return None


async def test_source_connection(source_name: str) -> dict[str, Any]:
    """Test connection to a data source.
    
    Args:
        source_name: Name of the data source.
        
    Returns:
        Connection test result.
    """
    import time
    
    source = await get_source_detail(source_name)
    
    if not source:
        return {
            "success": False,
            "error": f"Source '{source_name}' not found",
        }
    
    source_type = source.get("source_type")
    endpoint = source.get("endpoint", "")
    
    start_time = time.time()
    
    try:
        if source_type == "api":
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, follow_redirects=True)
                latency_ms = (time.time() - start_time) * 1000
                return {
                    "success": response.status_code < 500,
                    "latency_ms": round(latency_ms, 2),
                    "status_code": response.status_code,
                    "message": "Connection successful" if response.status_code < 500 else f"HTTP {response.status_code}",
                }
        elif source_type == "database":
            from openfinance.infrastructure.database.database import async_session_maker
            async with async_session_maker() as session:
                await session.execute("SELECT 1")
                latency_ms = (time.time() - start_time) * 1000
                return {
                    "success": True,
                    "latency_ms": round(latency_ms, 2),
                    "message": "Database connection successful",
                }
        elif source_type == "cache":
            import redis.asyncio as redis
            from openfinance.infrastructure.config.config import get_config
            config = get_config()
            redis_url = config.database.redis_url
            client = redis.from_url(redis_url)
            await client.ping()
            latency_ms = (time.time() - start_time) * 1000
            return {
                "success": True,
                "latency_ms": round(latency_ms, 2),
                "message": "Redis connection successful",
            }
        else:
            return {
                "success": True,
                "latency_ms": 0,
                "message": f"Source type '{source_type}' does not require connection test",
            }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "latency_ms": round(latency_ms, 2),
            "error": str(e),
            "message": f"Connection failed: {str(e)}",
        }


async def load_data(
    source_name: str,
    data_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Load data from a specific source.
    
    Args:
        source_name: Name of the data source.
        data_type: Type of data to load.
        params: Parameters for data loading.
        
    Returns:
        Loaded data and metadata.
    """
    import time
    
    source = await get_source_detail(source_name)
    
    if not source:
        return {
            "success": False,
            "error": f"Source '{source_name}' not found",
        }
    
    if data_type not in source.get("data_types", []):
        return {
            "success": False,
            "error": f"Data type '{data_type}' not supported by source '{source_name}'",
            "supported_types": source.get("data_types", []),
        }
    
    start_time = time.time()
    
    try:
        if source_name == "postgres_local" or source.get("source_type") == "database":
            result = await _load_from_database(data_type, params)
        elif source.get("source_type") == "api":
            result = await _load_from_api(source, data_type, params)
        else:
            result = {"data": [], "message": "Source type not implemented"}
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "source": source_name,
            "data_type": data_type,
            "latency_ms": round(latency_ms, 2),
            "record_count": len(result.get("data", [])),
            **result,
        }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "success": False,
            "source": source_name,
            "data_type": data_type,
            "latency_ms": round(latency_ms, 2),
            "error": str(e),
        }


async def _load_from_database(data_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Load data from local database.
    
    Args:
        data_type: Type of data to load.
        params: Query parameters.
        
    Returns:
        Query result.
    """
    from sqlalchemy import select
    from openfinance.datacenter.models.orm import StockBasicModel, StockDailyQuoteModel
    from openfinance.infrastructure.database.database import async_session_maker
    
    async with async_session_maker() as session:
        if data_type == "stock_quote":
            code = params.get("code", "").replace(".SH", "").replace(".SZ", "")
            query = select(StockDailyQuoteModel).where(
                StockDailyQuoteModel.code == code
            ).limit(params.get("limit", 100))
            result = await session.execute(query)
            records = result.scalars().all()
            return {
                "data": [
                    {
                        "code": r.code,
                        "trade_date": str(r.trade_date),
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                        "amount": r.amount,
                    }
                    for r in records
                ]
            }
        elif data_type == "stock_basic":
            query = select(StockBasicModel).limit(params.get("limit", 100))
            result = await session.execute(query)
            records = result.scalars().all()
            return {
                "data": [
                    {
                        "code": r.code,
                        "name": r.name,
                        "industry": getattr(r, "industry", None),
                        "market": getattr(r, "market", None),
                    }
                    for r in records
                ]
            }
        else:
            return {"data": [], "message": f"Data type '{data_type}' not implemented"}


async def _load_from_api(source: dict[str, Any], data_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Load data from external API.
    
    Args:
        source: Source configuration.
        data_type: Type of data to load.
        params: Query parameters.
        
    Returns:
        API response.
    """
    import httpx
    
    endpoint = source.get("endpoint", "")
    timeout = source.get("timeout_ms", 10000) / 1000
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(endpoint, params=params)
            if response.status_code == 200:
                return {"data": response.json(), "raw": True}
            else:
                return {"data": [], "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"data": [], "error": str(e)}
