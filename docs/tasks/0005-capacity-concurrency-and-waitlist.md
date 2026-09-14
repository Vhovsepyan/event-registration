# Task 0005: Capacity Concurrency and Waitlist

## Objective

Enforce event capacity atomically in PostgreSQL and place overflow registrations on a deterministic FIFO waitlist.

## Scope

- Lock the event row with `SELECT ... FOR UPDATE` for every registration seat decision.
- Count current confirmed registrations inside the locked transaction.
- Confirm when capacity is available; otherwise create a waitlisted registration.
- Assign monotonic per-event `waitlist_order` values under the same lock.
- Preserve normalized-email idempotency inside the locked transaction.
- Add database constraints/indexes for valid state shape and unique waitlist positions.
- Add overlapping-transaction tests for the last seat and focused capacity/waitlist tests.

## Out of scope

- Ticket creation, notifications, cancellation, and promotion.
- Frontend registration screens.

## Acceptance criteria

1. Capacity is never exceeded under concurrent requests.
2. Two overlapping registrations for a capacity-one event yield one confirmed and one waitlisted row.
3. Waitlist order is FIFO-monotonic per event.
4. Duplicate equivalent emails do not consume another seat.
5. All state changes occur in one database transaction protected by the event lock.
6. Migration and full verification are green.
