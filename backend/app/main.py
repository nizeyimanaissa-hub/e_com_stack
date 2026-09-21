import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.metrics import metrics_response
from app.core.middleware import RequestContextMiddleware
from app.routers import auth, bookings, journeys, me, stations, trains

configure_logging()
logger = logging.getLogger("railboard.errors")

app = FastAPI(title="RailBoard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Added after CORS so it's outermost and assigns a request id before any
# other middleware or route code runs (see app/core/middleware.py).
app.add_middleware(RequestContextMiddleware)

app.include_router(stations.router)
app.include_router(journeys.router)
app.include_router(auth.router)
app.include_router(trains.router)
app.include_router(bookings.router)
app.include_router(me.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log = logger.error if exc.status_code >= 500 else logger.warning
    log(
        exc.message,
        extra={"context": {"code": exc.code, "status_code": exc.status_code, "path": request.url.path}},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=exc.headers or None,
    )


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return metrics_response()
