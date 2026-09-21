import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var
from app.core.metrics import observe_request

logger = logging.getLogger("railboard.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns each request an id (reusing X-Request-ID if the caller sent
    one, so a request can be traced across services), makes it available to
    every log line emitted while handling the request via request_id_var,
    echoes it back in the response, and logs one structured access line."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_seconds = time.perf_counter() - start
            duration_ms = duration_seconds * 1000
            response.headers["X-Request-ID"] = request_id
            observe_request(request, response.status_code, duration_seconds)
            # Logged before the reset below, while request_id_var still holds
            # this request's id -- otherwise this line would log "-" for its
            # own request_id instead of the id it's reporting on.
            logger.info(
                "request completed",
                extra={
                    "context": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )
            return response
        finally:
            request_id_var.reset(token)
