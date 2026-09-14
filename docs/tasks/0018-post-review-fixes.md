# Task 0018 — Post-review fixes

## Objective

Fix cancelled-participant re-registration, expose participant cancellation in the React flow, and make the project's AI usage, current state, limitations, next steps, and proof easy to audit.

## Scope

- Permit a cancelled participant to create a new active registration attempt through the existing capacity-safe allocation path.
- Preserve cancelled registration rows, invalidated tickets, FIFO history, PostgreSQL event-row locking, and transactional notification creation.
- Replace lifetime event/email uniqueness with uniqueness among active registrations only.
- Add PostgreSQL-backed re-registration, ticket-lifecycle, notification, and concurrency tests.
- Add participant cancellation, confirmation, pending/error states, cancelled-state messaging, and re-registration to the event page.
- Add component and Playwright coverage for participant cancellation and re-registration.
- Add explicit AI-assisted development, current-state, limitations, and next-step README sections.
- Extend the demo and final verification evidence without removing the two-client SSE proof.

## Re-registration semantics

A cancelled row is historical and is never reactivated. A later request for the same normalized email creates a new registration row and runs through the same event lock and capacity calculation as any new participant. PostgreSQL enforces at most one active (`CONFIRMED` or `WAITLISTED`) row per event and normalized email.

This gives each participation attempt its own registration identity, ticket, and notification dedupe keys. The old ticket remains attached to the cancelled row and remains invalidated; waitlist order and cancellation timestamps remain auditable. Duplicate active requests remain idempotent, and the event-row lock serializes concurrent allocation.

## Out of scope

- Authentication or authorization.
- Changes to the transactional outbox worker or SMTP delivery contract.
- Changes to the event-row locking, FIFO promotion, SSE, or atomic check-in architecture.
- A broader frontend redesign.

## Acceptance criteria

1. Registering an email with only cancelled historical rows returns a new `CONFIRMED` or `WAITLISTED` registration, never the stale cancelled row.
2. Capacity, FIFO ordering, and duplicate-request behavior remain correct under concurrent PostgreSQL transactions.
3. A newly confirmed attempt receives a fresh valid ticket; every old cancelled-attempt ticket remains invalid.
4. Confirmation and promotion notifications are created once per applicable participation attempt.
5. Confirmed and waitlisted participant results expose a confirmed cancellation action, prevent repeated submission, show API errors, and transition to an unambiguous cancelled state.
6. A cancelled participant can submit the registration form again; no old ticket is shown as active.
7. README and demo material state the actual security and SMTP guarantees and identify the AI-assisted evidence trail.
8. All backend, frontend, migration, build, focused concurrency, and Playwright checks pass.

## Verification

Record exact results in `docs/demo/final-verification.md` and the timestamped development log after the full self-review passes.
