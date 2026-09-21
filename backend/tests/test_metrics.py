async def test_metrics_endpoint_reports_request_count(client):
    await client.get("/health")

    resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert 'railboard_http_requests_total{method="GET",path="/health",status_code="200"}' in body
    assert "railboard_http_request_duration_seconds" in body
