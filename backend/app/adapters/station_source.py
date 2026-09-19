from dataclasses import dataclass
from typing import Protocol


@dataclass
class StationRecord:
    eva_id: int
    name: str
    ds100: str | None
    lat: float | None
    lon: float | None
    federal_state: str | None


class StationSource(Protocol):
    """Anything that can look up stations by name. Implemented by StaDaStationSource
    today; a different upstream (or a fixture for tests) can implement this same
    shape without the rest of the app knowing the difference."""

    async def search(self, query: str) -> list[StationRecord]: ...

    async def list_all(self) -> list[StationRecord]: ...
