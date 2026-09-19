import httpx

from app.adapters.station_source import StationRecord
from app.core.config import Settings


class StaDaStationSource:
    """Talks to the official DB StaDa (Station Data) API.

    Docs: https://developers.deutschebahn.com/db-api-marketplace/apis/product/stada
    Note: StaDa serves static data — DB asks that it only be pulled ~1x/day per key,
    so this adapter is meant to be called from the sync job (app/scripts/sync_stations.py),
    never from a live request path.
    """

    def __init__(self, settings: Settings):
        self._base_url = settings.db_api_base_url
        self._headers = {
            "DB-Client-Id": settings.db_api_client_id,
            "DB-Api-Key": settings.db_api_key,
            "Accept": "application/json",
        }

    async def search(self, query: str) -> list[StationRecord]:
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=10) as client:
            response = await client.get("/stations", params={"searchstring": f"*{query}*"})
            response.raise_for_status()
            payload = response.json()

        return [self._to_record(item) for item in payload.get("result", [])]

    async def list_all(self, page_size: int = 1000) -> list[StationRecord]:
        records: list[StationRecord] = []
        offset = 0

        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=15) as client:
            while True:
                response = await client.get(
                    "/stations", params={"searchstring": "*", "limit": page_size, "offset": offset}
                )
                response.raise_for_status()
                payload = response.json()

                batch = payload.get("result", [])
                records.extend(self._to_record(item) for item in batch)

                offset += len(batch)
                if not batch or offset >= payload.get("total", offset):
                    break

        return records

    @staticmethod
    def _to_record(item: dict) -> StationRecord:
        eva_numbers = item.get("evaNumbers") or []
        primary_eva = next((e for e in eva_numbers if e.get("isMain")), eva_numbers[0] if eva_numbers else None)

        lat = lon = None
        if primary_eva and primary_eva.get("geographicCoordinates"):
            coords = primary_eva["geographicCoordinates"].get("coordinates") or [None, None]
            lon, lat = coords[0], coords[1]

        ril_identifiers = item.get("ril100Identifiers") or []
        primary_ril = next((r for r in ril_identifiers if r.get("isMain")), ril_identifiers[0] if ril_identifiers else None)
        ds100 = primary_ril.get("rilIdentifier") if primary_ril else None

        return StationRecord(
            eva_id=int(primary_eva["number"]) if primary_eva else int(item["number"]),
            name=item.get("name", ""),
            ds100=ds100,
            lat=lat,
            lon=lon,
            federal_state=item.get("federalState"),
        )
