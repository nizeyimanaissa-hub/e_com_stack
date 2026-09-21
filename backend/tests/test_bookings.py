import asyncio
import uuid
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.train import Coach, Seat, Train


async def _register_and_login(client: AsyncClient, email: str, password: str = "password123") -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _seed_train_with_seats(db_session, num_seats: int = 2) -> tuple[uuid.UUID, list[uuid.UUID]]:
    train = Train(
        category="ICE",
        number="TEST1",
        operator="Test Rail",
        origin_eva=1,
        destination_eva=2,
        departure=datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc),
        arrival=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
    )
    coach = Coach(coach_number=1, seat_class="second", price=49.90)
    seats = [Seat(seat_number=f"{i}A") for i in range(1, num_seats + 1)]
    coach.seats = seats
    train.coaches = [coach]

    db_session.add(train)
    await db_session.commit()
    return train.id, [s.id for s in seats]


async def test_create_booking_holds_seat(client, db_session):
    token = await _register_and_login(client, "booker1@example.com")
    train_id, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)

    resp = await client.post(
        "/api/v1/bookings",
        json={"seat_ids": [str(seat_ids[0])]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert len(body["items"]) == 1

    seats_resp = await client.get(f"/api/v1/trains/{train_id}/seats")
    seat = next(s for s in seats_resp.json() if s["id"] == str(seat_ids[0]))
    assert seat["status"] == "held"


async def test_double_booking_same_seat_sequentially_conflicts(client, db_session):
    token = await _register_and_login(client, "booker-seq@example.com")
    _, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)
    seat_id = str(seat_ids[0])

    first = await client.post(
        "/api/v1/bookings", json={"seat_ids": [seat_id]}, headers={"Authorization": f"Bearer {token}"}
    )
    second = await client.post(
        "/api/v1/bookings", json={"seat_ids": [seat_id]}, headers={"Authorization": f"Bearer {token}"}
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "seats_unavailable"


async def test_confirm_booking(client, db_session):
    token = await _register_and_login(client, "booker2@example.com")
    _, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)

    create = await client.post(
        "/api/v1/bookings", json={"seat_ids": [str(seat_ids[0])]}, headers={"Authorization": f"Bearer {token}"}
    )
    booking_id = create.json()["id"]

    resp = await client.post(f"/api/v1/bookings/{booking_id}/confirm", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    again = await client.post(f"/api/v1/bookings/{booking_id}/confirm", headers={"Authorization": f"Bearer {token}"})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "invalid_booking_state"


async def test_cancel_booking_releases_seat(client, db_session):
    token = await _register_and_login(client, "booker3@example.com")
    train_id, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)

    create = await client.post(
        "/api/v1/bookings", json={"seat_ids": [str(seat_ids[0])]}, headers={"Authorization": f"Bearer {token}"}
    )
    booking_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/bookings/{booking_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    seats_resp = await client.get(f"/api/v1/trains/{train_id}/seats")
    seat = next(s for s in seats_resp.json() if s["id"] == str(seat_ids[0]))
    assert seat["status"] == "free"


async def test_booking_not_visible_to_other_users(client, db_session):
    token_owner = await _register_and_login(client, "owner@example.com")
    _, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)

    create = await client.post(
        "/api/v1/bookings", json={"seat_ids": [str(seat_ids[0])]}, headers={"Authorization": f"Bearer {token_owner}"}
    )
    booking_id = create.json()["id"]

    token_intruder = await _register_and_login(client, "intruder@example.com")
    resp = await client.get(f"/api/v1/bookings/{booking_id}", headers={"Authorization": f"Bearer {token_intruder}"})
    assert resp.status_code == 404  # not 403 -- doesn't reveal that the booking exists


async def test_concurrent_booking_of_same_seat_only_one_succeeds(db_session):
    """The most important test in this project: two truly concurrent requests
    for the same seat must never both succeed. Two independent AsyncClient
    instances (separate connections/DB sessions via the app's connection
    pool) fired through asyncio.gather so the race is real, not simulated by
    sequential awaits on a single client -- this is what actually exercises
    the SELECT ... FOR UPDATE row lock in app/routers/bookings.py.
    """
    transport = ASGITransport(app=app)

    async with (
        AsyncClient(transport=transport, base_url="http://test") as client_a,
        AsyncClient(transport=transport, base_url="http://test") as client_b,
    ):
        token_a = await _register_and_login(client_a, "racer-a@example.com")
        token_b = await _register_and_login(client_b, "racer-b@example.com")
        _, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)
        seat_id = str(seat_ids[0])

        results = await asyncio.gather(
            client_a.post(
                "/api/v1/bookings", json={"seat_ids": [seat_id]}, headers={"Authorization": f"Bearer {token_a}"}
            ),
            client_b.post(
                "/api/v1/bookings", json={"seat_ids": [seat_id]}, headers={"Authorization": f"Bearer {token_b}"}
            ),
        )

        statuses = sorted(r.status_code for r in results)
        assert statuses == [201, 409]
