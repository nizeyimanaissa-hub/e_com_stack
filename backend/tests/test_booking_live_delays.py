from starlette.testclient import TestClient, WebSocketDisconnect

from app.main import app
from tests.test_bookings import _register_and_login, _seed_train_with_seats


async def _create_confirmed_booking(client, db_session) -> tuple[str, str]:
    token = await _register_and_login(client, "livedelay@example.com")
    _, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)

    create = await client.post(
        "/api/v1/bookings", json={"seat_ids": [str(seat_ids[0])]}, headers={"Authorization": f"Bearer {token}"}
    )
    booking_id = create.json()["id"]

    confirm = await client.post(
        f"/api/v1/bookings/{booking_id}/confirm", headers={"Authorization": f"Bearer {token}"}
    )
    assert confirm.status_code == 200
    return booking_id, token


async def test_live_delay_stream_sends_updates(client, db_session):
    booking_id, token = await _create_confirmed_booking(client, db_session)
    train_id = (await client.get(f"/api/v1/bookings/{booking_id}", headers={"Authorization": f"Bearer {token}"})).json()[
        "items"
    ][0]["train_id"]

    with TestClient(app) as ws_client:
        with ws_client.websocket_connect(f"/api/v1/bookings/{booking_id}/live?token={token}") as ws:
            first = ws.receive_json()
            assert first["train_id"] == train_id
            assert first["status"] in {"on_time", "delayed", "arrived"}
            assert isinstance(first["delay_minutes"], int)


async def test_live_delay_stream_rejects_invalid_token(client, db_session):
    booking_id, _ = await _create_confirmed_booking(client, db_session)

    with TestClient(app) as ws_client:
        try:
            with ws_client.websocket_connect(f"/api/v1/bookings/{booking_id}/live?token=garbage"):
                raise AssertionError("expected the server to reject the connection")
        except WebSocketDisconnect as exc:
            assert exc.code == 4401


async def test_live_delay_stream_rejects_someone_elses_booking(client, db_session):
    booking_id, _ = await _create_confirmed_booking(client, db_session)
    other_token = await _register_and_login(client, "not-the-owner@example.com")

    with TestClient(app) as ws_client:
        try:
            with ws_client.websocket_connect(f"/api/v1/bookings/{booking_id}/live?token={other_token}"):
                raise AssertionError("expected the server to reject the connection")
        except WebSocketDisconnect as exc:
            assert exc.code == 4404


async def test_live_delay_stream_rejects_unconfirmed_booking(client, db_session):
    token = await _register_and_login(client, "pending-booker@example.com")
    _, seat_ids = await _seed_train_with_seats(db_session, num_seats=1)

    create = await client.post(
        "/api/v1/bookings", json={"seat_ids": [str(seat_ids[0])]}, headers={"Authorization": f"Bearer {token}"}
    )
    booking_id = create.json()["id"]

    with TestClient(app) as ws_client:
        try:
            with ws_client.websocket_connect(f"/api/v1/bookings/{booking_id}/live?token={token}"):
                raise AssertionError("expected the server to reject the connection")
        except WebSocketDisconnect as exc:
            assert exc.code == 4409
