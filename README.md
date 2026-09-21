# RailBoard

A production-style, Deutsche Bahn–style train search & booking platform, built as a backend skill-building project (FastAPI + PostgreSQL + Redis).

Full project spec: [docs/spec.md](docs/spec.md)

## Status

- Phase 1 (Foundation): done — Docker Compose skeleton (API + Postgres + Redis), health-check endpoint.
- Phase 2 (Station data): done — `stations` table + Alembic migration, StaDa adapter, sync job, `GET /api/v1/stations?query=` backed by Postgres with a Redis read-through cache (5 min TTL).
- Phase 3 (Journey search): done and verified against live data. `GET /api/v1/journeys?from=&to=&when=` (EVA ids from `/stations`) resolves each station's lat/lon from our own table and queries a public [MOTIS](https://motis-project.de) instance (`api.transitous.org`), which routes over static GTFS data. Redis cache (1 min TTL), retry/backoff, `{ error: { code, message } }` envelope for upstream failures. See "Journey search" below for how we got here — two DB-backed approaches (`v6.db.transport.rest`, then a self-hosted `db-vendo-client` sidecar) both turned out to be genuinely broken, not just misconfigured.
- Phase 4 (Auth): done — `users` table (UUID primary key), bcrypt password hashing, JWT access (15 min) + refresh (7 day) tokens with a `type` claim so one can't be used as the other, `POST /api/v1/auth/{register,login,refresh}`, `GET /api/v1/auth/me` guarded by a bearer-token dependency.
- Phase 5 (Booking core): done — `trains`/`coaches`/`seats` (invented seat maps), `bookings`/`booking_items`/`payments`. Concurrency-safety via `SELECT ... FOR UPDATE` row locks, verified with a real concurrent-request test (two simultaneous bookings for the same seat: exactly one `201`, one `409`). Seat holds lazily expire via a `held_until` timestamp, no background sweep needed. Full flow: `POST /api/v1/bookings` (hold) → `POST /api/v1/bookings/{id}/confirm` (mock payment, finalize) → `DELETE /api/v1/bookings/{id}` (cancel, release). `GET /api/v1/me/bookings` isolated per user (unowned bookings 404, not 403).
  - **Journey search → booking bridge**: `POST /api/v1/trains/from-journey-leg` takes a selected leg from a real `/journeys` result (line name, times, operator) and idempotently registers its `trains` row — verified end-to-end with a real ICE 78 Hannover→Hamburg leg through to a completed booking. Covers direct (transfers=0) journeys only; a leg from a journey with transfers needs its intermediate stations resolved to EVA ids too, not yet built (`POST /api/v1/trains` still exists for fully manual/hand-typed train registration).
- Phase 6 (Frontend): done — minimal React + TypeScript + Vite app (`frontend/`), no router, just a step-based wizard: auth → journey search (station autocomplete) → results → seat picker → booking confirmation. Verified in an actual headless browser (Playwright), not just read — full flow works with zero console errors and zero failed requests: login, search Hannover Hbf → Hamburg Hbf, book a real ICE 76 seat, confirm it. The UI also correctly disables booking on journeys with transfers, matching the backend's real limitation.
- Phase 7 (Hardening): done — a pytest suite (`backend/tests/`) covering auth, stations, journeys, bookings, adapters, security helpers, rate limiting, middleware, and metrics, including the booking race condition (two concurrent requests for the same seat: exactly one `201`, one `409`) via a real async test against Postgres + Redis, not mocks. Redis-backed fixed-window rate limiting (`app/core/rate_limit.py`, `INCR`/`EXPIRE`) on `/auth/register`, `/auth/login`, and both search endpoints, returning the standard error envelope with a `429` + `Retry-After` header. Structured JSON logging (`app/core/logging.py`) with a request-ID middleware (`app/core/middleware.py`) that generates or echoes `X-Request-ID`, tagging every log line for a request via a `contextvar` so it's traceable end-to-end. Basic Prometheus metrics at `GET /metrics` (`app/core/metrics.py`) — request counts and latency histograms labeled by route template (not raw path, to avoid unbounded cardinality from ids like `booking_id`).
- Phase 8 (Stretch goal — WebSocket live delay updates): done — `GET /api/v1/bookings/{id}/live` (`app/routers/bookings.py`) upgrades to a WebSocket and streams simulated delay updates (`app/services/delay_feed.py`) for a confirmed booking's train: a random walk over `delay_minutes` ticking every 2s, since there's no real GTFS-RT feed behind the public MOTIS instance this project's journey search uses. Auth via a `?token=` query param (native browser WebSocket can't set an Authorization header), rejecting with a 4401/4404/4409 close code for an invalid token, someone else's booking, or a not-yet-confirmed one, mirroring the REST API's error cases. `frontend/src/components/LiveDelayPanel.tsx` connects automatically once a booking is confirmed and shows a live-updating status dot. 46 backend tests total (4 new, covering the stream and each rejection path); verified end-to-end against the live dev server too — real register → book → confirm → WebSocket connect, not just the test suite.

