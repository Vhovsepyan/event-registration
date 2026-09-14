# Task 0014: Event Rescheduling and Notifications

## Objective

Allow organizers to change an event's future start time and durably notify every active affected participant.

## Scope

- Implement `PATCH /api/events/{event_id}` for `starts_at` rescheduling.
- Validate a timezone-aware future replacement time.
- Lock the Event row and update it with notification creation in one transaction.
- Notify both confirmed and waitlisted registrations; exclude cancelled registrations.
- Include old/new schedule details in email payloads.
- Dedupe by event, registration, and new scheduled time.
- Prove a changed schedule creates a distinct reminder identity.

## Out of scope

- Editing title, description, or capacity.
- Frontend reschedule UI.

## Acceptance criteria

1. PATCH persists and returns the new future start time.
2. One reschedule outbox row is created for every active confirmed/waitlisted participant.
3. Cancelled participants receive no reschedule row.
4. Repeating the same time creates no notifications.
5. A new schedule can generate a new reminder despite an old-schedule reminder.
6. All changes are transactional and full verification is green.
