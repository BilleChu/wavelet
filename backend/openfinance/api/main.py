"""
FastAPI Application for OpenFinance.

Main application factory and configuration.
"""

from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from openfinance.api.routes.analysis import router as analysis_router
from openfinance.api.routes.chat import router as chat_router
from openfinance.api.routes.datacenter import router as datacenter_router
from openfinance.api.routes.datacenter_extended import router as datacenter_extended_router
from openfinance.api.routes.dataservice import router as dataservice_router
from openfinance.api.routes.graph import router as graph_router
from openfinance.api.routes.health import router as health_router
from openfinance.api.routes.intent import router as intent_router
from openfinance.api.routes.skills import router as skills_router
from openfinance.api.routes.metadata import router as metadata_router
from openfinance.api.routes.pipeline import router as pipeline_router
from openfinance.api.websocket import router as websocket_router
from openfinance.quant.api import router as quant_router
from openfinance.infrastructure.logging.logging_config import get_logger, setup_logging
from openfinance.domain.metadata import initialize_registries

setup_logging()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting OpenFinance API server...")
    
    initialize_registries()
    logger.info("Metadata registries initialized")
    
    yield
    
    logger.info("Shutting down OpenFinance API server...")


def create_app(
    title: str = "OpenFinance API",
    version: str = "1.0.0",
    description: str = "Intelligent Financial Analysis Platform API",
    **kwargs: Any,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=title,
        version=version,
        description=description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        **kwargs,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def ensure_utf8_encoding(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Type", "application/json; charset=utf-8")
        return response

    app.include_router(health_router, prefix="/api", tags=["Health"])
    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(intent_router, prefix="/api", tags=["Intent"])
    app.include_router(skills_router, prefix="/api", tags=["Skills"])
    app.include_router(quant_router, prefix="/api", tags=["Quant"])
    app.include_router(graph_router, prefix="/api", tags=["Graph"])
    app.include_router(analysis_router, prefix="/api", tags=["Analysis"])
    app.include_router(datacenter_router, prefix="/api", tags=["DataCenter"])
    app.include_router(datacenter_extended_router, prefix="/api", tags=["DataCenter Extended"])
    app.include_router(dataservice_router, prefix="/api", tags=["DataService"])
    app.include_router(metadata_router, prefix="/api", tags=["Metadata"])
    app.include_router(pipeline_router, prefix="/api", tags=["Pipeline"])
    app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": str(exc),
            },
        )

    @app.get("/")
    async def root():
        return {
            "name": "OpenFinance API",
            "version": version,
            "status": "running",
            "docs": "/docs",
        }

    return app


app = create_app()
