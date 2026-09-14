# Task 0009: Organizer Statistics

## Objective

Expose authoritative event capacity, confirmed, waitlist, and checked-in counts for organizers.

## Scope

- Implement `GET /api/events/{event_id}/stats`.
- Calculate all counts from Event, Registration, and active Ticket state.
- Exclude cancelled registrations and invalidated tickets appropriately.
- Return 404 for an unknown event.
- Add lifecycle-aware PostgreSQL integration tests.

## Out of scope

- Persisted/duplicated counters, SSE streaming, and frontend dashboard UI.

## Acceptance criteria

1. Capacity matches the Event record.
2. Confirmed and waitlist counts match active registration status.
3. Checked-in count includes only active tickets belonging to confirmed registrations.
4. Counts reflect registration, check-in, cancellation, and promotion changes.
5. Full verification is green.
