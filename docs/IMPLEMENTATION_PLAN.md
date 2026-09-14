# Event Registration — Implementation Plan

## 1. Goal

Build a client-server event registration product.

The product consists of:

- a separate Python backend
- a separate React frontend
- PostgreSQL storage
- local Docker-based infrastructure

Backend and frontend communicate over HTTP/SSE.

The implementation must be easy to run locally and must demonstrate correct behavior with multiple browser clients open at the same time.

---

# 2. Technology Stack

## Backend

- Python 3.13
- FastAPI
- SQLAlchemy 2.x
- PostgreSQL
- psycopg
- Alembic
- Pydantic
- pytest
- pytest-asyncio where needed
- httpx for API tests

## Frontend

- React
- TypeScript
- Vite
- React Router
- native EventSource for SSE

Avoid unnecessary frontend frameworks unless they materially simplify implementation.

## Infrastructure

- Docker Compose
- PostgreSQL
- Mailpit for local email delivery/testing

Mailpit is used as the local SMTP service so emails can be inspected in a browser without requiring a real external email provider.

---

# 3. Architecture

Use a monorepo with separate backend and frontend applications.

Structure:

event-registration/
backend/
frontend/
docs/
tasks/
decisions/
agent/
docker-compose.yml
README.md

Backend and frontend must remain independently runnable.

Do not implement microservices.

Do not introduce Kafka, RabbitMQ, Redis, Celery, or Kubernetes unless a concrete requirement later proves they are necessary.

PostgreSQL is the source of truth.

---

# 4. Backend Structure

Use feature-oriented modules.

backend/app/

    main.py

    event/
        models.py
        schemas.py
        repository.py
        service.py
        routes.py

    registration/
        models.py
        schemas.py
        repository.py
        service.py
        routes.py

    ticket/
        models.py
        service.py
        routes.py

    notification/
        models.py
        service.py
        worker.py

    organizer/
        routes.py
        service.py

    db/
        session.py
        base.py

    common/
        errors.py
        config.py

Avoid one global controllers/services/repositories package structure.

---

# 5. Core Data Model

## Event

Fields:

- id: UUID
- title
- description
- starts_at: timestamptz
- capacity
- created_at
- updated_at

Rules:

- title must not be blank
- starts_at must be in the future when created
- capacity must be greater than zero

---

## Registration

Fields:

- id: UUID
- event_id
- email
- normalized_email
- status
- waitlist_order
- created_at
- confirmed_at
- cancelled_at

Statuses:

- CONFIRMED
- WAITLISTED
- CANCELLED

Invariant:

UNIQUE(event_id, normalized_email)

A repeated registration for the same event/email must not consume another seat.

Email normalization must at minimum trim whitespace and compare case-insensitively.

---

## Ticket

Fields:

- id: UUID
- registration_id
- code
- created_at
- checked_in_at
- invalidated_at

Ticket code must be:

- unique
- unpredictable
- safe to type manually

Only confirmed registrations may have an active ticket.

---

## Notification Outbox

Fields:

- id
- type
- event_id
- registration_id
- recipient
- payload
- dedupe_key
- status
- attempts
- created_at
- sent_at

Types:

- REGISTRATION_CONFIRMED
- WAITLIST_PROMOTED
- EVENT_REMINDER
- EVENT_RESCHEDULED

Use a unique dedupe_key where duplicate generation must be prevented.

---

# 6. Concurrency Strategy

## Last available seat

This requirement must be enforced in PostgreSQL.

Registration transaction:

1. SELECT event FOR UPDATE
2. check existing registration for normalized email
3. count current CONFIRMED registrations
4. if count < event.capacity:
    - create/update registration as CONFIRMED
    - create ticket
    - create confirmation notification
5. otherwise:
    - create/update registration as WAITLISTED
    - assign deterministic waitlist order
6. commit

All operations that change seat availability must use the same event-row locking strategy.

This includes:

- new registration
- cancellation of confirmed participant
- waitlist promotion

Two concurrent registrations for the final seat must produce:

- exactly one CONFIRMED registration
- exactly one WAITLISTED registration

---

# 7. Waitlist

Use FIFO ordering.

A WAITLISTED registration receives a monotonic waitlist_order.

When a confirmed participant cancels:

