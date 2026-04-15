"""Database configuration and session management for Digital Literacy Bridge."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import get_dlb_settings

# Base class for all ORM models
Base = declarative_base()


def get_engine() -> AsyncEngine:
    """
    Get the async database engine.

    Uses aiosqlite by default for async SQLite operations.
    Engine is created fresh on each call (SQLite has issues with sharing).
    """
    settings = get_dlb_settings()
    return create_async_engine(
        settings.dlb_database_url,
        echo=settings.dlb_echo_sql,
    )


def get_session_factory():
    """
    Get a session factory bound to the current engine.

    Returns:
        sessionmaker configured for async operations with AsyncSession.
    """
    engine = get_engine()
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a database session.

    The session is automatically rolled back at the end of the request
    unless explicitly committed, ensuring no partial transactions persist.

    Yields:
        AsyncSession: A database session for the request lifecycle.
    """
    async_session = get_session_factory()
    async with async_session() as session:
        yield session
        await session.rollback()


async def create_tables() -> None:
    """
    Create all database tables.

    This uses Base.metadata.create_all() which is suitable for development.
    For production migrations, consider using Alembic.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
