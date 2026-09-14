# Task 0003: Event Creation and Viewing

## Objective

Implement event creation and retrieval as the first backend domain slice, persisted in PostgreSQL and exposed through the required HTTP API.

## Scope

- Add the Event SQLAlchemy model with UUID identity, title, description, timezone-aware start time, capacity, and timestamps.
- Protect nonblank titles and positive capacities in both request validation and PostgreSQL constraints.
- Reject event creation unless `starts_at` is in the future.
- Add feature-oriented event schemas, repository, service, and routes.
- Implement `POST /api/events` and `GET /api/events/{event_id}`.
- Return structured 404 responses for unknown events.
- Add the first Alembic domain migration.
- Add PostgreSQL-backed API integration tests for valid creation/retrieval and invalid title, capacity, and date.
- Record the deliberate no-authentication scope decision.

## Out of scope

- Event updates/rescheduling (task 0014).
- Registration, capacity allocation, waitlists, tickets, statistics, and notifications.
- Event product screens or frontend API integration (task 0015).

## Acceptance criteria

1. A valid event can be created and retrieved with stable UUID and timestamp fields.
2. Blank titles, nonpositive capacities, and nonfuture start times return validation errors.
3. Event data is stored in PostgreSQL.
4. An unknown UUID returns HTTP 404.
5. The migration applies from the task 0002 database state.
6. Task-specific and existing tests, lint, and builds remain green.

## Verification

```powershell
$env:POSTGRES_PORT='5433'
docker compose up -d postgres
docker compose --profile test up -d postgres-test
$env:DATABASE_URL='postgresql+psycopg://event_registration:event_registration@localhost:5433/event_registration'
$env:TEST_DATABASE_URL='postgresql+psycopg://event_registration:event_registration@localhost:5434/event_registration_test'
cd backend
uv run alembic upgrade head
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
