"""
Quantitative Analysis API for OpenFinance.

Modular, high-performance API providing:
- Factor management and analysis
- Strategy construction and optimization  
- Backtesting with professional metrics
- Risk analytics and attribution
"""

from datetime import datetime
import logging

from fastapi import APIRouter

from openfinance.quant.api.routes.factors import router as factors_router
from openfinance.quant.api.routes.analytics import router as analytics_router
from openfinance.quant.api.routes.strategies import router as strategies_router
from openfinance.quant.api.routes.factor_creator import router as factor_creator_router
from openfinance.quant.api.routes.strategy_creator import router as strategy_creator_router
from openfinance.quant.factors.registry import get_factor_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quant", tags=["quant"])


@router.get("/health")
async def health_check():
    """Health check endpoint for quantitative analysis module."""
    try:
        registry = get_factor_registry()
        stats = registry.get_statistics()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "factors_available": stats["total_factors"],
            "builtin_factors": stats["builtin_factors"],
            "custom_factors": stats["custom_factors"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# Include modular routers
router.include_router(factors_router)
router.include_router(analytics_router)
router.include_router(strategies_router)
router.include_router(factor_creator_router)
router.include_router(strategy_creator_router)
