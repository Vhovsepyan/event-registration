# Task 0004: Participant Registration

## Objective

Allow a participant to register an email address for an existing event, with PostgreSQL-backed identity and idempotency guarantees.

## Scope

- Add the Registration model and status enum with all core fields.
- Add the `(event_id, normalized_email)` unique database constraint.
- Validate email syntax and normalize with trimming and case-insensitive comparison.
- Implement registration repository/service/routes under the registration feature.
- Implement `POST /api/events/{event_id}/registrations`.
- Return the existing registration for repeated equivalent email submissions.
- Create registrations as `CONFIRMED` in this task; capacity/waitlisting is task 0005.
- Add migration and PostgreSQL integration tests.

## Out of scope

- Capacity enforcement, row locking, and waitlist ordering.
- Tickets, cancellation, notifications, statistics, and frontend integration.

## Acceptance criteria

1. A valid email registers for an existing event as `CONFIRMED`.
2. Email normalization trims and compares case-insensitively.
3. Repeating an equivalent email returns the same registration and leaves exactly one row.
4. PostgreSQL enforces unique event/email identity.
5. Invalid emails return 422 and unknown events return 404.
6. Migration, task tests, and the full suite are green.
