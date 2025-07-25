from typing import AsyncGenerator
from app.db.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator:
    """
    Dependency function to provide a database session.

    This function is an asynchronous generator that yields a database session
    from the `AsyncSessionLocal` context. It ensures proper cleanup of the
    session after use by leveraging Python's `async with` statement.

    Yields:
        AsyncGenerator: An asynchronous database session.
    """
    async with AsyncSessionLocal() as session:
        yield session
