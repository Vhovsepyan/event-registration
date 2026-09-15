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

## 2026-09-14T14:25:43+04:00 — Task 0007 started

- Task: Cancellation and FIFO promotion
- Agent/tool: OpenAI Codex using PostgreSQL locks/transactions, FastAPI, SQLAlchemy, Alembic, pytest/httpx, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` waitlist rules and `docs/tasks/0007-cancellation-and-fifo-promotion.md`
- Existing work: Capacity-safe registration and ticket issuance from tasks 0005/0006 are committed and green
- Decisions: Reuse event-row locking for cancellation; retain historical waitlist order after promotion/cancellation to prevent reuse; connect promotion outbox rows in task 0011 when the required durable model exists
- Status: Completed at 2026-09-14T14:27:53+04:00
- Result: Added event-locked cancellation, ticket invalidation, atomic earliest-waitlisted promotion, promoted ticket issuance, idempotent repeat behavior, historical queue-order preservation, response schemas/API, migration, and PostgreSQL integration tests.
- Failures diagnosed: Ruff identified unused test bindings and normalized formatting; these were corrected before final verification.
- Tests/checks: Waitlist-history migration downgrade/upgrade; `alembic check` (no drift); Ruff lint/format; pytest (23 passed) against PostgreSQL; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; Git whitespace checks.
- Self-review: New registration and cancellation now share the Event serialization lock, cancellation/promotion/ticket changes share one transaction, original tickets invalidate, FIFO order is stable, and repeat cancellation cannot promote twice. Promotion outbox creation remains explicitly queued for task 0011. All task 0007 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:28:25+04:00 — Task 0008 started

- Task: Atomic check-in
- Agent/tool: OpenAI Codex using SQLAlchemy Core update/returning, PostgreSQL, FastAPI, pytest/httpx concurrent requests, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` atomic check-in rules and `docs/tasks/0008-atomic-check-in.md`
- Existing work: Active/inactivated ticket lifecycle from tasks 0006/0007 is committed and green
- Decisions: Make success depend only on one conditional database update; use a follow-up read solely to classify a failed update as already-used versus invalid
- Status: Completed at 2026-09-14T14:30:03+04:00
- Result: Added the check-in API and typed outcomes backed by one conditional PostgreSQL update/returning statement, normalized manual codes, repeat/invalid classification, and sequential plus forced-overlap integration tests.
- Failures diagnosed: Ruff normalized formatting. Self-review found that a previously checked-in ticket cancelled later could be misclassified as already checked in; invalidation now takes precedence and a regression test covers it.
- Tests/checks: `alembic check` (no drift); Ruff lint/format; pytest (27 passed), including overlapping same-ticket requests against PostgreSQL; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; Git whitespace checks.
- Self-review: Success depends solely on the atomic conditional update, concurrent losers observe the committed timestamp and return already checked in, and unknown/invalidated tickets remain invalid. All task 0008 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:30:30+04:00 — Task 0009 started

- Task: Organizer statistics
- Agent/tool: OpenAI Codex using SQLAlchemy aggregate queries, FastAPI, PostgreSQL, pytest/httpx, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` organizer statistics rules and `docs/tasks/0009-organizer-statistics.md`
- Existing work: Registration, waitlist, cancellation/promotion, ticket, and check-in state are committed and green
- Decisions: Derive every statistic from authoritative rows on request; count only non-invalidated checked-in tickets attached to currently confirmed registrations
- Status: Completed at 2026-09-14T14:32:23+04:00
- Result: Added organizer snapshot service/API returning capacity, confirmed, waitlisted, and active checked-in counts derived from authoritative tables, with lifecycle and unknown-event tests.
- Failures diagnosed: Initial implementation used separate aggregate statements; self-review identified possible mixed snapshots under READ COMMITTED. All values now come from one SQL statement and one database snapshot.
- Tests/checks: `alembic check` (no drift); Ruff lint/format; pytest (29 passed) against PostgreSQL; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; Git whitespace checks.
- Self-review: No counters are duplicated, cancelled registrations/invalidated tickets cannot inflate results, and one-statement evaluation makes each response internally consistent. All task 0009 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:33:10+04:00 — Task 0010 started

- Task: SSE live dashboard
- Agent/tool: OpenAI Codex using FastAPI StreamingResponse, asyncio, SQLAlchemy/PostgreSQL polling, pytest/httpx, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` live-update rules and `docs/tasks/0010-sse-live-dashboard.md`
- Existing work: One-statement authoritative statistics endpoint from task 0009 is committed and green
- Decisions: Use native SSE with change-only PostgreSQL polling, one short-lived session per read, and one independent generator per client; avoid WebSockets and external pub/sub
- Status: Completed at 2026-09-14T14:34:45+04:00
- Result: Added the SSE statistics stream endpoint, change-only event encoding, configurable polling, per-snapshot short-lived sessions, disconnect handling, cache/buffering headers, and tests for endpoint format plus two independent clients observing one update.
- Failures diagnosed: Ruff normalized imports. Self-review identified a potential busy loop from a nonpositive configured poll interval; Pydantic now rejects such configuration.
- Tests/checks: `alembic check` (no drift); Ruff lint/format; pytest (31 passed), including dual-stream SSE tests against PostgreSQL; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; Git whitespace checks.
- Self-review: Streaming uses native SSE, database reads execute off the event loop with a fresh session per snapshot, only changes emit, and no external pub/sub infrastructure was added. All task 0010 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:35:50+04:00 — Task 0011 started

