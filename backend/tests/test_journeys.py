from datetime import datetime, timezone

from app.adapters.journey_source import JourneyLeg, JourneyRecord
from app.models.station import Station

FAKE_RECORD = JourneyRecord(
    legs=[
        JourneyLeg(
            mode="HIGHSPEED_RAIL",
            origin_name="Origin",
            destination_name="Destination",
            departure=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
            arrival=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
            line_name="ICE 1",
            operator="Test Rail",
        )
    ],
    departure=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
    arrival=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
    duration_minutes=60,
    transfers=0,
    price_amount=None,
    price_currency=None,
)


async def _seed_stations(db_session):
    db_session.add_all(
        [
            Station(eva_id=1, name="Origin", ds100=None, lat=50.0, lon=8.0, federal_state=None),
            Station(eva_id=2, name="Destination", ds100=None, lat=53.0, lon=10.0, federal_state=None),
        ]
    )
    await db_session.commit()


async def test_search_journeys_returns_fake_source_results(client, db_session, fake_journey_source):
    await _seed_stations(db_session)
    fake_journey_source.records = [FAKE_RECORD]

    resp = await client.get("/api/v1/journeys", params={"from": 1, "to": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["legs"][0]["line_name"] == "ICE 1"
    assert len(fake_journey_source.calls) == 1


async def test_search_journeys_unknown_station_404s(client, db_session, fake_journey_source):
    await _seed_stations(db_session)

    resp = await client.get("/api/v1/journeys", params={"from": 1, "to": 999999})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "station_not_found"


async def test_search_journeys_caches_result(client, db_session, fake_journey_source):
    await _seed_stations(db_session)
    fake_journey_source.records = [FAKE_RECORD]

    params = {"from": 1, "to": 2, "when": "2026-10-01T08:00:00+00:00"}
    first = await client.get("/api/v1/journeys", params=params)
    second = await client.get("/api/v1/journeys", params=params)

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(fake_journey_source.calls) == 1  # second request served from cache
