# Decision 0013: Reminder Recipients

- Status: Accepted
- Date: 2026-09-14

## Decision

Send approximately 24-hour reminders only to currently confirmed participants with active tickets. Waitlisted users are not confirmed event participants and therefore do not receive reminders.

## Consequences

Promotion into a confirmed state makes a participant eligible on the next worker poll. Cancellation/invalidation removes eligibility, and since task 0020 it also suppresses an already queued reminder. Schedule time and revision are part of the dedupe key so rescheduling creates a new reminder; see decisions 0019 and 0020.
