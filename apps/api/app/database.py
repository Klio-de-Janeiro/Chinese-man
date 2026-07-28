from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

from .settings import get_settings


def create_database_engine() -> AsyncEngine:
    """Create the shared asynchronous PostgreSQL engine."""

    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
    )


database_engine = create_database_engine()


async def database_is_ready() -> bool:
    """Check that PostgreSQL accepts a simple query."""

    async with database_engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return True
