# Event Registration

A client-server event registration product with capacity-safe registration, FIFO waitlisting and promotion, manually typable tickets, atomic check-in, live organizer statistics, and durable email notifications.

The backend and frontend are separate applications. FastAPI owns the HTTP/SSE API and PostgreSQL state; React communicates with it over the network. Mailpit captures local SMTP messages for inspection.

## Where the emails go

All email is delivered by the notification worker through SMTP to **Mailpit**, a local mail sink started by Docker Compose. Nothing leaves your machine: whatever address you register with, open **http://localhost:8025** to read the confirmation, waiting-list, promotion, reminder, and reschedule messages. Two things must be true to see mail: the worker terminal is running (see "Start locally") and Mailpit is up. To send through a real provider instead, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, and optionally `SMTP_STARTTLS=true`, `SMTP_USERNAME`, `SMTP_PASSWORD` in `backend/.env`; `FRONTEND_BASE_URL` controls the self-service links inside the messages.

## Current state

The implemented product supports event discovery for participants and organizers, event creation and rescheduling, capacity-safe participant registration, cancellation from the event page or the self-service link in every email, re-registration, a waiting-list email with the participant's place in line, FIFO waitlisting and automatic promotion, fresh tickets per confirmed participation attempt, atomic one-time check-in, live organizer counts over SSE, and durable notification intent through a PostgreSQL transactional outbox. Cancelled registrations remain as history, and their tickets remain invalid.

PostgreSQL event-row locks serialize registration, cancellation, promotion, and re-registration seat decisions. Database constraints permit at most one active registration per normalized email and event. Notification generation is deduplicated in PostgreSQL; a separate worker claims and delivers pending messages through SMTP.

## Known limitations

- Authentication and authorization are intentionally not implemented. Organizer, rescheduling, and staff check-in routes can be gated by one shared `ORGANIZER_KEY` for a public demo (no accounts, roles, or ownership); participant cancellation relies on possession of the registration link.
- There is no participant account. Every email links to the registration's self-service page (`/events/{event_id}/registrations/{registration_id}`); possession of that link, like possession of a ticket code, is what lets someone view or cancel the registration.
- SMTP delivery is at-least-once at the transport boundary. Each outbox row is claimed with an ownership token immediately before its own send, so a slow batch cannot be resent by a second worker and a stale owner cannot overwrite a newer claim; but if the worker crashes after SMTP accepts a message, or a single SMTP call outlives the claim lease, before the row is marked `SENT`, the row is reclaimed and the recipient can receive a duplicate.
- Queued reminders, confirmations, and promotions are suppressed when a participant cancels, queued reminders are suppressed when the event is rescheduled or has already started, and a burst of reschedules delivers only the latest notice per participant; reminders are re-verified when the worker claims them. A cancellation or reschedule that commits after that verification and before SMTP accepts the message cannot recall it (see `docs/decisions/0020-reminder-suppression.md`).
- Mailpit and the included configuration are for local development, not production deployment.
- The API has no rate limiting or abuse controls.
- Outbox rows that fail permanently or exhaust their retries stay `FAILED` until an operator runs the `retry-failed` command; there is no alerting for them beyond the database state.
- After re-registration history exists, downgrading migration `20260914_0007` requires resolving duplicate historical event/email rows before the former lifetime-unique constraint can be restored; the upgrade path is non-destructive. Likewise, downgrading `20260914_0005` refuses to run while promoted registrations keep their historical waitlist order and prints the deliberate normalising statement.
- Event capacity is capped at 1,000,000 seats.
- Every API request and every organizer SSE poll (once per `SSE_POLL_INTERVAL_SECONDS`, a few milliseconds each) borrows one pooled PostgreSQL connection. The pool is `DATABASE_POOL_SIZE` (5) plus `DATABASE_MAX_OVERFLOW` (10) connections per API process; raise them, or run more API processes, before serving hundreds of simultaneously open dashboards.

## What I would do next

- Add organizer/staff authentication and role-based authorization, then design a secure participant registration-management flow.
- Integrate a production email provider with provider-supported idempotency and delivery-event handling.
- Add structured logging, metrics, tracing, outbox-lag alerts, and operational dashboards.
- Move from the single-host Compose deployment to Cloud Run (API and worker) with Cloud SQL and a managed email provider; add secrets management, backups, monitoring, and rollback procedures.
- Add rate limiting and request-abuse protection at the API edge.

## AI-assisted development

Two AI coding agents were used, each recorded per task in the development log:

- **OpenAI Codex** implemented tasks 0001–0018 (foundation through the first post-review fixes) and produced the ChatGPT Astra 6 review in `docs/reviews/`. The repository holds no evidence of a more specific model identifier for those tasks, so none is claimed.
- **Claude Code with Claude Opus 5** implemented tasks 0019–0027: the four P1 and two P2 review follow-ups and the second-round review fixes.

In both cases the agent inspected the repository, implemented focused tasks, ran tests and local proof, diagnosed failures, and recorded technical decisions under the workflow in `docs/master-instruction.md`, so the work stays auditable. The incremental commit history lives at https://github.com/Vhovsepyan/event-registration; a zip export of the tree does not carry it.

