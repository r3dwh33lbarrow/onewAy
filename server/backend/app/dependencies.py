from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.settings import settings


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
    test_engine = create_async_engine(settings.database_url)
    TestAsyncSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
