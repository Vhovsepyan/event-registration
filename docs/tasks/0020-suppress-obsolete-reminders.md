ChatGPT Astra 6 review

# Task 0020 — P1: Suppress queued reminders after cancellation or rescheduling

- Status: DONE (2026-09-14, task 0020 commit)
- Priority: P1
- Created: 2026-09-14T17:27:36+04:00
- Reviewed commit: `75581e6`
- Source: [review](../reviews/2026-09-14-astra6-review.md)

## Problem and evidence

Reminder eligibility is checked only when generating rows (`backend/app/notification/service.py:148`). Delivery blindly sends the stored payload (`backend/app/notification/worker.py:62`); cancellation and rescheduling do not invalidate it.

Generate a reminder for an event in 23 hours while delivery is paused, postpone it seven days, then resume the worker. The old reminder is delivered with the original date. Cancelling the participant instead still delivers a reminder with an invalid ticket. Both cases were reproduced without overlapping transactions.

Cases: `stale_reminder_after_reschedule` and `stale_reminder_after_cancel` each report one obsolete reminder delivered. This can misdirect participants after a valid product action.

## Acceptance criteria

1. Record enough schedule/participation identity to determine whether a reminder remains applicable at dispatch.
2. Suppress unsent reminders for cancelled registrations, invalid tickets, or obsolete event schedules, with an auditable terminal state.
3. Coordinate generation/invalidation so an in-flight generator cannot resurrect obsolete intent after cancellation or rescheduling commits; define the remaining in-flight SMTP boundary explicitly.
4. A postponed event gets its current reminder at the new due window, once per documented schedule identity.
5. Add PostgreSQL worker tests for queued-then-cancelled, queued-then-postponed, re-registration, and overlapping generation/rescheduling; preserve asynchronous SMTP.

## Resolution

- Migration `20260914_0009` adds `notification_outbox.schedule_revision`, `suppressed_at`, `suppression_reason`, and the terminal `SUPPRESSED` status, and back-fills revisions for existing rows (a reminder whose stored time no longer matches its event is tagged `-1`).
- `RegistrationService.cancel` and `EventService.reschedule` suppress `PENDING` reminders in their own transactions (`registration cancelled`, `event rescheduled to revision N`).
- `ReminderService.generate_due` share-locks due Event rows before selecting recipients, so it serializes with every `FOR UPDATE` seat/schedule change.
- `NotificationWorker._claim` re-verifies each claimed reminder (event revision, registration `CONFIRMED`, ticket valid) inside the claim transaction and suppresses obsolete rows with a `before delivery` reason. `PROCESSING` rows are the explicit in-flight boundary; see decision 0020.
- Tests in `backend/tests/notification/test_reminder_lifecycle.py`: queued-then-cancelled, queued-then-postponed with one reminder at the new window, re-registration, dispatch-time suppression of resurrected intent, and forced overlap of generation with rescheduling in both lock orders.

## Verification

Convert the linked diagnostic scenario into regression tests asserting the corrected behavior. Run the PostgreSQL suite, relevant worker tests, migration checks when needed, and existing frontend/browser checks if affected. The review reproduction is [here](../reviews/astra6-reproduce.py); it currently asserts the observed defective behavior and is not a passing acceptance test.
