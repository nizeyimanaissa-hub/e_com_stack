import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

# Set by RequestContextMiddleware for the lifetime of one request; read here
# so every log line emitted while handling that request -- from any module,
# without threading a request object through every call -- carries the same
# id, without changing any function signature.
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }

        context = getattr(record, "context", None)
        if context:
            payload.update(context)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Quiet down uvicorn's own access logger -- RequestContextMiddleware
    # emits one structured "request completed" line per request instead.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False
