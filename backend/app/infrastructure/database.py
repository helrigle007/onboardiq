from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    global engine, async_session_factory
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False, pool_size=5)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def close_db() -> None:
    global engine
    if engine:
        await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    assert async_session_factory is not None, "Database not initialized. Call init_db() first."
    async with async_session_factory() as session:
        yield session
