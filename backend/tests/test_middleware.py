import uuid


async def test_response_includes_generated_request_id(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    uuid.UUID(resp.headers["X-Request-ID"])  # raises if not a valid uuid


async def test_response_echoes_caller_supplied_request_id(client):
    resp = await client.get("/health", headers={"X-Request-ID": "test-fixed-id"})
    assert resp.headers["X-Request-ID"] == "test-fixed-id"
