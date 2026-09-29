"""Async SQLAlchemy engine and session factory.

Provides `get_db` — an async generator used as a FastAPI dependency
to inject a session-per-request.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite) drivers
based on the DATABASE_URL setting.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# SQLite needs connect_args for thread-safety in async mode.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    # pool_size and max_overflow are not supported by SQLite
    **({} if settings.DATABASE_URL.startswith("sqlite") else {"pool_size": 20, "max_overflow": 10, "pool_pre_ping": True}),
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a scoped async session, commit on success, rollback on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
