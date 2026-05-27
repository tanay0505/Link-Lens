import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.database import Base, get_db
from app.dependencies import get_redis

TEST_DATABASE_URL = "postgresql+asyncpg://urluser:urlpass@localhost:5432/urlshortener_test"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Fresh engine per test with NullPool — fixes "attached to different loop"
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
def mock_redis():
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.aclose = AsyncMock(return_value=None)
    pipeline_mock = MagicMock()
    pipeline_mock.incr = AsyncMock(return_value=None)
    pipeline_mock.expire = AsyncMock(return_value=None)
    pipeline_mock.execute = AsyncMock(return_value=[1, True])
    mock.pipeline = MagicMock(return_value=pipeline_mock)
    return mock


@pytest_asyncio.fixture(scope="function")
async def client(db_session, mock_redis):
    async def override_get_db():
        yield db_session

    def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={
        "email": "testuser@test.com",
        "password": "testpass123"
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "testuser@test.com",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}