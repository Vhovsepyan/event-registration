# Task 0020 prompt evidence

Source: the user's instruction on 2026-09-14 to continue the implementation plan from task 0019 onward, executed with Claude Code (Claude Opus 5); the task specification was authored by the ChatGPT Astra 6 review in `docs/tasks/0020-suppress-obsolete-reminders.md`.

Record the schedule revision on outbox rows, suppress unsent reminders in the cancellation and reschedule transactions with an auditable terminal state, serialize reminder generation with those transactions on the Event row lock, re-verify reminders at dispatch, state the remaining in-flight SMTP boundary explicitly, and prove queued-then-cancelled, queued-then-postponed, re-registration, and overlapping generation/rescheduling against PostgreSQL without moving SMTP into business transactions.
