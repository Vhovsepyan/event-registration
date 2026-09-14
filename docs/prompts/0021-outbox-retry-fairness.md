# Task 0021 prompt evidence

Source: the user's instruction on 2026-09-14 to continue the implementation plan from task 0019 onward, executed with Claude Code (Claude Opus 5); the task specification was authored by the ChatGPT Astra 6 review in `docs/tasks/0021-outbox-retry-fairness.md`.

Persist a next-attempt time with backoff, classify permanent versus transient delivery failures with a terminal audited state and a deliberate retry mechanism, reject line breaks in titles while rendering already persisted subjects safely, and prove with PostgreSQL worker tests that a full batch of permanent failures no longer starves later confirmation, promotion, reminder, and reschedule mail while transient failures still retry successfully.
