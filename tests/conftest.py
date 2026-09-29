"""Shared pytest fixtures for the test suite.

Sets up:
- An in-process SQLite async database (no Postgres needed for tests)
- Override of the FastAPI `get_db` dependency to use the test DB
- A mock Redis client (fakeredis) so tests don't need a running Redis
- An async httpx client pointed at the test app
- Helper functions to create test users and obtain JWT tokens
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Base
from app.models.user import User, UserRole

# ── Test database (SQLite async via aiosqlite) ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db





@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables before tests and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def create_test_user(
    db: AsyncSession, email: str = "test@example.com", role: UserRole = UserRole.USER
) -> User:
    """Insert a test user directly into the DB."""
    user = User(
        name="Test User",
        email=email,
        password_hash=hash_password("password123"),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def get_auth_headers(user_id: int, role: str = "user") -> dict[str, str]:
    """Generate Authorization headers with a valid JWT for the given user."""
    token = create_access_token(data={"sub": str(user_id), "role": role})
    return {"Authorization": f"Bearer {token}"}
