# RailBoard — Project Specification
### A production-style Deutsche Bahn–style train search & booking platform (backend skill-building project)

---

## 1. Goal & Scope

The point of this project is not to rebuild bahn.de — it's to give you a realistic, end-to-end backend engineering exercise: real external data, a proper relational schema, authentication, business logic (seat locking, pricing, booking state machines), and an API that a frontend actually consumes.

**Primary goal:** get hands-on with backend patterns you don't get much of in ABAP/SAP work — REST API design, async I/O, relational modeling with real-world constraints, and testing outside SAP's walled garden.

**Non-goals:** real payments, real ticket issuance, 100% schedule accuracy, mobile apps.

---

## 2. Data Sources

Two realistic options, and you should actually use both (primary + fallback — this itself is a good production pattern to practice):

### Option A — Official: DB API Marketplace (`developers.deutschebahn.com`)
- Free registration, gives you a Client ID + API Key.
- **Timetables API** — planned + live (delays, cancellations, platform changes) departures/arrivals per station, queried by **EVA number** (DB's numeric station ID) and hour-slices.
- **StaDa (Station Data) API** — searchable master data for stations: name, EVA number, DS100 code, coordinates, federal state, category.
- Realistic constraint to design around: data comes back in **hourly slices with no timezone info** — you'll need to normalize this yourself, which is a good exercise in defensive data-layer design.

### Option B — Community wrapper: `v6.db.transport.rest`
- No API key needed, but rate-limited (100 req/min, burst 200).
- Much easier to prototype with: `/locations` (station search), `/stops/:id/departures`, `/journeys?from=&to=&departure=` (actual routable journeys with legs, transfers, prices where available).
- Good for the **journey search / trip planning** feature since the official API only gives per-station timetables, not routed A→B journeys.

**Recommended split:** use `v6.db.transport.rest` for journey search (origin → destination, transfers, duration) and the official Timetables/StaDa APIs for station master data and live departure boards. This mirrors a real system that stitches together multiple upstream sources — build a thin adapter layer so the rest of your app doesn't care which one it's talking to.

---

## 3. Recommended Tech Stack

Given your OOP/ABAP background, a framework that rewards class-based, dependency-injected design will feel closest to home while still teaching you idiomatic backend patterns.

| Layer | Recommendation | Why |
|---|---|---|
| Backend | **NestJS (TypeScript)** | Decorator-based, modular, DI container — structurally close to OOP you already know, but forces you to learn REST/async idioms |
| Alternative | Python + FastAPI | If you'd rather build Python skills; Pydantic models map cleanly to a spec-first approach |
| Database | **PostgreSQL** | Real relational constraints, transactions for seat booking, good practice for schema design |
| ORM | Prisma (Nest) or SQLAlchemy (FastAPI) | Migrations + type-safe queries |
| Auth | JWT (access + refresh tokens), bcrypt for passwords | Standard, portable pattern |
| Cache/Queue | Redis | For caching upstream API responses and seat-lock TTLs |
| Frontend | React + TypeScript (Vite) | Keep it simple — this project is backend-focused |
| Infra | Docker Compose (api + db + redis), GitHub Actions CI | "Production style" = containerized, tested, CI'd |
| Testing | Jest/Vitest (unit) + Supertest (integration) | Non-negotiable for a "production style" claim |

---

## 4. Architecture

```
                         ┌─────────────────────┐
                         │   React Frontend     │
                         └──────────┬───────────┘
                                    │ REST/JSON
                         ┌──────────▼───────────┐
                         │   API Gateway Layer   │  (auth guard, rate limit, validation)
                         └──────────┬───────────┘
              ┌─────────────────────┼─────────────────────┐
      ┌───────▼───────┐   ┌─────────▼────────┐   ┌─────────▼─────────┐
      │ Station/Search │   │  Booking/Seats    │   │   Auth/Users       │
      │    Module      │   │     Module        │   │     Module         │
      └───────┬───────┘   └─────────┬────────┘   └────────────────────┘
              │                     │
      ┌───────▼────────┐   ┌────────▼─────────┐
      │ DB Adapter Layer│   │   PostgreSQL      │
      │ (transport.rest │   │  (bookings, seats,│
      │  + DB Timetables│   │   users, orders)  │
      │  behind one     │   └──────────────────┘
      │  interface)     │
      └───────┬────────┘
              │
      ┌───────▼────────┐        ┌──────────────┐
      │ Redis cache     │        │ External DB   │
      │ (station data,  │◄──────►│ APIs (A & B)  │
      │  journey search)│        └──────────────┘
      └────────────────┘
```

Key design decision to practice: **your own DB never stores train/timetable data long-term** (it's not yours to own) — only caches it briefly (Redis, TTL ~1–5 min). What you *do* own and persist is booking/order/seat state, which is your actual business logic.

---

## 5. Core Domain Model (Postgres schema, simplified)

```
users            (id, email, password_hash, created_at)
stations         (eva_id PK, name, ds100, lat, lon, federal_state)   -- cached/synced from StaDa
journeys_cache   (id, origin_eva, dest_eva, departure, arrival, legs_json, fetched_at)  -- short TTL cache
trains           (id, journey_leg_ref, category, number, operator)
coaches          (id, train_id, coach_number, class)                 -- your own invented seat map, since DB doesn't expose real seat maps publicly
seats            (id, coach_id, seat_number, status: free|held|booked)
bookings         (id, user_id, status: pending|confirmed|cancelled, created_at)
booking_items    (id, booking_id, seat_id, journey_ref, price)
payments         (id, booking_id, status, amount, mock_provider_ref)
```

**The interesting backend problem here:** seat availability under concurrency. Two users hitting "book seat 12A" at the same moment must not both succeed. This is your excuse to practice:
- Row-level locking (`SELECT ... FOR UPDATE`) or
- Optimistic locking with a `version` column, or
- A Redis-based short-lived hold (`SETNX` with TTL) before committing to Postgres.

Pick one, implement it, and be ready to explain the trade-offs — that's a very real interview topic for backend roles.

---

## 6. API Design (REST, v1)

```
GET   /api/v1/stations?query=Frankfurt          → search stations (proxies StaDa, cached)
GET   /api/v1/stations/:eva/departures          → live departure board (Timetables API)
GET   /api/v1/journeys?from=&to=&when=          → routed journeys (transport.rest)

POST  /api/v1/auth/register
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh

POST  /api/v1/bookings                          → create a pending booking (holds seats)
GET   /api/v1/bookings/:id
POST  /api/v1/bookings/:id/confirm              → simulate payment, finalize
DELETE /api/v1/bookings/:id                      → cancel / release held seats

GET   /api/v1/me/bookings
```

Non-functional bits worth doing "properly":
- Consistent error envelope (`{ error: { code, message } }`)
- Input validation via DTOs (class-validator in Nest / Pydantic in FastAPI)
- Pagination on list endpoints
- OpenAPI/Swagger docs generated from code, not hand-written

---

## 7. Suggested Build Order (phases)

1. **Foundation** — Docker Compose skeleton (api + Postgres + Redis), health-check endpoint, CI pipeline that runs lint + tests on push.
2. **Station data** — StaDa sync job + `/stations` search endpoint, Redis caching.
3. **Journey search** — adapter around `v6.db.transport.rest`, `/journeys` endpoint, response normalization.
4. **Auth** — register/login/refresh, password hashing, JWT guards.
5. **Booking core** — seat map generation (your own invented data per journey), booking creation with concurrency-safe holds, confirm/cancel flow.
6. **Frontend** — minimal React UI: search form → results list → seat picker → booking confirmation.
7. **Hardening** — integration tests for the booking race condition, rate limiting on public endpoints, structured logging, basic metrics.
8. **Stretch goals** (pick any): email confirmation via a mock mail service, admin panel for seeing all bookings, WebSocket live delay updates on a booked journey, price variation logic (peak/off-peak).

---

## 8. Why this maps well to "backend developer" skills

- Real external API integration with rate limits, inconsistent data, and no-timezone timestamps (data normalization).
- A genuine concurrency problem (seat booking) instead of a toy CRUD app.
- Auth done from scratch instead of SAP's built-in user management.
- Containerization + CI, which ABAP/SAP work rarely touches.
- A layered architecture (adapter/module boundaries) that's a direct, transferable analogue to the OOP class separation you already do in ABAP (`lcl_dashboard`, `lcl_events`, `lcl_screen`-style separation, just in a web stack).

---

**Stack decision for this build:** Python + FastAPI (chosen over NestJS to focus on Python skills).
