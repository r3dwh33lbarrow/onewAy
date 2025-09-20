import asyncio
import shutil
import sys
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from httpx_ws.transport import ASGIWebSocketTransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import Base
from app.dependencies import get_db
from app.main import app
from app.settings import settings

BACKUP_SUFFIX = "_backup"

if settings.testing.database.url is None:
    raise RuntimeError("Testing database URL is not set.")

if settings.testing.security.secret_key is None:
    raise RuntimeError("Testing secret key is not set.")

settings.testing.testing = True
settings = settings.inject_testing()


test_engine = create_async_engine(
            settings.database.url,
            echo=settings.database.echo,
            future=True,
            pool_size=settings.database.pool_size,
            pool_timeout=settings.database.pool_timeout
)
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

    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    try:
        yield client
    finally:
        await client.aclose()
        app.dependency_overrides.clear()


@pytest.fixture(scope="session", autouse=True)
def copy_and_restore_module_dir():
    module_dir = Path(settings.paths.module_dir)
    backup_dir = Path(str(module_dir) + BACKUP_SUFFIX)

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(module_dir, backup_dir)

    yield

    if module_dir.exists():
        shutil.rmtree(module_dir)
    shutil.copytree(backup_dir, module_dir)
    shutil.rmtree(backup_dir, ignore_errors=True)