- Task: Notification outbox and Mailpit
- Agent/tool: OpenAI Codex using SQLAlchemy/PostgreSQL JSONB and conflict handling, Python SMTP, Mailpit/Docker Compose, pytest fakes, Ruff, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` email/outbox rules and `docs/tasks/0011-notification-outbox-and-mailpit.md`
- Existing work: Registration and promotion transactions are committed and have documented notification integration points
- Decisions: Persist notification intent with business state; dedupe in PostgreSQL; perform SMTP only in a separately invoked polling worker; retain failed rows as pending for later retry; pin locally verified Mailpit v1.27.8
- Status: Completed at 2026-09-14T14:39:39+04:00
- Result: Added the PostgreSQL JSONB notification outbox/migration, atomic confirmed/promotion enqueues, semantic dedupe, multi-worker-safe claim/recovery, SMTP adapter, retrying worker entry point, pinned Mailpit service, and worker/outbox integration tests.
- Failures diagnosed: One test compared a PostgreSQL UUID to its JSON string representation; the assertion was corrected. Ruff normalized migration formatting.
- Tests/checks: Outbox migration downgrade/upgrade; `alembic check` (no drift); Ruff lint/format; pytest (33 passed), including dedupe and fail-then-retry delivery; frontend lint, Vitest (2 passed), and build; default/test Compose validation; live Mailpit API HTTP 200; Git whitespace checks.
- Self-review: Business commits contain durable intent but no SMTP calls, duplicate producers are database-safe, concurrent workers skip locked claims, crashed claims can age out, and failed sends return to pending with attempts/errors recorded. All task 0011 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:40:18+04:00 — Task 0012 started

- Task: Confirmation and promotion emails
- Agent/tool: OpenAI Codex using typed Python templates, transactional outbox services, SMTP/Mailpit, PostgreSQL, pytest, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` confirmation/promotion email requirements and `docs/tasks/0012-confirmation-and-promotion-emails.md`
- Existing work: Durable outbox, worker, retry behavior, and Mailpit infrastructure from task 0011 are committed and green
- Decisions: Keep rendering deterministic and plain-text; include event title, ISO scheduled time, and ticket code; expose producer-specific enqueue methods over the generic deduplicated primitive
- Status: Completed at 2026-09-14T14:42:38+04:00
- Result: Added deterministic confirmation/promotion templates and producer-specific outbox methods containing event, schedule, and ticket details. Verified the real worker delivered a confirmation through SMTP to Mailpit and the inbox API exposed the expected recipient/subject.
- Failures diagnosed: A test compared equivalent UTC strings rendered as `Z` and `+00:00`; expected time is now normalized semantically. Live standalone-worker verification exposed an incomplete SQLAlchemy model registry; the worker now explicitly loads all database models before claiming ORM rows.
- Tests/checks: `alembic check` (no drift); Ruff lint/format; pytest (34 passed) including both message types/content; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; live Uvicorn registration → outbox worker → SMTP → Mailpit delivery (one message, expected subject/recipient); Git whitespace checks.
- Self-review: Templates contain actionable event/time/ticket information, producer methods retain database dedupe, worker startup is independent of API imports, and actual local delivery is proven. All task 0012 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:43:13+04:00 — Task 0013 started

- Task: 24-hour event reminders
- Agent/tool: OpenAI Codex using PostgreSQL due queries, transactional outbox dedupe, worker polling, pytest, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` reminder rules and `docs/tasks/0013-event-reminders.md`
- Existing work: Outbox worker and deterministic email templates from tasks 0011/0012 are committed and green
- Decisions: Derive due reminders from database state every poll; include confirmed active-ticket holders only; identify a reminder by event, registration, and exact scheduled time
- Status: Completed at 2026-09-14T14:44:50+04:00
- Result: Added reminder template/producer, PostgreSQL due-window discovery, worker-cycle generation, configured lead time, active confirmed-ticket filtering, schedule-specific dedupe, and idempotency/window tests.
- Failures diagnosed: The reminder content test compared equivalent `Z` and `+00:00` UTC representations; it now compares a normalized ISO representation.
- Tests/checks: `alembic check` (no drift); Ruff lint/format; pytest (36 passed), including repeat generation and waitlist exclusion; frontend lint, Vitest (2 passed), and build; test-profile Compose validation; Git whitespace checks.
- Self-review: Eligibility is recalculated from PostgreSQL on every worker poll, no in-memory timer is required, cancelled/waitlisted users are excluded, and the exact schedule participates in dedupe. All task 0013 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:45:34+04:00 — Task 0014 started

- Task: Event rescheduling and notifications
- Agent/tool: OpenAI Codex using FastAPI PATCH, PostgreSQL event locking, SQLAlchemy, transactional outbox, pytest/httpx, Ruff, Docker Compose, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` reschedule rules and `docs/tasks/0014-event-rescheduling-and-notifications.md`
- Existing work: Events, active participant state, outbox delivery, and schedule-specific reminders are committed and green
- Decisions: Restrict PATCH to future `starts_at`; serialize rescheduling with seat operations on the Event row; notify confirmed and waitlisted but not cancelled participants; dedupe against the new schedule
- Status: Completed at 2026-09-14T14:56:12+04:00
- Result: Added event rescheduling through a validated PATCH endpoint, serialized the update on the Event row, and atomically queued deterministic reschedule notifications for every confirmed and waitlisted participant. Schedule-specific notification and reminder identities allow a genuinely new event time to produce new messages while a no-op update remains idempotent.
- Failures diagnosed: The first reschedule test compared equivalent UTC timestamps rendered as `Z` and `+00:00`; expected timestamps are now normalized before comparison.
- Tests/checks: `alembic check` (no drift); Ruff lint/format; pytest (39 passed), including active-recipient, no-op dedupe, new-reminder-schedule, and invalid-past cases; frontend lint, Vitest (2 passed), and production build; test-profile Compose validation; Git whitespace checks.
- Self-review: The schedule and all notification intents change in one transaction, cancelled registrations are excluded, both active statuses are included, past dates are rejected, and dedupe includes the new schedule. All task 0014 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T14:57:56+04:00 — Task 0015 started

