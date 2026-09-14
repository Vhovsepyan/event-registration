# Task 0008: Atomic Check-in

## Objective

Check in a valid active ticket exactly once using a single conditional PostgreSQL update.

## Scope

- Implement `POST /api/check-ins` with a manually entered ticket code.
- Normalize code input to trimmed uppercase.
- Atomically set `checked_in_at` using `UPDATE ... WHERE ... RETURNING`.
- Return distinct `SUCCESS`, `ALREADY_CHECKED_IN`, and `INVALID_TICKET` outcomes.
- Treat unknown and invalidated/cancelled tickets as invalid.
- Add sequential and forced-overlap PostgreSQL concurrency tests.

## Out of scope

- Organizer statistics/dashboard and frontend check-in UI.

## Acceptance criteria

1. First active-ticket check-in succeeds and persists one timestamp.
2. Later attempts return already checked in without changing the timestamp.
3. Unknown and cancelled tickets return invalid ticket.
4. Two overlapping attempts produce exactly one success.
5. No read-then-write race determines success.
6. Full verification is green.
