# Event Registration

A client-server event registration product with capacity-safe registration, FIFO waitlisting and promotion, manually typable tickets, atomic check-in, live organizer statistics, and durable email notifications.

The backend and frontend are separate applications. FastAPI owns the HTTP/SSE API and PostgreSQL state; React communicates with it over the network. Mailpit captures local SMTP messages for inspection.

## Prerequisites

- Python 3.13.15
- [uv](https://docs.astral.sh/uv/)
- Node.js with npm
- Docker with Docker Compose
- Microsoft Edge for the default Playwright run, or Google Chrome with `PLAYWRIGHT_CHANNEL=chrome`

## Repository structure

- `backend/` — Python 3.13.15, FastAPI, SQLAlchemy, Alembic, PostgreSQL, and the notification worker
- `frontend/` — React, TypeScript, Vite, React Router, native EventSource, Vitest, and Playwright
- `docs/tasks/` — task specifications
- `docs/decisions/` — architecture and product decisions
- `docs/prompts/` — AI prompt/reference evidence
- `docs/agent/development-log.md` — timestamped implementation evidence
- `docs/demo/` — manual and automated demo instructions

## Start locally

From the repository root, start PostgreSQL and Mailpit:

```powershell
docker compose up -d
```

If port 5432 is occupied, use another host port and carry the matching URL into every backend shell. This repository was finally verified on port 5433:

```powershell
$env:POSTGRES_PORT = "5433"
docker compose up -d
$env:DATABASE_URL = "postgresql+psycopg://event_registration:event_registration@localhost:5433/event_registration"
```

In a backend terminal:

```powershell
cd backend
uv sync --locked
uv run python --version
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Python must report `3.13.15`. The API is at `http://localhost:8000`, health is at `http://localhost:8000/health`, and OpenAPI is at `http://localhost:8000/docs`.

In a second backend terminal, with the same `DATABASE_URL` when a port override is used, start durable email/reminder processing:

```powershell
cd backend
uv run python -m app.notification.worker
```

In a frontend terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Mailpit's inbox is at `http://localhost:8025`. The frontend defaults to `http://localhost:8000`; copy `frontend/.env.example` to `frontend/.env` to change `VITE_API_BASE_URL`.

## Product routes

- `/` — create an event
- `/events/{event_id}` — event details and participant registration
- `/events/{event_id}/organizer` — live organizer dashboard and rescheduling
- `/tickets/{ticket_code}` — ticket details and status
- `/check-in` — manual staff check-in

Authentication is deliberately outside the initial product scope. Organizer and staff routes must not be exposed publicly without a separate security design.

## Tests and quality checks

Start the isolated PostgreSQL test service first:

```powershell
$env:POSTGRES_TEST_PORT = "5434"
docker compose --profile test up -d postgres-test
```

Backend (tests use PostgreSQL at port 5434 by default):

```powershell
cd backend
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run alembic check
uv run pytest
```

Frontend:

```powershell
cd frontend
npm ci
npm run lint
npm test -- --run
npm run build
```

Two-browser live-update proof (development PostgreSQL must be migrated and reachable through `DATABASE_URL`):

```powershell
cd frontend
npm run test:e2e
```

See [the multi-client verification](docs/demo/multi-client-verification.md) for prerequisites and its manual equivalent. The complete demonstration order is in [the product demo script](docs/demo/demo-script.md).

## API summary

- `POST /api/events`; `GET/PATCH /api/events/{event_id}`
- `POST /api/events/{event_id}/registrations`
- `POST /api/events/{event_id}/registrations/{registration_id}/cancel`
- `GET /api/tickets/{code}`; `POST /api/check-ins`
- `GET /api/events/{event_id}/stats`
- `GET /api/events/{event_id}/stats/stream` (SSE)

Registration, cancellation/promotion, ticket issuance, and notification intent commit transactionally. PostgreSQL event-row locks serialize seat changes. Ticket check-in uses a conditional atomic update. SMTP happens only in the separate retrying outbox worker.