- Task: Frontend integration and UX completion
- Agent/tool: OpenAI Codex using React, TypeScript, React Router, native EventSource, Testing Library/Vitest, FastAPI CORS, Oxlint, Vite, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` frontend/API/testing requirements and `docs/tasks/0015-frontend-integration-and-ux-completion.md`
- Existing work: The backend product APIs through task 0014 and the neutral React/Vite foundation are committed and green
- Decisions: Use route-local React state and a small typed fetch client; load an initial organizer snapshot before subscribing to native SSE; permit only configured local frontend origins; defer multi-browser automation to task 0016
- Status: Completed at 2026-09-14T15:09:36+04:00
- Result: Replaced the frontend shell with responsive event creation, participant registration, ticket, staff check-in, and organizer dashboard routes; added typed HTTP integration, native SSE updates, organizer rescheduling, accessible loading/error/result states, configured CORS, and focused UI tests.
- Failures diagnosed: Parameterized check-in tests initially retained prior rendered trees because Vitest globals did not provide Testing Library's automatic cleanup hook; explicit cleanup fixed isolation. The first backend verification attempt was sandboxed from uv's user cache and was rerun with the required permission. Self-review also found the organizer had no way to invoke the completed reschedule API and the frontend README still described integration as future work; both were corrected.
- Tests/checks: Ruff lint/format; `alembic check` (no drift); backend pytest (40 passed); Oxlint; Vitest (7 passed, including confirmed registration, all check-in outcomes, and live statistics); TypeScript/Vite production build; test-profile Compose validation; Git whitespace checks.
- Self-review: Every required screen is routed and network-backed, the dashboard loads an authoritative initial snapshot and subscribes with native EventSource, configured CORS is narrowly scoped, responsive layouts retain labelled inputs and visible focus states, and no domain behavior was duplicated in the client. All task 0015 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T15:11:25+04:00 — Task 0016 started

- Task: Concurrency and multi-client proof
- Agent/tool: OpenAI Codex using PostgreSQL forced-overlap pytest cases, Playwright, installed Chromium browser channels, two isolated browser contexts, FastAPI/Uvicorn, Vite, native SSE, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` concurrency/multi-client/final-proof requirements and `docs/tasks/0016-concurrency-and-multi-client-proof.md`
- Existing work: Database concurrency coverage and SSE service tests are committed; task 0015 provides the full browser journeys
- Decisions: Exercise real HTTP, PostgreSQL, and SSE from two isolated contexts; use a locally installed browser channel to avoid storing downloaded browser binaries; retain the focused database race tests as the authoritative invariant proof
- Status: Completed at 2026-09-14T15:22:57+04:00
- Result: Added a Playwright proof that starts the separate backend/frontend processes, creates and registers through the real UI, operates two isolated browser contexts, checks in the issued ticket in browser B, and verifies browser A changes from zero to one checked-in through SSE without refresh. Added repeatable automated/manual instructions and accessible statistic labels.
- Failures diagnosed: Vitest initially discovered the Playwright file, so its include pattern is now restricted to frontend unit tests. The first browser run used a `127.0.0.1` page origin while CORS permits `localhost`, causing a correctly blocked fetch; the browser base URL now matches the configured origin. The next run proved the count update but a broad `Live` locator also matched the generated event title; an exact locator fixed the assertion. Playwright artifacts are now ignored.
- Tests/checks: Focused PostgreSQL concurrency suite (7 passed); Playwright two-context live-update proof (1 passed); Ruff lint/format; `alembic check` (no drift); backend pytest (40 passed); Oxlint; Vitest (7 passed); TypeScript/Vite build; test-profile Compose validation; Git whitespace checks.
- Self-review: The browser scenario uses real network boundaries, PostgreSQL, issued tickets, atomic check-in, and native SSE; no API calls are bypassed and no page refresh occurs. Forced-overlap backend tests remain the direct proof for the last-seat and one-time-check-in invariants. All task 0016 criteria pass with no remaining Critical or Important findings.

## 2026-09-14T15:25:03+04:00 — Task 0017 started

- Task: Documentation, decision log, demo, and final verification
- Agent/tool: OpenAI Codex using README/demo documentation, Docker Compose, PostgreSQL/Alembic, uv, pytest, Vite/Vitest/Oxlint, Playwright, Uvicorn, Mailpit API/SMTP, PowerShell, and Git
- Prompt/reference: `docs/IMPLEMENTATION_PLAN.md` evidence/local-development/final-proof requirements and `docs/tasks/0017-documentation-demo-and-final-verification.md`
- Existing work: Tasks 0001–0016 are independently committed and green; all required product behavior and automated two-client coverage exist
- Decisions: Treat task 0017 as handoff/proof only; verify an empty ephemeral PostgreSQL instance without deleting persistent development data; record exact port-override commands because this machine uses 5433 for the project database
- Status: Completed at 2026-09-14T15:36:13+04:00
- Result: Replaced foundation-era handoff text with exact infrastructure, backend, worker, frontend, test, and Playwright instructions; added a complete product demo and final verification record; audited all task/prompt/decision evidence; and proved the application from an empty PostgreSQL schema through live HTTP, SMTP/Mailpit, concurrency, and two-client SSE behavior.
- Failures diagnosed: The first clean `npm ci` could not replace a native build module because temporary startup verification had stopped wrapper processes but left their repository-scoped Uvicorn, Vite, and worker child processes alive. Their exact command lines and process IDs were verified, only those processes were stopped, ports 8000/5173 were confirmed free, and clean install plus all frontend checks then passed. The first Mailpit polling expression mishandled PowerShell's singleton recipient shape even though PostgreSQL showed the row as SENT; direct inbox inspection and a corrected unique-subject/recipient assertion confirmed real delivery.
- Tests/checks: Empty tmpfs PostgreSQL recreation and base-to-head migration; `uv lock --check`; locked backend sync; Python 3.13.15; Ruff lint/format; Alembic drift check; backend pytest (40 passed); four focused final-invariant tests; backend sdist/wheel build; clean `npm ci` (0 vulnerabilities); Oxlint; Vitest (7 passed); TypeScript/Vite build; Playwright two-context proof (1 passed); standalone backend/frontend HTTP 200; live API → worker → SMTP → Mailpit delivery; default/test Compose validation; evidence/decision audit; Git whitespace checks.
- Self-review: Found and fixed an Important mismatch where Playwright's fallback database port and the multi-client instructions assumed this machine's 5433 override instead of the project's standard 5432 default. README commands now match the repository and separate-process architecture, port overrides propagate explicitly, security scope is called out, all minimum decisions and task evidence exist, the final demo covers every visible outcome, and every final-proof item in the implementation plan has direct recorded evidence. No Critical or Important findings remain; all task 0017 and overall implementation-plan acceptance criteria pass.

