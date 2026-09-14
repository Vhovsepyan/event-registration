ChatGPT Astra 6 review

# Task 0019 — P1: Notify participants on every actual reschedule

- Status: DONE (2026-09-14, task 0019 commit)
- Priority: P1
- Created: 2026-09-14T17:27:36+04:00
- Reviewed commit: `75581e6`
- Source: [review](../reviews/2026-09-14-astra6-review.md)

## Problem and evidence

The destination timestamp is used as the reschedule notification identity in `backend/app/notification/service.py:140`. Consequently A → B → A → B creates only two messages per active registration. The last change commits successfully but its notification is silently discarded by `ON CONFLICT DO NOTHING`. Participants can retain the wrong schedule.

This follows the current task 0014 specification literally, but that specification fails the assignment's requirement to notify participants whenever the organizer moves an event. Correct the specification and decision 0014 with the implementation.

Reproduction: run `astra6-reproduce.py` as described in the review. Case `reschedule_revisit` reports three changes and only two notification rows. This occurs without concurrency, transport failures, or worker crashes.

## Acceptance criteria

1. Persist a schedule revision or equivalent change identity, incremented only when the instant actually changes under the existing Event lock.
2. Create one reschedule notification per active recipient and actual change, including repeated transitions and revisited dates; keep all intent in the event transaction.
3. A repeated PATCH of the current instant, including an equivalent timezone representation, creates no new change or notification.
4. Add PostgreSQL tests for A → B → A → B, confirmed and waitlisted recipients, no-op updates, and rollback atomicity.
5. Document how schedule revisions interact with reminder identity; preserve historical notifications and update decision 0014.

## Resolution

- `events.schedule_revision` (migration `20260914_0008`) starts at 0 and is incremented in `EventService.reschedule` under the Event row lock only when the requested instant differs from the stored one; aware datetimes compare as instants, so an equivalent timezone representation is a no-op.
- Reschedule rows are keyed `event-rescheduled:{event_id}:{registration_id}:r{revision}`; reminders are keyed `event-reminder:{event_id}:{registration_id}:{starts_at}:r{revision}`. Payloads carry `schedule_revision`. Historical rows are untouched.
- `EventRead` exposes `schedule_revision`.
- Regression tests in `backend/tests/event/test_reschedule.py`: A → B → A → B yields three rows per confirmed and waitlisted recipient with revisions 1–3; same-instant PATCH in UTC and +04:00 creates nothing; a failing notification enqueue rolls the schedule and revision back; a revisited date yields a new reminder identity.
- Decision 0014 and task 0014 corrected; decision 0019 records the identity.

## Verification

Convert the linked diagnostic scenario into regression tests asserting the corrected behavior. Run the PostgreSQL suite, relevant worker tests, migration checks when needed, and existing frontend/browser checks if affected. The review reproduction is [here](../reviews/astra6-reproduce.py); it currently asserts the observed defective behavior and is not a passing acceptance test.
