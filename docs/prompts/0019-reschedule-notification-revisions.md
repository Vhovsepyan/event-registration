# Task 0019 prompt evidence

Source: the user's instruction on 2026-09-14 to read `docs/` completely, then continue the implementation plan from task 0019, executed with Claude Code (Claude Opus 5); the task specification was authored by the ChatGPT Astra 6 review in `docs/tasks/0019-reschedule-notification-revisions.md`.

Persist a schedule revision incremented only on an actual instant change under the Event lock, key reschedule notifications by that revision so every real change notifies every active participant, keep equivalent-representation PATCHes idempotent, prove A → B → A → B, no-op, and rollback behavior against PostgreSQL, and correct task 0014/decision 0014 without rewriting historical notifications.
