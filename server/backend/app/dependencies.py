from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.logger import get_logger
from app.settings import settings

log = get_logger()
test_engine: AsyncEngine | None = None
TestAsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


async def get_db():
    if settings.testing and settings.testing.testing:
        async for session in _get_db_testing():
            yield session
    else:
        async for session in _get_db():
            yield session


async def _get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session


async def _get_db_testing() -> AsyncGenerator[AsyncSession, None]:
    global TestAsyncSessionLocal
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Creates DB tables for the testing database"""
    global test_engine, TestAsyncSessionLocal
    if test_engine is None and TestAsyncSessionLocal is None:
        test_engine = create_async_engine(
            settings.database.url,
            echo=settings.database.echo,
            future=True,
            pool_size=settings.database.pool_size,
            pool_timeout=settings.database.pool_timeout,
        )
        TestAsyncSessionLocal = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            log.debug("DB tables created")


async def cleanup_db() -> None:
    """Drops all DB tables from the testing database"""
    if test_engine and TestAsyncSessionLocal:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            log.debug("DB tables dropped")