Task specifications are in `docs/tasks/`, prompt evidence is in `docs/prompts/`, architecture and product decisions are in `docs/decisions/`, timestamped implementation evidence is in `docs/agent/development-log.md`, and demonstration/verification records are in `docs/demo/`.

## Prerequisites

- Python 3.13.15
- [uv](https://docs.astral.sh/uv/)
- Node.js 22.12 or newer (24 LTS recommended; the locked Vitest 5 refuses to start on Node 18/20) with npm
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

The worker survives transient database or network failures by logging the failed cycle and retrying with backoff. Transient SMTP failures (4yz replies, connection errors) are retried with exponential backoff (`NOTIFICATION_RETRY_BASE_SECONDS`, `NOTIFICATION_RETRY_MAX_SECONDS`); a row that fails permanently or exhausts `NOTIFICATION_MAX_ATTEMPTS` is kept as `FAILED` with its error. To give failed rows one more delivery cycle:

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

## Deploy the demo on one host

`docker-compose.deploy.yml` adds container images for the API, worker, and frontend plus Caddy for HTTPS, with PostgreSQL and Mailpit kept internal and the Mailpit inbox published under `/mail` behind basic auth:

```powershell
cp .env.deploy.example .env.deploy   # set the password, domain, organizer key, and inbox hash
docker compose --env-file .env.deploy -f docker-compose.yml -f docker-compose.deploy.yml up -d --build
```

The step-by-step guide for a Google Cloud `e2-micro`, the variables, and the verified local rehearsal are in [docs/deploy/google-cloud-vm.md](docs/deploy/google-cloud-vm.md). The local development workflow above is unchanged.

## Product routes

- `/` — participant home: upcoming events with seats left or waiting-list size
- `/organizer` — organizer area: create an event and open any event's dashboard
- `/events/{event_id}` — event details, participant registration, cancellation, and re-registration
- `/events/{event_id}/registrations/{registration_id}` — self-service page linked from every email: status, ticket, cancel
- `/events/{event_id}/organizer` — live organizer dashboard and rescheduling
- `/tickets/{ticket_code}` — ticket details and status
- `/check-in` — manual staff check-in

Authentication is deliberately outside the product scope. For a deployment reachable from the internet, set `ORGANIZER_KEY` in `backend/.env`: event creation, rescheduling, statistics, the live stream, and check-in then require it (`X-Organizer-Key` header; the dashboard stream passes it as `organizer_key`). The organizer and check-in screens ask for the key once and remember it in the browser. The key must be printable ASCII without spaces (it travels in an HTTP header; a browser cannot send other characters), which is validated at API startup and in the prompt. Participant routes stay open. Leave it unset for local development.

Health endpoints: `GET /health` is process liveness (no database); `GET /ready` executes `SELECT 1` and returns 503 while PostgreSQL is unreachable, for load balancers and container health checks.

## Tests and quality checks

Start the isolated PostgreSQL test service first:

```powershell
$env:POSTGRES_TEST_PORT = "5434"
docker compose --profile test up -d postgres-test
```

Backend (tests use PostgreSQL at port 5434 by default; the fixture drops and recreates every table, so it refuses any `TEST_DATABASE_URL` whose database name does not end in `_test`). Alembic reads `DATABASE_URL`, so point it at the test service for the migration and drift checks; the test fixture also removes `alembic_version`, so the checks and the suite can run in any order:

```powershell
cd backend
uv sync --locked
uv run ruff check .
uv run ruff format --check .
$env:DATABASE_URL = "postgresql+psycopg://event_registration:event_registration@localhost:5434/event_registration_test"
uv run alembic upgrade head
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

Two-browser live-update proof (development PostgreSQL must be migrated and reachable through `DATABASE_URL`; Playwright starts its own API and Vite servers on ports 8000/5173, or set `PLAYWRIGHT_REUSE_SERVERS=1` to run against the ones you already have running):

```powershell
cd frontend
npm run test:e2e
```

See [the multi-client verification](docs/demo/multi-client-verification.md) for prerequisites and its manual equivalent. The complete demonstration order is in [the product demo script](docs/demo/demo-script.md).

## API summary

- `GET /api/events[?include_past=true]` (upcoming events with confirmed/waitlisted counts and seats left); `POST /api/events`; `GET/PATCH /api/events/{event_id}`
- `POST /api/events/{event_id}/registrations`; `GET /api/events/{event_id}/registrations/{registration_id}`
- `POST /api/events/{event_id}/registrations/{registration_id}/cancel`
- `GET /api/tickets/{code}`; `POST /api/check-ins`
- `GET /api/events/{event_id}/stats`
- `GET /api/events/{event_id}/stats/stream` (SSE)
- `GET /health` (liveness); `GET /ready` (database readiness)
- With `ORGANIZER_KEY` set: `POST /api/events`, `PATCH /api/events/{event_id}`, both stats routes, and `POST /api/check-ins` require `X-Organizer-Key`

Registration, re-registration, cancellation/promotion, ticket issuance, and notification intent commit transactionally. PostgreSQL event-row locks serialize seat changes. Ticket check-in uses a conditional atomic update. SMTP happens only in the separate retrying outbox worker, which claims one row at a time under an ownership token, defers transient failures with backoff, retires permanent failures as `FAILED`, suppresses obsolete reminders, and has the at-least-once transport limitation described above.