## 2026-09-14T16:31:27+04:00 — Task 0018 started

- Task: Focused post-review fixes
- Agent/tool: OpenAI Codex using FastAPI, SQLAlchemy/Alembic, PostgreSQL row locking and partial indexes, pytest/httpx, React/TypeScript, Testing Library/Vitest, Playwright, Ruff, Oxlint, Vite, Docker Compose, and Git
- Prompt/reference: `docs/prompts/0018-post-review-fixes.md` and `docs/tasks/0018-post-review-fixes.md`
- Existing work: Tasks 0001–0017 are committed and green; cancelled registrations are retained but lifetime event/email uniqueness prevents creating a safe new participation attempt
- Decisions: Keep cancelled rows immutable; create a new registration attempt under the existing Event row lock; enforce normalized-email uniqueness only for active rows; preserve old invalidated tickets and use the new registration ID for ticket and notification identities
- Status: Completed at 2026-09-14T16:54:08+04:00
- Result: Replaced lifetime event/email uniqueness with PostgreSQL uniqueness for active registrations, kept cancelled attempts as history, and routed same-email re-registration through normal locked capacity allocation. Each confirmed attempt now has a fresh registration/ticket/notification identity while prior tickets stay invalid. Added confirmed/waitlisted cancellation UI with confirmation, pending/error protection, explicit cancelled messaging, and an in-place re-registration action. Added honest AI/current-state/limitations/next-step documentation and expanded demo/proof evidence.
- Failures diagnosed: The first static-check command ran package tools from the repository root and uv could not access its shared cache in the sandbox; checks were rerun from each application directory with the required cache permission. The first new Playwright run read the event ID before post-create navigation completed; adding the same explicit organizer-URL wait used by the existing scenario fixed the test.
- Tests/checks: Empty PostgreSQL schema (0 tables) migration from base through `20260914_0007`; development-schema upgrade; Alembic head/drift checks; locked backend sync; Ruff lint/format (60 files); focused PostgreSQL invariants (16 passed); full pytest (46 passed); backend sdist/wheel build; clean `npm ci` (118 packages, 0 vulnerabilities); Oxlint; Vitest (11 passed); TypeScript/Vite build; Playwright (2 passed, including retained two-client SSE proof); direct PostgreSQL catalog/data invariant queries; Git whitespace checks.
- Self-review: Confirmed that only active registrations participate in email uniqueness and lookup, Event row locking still serializes allocation, cancelled rows/timestamps/waitlist order remain historical, confirmed counts never exceed capacity, every confirmed re-registration has one fresh valid ticket, prior tickets remain invalid, notification dedupe keys are unique per new registration identity, and the frontend cannot display the prior ticket or waiting state after cancellation. Documented the inherent downgrade prerequisite for historical duplicates. No Critical or Important findings remain.

## 2026-09-14T17:27:36+04:00 — ChatGPT Astra 6 review

- Request: Read `docs/`, deeply review against the original assignment
- Reviewed revision: `75581e6`; tool: OpenAI Codex.
- Work: Read documentation and inspected domain transactions, database constraints/migrations, notifications, frontend flows, and proof coverage. Frontend test run started at 17:24:07 +04:00; findings and verification recorded at 17:27:36 +04:00.
- Results: No P0 identified. Reproduced four P1 issues and opened repository tasks 0019–0022 for reschedule identity, obsolete reminders, retry starvation, and worker claim ownership. Application code was not changed.
- Verification: Backend 46 passed; frontend 11 passed; Playwright 2 passed; backend/frontend lint, backend format, frontend build, and empty-test-database Alembic upgrade through 0007 plus drift check passed. Five isolated PostgreSQL diagnostic cases reproduced the four defects.
- Environment: Started only the isolated PostgreSQL test service; used port 5434 for tests, migration and browser proof. Pytest reported a cache permission warning; the initial browser run was blocked by uv cache access and the approved rerun passed.
- Artifacts: `docs/reviews/2026-09-14-astra6-review.md`, `docs/reviews/astra6-reproduce.py`, and OPEN specifications in `docs/tasks/0019` through `0022` (full filenames linked from the review). Review tasks remain unimplemented.

## 2026-09-14T17:55:34+04:00 — Task 0019 started

- Task: P1: Notify participants on every actual reschedule
- Agent/tool: Claude Code (Claude Opus 5) using FastAPI, SQLAlchemy/Alembic, PostgreSQL row locking, pytest/httpx, Ruff, Vitest, and Git
- Prompt/reference: `docs/prompts/0019-reschedule-notification-revisions.md`, `docs/tasks/0019-reschedule-notification-revisions.md`, and `docs/reviews/2026-09-14-astra6-review.md`
- Existing work: Tasks 0001–0018 are committed and green (46 backend, 11 frontend, 2 Playwright); the review reproduction showed A → B → A → B creating two reschedule rows instead of three
- Decisions: Persist `events.schedule_revision` and increment it under the existing Event row lock only when the requested instant differs; key reschedule rows by revision and reminders by scheduled time plus revision; leave historical rows and their keys untouched; record the identity change in decision 0019 and correct task/decision 0014 rather than silently diverging from them
- Status: Completed at 2026-09-14T17:59:11+04:00
- Result: Every actual schedule change now creates one reschedule outbox row per confirmed and waitlisted participant, including repeated transitions and revisited dates; equivalent timezone representations of the current instant are no-ops; a failing notification enqueue rolls the schedule and revision back together. `EventRead` exposes `schedule_revision` and migration `20260914_0008` adds the column with default 0.
- Failures diagnosed: A scripted edit rewrote four source files with CRLF endings on Windows and truncated a decision file through a cp1252 encode error; the files were normalized to LF, the decision restored from Git, and the edits redone with explicit UTF-8. New tests initially failed Ruff for missing imports, which were added.
- Tests/checks: Ruff lint/format; empty test-database migration from base through `20260914_0008`, `alembic check` (no drift), and `0008` downgrade/upgrade; backend pytest (50 passed, including four new reschedule regression tests); review script case `reschedule_revisit` now reports 3 changes and 3 notifications; Vitest (11 passed); Git whitespace check.
- Self-review: The revision changes only inside the locked reschedule transaction, both active statuses receive a row for each of three changes with revisions 1–3 and correct old/new times, cancelled participants receive nothing, a same-instant PATCH in UTC and +04:00 leaves revision 0 and creates no rows, and the reminder identity distinguishes a revisited date. No Critical or Important findings remain.

