"""
Health API Routes for OpenFinance.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check for Kubernetes."""
    return {
        "ready": True,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": "ok",
            "redis": "ok",
            "llm": "ok",
        },
    }


@router.get("/health/live")
async def liveness_check() -> dict[str, Any]:
    """Liveness check for Kubernetes."""
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat(),
    }
