from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.database.echo,
    future=True,
    pool_size=settings.database.pool_size,
    pool_timeout=settings.database.pool_timeout,
)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
)