1. lock the event row
2. cancel the registration
3. invalidate its ticket
4. select the earliest active WAITLISTED registration
5. promote it to CONFIRMED
6. create a ticket
7. create notification
8. commit

Cancellation and promotion must happen in the same transaction.

---

# 8. Check-in

Endpoint accepts a ticket code.

Check-in must be atomic.

Conceptually:

UPDATE ticket
SET checked_in_at = now()
WHERE code = :code
AND checked_in_at IS NULL
AND invalidated_at IS NULL
RETURNING ...

Results:

- first attempt: success
- subsequent attempt: already checked in
- unknown code: invalid ticket
- cancelled ticket: invalid ticket

Do not implement check-in as a read-then-write race.

---

# 9. Organizer Statistics

Organizer screen shows:

- capacity
- confirmed registrations
- waitlist size
- checked-in count

Do not maintain unnecessary duplicated counters initially.

Calculate statistics from authoritative registration/ticket state.

---

# 10. Live Updates

Use Server-Sent Events.

Endpoint:

GET /api/events/{event_id}/stats/stream

The organizer frontend uses EventSource.

The implementation must support at least two browser clients simultaneously.

A simple implementation may periodically read statistics from PostgreSQL and emit a new snapshot when values change.

This avoids introducing Redis or a distributed pub/sub system.

---

# 11. Email

Use SMTP through Mailpit locally.

Email is generated for:

- confirmed registration with ticket
- waitlist promotion with ticket
- event reminder
- event reschedule

External email delivery must not happen inside the main business transaction.

Use the notification outbox.

A background worker polls pending outbox rows and sends them through SMTP.

Failures are retried.

---

# 12. Reminder

Confirmed participants receive one reminder approximately 24 hours before the event.

Decision:

WAITLISTED users are not considered confirmed event participants for reminder delivery.

This interpretation must be recorded in the decision log.

Reminder generation must be idempotent.

Example dedupe key:

event-reminder:{event_id}:{registration_id}:{starts_at}

A polling worker periodically finds due reminders.

Do not depend on an in-memory timer that is lost on server restart.

---

# 13. Event Reschedule

Organizer may change event starts_at.

When starts_at changes:

1. update event in a database transaction
2. create EVENT_RESCHEDULED notifications
3. send email asynchronously

Notify:

- CONFIRMED participants
- WAITLISTED participants

Reason:
both groups are affected by the event schedule.

The decision must be recorded.

A changed event date creates a new reminder schedule.

The reminder dedupe identity must include the scheduled event time so a reminder may be sent again for the new schedule.

---

# 14. Frontend

Use React + TypeScript.

Required screens:

## Event creation

Organizer can create:

- title
- description
- date/time
- capacity

---

## Participant registration

User sees event information.

User enters email.

Result clearly shows:

- confirmed
  or
- waiting list

Confirmed registration displays ticket information.

---

## Ticket

Display:

- event
- ticket code
- status

No QR scanner is required.

Manual ticket-code entry is sufficient.

---

## Check-in

Staff enters ticket code.

Display:

- successful check-in
- already checked in
- invalid ticket

---

## Organizer dashboard

Display live:

- capacity
- confirmed count
- waitlist count
- checked-in count

Use SSE without page refresh.

---

# 15. API

Minimum API:

POST   /api/events
GET    /api/events/{event_id}
PATCH  /api/events/{event_id}

POST   /api/events/{event_id}/registrations
POST   /api/events/{event_id}/registrations/{registration_id}/cancel

GET    /api/tickets/{code}
POST   /api/check-ins

GET    /api/events/{event_id}/stats
GET    /api/events/{event_id}/stats/stream

Exact resource naming may be adjusted if the resulting API is cleaner.

---

# 16. Authentication

Authentication is not required for the initial implementation.

The assignment explicitly permits products without login.

Document this as a deliberate scope decision.

Do not build authentication unless required later.

---

# 17. Automated Testing

Backend tests must use PostgreSQL.

Do not use SQLite for concurrency-sensitive integration tests.

Required coverage:

## Event

- create valid event
- invalid capacity
- invalid date

## Registration

- confirmed registration
- duplicate email does not consume second seat
- full event creates WAITLISTED registration

## Concurrency

Test:

capacity = 1

Start two registrations concurrently.

Assert:

