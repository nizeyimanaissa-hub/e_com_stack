import json

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.redis import get_redis
from app.models.station import Station
from app.schemas.station import StationOut

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])


@router.get("", response_model=list[StationOut])
async def search_stations(
    query: str = Query(..., min_length=2, description="Partial station name, e.g. 'Frankfurt'"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> list[StationOut]:
    cache_key = f"stations:search:{query.lower()}"

    cached = await redis.get(cache_key)
    if cached is not None:
        return [StationOut.model_validate_json(item) for item in json.loads(cached)]

    result = await db.execute(
        select(Station).where(Station.name.ilike(f"%{query}%")).order_by(Station.name).limit(20)
    )
    stations = [StationOut.model_validate(row) for row in result.scalars().all()]

    if stations:
        await redis.set(
            cache_key,
            json.dumps([s.model_dump_json() for s in stations]),
            ex=settings.stations_cache_ttl_seconds,
        )

    return stations
