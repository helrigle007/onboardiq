from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings

engine = None
async_session_factory = None


async def init_db():
    global engine, async_session_factory
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False, pool_size=5)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def close_db():
    global engine
    if engine:
        await engine.dispose()


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
