from sqlalchemy import delete

from app.models.station import Station


async def test_search_stations_returns_matches(client, db_session):
    db_session.add_all(
        [
            Station(eva_id=1, name="Frankfurt (Main) Hbf", ds100="FF", lat=50.1, lon=8.6, federal_state="Hessen"),
            Station(eva_id=2, name="Frankfurt (Main) West", ds100="FFW", lat=50.1, lon=8.6, federal_state="Hessen"),
            Station(eva_id=3, name="Berlin Hauptbahnhof", ds100="BL", lat=52.5, lon=13.3, federal_state="Berlin"),
        ]
    )
    await db_session.commit()

    resp = await client.get("/api/v1/stations", params={"query": "Frankfurt"})
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert names == {"Frankfurt (Main) Hbf", "Frankfurt (Main) West"}


async def test_search_stations_requires_min_length(client):
    resp = await client.get("/api/v1/stations", params={"query": "F"})
    assert resp.status_code == 422


async def test_search_stations_is_cached(client, db_session):
    db_session.add(Station(eva_id=1, name="Uniquetown", ds100=None, lat=None, lon=None, federal_state=None))
    await db_session.commit()

    first = await client.get("/api/v1/stations", params={"query": "Uniquetown"})
    assert len(first.json()) == 1

    # Delete straight from the DB. If the endpoint queried Postgres again,
    # this would now return nothing -- an unchanged result proves it was
    # served from the Redis cache instead.
    await db_session.execute(delete(Station).where(Station.eva_id == 1))
    await db_session.commit()

    second = await client.get("/api/v1/stations", params={"query": "Uniquetown"})
    assert len(second.json()) == 1