## 2026-09-14T18:00:13+04:00 — Task 0020 started

- Task: P1: Suppress queued reminders after cancellation or rescheduling
- Agent/tool: Claude Code (Claude Opus 5) using SQLAlchemy/Alembic, PostgreSQL row locking (`FOR SHARE`/`FOR UPDATE`), the outbox worker, pytest with forced-overlap threads, Ruff, and Git
- Prompt/reference: `docs/prompts/0020-suppress-obsolete-reminders.md`, `docs/tasks/0020-suppress-obsolete-reminders.md`, and the Astra review cases `stale_reminder_after_reschedule`/`stale_reminder_after_cancel`
- Existing work: Task 0019 committed the schedule revision; reminders were still delivered from their stored payload regardless of later cancellation or rescheduling
- Decisions: Keep obsolete rows as an auditable terminal `SUPPRESSED` state instead of deleting them; suppress only `PENDING` rows in business transactions so a row actually handed to SMTP is never recorded as suppressed; share-lock due Event rows during generation to serialize with every `FOR UPDATE` seat/schedule change; re-verify each reminder in the worker's claim transaction as the last gate; document the remaining verification-to-SMTP window in decision 0020
- Status: Completed at 2026-09-14T18:07:23+04:00
- Result: Cancellation and rescheduling now retire queued reminders in their own transactions, generation cannot resurrect stale intent around a concurrent change, dispatch suppresses anything that slipped through, and a postponed event receives exactly one reminder for its current revision when the new schedule becomes due. Migration `20260914_0009` adds the columns/status and back-fills revisions for existing rows, tagging mismatched reminders `-1`.
- Failures diagnosed: Long scripted edits failed Git Bash's heredoc parser twice; the edit scripts were written to the session scratchpad and executed from there. Initial lifecycle tests asserted `process_once() == 0` although the worker also delivers pending confirmation/reschedule mail, and one case did not account for the worker legitimately generating a revision-1 reminder after the simulated revision bump; the assertions now target reminder deliveries and the stale row specifically.
- Tests/checks: Ruff lint/format; empty test database migrated to `20260914_0008`, seeded with matching, mismatched, tagged, and non-reminder outbox rows, upgraded to `0009` with the expected back-fill (3, -1, 2, NULL) and enum value; `alembic check` (no drift); `0009` downgrade/upgrade; downgrade guard rejects existing `SUPPRESSED` rows; backend pytest (57 passed, including seven new lifecycle/overlap tests); review script stale-reminder cases now report 0 deliveries for both postponement and cancellation; Git whitespace check.
- Self-review: Suppression and the state change commit together, `PROCESSING` rows are left to their owning worker, the generator's share lock provably waits for an in-flight reschedule and an in-flight reschedule provably waits for generation and then suppresses its output, dispatch re-verification covers revision, registration status, and ticket validity, and SMTP remains outside every business transaction. No Critical or Important findings remain.

## 2026-09-14T18:08:06+04:00 — Task 0021 started

- Task: P1: Prevent failing messages from starving the outbox
- Agent/tool: Claude Code (Claude Opus 5) using SQLAlchemy/Alembic, PostgreSQL, Python `EmailMessage`/`smtplib` classification, pytest with an injected worker clock, Ruff, Vitest, and Git
- Prompt/reference: `docs/prompts/0021-outbox-retry-fairness.md`, `docs/tasks/0021-outbox-retry-fairness.md`, and the Astra review case `poison_starvation`
- Existing work: Tasks 0019–0020 committed; the worker still claimed the oldest pending batch and returned failures to `PENDING` immediately with no retry time or terminal state
- Decisions: Schedule retries with a persisted `next_attempt_at` and capped exponential backoff ordered ahead of nothing that became due earlier; classify message-construction and SMTP 5xx rejections as permanent and everything else as transient; make `FAILED` terminal with `failed_at`/`last_error` and a deliberate `retry-failed` command instead of silent spinning; reject CR/LF titles at API and database while folding persisted subjects in the mailer so old rows still deliver; inject a clock into the worker for deterministic tests
- Status: Completed at 2026-09-14T18:16:14+04:00
- Result: A full batch of permanently failing rows is terminal after one attempt and healthy confirmation, promotion, reminder, and reschedule mail is delivered on the very next cycle; transient failures back off without blocking newer work and retry successfully; exhausted rows stay `FAILED` until an operator requeues them. Migration `20260914_0010` adds the scheduling columns, status, index, title fold, and constraint.
- Failures diagnosed: The existing fail-then-succeed retry test assumed an immediate retry; it now advances the injected clock across the backoff and additionally asserts the deferral. A frozen test clock could not see rows the worker generated with a database-side `next_attempt_at`; the test clock starts two seconds ahead of wall time. The review reproduction could no longer create a newline title through the API, so it now mutates persisted recipients to be unrenderable; a trailing newline is silently stripped by `EmailMessage`, so the mutation embeds the line break instead. Ruff line-length and an asyncio-mark warning were corrected.
- Tests/checks: Ruff lint/format; empty test database migrated to `0009`, seeded with a CR/LF title and an old outbox row, upgraded to `0010` (title folded, `next_attempt_at = created_at`, enum contains `FAILED`, index on `(status, next_attempt_at)`, constraint rejects a newline insert); `alembic check` (no drift); `0010` downgrade/upgrade; downgrade guard rejects existing `FAILED` rows; backend pytest (64 passed, including seven new fairness tests); review script `poison_starvation` now reports healthy attempts 1 and 20 terminal failures; `retry-failed` CLI help; Vitest (11 passed); Git whitespace check.
- Self-review: Ordering by `next_attempt_at` guarantees deferred rows never precede work that became due earlier, permanent failures never re-enter the queue automatically, attempts and errors are retained through retry, SMTP stays outside business transactions, and the title rule is enforced at both boundaries while historical payloads remain deliverable. No Critical or Important findings remain.

