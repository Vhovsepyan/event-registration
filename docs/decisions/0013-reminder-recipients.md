# Decision 0013: Reminder Recipients

- Status: Accepted
- Date: 2026-09-14

## Decision

Send approximately 24-hour reminders only to currently confirmed participants with active tickets. Waitlisted users are not confirmed event participants and therefore do not receive reminders.

## Consequences

Promotion into a confirmed state makes a participant eligible on the next worker poll. Cancellation/invalidation removes eligibility. Schedule time is part of the dedupe key so task 0014 can create a new reminder after rescheduling.
