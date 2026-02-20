"""
Database configuration and session management for OpenFinance.
"""

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from openfinance.domain.models.base import MetaData

import os

logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://openfinance:openfinance@{DB_HOST}:5432/openfinance?client_encoding=utf8"
)

if DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = None
async_session_maker = None
_db_available = False

try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    _db_available = True
except Exception as e:
    logger.warning(f"Database engine creation failed: {e}")


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Get database session."""
    if not async_session_maker:
        yield None
        return
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            yield None
        finally:
            await session.close()


def is_db_available() -> bool:
    """Check if database is available."""
    return _db_available
