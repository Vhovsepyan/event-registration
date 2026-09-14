# Task 0011: Notification Outbox and Mailpit

## Objective

Persist notification intent atomically with business state and deliver pending messages asynchronously to local Mailpit with retries.

## Scope

- Add Notification Outbox persistence, enums, dedupe constraint, and migration.
- Enqueue confirmed-registration and waitlist-promotion intent in their existing transactions.
- Add PostgreSQL `ON CONFLICT DO NOTHING` deduplication.
- Add an SMTP adapter and polling worker that sends outside core business transactions.
- Mark successes sent and leave failures pending with incremented attempts for retry.
- Add Mailpit to Docker Compose with SMTP and browser ports.
- Add outbox atomicity/deduplication and worker retry tests.

## Out of scope

- Final confirmation/promotion email rendering and live Mailpit delivery proof (task 0012).
- Reminders and reschedule notifications.

## Acceptance criteria

1. Confirmed creation and waitlist promotion create durable outbox rows in the same transaction.
2. Unique dedupe keys prevent duplicate generation.
3. The worker sends pending rows via SMTP and marks success.
4. Failed delivery increments attempts, remains pending, and succeeds on a later poll.
5. Mailpit is locally runnable and inspectable.
6. Migration and full verification are green.
