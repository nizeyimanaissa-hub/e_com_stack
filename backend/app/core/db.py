import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# Tests give each async test its own event loop (see tests/conftest.py),
# and pooled asyncpg connections can't be reused across event loops --
# NullPool opens a fresh connection per checkout instead of fighting
# pytest-asyncio's loop management to keep one pooled connection alive.
_engine_kwargs = {"poolclass": NullPool} if os.environ.get("TESTING") else {}
engine = create_async_engine(settings.database_url, echo=False, **_engine_kwargs)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