- confirmed count = 1
- waitlisted count = 1

The test must actually execute overlapping transactions.

---

## Cancellation

Given:

- one confirmed participant
- two waitlisted participants

Cancel confirmed participant.

Assert:

- first waitlisted user becomes CONFIRMED
- second remains WAITLISTED
- promoted participant gets ticket
- notification is created

---

## Check-in

Two concurrent requests use the same ticket.

Assert:

- exactly one succeeds
- final checked-in count increases once

---

## Reminder

Run reminder processing twice.

Assert:

- only one reminder notification exists for the same schedule

---

## Reschedule

Change event date.

Assert notifications are generated for all active participants.

---

# 18. Frontend Testing

Add focused frontend tests for important UI behavior.

At minimum:

- registration result rendering
- check-in result rendering
- organizer statistics rendering

Prefer a small number of meaningful tests over large superficial coverage.

---

# 19. Multi-client Verification

The application must work with two simultaneously open browser clients.

Create a documented verification scenario:

1. open organizer dashboard in browser A
2. open check-in page in browser B
3. check in a ticket in B
4. organizer count changes in A without refresh

This scenario must be included in the final demo instructions.

Automate it with Playwright if implementation time allows.

---

# 20. AI / Development Evidence

Maintain:

docs/agent/development-log.md
docs/decisions/
docs/prompts/

For each development task record:

- timestamp
- task
- agent/tool used
- important prompt or reference to prompt
- decisions made
- result
- tests run

Commit incrementally.

Do not produce the entire project as one final commit.

---

# 21. Decision Log

Record important architecture decisions.

At minimum:

- why Python/FastAPI was chosen
- why PostgreSQL
- why React
- why modular monolith
- why SELECT FOR UPDATE for capacity
- why SSE instead of WebSocket
- why transactional outbox
- why no authentication
- who receives reminders
- who receives reschedule emails
- why Mailpit is used

Keep decisions short and concrete.

---

# 22. Local Development

Target developer experience:

docker compose up -d

Backend:

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

Frontend:

cd frontend
npm install
npm run dev

Final README must contain exact verified commands.

---

# 23. Final Proof

Before declaring the project complete:

- backend tests pass
- frontend tests pass
- migrations work from an empty database
- frontend builds
- backend starts
- frontend starts
- email can be inspected in Mailpit
- last-seat concurrency test passes
- one-time check-in test passes
- reminder deduplication test passes
- two-browser live-update scenario works

---

# 24. Task Order

Implement incrementally.

0001 Repository and Python/FastAPI foundation
0002 React frontend foundation
0003 Event creation and viewing
0004 Participant registration
0005 Capacity concurrency and waitlist
0006 Ticket generation and display
0007 Cancellation and FIFO promotion
0008 Check-in
0009 Organizer statistics
0010 SSE live dashboard
0011 Notification outbox and Mailpit
0012 Confirmation and promotion emails
0013 24-hour reminders
0014 Event rescheduling and notifications
0015 Frontend integration and UX completion
0016 Concurrency and multi-client proof
0017 Documentation, decision log, demo and final verification
0018 — Post-review fixes
0019 — P1: Notify participants on every actual reschedule
0020 — P1: Suppress queued reminders after cancellation or rescheduling
0021 — P1: Prevent failing messages from starving the outbox
0022 — P1: Keep live worker claims from expiring during a batch
0023 — P2: Never let an older HTTP snapshot replace a newer SSE snapshot
0024 — P2: Release the SSE route's preliminary database session before streaming

Each task must:

Each task must:

1. implement only its scope
2. run its relevant tests
3. diagnose and fix failures autonomously
4. run the existing full test suite
5. self-review
6. fix all Critical and Important findings
7. rerun verification
8. update the development log with timestamps
9. commit the completed task with a focused commit message
10. automatically proceed to the next task in the defined task order

Do not wait for user approval between tasks.

Continue autonomously until all tasks in this implementation plan are completed.

Stop only if:
- there is a genuine external blocker that cannot be solved from the repository or machine environment
- requirements are contradictory and require a product decision
- completing the next task would require changing an explicit architecture decision

Ordinary compile errors, test failures, dependency issues, migration problems, frontend errors, Docker issues that can be diagnosed locally, or application bugs are not reasons to stop. Diagnose and fix them autonomously.