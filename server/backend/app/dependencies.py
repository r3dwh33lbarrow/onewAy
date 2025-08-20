from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine

from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.logger import get_logger
from app.settings import settings

log = get_logger()
test_engine: AsyncEngine | None = None
TestAsyncSessionLocal: AsyncSession | None = None


async def get_db():
    if settings.testing:
        async for session in _get_db_testing():
            yield session
    else:
        async for session in _get_db():
            yield session


async def _get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session


async def _get_db_testing() -> AsyncGenerator[AsyncSession, None]:
    global test_engine, TestAsyncSessionLocal
    if test_engine is None and TestAsyncSessionLocal is None:
        test_engine = create_async_engine(settings.database_url)
        TestAsyncSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        log.debug("DB tables created")

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def cleanup_db() -> None:
    if test_engine and TestAsyncSessionLocal:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            log.debug("DB tables dropped")
