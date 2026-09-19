from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class Coordinates:
    lat: float
    lon: float


@dataclass
class JourneyLeg:
    mode: str  # e.g. "WALK", "HIGHSPEED_RAIL", "REGIONAL_RAIL"
    origin_name: str
    destination_name: str
    departure: datetime
    arrival: datetime
    line_name: str | None
    operator: str | None


@dataclass
class JourneyRecord:
    legs: list[JourneyLeg]
    departure: datetime
    arrival: datetime
    duration_minutes: int
    transfers: int
    price_amount: float | None
    price_currency: str | None


class JourneySource(Protocol):
    async def search(self, origin: Coordinates, destination: Coordinates, when: datetime) -> list[JourneyRecord]: ...
