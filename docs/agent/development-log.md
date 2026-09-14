# Development Log

## 2026-09-14T13:48:12+04:00 — Task 0001 started

- Task: Repository and Python/FastAPI foundation
- Agent/tool: OpenAI Codex using PowerShell, `uv`, pytest, Git, and Docker tooling
- Prompt/reference: `docs/master-instruction.md`, `docs/IMPLEMENTATION_PLAN.md`, and the user instruction that initiated autonomous task execution
- Existing work: Preserved the repository directories, bare `uv` metadata, Python 3.13.15 pin, root README, and ignore rules
- Decisions: The Java/Spring `AGENTS.md` discovered in a sibling repository is outside this repository and does not apply; use this repository's Python/FastAPI plan as authoritative; keep PostgreSQL infrastructure in task 0001 and defer Mailpit to task 0011; expose only an infrastructure health route
- Status: Completed at 2026-09-14T13:53:23+04:00
- Result: Added an installable FastAPI backend shell, typed settings, SQLAlchemy/Alembic foundations, feature packages, PostgreSQL Compose service, health endpoint, smoke tests, and architecture/prompt evidence. No domain behavior or frontend tooling was added.
- Failures diagnosed: Ruff found import/formatting issues in generated Alembic code; these were fixed. FastAPI's compatibility `TestClient` produced dependency deprecation warnings; the smoke test now uses direct async `httpx` ASGI transport. Host port 5432 was occupied by an unrelated running container; Compose now supports a `POSTGRES_PORT` override and this project's database was verified on 5433 without disturbing the existing service.
- Tests/checks: `uv lock --check`; `uv sync --locked`; `uv run python --version` (3.13.15); `uv run ruff check .`; `uv run ruff format --check .`; `uv run pytest` (2 passed); `uv build`; offline Alembic upgrade generation; online Alembic upgrade/current against PostgreSQL 17; `docker compose config --quiet`; live Uvicorn startup and `GET /health` (200); Git whitespace checks.
- Self-review: All task 0001 acceptance criteria pass. No Critical or Important findings remain. The only exposed route is infrastructure health, migrations contain no domain schema, and `frontend/` remains uninitialized.

## 2026-09-14T13:56:52+04:00 — Task 0002 started

- Task: React frontend foundation
- Agent/tool: OpenAI Codex using PowerShell, npm, Vite, TypeScript, Oxlint, Vitest, Testing Library, Git, and the existing backend verification tools
- Prompt/reference: User instruction to proceed with task 0002, `docs/IMPLEMENTATION_PLAN.md`, and `docs/tasks/0002-react-frontend-foundation.md`
- Existing work: Preserved the complete task 0001 backend; the frontend contains only a `.gitkeep` placeholder
- Decisions: Establish routing and testing now, expose only neutral shell/not-found routes, and defer all event UI and backend integration to their defined tasks
- Status: Completed at 2026-09-14T14:03:50+04:00
- Result: Replaced the frontend placeholder with an independently runnable React 19 and TypeScript application using Vite, React Router, Oxlint, Vitest, jsdom, and Testing Library. Added a responsive accessible shell, root/not-found routes, environment typing, lockfile, tests, and local commands without product behavior or backend calls.
- Failures diagnosed: The initial npm command reached the execution timeout and left an inconsistent `node_modules`; a forced clean lockfile install repaired it. The first Vitest run failed because test globals were intentionally not configured; explicit Vitest imports fixed both runtime and TypeScript failures.
- Tests/checks: Clean `npm ci` (0 vulnerabilities); `npm run lint`; `npm test -- --run` (2 passed); `npm run build`; live Vite startup with successful root and history-fallback HTTP responses; backend `uv lock --check`, `uv sync --locked`, Ruff lint/format checks, and pytest (2 passed); Docker Compose validation; Git whitespace checks.
- Self-review: Corrected the root README's stale frontend description. All task 0002 acceptance criteria pass, no Critical or Important findings remain, no backend files changed, and task 0003 functionality was not started.

## 2026-09-14T14:12:08+04:00 — Task 0003 started

- Task: Event creation and viewing
- Agent/tool: OpenAI Codex using FastAPI, SQLAlchemy, Alembic, Pydantic, pytest/httpx, PostgreSQL 17, Ruff, Docker Compose, and Git
- Prompt/reference: Updated `docs/IMPLEMENTATION_PLAN.md`, the user's autonomous continuation instruction, and `docs/tasks/0003-event-creation-and-viewing.md`
- Existing work: Tasks 0001 and 0002 are committed and green; the updated implementation plan is preserved as a user-authored working-tree change
- Decisions: Implement the event feature as a vertical backend slice; enforce title/capacity invariants at API and database boundaries; defer rescheduling and frontend integration; keep authentication out of initial scope as explicitly permitted
- Status: Completed at 2026-09-14T14:16:29+04:00
- Result: Added the PostgreSQL Event model and migration, validated create/read schemas, feature repository/service/routes, structured 404 handling, isolated PostgreSQL integration infrastructure, and API/database invariant tests. No registration behavior or frontend product screen was introduced.
- Failures diagnosed: Ruff corrected generated/import and Python 3.13 modernization issues. Initial API tests passed, but self-review found that destructive schema resets defaulted to the development database; a profile-gated ephemeral `postgres-test` service and dedicated test URL now isolate all integration tests.
- Tests/checks: Migration downgrade/upgrade from base; `alembic check` (no drift); Ruff lint/format; pytest (9 passed) against PostgreSQL 17; frontend lint (green), Vitest (2 passed), and production build; default/test Docker Compose validation; OpenAPI route inspection; Git whitespace checks.
- Self-review: Event validation exists at the API boundary and title/capacity invariants are also PostgreSQL constraints with direct tests. Test data cannot affect the development database. All task 0003 acceptance criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:17:09+04:00 — Task 0004 started

