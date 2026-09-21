async def test_register_creates_user(client):
    resp = await client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "password" not in body
    assert "password_hash" not in body


async def test_register_duplicate_email_conflicts(client):
    await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "b@example.com", "password": "password123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={"email": "c@example.com", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "c@example.com", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


async def test_me_requires_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_token"


async def test_me_returns_current_user(client):
    await client.post("/api/v1/auth/register", json={"email": "d@example.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": "d@example.com", "password": "password123"})
    token = login.json()["access_token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "d@example.com"


async def test_refresh_issues_new_access_token(client):
    await client.post("/api/v1/auth/register", json={"email": "e@example.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": "e@example.com", "password": "password123"})
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_refresh_rejects_access_token(client):
    await client.post("/api/v1/auth/register", json={"email": "f@example.com", "password": "password123"})
    login = await client.post("/api/v1/auth/login", json={"email": "f@example.com", "password": "password123"})
    access_token = login.json()["access_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