## 2026-09-14T18:16:39+04:00 — Task 0022 started

- Task: P1: Keep live worker claims from expiring during a batch
- Agent/tool: Claude Code (Claude Opus 5) using SQLAlchemy/Alembic, PostgreSQL `FOR UPDATE SKIP LOCKED`, pytest with two real worker instances and a shared simulated clock, Playwright, Ruff, Oxlint, Vite, and Git
- Prompt/reference: `docs/prompts/0022-outbox-claim-ownership.md`, `docs/tasks/0022-outbox-claim-ownership.md`, and the Astra review case `slow_batch_duplicate`
- Existing work: Tasks 0019–0021 committed; the worker still claimed a whole batch under one lease timestamp and finished rows by ID alone
- Decisions: Claim one row immediately before its own send with a fresh random `claim_token`, so a lease only has to cover one SMTP call; condition completion and failure on `id`, token, and `PROCESSING` status so a stale owner changes nothing and logs the takeover; keep lease-based recovery for abandoned claims; state in decision 0022 and README that SMTP delivery remains at-least-once when one call outlives the lease or the worker dies after SMTP acceptance
- Status: Completed at 2026-09-14T18:22:19+04:00
- Result: Two workers now share unclaimed work without duplicating it, a healthy slow batch cannot lose ownership of rows it is still sending, stale owners cannot overwrite or reset newer claims, and abandoned claims are still recovered after the lease. Migration `20260914_0011` adds `claim_token`. The review reproduction script now asserts the corrected behavior for all five cases, and its module-patched clock was replaced by the worker's injectable clock.
- Failures diagnosed: The review script's simulated clock started at wall time, before the reminders generated inside the cycle received their database-side `next_attempt_at`, so nothing was due; the script now starts its clock two seconds ahead, matching the new tests. A `noqa` on the ownership-update helper was replaced with SQLAlchemy's `Update` return type.
- Tests/checks: Ruff lint/format; empty test database migrated to `20260914_0011`, `alembic check` (no drift), `0011` downgrade/upgrade; development database upgraded to `0011`; backend pytest (70 passed, including six new ownership tests); focused invariant tests (16 passed); complete review reproduction script (five cases corrected); Oxlint; Vitest (11 passed); TypeScript/Vite build; Playwright (2 passed) with ports released; Git whitespace check. Recorded in `docs/demo/final-verification.md`.
- Self-review: Every claim is a per-attempt snapshot with its own token, the only path to `SENT`/`FAILED`/`PENDING`-with-backoff from `PROCESSING` is ownership-conditioned, reminder re-verification still happens inside the claim transaction, cycles remain bounded by the batch size, crash recovery is unchanged, and the honest double-delivery outcome is tested rather than hidden. No Critical or Important findings remain; tasks 0019–0022 from the implementation plan are complete.

## 2026-09-14T18:31:44+04:00 — Task 0023 started

- Task: P2: Never let an older HTTP snapshot replace a newer SSE snapshot
- Agent/tool: Claude Code (Claude Opus 5) using React/TypeScript, Testing Library/Vitest, Oxlint, Vite, Playwright, and Git
- Prompt/reference: `docs/prompts/0023-organizer-snapshot-ordering.md`, `docs/tasks/0023-organizer-snapshot-ordering.md`, and the "Other observations" section of `docs/reviews/2026-09-14-astra6-review.md`; the user asked for tasks 0023/0024 to be created, added to `docs/IMPLEMENTATION_PLAN.md`, and completed under the existing rules
- Existing work: Tasks 0001–0022 committed; the organizer page applied both the initial HTTP statistics response and SSE snapshots through the same setter with no ordering rule
- Decisions: Keep the HTTP snapshot as the pre-connection fallback but make SSE authoritative once any live snapshot has been applied, tracked with an effect-local flag; no server-side sequence numbers because the change-only stream already re-emits anything newer than its last snapshot
- Status: Completed at 2026-09-14T18:34:31+04:00
- Result: A late-resolving initial HTTP statistics response can no longer overwrite live counts; event details still render regardless of ordering.
- Failures diagnosed: None in implementation. The new component test was run against the previous page implementation to confirm it fails (stale checked-in count rendered) before being accepted.
- Tests/checks: Vitest (12 passed, including the new delayed-response test); Oxlint; TypeScript/Vite production build; Playwright two-context proof and cancellation/re-registration scenario (2 passed) with ports released; Git whitespace check.
- Self-review: Every acceptance criterion in the task is covered by a test or an unchanged existing test; the fix is confined to the organizer effect and no API or backend behavior changed. No Critical or Important findings remain.

## 2026-09-14T18:34:46+04:00 — Task 0024 started

- Task: P2: Release the SSE route's preliminary database session before streaming
- Agent/tool: Claude Code (Claude Opus 5) using FastAPI dependencies, SQLAlchemy pooling, pytest/httpx, Ruff, Playwright, and Git
- Prompt/reference: `docs/prompts/0024-sse-preliminary-session-release.md`, `docs/tasks/0024-sse-preliminary-session-release.md`, and the "Other observations" section of `docs/reviews/2026-09-14-astra6-review.md`
- Existing work: Task 0023 committed; the stream route ran its 404 pre-check on the request-scoped yield session, which FastAPI keeps open for the whole streaming response
- Decisions: Give long-lived handlers a session-factory dependency instead of a session so the pre-check session is closed before the response starts; keep the 404 pre-check and per-snapshot short-lived sessions unchanged; override the new dependency in tests so polling still targets the isolated test engine
- Status: Completed at 2026-09-14T18:36:03+04:00
- Result: A connected organizer no longer pins a pooled PostgreSQL connection for the stream lifetime; unknown events still return 404 as JSON before any stream bytes.
- Failures diagnosed: None in implementation. The new pool test was written first and observed one checked-out connection against the previous route, then zero after the change.
- Tests/checks: Ruff lint/format; backend pytest (72 passed, including the pool-release and stream 404 tests); Playwright two-context SSE proof and cancellation scenario (2 passed) with ports released; Git whitespace check.
- Self-review: Task 0010's no-lifetime-session criterion now holds for the whole request, the stream and the pre-check use the same configured engine in production and tests, and no polling design, interval, or payload changed. No Critical or Important findings remain; tasks 0023 and 0024 close the review's remaining observations.

