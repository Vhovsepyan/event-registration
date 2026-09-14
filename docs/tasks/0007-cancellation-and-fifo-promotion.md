# Task 0007: Cancellation and FIFO Promotion

## Objective

Cancel registrations safely and promote the earliest active waitlisted participant whenever a confirmed cancellation frees a seat.

## Scope

- Implement `POST /api/events/{event_id}/registrations/{registration_id}/cancel`.
- Lock the event row before every cancellation/seat-release decision.
- Mark the target cancelled and invalidate its active ticket.
- Promote the smallest active FIFO waitlist order in the same transaction.
- Issue the promoted participant a ticket before commit.
- Make repeated cancellation idempotent.
- Preserve historical waitlist order so assigned values remain monotonic and are never reused.
- Add PostgreSQL integration tests for confirmed cancellation/promotion, waitlisted cancellation, and repeat behavior.

## Deferred integration

The plan orders transactional outbox persistence in task 0011. Promotion notification creation will be connected to this same transaction in task 0011 and its delivery behavior in task 0012; no unreliable pre-outbox side effect is introduced here.

## Acceptance criteria

1. Confirmed cancellation, ticket invalidation, earliest promotion, and promoted ticket issuance commit atomically under the event lock.
2. The next FIFO participant is promoted; later participants remain waitlisted.
3. Cancelling a waitlisted participant does not free a seat or trigger promotion.
4. Repeating cancellation has no additional effect.
5. Historical queue ordering remains monotonic and unambiguous.
6. Migration and full verification are green.