## Running locally

```bash
cp .env.example .env   # then fill in DB_API_CLIENT_ID / DB_API_KEY from developers.deutschebahn.com
docker compose up --build
curl http://localhost:8000/health
```

Postgres is published on host port **5433** (not the default 5432) — this machine already
has a native Postgres server bound to 5432, so we moved ours to avoid the conflict. When
connecting a GUI client or VS Code's PostgreSQL extension, use `localhost:5433`
(user/password/db: `railboard`). The app itself talks to Postgres over the internal Docker
network on the normal port, so `DATABASE_URL` is unaffected.

### Database migrations (Alembic)

```bash
docker compose exec api alembic upgrade head                              # apply migrations
docker compose exec api alembic revision --autogenerate -m "description"  # after changing a model
```

### Running tests

Tests run against a separate `railboard_test` database and Redis db index (2),
never the dev data. Create the test database once (`CREATE DATABASE railboard_test;`
via `docker compose exec postgres psql -U railboard -d railboard`), then:

```bash
docker compose exec api pytest -v
```

### Syncing station data from StaDa

Requires real credentials in `.env`. StaDa serves static data, so DB asks that it
only be polled ~1x/day per key — run this as an occasional job, not per-request.

```bash
docker compose exec api python -m app.scripts.sync_stations              # full sync, ~5,400 stations, paginated
docker compose exec api python -m app.scripts.sync_stations "Frankfurt"  # narrower sync, for quick testing
curl "http://localhost:8000/api/v1/stations?query=Frankfurt"
```

### Journey search (MOTIS / transitous.org)

```bash
curl "http://localhost:8000/api/v1/journeys?from=8000152&to=8002549&when=2026-09-21T08:00:00%2B02:00"
# -> real ICE/RE journeys between Hannover Hbf and Hamburg Hbf, with legs, times, transfers
```

**How we got here (worth knowing since it's a real lesson in vendor dependencies):**
1. The spec's plan, the community wrapper `v6.db.transport.rest`, is down for good —
   DB retired the HAFAS API it depended on in 2025.
2. We tried self-hosting `db-rest` (the same project, wrapping `db-vendo-client`,
   the actively-maintained successor) as a Docker sidecar. It also failed: DB's
   real backend (`app.services-bahn.de`) rejected every request with
   `{"message":"Unknown"}`. This turned out to be DB blocking datacenter IPs
   outright — confirmed via `db-vendo-client`'s own GitHub issues, where the
   maintainers now recommend against relying on DB's backend directly.
3. Their recommended alternative is **MOTIS**, a routing engine over static GTFS
   data with no dependency on DB's live backend at all — so it can't be blocked
   the same way. We use the free public instance at `api.transitous.org` rather
   than self-hosting (self-hosting needs OpenStreetMap + GTFS files managed
   locally, a bigger undertaking not justified yet).

**Known limitations of this approach:**
- No price data — transitous has no fare feed loaded (`price_amount`/`price_currency`
  are always `null`).
- Takes coordinates, not station IDs — `app/routers/journeys.py` resolves EVA ids to
  lat/lon via our own `stations` table before calling the adapter, so both stations
  must already be synced (see the sync job above).
- Their usage policy requires an identifying `User-Agent` (see `app/adapters/motis.py`);
  generic library user-agents get a `403`.

### Auth

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"a-real-password"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"a-real-password"}'
# -> { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