## 2026-09-15T09:11:17+04:00 — Task 0025 started

- Task: Worker robustness and delivery correctness (second review round)
- Agent/tool: Claude Code (Claude Opus 5) using Python `smtplib`/RFC 5321 reply classes, SQLAlchemy, pytest with fake SMTP and an injected worker clock, Ruff, and Git
- Prompt/reference: `docs/prompts/0025-worker-robustness-and-delivery-correctness.md`, `docs/tasks/0025-worker-robustness-and-delivery-correctness.md`; the user supplied GPT 5.6 ultra and Copilot Opus 5 review findings, which were verified against the code and the running application before tasks 0025–0027 were added to the plan
- Existing work: Tasks 0001–0024 committed and pushed; worker loop had no error handling, SMTP 4yz replies were terminal, the dispatch gate ignored the clock, cancellation retired reminders only, and reschedule bursts delivered every intermediate notice
- Decisions: Keep the process alive with logged, capped-backoff retries rather than a supervisor; classify SMTP by reply class (5yz permanent, 4yz transient) per RFC 5321; extend cancellation suppression to confirmation/promotion rows; bound reschedule delivery by superseding unsent notices while retaining every change's intent row (addenda to decisions 0003, 0019, 0020, 0021)
- Status: Completed at 2026-09-15T09:15:31+04:00
- Result: The worker no longer dies on transient database or network errors, greylisting and mailbox-busy replies are retried, reminders are never sent after the event starts, cancelled participants receive no stale confirmation/promotion, and a burst of schedule changes delivers one current notice per participant.
- Failures diagnosed: Shell heredocs for the long task specifications failed to parse again; the files were written with the editor tool. The fairness fixture cancelled the only confirmed participant, whose confirmation is now (correctly) suppressed; the fixture was restructured so a retained participant carries the healthy confirmation and the cancelled one's suppression is asserted. `alembic check` reported drift against the test database because the pytest fixture leaves it without tables; recreating the schema and migrating showed no drift (the README recipe issue is task 0027).
- Tests/checks: Ruff lint/format; backend pytest (83 passed, including 11 new robustness tests); empty test database migrated to head with `alembic check` clean (no schema change in this task); review reproduction script (five cases still corrected); Git whitespace check.
- Self-review: Every acceptance criterion has a direct test; suppression still touches only `PENDING` rows so in-flight sends are never misrecorded; per-row claim ownership, reminder identity, and the at-least-once boundary are unchanged. No Critical or Important findings remain.

## 2026-09-15T09:15:47+04:00 — Task 0026 started

