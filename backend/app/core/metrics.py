from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "railboard_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "railboard_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


def observe_request(request: Request, status_code: int, duration_seconds: float) -> None:
    # request.scope["route"] is set once Starlette's router matches a route;
    # its .path is the registered template (e.g. "/api/v1/bookings/{booking_id}"),
    # not the raw URL -- using the raw path would give every distinct booking
    # id its own label series, growing metrics cardinality without bound.
    route = request.scope.get("route")
    path = route.path if route is not None else request.url.path

    REQUEST_COUNT.labels(method=request.method, path=path, status_code=status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration_seconds)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