- Task: Participant registration
- Agent/tool: OpenAI Codex using FastAPI, SQLAlchemy, Alembic, Pydantic EmailStr, pytest/httpx, PostgreSQL, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md`, the autonomous continuation instruction, and `docs/tasks/0004-participant-registration.md`
- Existing work: Task 0003 event APIs and isolated PostgreSQL test infrastructure are committed and green
- Decisions: Establish registration identity/idempotency and confirmed state now; defer capacity locking/waitlisting, tickets, and notifications to tasks 0005, 0006, and 0011/0012
- Status: Completed at 2026-09-14T14:19:26+04:00
- Result: Added the registration status/data model and migration, normalized-email identity, registration repository/service/API, EmailStr validation, confirmed-state creation, idempotent repeat behavior, and PostgreSQL integration/constraint tests.
- Failures diagnosed: Migration formatting required Ruff normalization; the PostgreSQL enum migration was made explicitly reversible with a non-auto-creating dialect enum so repeated upgrade/downgrade does not collide with its type.
- Tests/checks: Registration migration downgrade/upgrade; `alembic check` (no drift); Ruff lint/format; pytest (14 passed) against isolated PostgreSQL; frontend lint, Vitest (2 passed), and production build; test-profile Compose validation; Git whitespace checks.
- Self-review: The event/email uniqueness invariant is protected and tested in PostgreSQL, normalization is case-insensitive and trims input, and API repeats return the original record. Concurrency races are explicitly deferred to task 0005. All task 0004 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:20:11+04:00 — Task 0005 started

- Task: Capacity concurrency and waitlist
- Agent/tool: OpenAI Codex using PostgreSQL row locks, SQLAlchemy transactions, FastAPI/httpx, pytest concurrent tasks/thread synchronization, Alembic, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` concurrency strategy and `docs/tasks/0005-capacity-concurrency-and-waitlist.md`
- Existing work: Registration identity and confirmed-state behavior from task 0004 are committed and green
- Decisions: Serialize all allocation decisions on the Event row; derive confirmed count from registrations; allocate waitlist order under the lock; enforce state shape and unique queue positions in PostgreSQL
- Status: Completed at 2026-09-14T14:21:56+04:00
- Result: Registration allocation now locks the event row, derives confirmed occupancy from PostgreSQL, confirms within capacity, assigns monotonic FIFO waitlist positions when full, and preserves duplicate-email idempotency inside one transaction. Added state/queue constraints, index, reversible migration, and forced-overlap concurrency coverage.
- Failures diagnosed: Ruff normalized imports/long generated migration lines. No runtime or concurrency failures remained after implementing the lock discipline.
- Tests/checks: Waitlist migration downgrade/upgrade; `alembic check` (no drift); Ruff lint/format; pytest (17 passed), including a barrier-forced overlapping last-seat test against PostgreSQL; frontend lint, Vitest (2 passed), and production build; test-profile Compose validation; Git whitespace checks.
- Self-review: PostgreSQL is the serialization authority; every registration allocation locks the event before identity/capacity/queue reads, waitlist positions are unique per event, and state shape is database-constrained. All task 0005 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:22:39+04:00 — Task 0006 started

- Task: Ticket generation and display
- Agent/tool: OpenAI Codex using Python `secrets`, FastAPI, SQLAlchemy, Alembic, Pydantic, PostgreSQL, pytest/httpx, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` ticket model/API requirements and `docs/tasks/0006-ticket-generation-and-display.md`
- Existing work: Capacity-safe confirmed/waitlisted allocation from task 0005 is committed and green
- Decisions: Use a 60-bit ambiguity-reduced grouped code; create tickets in the allocation transaction only for confirmed registrations; return event and registration context from ticket lookup
- Status: Completed at 2026-09-14T14:24:48+04:00
- Result: Added Ticket persistence/migration, 60-bit grouped code generation, atomic ticket issuance for confirmed registrations, optional registration ticket responses, and ticket detail lookup with event/registration context. Waitlisted registrations remain ticketless.
- Failures diagnosed: Ruff reformatted the generated migration; ticket detail construction was kept explicit so required nested event/status fields are validated rather than inferred from unrelated ORM attributes.
- Tests/checks: Ticket migration downgrade/upgrade; `alembic check` (no drift); Ruff lint/format; pytest (20 passed) against PostgreSQL, including issue/retrieve/waitlist/idempotency cases; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; Git whitespace checks.
- Self-review: Codes use `secrets` with 60 bits of entropy and exclude ambiguous characters, uniqueness is database-enforced, repeated registration returns the same ticket, and issuance shares the capacity transaction. All task 0006 criteria pass with no remaining Critical or Important findings.
