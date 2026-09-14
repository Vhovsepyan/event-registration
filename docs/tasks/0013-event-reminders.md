# Task 0013: 24-hour Event Reminders

## Objective

Generate one durable reminder per confirmed participant and event schedule when the event enters its approximately 24-hour reminder window.

## Scope

- Poll PostgreSQL for future events within the configured lead window.
- Include only confirmed registrations with active tickets.
- Enqueue reminder content with event time and ticket code.
- Use `event-reminder:{event_id}:{registration_id}:{starts_at}` dedupe identity.
- Run reminder generation from the persistent notification worker cycle.
- Add due-window, recipient-selection, and repeat-run idempotency tests.

## Out of scope

- Rescheduling and new-schedule reminder behavior (task 0014).

## Acceptance criteria

1. A confirmed participant receives one reminder row inside the lead window.
2. Waitlisted participants receive no reminder.
3. Running reminder generation repeatedly creates no duplicate for one schedule.
4. A restart loses no schedule because due work is derived from PostgreSQL.
5. Reminder payload contains event time and active ticket code.
6. Full verification is green.
