# Event Registration

A client-server event registration product with capacity-safe registration, FIFO waitlisting and promotion, manually typable tickets, atomic check-in, live organizer statistics, and durable email notifications.

The backend and frontend are separate applications. FastAPI owns the HTTP/SSE API and PostgreSQL state; React communicates with it over the network. Mailpit captures local SMTP messages for inspection.

## Current state

The implemented product supports event creation and rescheduling, capacity-safe participant registration, cancellation and re-registration, FIFO waitlisting and automatic promotion, fresh tickets per confirmed participation attempt, atomic one-time check-in, live organizer counts over SSE, and durable notification intent through a PostgreSQL transactional outbox. Cancelled registrations remain as history, and their tickets remain invalid.

PostgreSQL event-row locks serialize registration, cancellation, promotion, and re-registration seat decisions. Database constraints permit at most one active registration per normalized email and event. Notification generation is deduplicated in PostgreSQL; a separate worker claims and delivers pending messages through SMTP.

## Known limitations

- Authentication and authorization are intentionally not implemented. Organizer, rescheduling, and staff check-in routes must not be exposed publicly as-is; participant cancellation also relies on possession of event and registration identifiers.
- Participant state is held in the current browser flow. There is no authenticated participant account or recovery/list endpoint after a page refresh.
- SMTP delivery is at-least-once at the transport boundary. If the worker crashes after SMTP accepts a message but before the outbox row is marked `SENT`, the stale claim is retried and the recipient can receive a duplicate.
- Queued reminders are suppressed when a participant cancels or the event is rescheduled, and re-verified when the worker claims them. A cancellation or reschedule that commits after that verification and before SMTP accepts the message cannot recall it (see `docs/decisions/0020-reminder-suppression.md`).
- Mailpit and the included configuration are for local development, not production deployment.
- The API has no rate limiting or abuse controls.
- Outbox rows that fail permanently or exhaust their retries stay `FAILED` until an operator runs the `retry-failed` command; there is no alerting for them beyond the database state.
- After re-registration history exists, downgrading migration `20260914_0007` requires resolving duplicate historical event/email rows before the former lifetime-unique constraint can be restored; the upgrade path is non-destructive.

## What I would do next

- Add organizer/staff authentication and role-based authorization, then design a secure participant registration-management flow.
- Integrate a production email provider with provider-supported idempotency and delivery-event handling.
- Add structured logging, metrics, tracing, outbox-lag alerts, and operational dashboards.
- Add production deployment, secrets, TLS, backup, migration, and rollback configuration.
- Add rate limiting and request-abuse protection at the API edge.

## AI-assisted development

OpenAI Codex was used as the implementation agent to inspect the repository, implement focused tasks, run tests and local proof, diagnose failures, and record technical decisions. It was used to provide a repeatable implementation-and-verification workflow while keeping the work auditable. The repository does not contain evidence for a more specific model identifier, so none is claimed here.

Task specifications are in `docs/tasks/`, prompt evidence is in `docs/prompts/`, architecture and product decisions are in `docs/decisions/`, timestamped implementation evidence is in `docs/agent/development-log.md`, and demonstration/verification records are in `docs/demo/`.

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

Transient SMTP failures are retried with exponential backoff (`NOTIFICATION_RETRY_BASE_SECONDS`, `NOTIFICATION_RETRY_MAX_SECONDS`); a row that fails permanently or exhausts `NOTIFICATION_MAX_ATTEMPTS` is kept as `FAILED` with its error. To give failed rows one more delivery cycle:

```powershell
uv run python -m app.notification.worker retry-failed
uv run python -m app.notification.worker retry-failed --id <outbox-row-uuid>
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
- `/events/{event_id}` — event details, participant registration, cancellation, and re-registration
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

Registration, re-registration, cancellation/promotion, ticket issuance, and notification intent commit transactionally. PostgreSQL event-row locks serialize seat changes. Ticket check-in uses a conditional atomic update. SMTP happens only in the separate retrying outbox worker and has the at-least-once transport limitation described above.
