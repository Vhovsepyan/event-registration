# Decision 0019: Schedule Revision as Change Identity

- Status: Accepted
- Date: 2026-09-14

## Context

Task 0014 identified reschedule notifications by the destination time. Moving an event A → B → A → B is three real changes, but the third change conflicted with the first visit to B and was discarded by `ON CONFLICT DO NOTHING`, so participants were not told about the final schedule. The assignment requires a notification for every organizer move.

## Decision

Persist `events.schedule_revision`, an integer that starts at 0 and is incremented under the existing Event row lock only when the requested instant differs from the stored one. Equivalent representations of the same instant (for example another timezone offset) compare equal and are no-ops.

- Reschedule notification identity: `event-rescheduled:{event_id}:{registration_id}:r{revision}`.
- Reminder identity: `event-reminder:{event_id}:{registration_id}:{starts_at}:r{revision}`. It still contains the scheduled time, as the plan requires, and the revision makes a revisited date a new reminder schedule.
- Notification payloads record the revision they were generated for.

## Consequences

Every actual change creates one new reschedule row per active participant, including repeated transitions and returns to earlier dates. No-op updates remain idempotent. Historical rows keep their original dedupe keys; the migration only adds the revision column with default 0. Task 0020 uses the persisted revision to decide at dispatch whether a queued reminder still describes the current schedule.
