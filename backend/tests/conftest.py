import asyncio
import os

# Force test isolation regardless of what the container's own environment
# already sets (docker-compose sets DATABASE_URL/REDIS_URL to the real dev
# values) -- these must be overridden before anything under app.core is
# imported, since Settings/engine/redis client are constructed at import time.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://railboard:railboard@postgres:5432/railboard_test"
os.environ["REDIS_URL"] = "redis://redis:6379/2"
os.environ["TESTING"] = "1"

from collections.abc import AsyncGenerator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from redis.asyncio import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.core.redis as redis_module  # noqa: E402
from app.core.db import Base, async_session_factory, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import booking, station, train, user  # noqa: E402,F401  (register all tables on Base.metadata)
from app.routers.journeys import get_journey_source  # noqa: E402

TABLES = "booking_items, payments, bookings, seats, coaches, trains, stations, users"


def pytest_configure(config):
    """One-time table setup, run in its own throwaway event loop via
    asyncio.run() -- deliberately outside pytest-asyncio's per-test loop
    management, so there's no session-vs-function loop scope to reconcile.
    Safe because the engine uses NullPool in tests (see app/core/db.py):
    it never holds a connection open across separate asyncio.run() calls.
    """

    async def _create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())


@pytest_asyncio.fixture(autouse=True)
async def _clean_state():
    # redis-py's async connections are bound to the event loop they were
    # opened in, same as asyncpg's -- but unlike the SQLAlchemy engine,
    # there's no NullPool equivalent, and even gracefully disconnecting a
    # stale client requires the ORIGINAL (now-dead) loop. So: don't reuse the
    # module-level client across tests at all -- swap in a fresh one bound to
    # this test's own loop from the start. app.core.redis.get_redis() reads
    # this module attribute at call time, so every request during this test
    # (including from the app itself, via the ASGI client) picks it up.
    fresh_redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    redis_module.redis_client = fresh_redis
    yield
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE"))
    await fresh_redis.flushdb()
    await fresh_redis.aclose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


class FakeJourneySource:
    """Swapped in for the real MOTIS adapter via app.dependency_overrides so
    journey-search tests don't depend on a real, external, rate-limited API."""

    def __init__(self, records=None):
        self.records = records or []
        self.calls: list[tuple] = []

    async def search(self, origin, destination, when):
        self.calls.append((origin, destination, when))
        return self.records


@pytest_asyncio.fixture
async def fake_journey_source() -> AsyncGenerator[FakeJourneySource, None]:
    fake = FakeJourneySource()
    app.dependency_overrides[get_journey_source] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_journey_source, None)
