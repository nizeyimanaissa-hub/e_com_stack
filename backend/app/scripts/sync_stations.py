"""Pulls station master data from StaDa and upserts it into our Postgres `stations`
table. Meant to run on a schedule (e.g. daily via cron/CI), not per-request --
see the note in app/adapters/stada.py about StaDa's rate limits.

Usage (inside the api container):
    python -m app.scripts.sync_stations              # full sync, all ~5,400 stations
    python -m app.scripts.sync_stations "Frankfurt"   # only stations matching a name
"""

import asyncio
import sys

from sqlalchemy.dialects.postgresql import insert

from app.adapters.stada import StaDaStationSource
from app.adapters.station_source import StationRecord
from app.core.config import get_settings
from app.core.db import async_session_factory
from app.models.station import Station


async def sync(query: str | None) -> int:
    settings = get_settings()
    source = StaDaStationSource(settings)
    records = await source.list_all() if query is None else await source.search(query)

    if not records:
        return 0

    await _upsert(records)
    return len(records)


async def _upsert(records: list[StationRecord]) -> None:
    insert_stmt = insert(Station)
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[Station.eva_id],
        set_={
            "name": insert_stmt.excluded.name,
            "ds100": insert_stmt.excluded.ds100,
            "lat": insert_stmt.excluded.lat,
            "lon": insert_stmt.excluded.lon,
            "federal_state": insert_stmt.excluded.federal_state,
        },
    )

    params = [
        {
            "eva_id": r.eva_id,
            "name": r.name,
            "ds100": r.ds100,
            "lat": r.lat,
            "lon": r.lon,
            "federal_state": r.federal_state,
        }
        for r in records
    ]

    async with async_session_factory() as session:
        await session.execute(upsert_stmt, params)
        await session.commit()


if __name__ == "__main__":
    search_query = sys.argv[1] if len(sys.argv) > 1 else None
    count = asyncio.run(sync(search_query))
    label = f"query '{search_query}'" if search_query else "all stations"
    print(f"Synced {count} station(s) for {label}")