curl http://localhost:8000/api/v1/auth/me -H "Authorization: Bearer <access_token>"
```

### Booking core

```bash
# 1a. Register a train from a real journey search result (preferred):
#     pick one leg (mode != "WALK") from a GET /journeys response and echo its
#     fields back -- only works for a direct (transfers=0) journey's leg, whose
#     origin/destination are exactly the queried origin_eva/destination_eva.
curl -X POST http://localhost:8000/api/v1/trains/from-journey-leg -H "Content-Type: application/json" -d '{
  "origin_eva":8000152,"destination_eva":8002549,
  "line_name":"ICE 78","operator":"DB Fernverkehr AG",
  "departure":"2026-09-21T06:08:00Z","arrival":"2026-09-21T07:29:00Z"
}'
# -> { "id": "<train_id>", "category":"ICE", "number":"78", ... }

# 1b. Or register one by hand instead (e.g. for testing without a live journey search):
curl -X POST http://localhost:8000/api/v1/trains -H "Content-Type: application/json" -d '{
  "category":"ICE","number":"1002","operator":"DB Fernverkehr",
  "origin_eva":8000152,"destination_eva":8002549,
  "departure":"2026-09-20T08:00:00+02:00","arrival":"2026-09-20T09:15:00+02:00"
}'
# -> { "id": "<train_id>", ... }

# 2. View its seat map
curl "http://localhost:8000/api/v1/trains/<train_id>/seats"

# 3. Book a seat (needs an access token from /auth/login)
curl -X POST http://localhost:8000/api/v1/bookings \
  -H "Content-Type: application/json" -H "Authorization: Bearer <access_token>" \
  -d '{"seat_ids": ["<seat_id>"]}'
# -> booking status "pending", seat status now "held"

# 4. Confirm (mock payment) or cancel
curl -X POST http://localhost:8000/api/v1/bookings/<booking_id>/confirm -H "Authorization: Bearer <access_token>"
curl -X DELETE http://localhost:8000/api/v1/bookings/<booking_id> -H "Authorization: Bearer <access_token>"
```

**On the concurrency guarantee:** `POST /api/v1/bookings` runs `SELECT ... FOR UPDATE`
on the requested seat rows before checking availability. If two requests race for the
same seat, the second one's `SELECT` blocks until the first transaction commits or
rolls back, then re-reads the now-updated row and correctly rejects with `409
seats_unavailable` — both requests can never both see "free". This was verified with
an actual concurrent test (`asyncio.gather` firing two real requests at once), not
just reasoned about: exactly one `201`, one `409`, every time.

### Frontend

Runs in Docker too (no Node installed on this machine) — already started by
`docker compose up`. Just open it:

```
http://localhost:5173
```

Log in with an account you've registered via the API (or use the form's
"Need an account? Register" link), then search a journey between two synced
stations, e.g. **Hannover Hbf → Hamburg Hbf**. Booking only works on a
*direct* result (no transfers) — the UI disables the button and explains why
on journeys with a transfer, matching the backend's current limitation (see
the booking-bridge note above).

`frontend/src/lib/api.ts` is the one place that knows about the backend's
URL, auth headers, and `{ error: { code, message } }` envelope — every
component goes through it rather than calling `fetch` directly.

## Build order

1. Foundation — Docker Compose skeleton, health check, CI
2. Station data — StaDa sync + `/stations` search, Redis caching
3. Journey search — adapter around `v6.db.transport.rest`
4. Auth — register/login/refresh, JWT
5. Booking core — seat holds, concurrency-safe booking
6. Frontend — minimal React UI
7. Hardening — tests, rate limiting, logging
8. Stretch goals
