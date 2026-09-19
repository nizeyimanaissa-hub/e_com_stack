import asyncio
from datetime import datetime

import httpx

from app.adapters.journey_source import Coordinates, JourneyLeg, JourneyRecord
from app.core.config import Settings
from app.core.errors import UpstreamUnavailableError

TRANSIENT_STATUS_CODES = {500, 502, 503, 504}

# transitous.org's usage policy requires an identifying User-Agent (app name,
# version, contact) and rejects generic library defaults like "python-httpx/...".
USER_AGENT = "RailBoard/0.1 (learning project; no-contact-configured)"


class MotisJourneySource:
    """Talks to a MOTIS (motis-project.de) instance for routed A-to-B journeys.
    Defaults to the free public instance at api.transitous.org.

    We ended up here after two DB-backed options failed: the community
    v6.db.transport.rest wrapper has been down since DB retired the old HAFAS
    API it depended on, and even our own self-hosted db-vendo-client sidecar
    got rejected by DB's backend (app.services-bahn.de) with a bare
    {"message":"Unknown"} -- DB blocks datacenter IPs, which db-vendo-client's
    own maintainers now warn about and recommend MOTIS as the alternative for.
    MOTIS routes over static GTFS data, so it has no dependency on DB's live
    backend at all -- it can't be blocked the way the other two were.

    Trade-offs: no fare/price data (transitous has no fare feed loaded, hence
    price_amount/price_currency are always None below), and it takes lat/lon
    coordinates rather than station EVA ids -- the caller resolves EVA ids to
    coordinates via our own `stations` table before calling this adapter.
    """

    def __init__(self, settings: Settings, max_retries: int = 2):
        self._base_url = settings.motis_base_url
        self._max_retries = max_retries

    async def search(self, origin: Coordinates, destination: Coordinates, when: datetime) -> list[JourneyRecord]:
        params = {
            "fromPlace": f"{origin.lat},{origin.lon}",
            "toPlace": f"{destination.lat},{destination.lon}",
            "time": when.isoformat(),
        }
        payload = await self._get_with_retries("/api/v1/plan", params)
        return [self._to_record(itinerary) for itinerary in payload.get("itineraries", [])]

    async def _get_with_retries(self, path: str, params: dict) -> dict:
        last_error: Exception | None = None
        timeout = httpx.Timeout(connect=3.0, read=8.0, write=3.0, pool=3.0)

        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(base_url=self._base_url, timeout=timeout, headers=headers) as client:
            for attempt in range(self._max_retries):
                try:
                    response = await client.get(path, params=params)
                except httpx.TransportError as exc:
                    last_error = exc
                else:
                    if response.status_code < 400:
                        return response.json()
                    if response.status_code not in TRANSIENT_STATUS_CODES:
                        response.raise_for_status()
                    last_error = httpx.HTTPStatusError(
                        f"transient upstream error {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.3 * (2**attempt))

        raise UpstreamUnavailableError(
            "Journey search is temporarily unavailable (upstream MOTIS/transitous.org)."
        ) from last_error

    @staticmethod
    def _to_record(itinerary: dict) -> JourneyRecord:
        legs = [MotisJourneySource._to_leg(leg) for leg in itinerary.get("legs", [])]
        return JourneyRecord(
            legs=legs,
            departure=datetime.fromisoformat(itinerary["startTime"]),
            arrival=datetime.fromisoformat(itinerary["endTime"]),
            duration_minutes=int(itinerary.get("duration", 0)) // 60,
            transfers=int(itinerary.get("transfers", 0)),
            price_amount=None,
            price_currency=None,
        )

    @staticmethod
    def _to_leg(leg: dict) -> JourneyLeg:
        origin = leg.get("from") or {}
        destination = leg.get("to") or {}

        return JourneyLeg(
            mode=leg.get("mode", "UNKNOWN"),
            origin_name=origin.get("name", ""),
            destination_name=destination.get("name", ""),
            departure=datetime.fromisoformat(leg["startTime"]),
            arrival=datetime.fromisoformat(leg["endTime"]),
            line_name=leg.get("routeShortName") or leg.get("displayName"),
            operator=leg.get("agencyName"),
        )