- Task: Input and safety bounds (second review round)
- Agent/tool: Claude Code (Claude Opus 5) using Pydantic, SQLAlchemy/Alembic, PostgreSQL check constraints, pytest, Ruff, and Git
- Prompt/reference: `docs/prompts/0026-input-and-safety-bounds.md` and `docs/tasks/0026-input-and-safety-bounds.md`
- Existing work: Task 0025 committed; capacity had no upper bound, the title constraint trimmed spaces only, the test fixture could reset any PostgreSQL database, migration 0005 could not downgrade promoted rows, and pool sizing was hard-coded
- Decisions: Cap capacity at 1,000,000 as a product bound rather than the raw integer limit; keep the API's `strip()` rule and mirror it in the database with `btrim` over space/tab/CR/LF; require a `_test` database-name suffix with an explicit override variable instead of a heuristic; make 0005's downgrade fail fast and print the deliberate lossy normalisation rather than silently nulling history; expose pool size/overflow as settings and document the SSE per-poll cost (the review's `/health` claim was not reproduced because `/health` never touches the database)
- Status: Completed at 2026-09-15T09:18:43+04:00
- Result: Oversized capacities are 422s, whitespace-only titles are rejected at both boundaries, the test suite cannot reset a non-test database by accident, migration 0005 refuses an unsafe downgrade with instructions, and pool sizing is configurable and documented. Migration `20260914_0012` updates the title constraint.
- Failures diagnosed: None; all new tests passed on first run after the formatter normalised line lengths.
- Tests/checks: Ruff lint/format; backend pytest (92 passed, including nine new bound/guard tests); empty test database migrated to `20260914_0012` with `alembic check` clean, `0012` downgrade/upgrade, direct tab-only insert rejected; `0005` downgrade refused with a seeded promoted registration and succeeded after the documented `UPDATE`; development database upgraded to `0012`; Git whitespace check.
- Self-review: Each acceptance criterion has a direct test or migration proof; no product behavior changed for valid input; the guard cannot be bypassed without the explicit environment variable. No Critical or Important findings remain.

## 2026-09-15T09:18:59+04:00 — Task 0027 started

- Task: Documentation, provenance, and organizer error isolation (second review round)
- Agent/tool: Claude Code (Claude Opus 5) using README/package metadata, pytest fixtures, React/Testing Library, Oxlint, Vite, Playwright, and Git
- Prompt/reference: `docs/prompts/0027-documentation-provenance-and-organizer-errors.md` and `docs/tasks/0027-documentation-provenance-and-organizer-errors.md`
- Existing work: Tasks 0025–0026 committed; README's test recipe pointed Alembic at the development database, Node's minimum version was undocumented, the provenance section still named only Codex, and the organizer page coupled its two initial requests
- Decisions: Point the documented migration checks at the test service and make the fixture drop `alembic_version` so order does not matter; declare `engines.node` from the locked toolchain; state both agents and their task ranges plainly and link the repository; split the organizer requests rather than swallow one failure
- Status: Completed at 2026-09-15T09:22:35+04:00
- Result: The README test recipe runs as written from a shell with only the test service up, Node requirements are explicit, AI provenance matches the development log, and a failed statistics or event request no longer hides the other response on the dashboard.
- Failures diagnosed: The Playwright run was blocked because the API, worker, and Vite processes started earlier for the user's "run the project" request were still bound to ports 8000/5173, and stopping the Vite wrapper left its node child alive; the child was identified by command line and stopped individually, after which the browser proof passed. A shell pipeline aborted on `grep -c` returning 0 during the recipe proof; the proof was rerun with a database-backed test in between.
- Tests/checks: Vitest (14 passed, two new error-isolation tests); Oxlint; TypeScript/Vite build; backend pytest (92 passed) followed by `alembic upgrade head` (12 upgrades from base) and a clean `alembic check` against the test service, proving the documented order; Playwright (2 passed) with ports released; Git whitespace check.
- Self-review: All five acceptance criteria are met and verified; no backend behavior changed beyond the test fixture. Tasks 0025–0027 close every confirmed finding from the second review round. No Critical or Important findings remain.

## 2026-09-15T10:06:36+04:00 — Task 0028 started

- Task: Event discovery by role
- Agent/tool: Claude Code (Claude Opus 5) using FastAPI/SQLAlchemy scalar-subquery listing, pytest/httpx, React/TypeScript, Testing Library/Vitest, Oxlint, Vite, Playwright, and Git
- Prompt/reference: `docs/prompts/0028-event-discovery-by-role.md` and `docs/tasks/0028-event-discovery-by-role.md`; the user's product review found no event list for either role and no way for participants to discover events
- Existing work: Tasks 0001–0027 committed and pushed; the root route was the organizer's create form and events were reachable only through copied links
- Decisions: Separate roles by area, not permission, keeping decision 0003 (no login) intact; one list endpoint with authoritative counts and an `include_past` flag rather than two endpoints; participant home at `/`, organizer area at `/organizer`, existing deep routes unchanged; let Playwright reuse already-running servers behind an explicit env var so proofs can run without stopping a developer's instances
- Status: Completed at 2026-09-15T10:13:41+04:00
- Result: Participants open the app and see upcoming events with seats left or waiting-list size and register directly; organizers create events and return to any dashboard from a list that includes past events. Counts on both lists come from the same registration state as the statistics endpoint.
- Failures diagnosed: Oxlint flagged `Date.now()` inside render for the "past" label; the timestamp is now captured once per mount. The Playwright ports were occupied by the user's own `uvicorn --reload` and Vite processes (started after the run instructions); rather than stopping them, the config gained `PLAYWRIGHT_REUSE_SERVERS=1` and the proof ran against those instances, which serve the current code.
- Tests/checks: Ruff lint/format; backend pytest (95 passed, three new list tests cross-checked against `/stats`); Oxlint; Vitest (18 passed, three new list tests and two updated routing tests); TypeScript/Vite build; Playwright (2 passed) starting at `/organizer` against the running application; a real-browser screenshot of the participant home showing the user's live events; Git whitespace check.
- Self-review: All five acceptance criteria are met; no allocation, outbox, or check-in logic changed; the API addition is the plan's permitted "cleaner resource naming" extension rather than an architecture change and is recorded in decision 0028. No Critical or Important findings remain.

## 2026-09-15T10:14:02+04:00 — Task 0029 started

- Task: Registration self-service and waitlist email
- Agent/tool: Claude Code (Claude Opus 5) using FastAPI, SQLAlchemy/Alembic (enum extension), typed email templates, `smtplib` STARTTLS/login, pytest, React/TypeScript, Testing Library/Vitest, Playwright, and Git
- Prompt/reference: `docs/prompts/0029-registration-self-service-and-waitlist-email.md` and `docs/tasks/0029-registration-self-service-and-waitlist-email.md`; the user asked how a participant cancels later and why no email arrived in a personal inbox
- Existing work: Task 0028 committed; cancellation was reachable only on the post-registration result screen, waitlisted participants received no mail, and emails carried no link back
- Decisions: Use the registration id in a self-service link as the participant's possession-based identity (decision 0029), mirroring the ticket code; add a `WAITLIST_JOINED` email with the FIFO position rather than leaving waitlisted participants silent; share one `RegistrationStatus` component between the event page and the self-service page; keep Mailpit the default and make real-provider SMTP purely optional settings; explain where email goes at the top of the README
- Status: Completed at 2026-09-15T10:24:06+04:00
- Result: Every participant email links to a page where the registration can be viewed and cancelled at any time, waitlisted participants receive one email with their place in line, and the cancellation browser proof now runs through that page. Migration `20260915_0013` adds the notification type.
- Failures diagnosed: Three existing tests enumerated notification rows and were updated for the new waitlist email. An Oxlint unused-parameter warning was fixed. The first Playwright run failed with "Failed to fetch" on cancel: the user's own `uvicorn --reload` server was serving the new code against a development database still at migration 0012, so the cancel's `WAITLIST_JOINED` suppression hit an unknown enum value and returned a 500 without CORS headers; upgrading the development database fixed it and the task file records the lesson.
- Tests/checks: Ruff lint/format; backend pytest (100 passed, five new self-service tests); empty test database migrated to `20260915_0013` with `alembic check` clean and `0013` downgrade/upgrade; development database upgraded to `0013`; Oxlint; Vitest (21 passed, three new); TypeScript/Vite build; Playwright (2 passed) against the user's running servers with `PLAYWRIGHT_REUSE_SERVERS=1`; Git whitespace check.
- Self-review: All five acceptance criteria are met; suppression on cancel now covers every participant email type; email templates are the only place links are rendered and all five are tested; no locking, outbox, or check-in logic changed. No Critical or Important findings remain; tasks 0028–0029 close the user's product review.
