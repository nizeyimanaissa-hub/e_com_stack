import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.journey_source import Coordinates
from app.adapters.motis import MotisJourneySource
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.errors import AppError
from app.core.redis import get_redis
from app.models.station import Station
from app.schemas.journey import JourneyOut

router = APIRouter(prefix="/api/v1/journeys", tags=["journeys"])


class StationNotFoundError(AppError):
    def __init__(self, eva_id: int) -> None:
        super().__init__(
            f"No station with EVA id {eva_id} (sync it via the /stations sync job first)",
            code="station_not_found",
            status_code=404,
        )


@router.get("", response_model=list[JourneyOut])
async def search_journeys(
    origin_eva: int = Query(..., alias="from", description="Origin station EVA id, from /api/v1/stations"),
    dest_eva: int = Query(..., alias="to", description="Destination station EVA id, from /api/v1/stations"),
    when: datetime | None = Query(None, description="Departure time (ISO 8601); defaults to now"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> list[JourneyOut]:
    departure = when or datetime.now().astimezone()
    cache_key = f"journeys:{origin_eva}:{dest_eva}:{departure.strftime('%Y-%m-%dT%H:%M')}"

    cached = await redis.get(cache_key)
    if cached is not None:
        return [JourneyOut.model_validate_json(item) for item in json.loads(cached)]

    origin = await _station_coords(db, origin_eva)
    destination = await _station_coords(db, dest_eva)

    source = MotisJourneySource(settings)
    records = await source.search(origin, destination, departure)
    journeys = [JourneyOut.model_validate(record) for record in records]

    if journeys:
        await redis.set(
            cache_key,
            json.dumps([j.model_dump_json() for j in journeys]),
            ex=settings.journeys_cache_ttl_seconds,
        )

    return journeys


async def _station_coords(db: AsyncSession, eva_id: int) -> Coordinates:
    station = await db.get(Station, eva_id)
    if station is None or station.lat is None or station.lon is None:
        raise StationNotFoundError(eva_id)
    return Coordinates(lat=station.lat, lon=station.lon)
