# Decision 0014: Reschedule Recipients

- Status: Accepted
- Date: 2026-09-14

## Decision

Send event-reschedule notifications to both confirmed and waitlisted registrations because both groups made plans around the published schedule. Exclude cancelled registrations because they are no longer active participants.

## Consequences

Rescheduling locks the event row, snapshots active recipients, updates the schedule, increments the event's schedule revision, and creates outbox rows in one transaction.

Revised 2026-09-14 by task 0019: the reschedule notification identity is the schedule revision (`event-rescheduled:{event_id}:{registration_id}:r{revision}`), not the destination time. The original destination-time key dropped the message for a date that had been used before (A → B → A → B produced two rows instead of three). The reminder identity includes both the scheduled time and the revision; see `0019-schedule-revision.md`.
