from app.core.config import get_settings

settings = get_settings()


async def test_register_is_rate_limited_after_configured_calls(client):
    limit = settings.rate_limit_auth_per_minute

    for _ in range(limit):
        resp = await client.post(
            "/api/v1/auth/register", json={"email": "spam@example.com", "password": "password123"}
        )
        assert resp.status_code != 429

    resp = await client.post("/api/v1/auth/register", json={"email": "spam@example.com", "password": "password123"})
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"
    assert "Retry-After" in resp.headers


async def test_login_is_rate_limited_independently_of_register(client):
    limit = settings.rate_limit_auth_per_minute

    for _ in range(limit):
        resp = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
        assert resp.status_code != 429

    resp = await client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert resp.status_code == 429


async def test_station_search_is_rate_limited(client):
    limit = settings.rate_limit_search_per_minute

    for _ in range(limit):
        resp = await client.get("/api/v1/stations", params={"query": "Berlin"})
        assert resp.status_code != 429

    resp = await client.get("/api/v1/stations", params={"query": "Berlin"})
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"
