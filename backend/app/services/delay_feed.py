import asyncio
import random
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from pydantic import BaseModel


class DelayUpdate(BaseModel):
    train_id: uuid.UUID
    status: str  # "on_time" | "delayed" | "arrived"
    delay_minutes: int
    updated_at: datetime


async def stream_delay_updates(
    train_id: uuid.UUID, ticks: int = 20, interval_seconds: float = 2.0
) -> AsyncIterator[DelayUpdate]:
    """Simulates a live GTFS-RT-style delay feed for a train.

    There's no real one available: the MOTIS instance this project's journey
    search uses (api.transitous.org) routes over static schedule data, not a
    live feed (see README's "Journey search" section for why two DB-backed
    alternatives with real-time data didn't pan out). This is a random walk
    over `delay_minutes`, ticking every `interval_seconds` regardless of the
    train's real scheduled duration -- compressed for demo purposes, not
    synced to wall-clock departure/arrival time.
    """
    rng = random.Random()
    delay = 0

    for tick in range(ticks):
        is_last = tick == ticks - 1
        if is_last:
            status = "arrived"
        else:
            roll = rng.random()
            if roll < 0.25:
                delay = min(delay + rng.randint(1, 5), 45)
            elif roll < 0.4 and delay > 0:
                delay = max(delay - rng.randint(1, 3), 0)
            status = "on_time" if delay == 0 else "delayed"

        yield DelayUpdate(
            train_id=train_id,
            status=status,
            delay_minutes=delay,
            updated_at=datetime.now(timezone.utc),
        )

        if not is_last:
            await asyncio.sleep(interval_seconds)
