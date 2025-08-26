import sys
from pathlib import Path

import httpx
from httpx_ws.transport import ASGIWebSocketTransport

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.dependencies import get_db
from app.main import app

# Load the environment variables first
print(f"{os.path.dirname(os.path.abspath(__file__))}/.env.test")
load_dotenv(f"{os.path.dirname(os.path.abspath(__file__))}/.env.test", verbose=True)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

test_engine = create_async_engine(TEST_DATABASE_URL)
TestAsyncSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def ws_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGIWebSocketTransport(app=app)

    # Create the client without entering the async context manager here
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    try:
        yield client
    finally:
        # Clean up the client properly
        await client.aclose()
        app.dependency_overrides.clear()
