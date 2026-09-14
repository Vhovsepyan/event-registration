# Decision 0014: Reschedule Recipients

- Status: Accepted
- Date: 2026-09-14

## Decision

Send event-reschedule notifications to both confirmed and waitlisted registrations because both groups made plans around the published schedule. Exclude cancelled registrations because they are no longer active participants.

## Consequences

Rescheduling locks the event row, snapshots active recipients, updates the schedule, and creates outbox rows in one transaction. The new schedule appears in both reschedule and reminder dedupe keys, allowing a new reminder after a date change.
