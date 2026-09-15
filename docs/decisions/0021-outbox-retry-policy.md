# Decision 0021: Outbox Retry Policy and Failure Classification

- Status: Accepted
- Date: 2026-09-14

## Context

The worker claimed the oldest pending rows with a fixed batch limit and returned failures to `PENDING` immediately. A batch of rows that could never be delivered was reclaimed every cycle ahead of all newer mail, so one bad event could stop every confirmation, promotion, reminder, and reschedule email indefinitely.

## Decision

- Every outbox row carries `next_attempt_at`. The worker claims only rows whose time has come and orders them by `next_attempt_at`, then `created_at`, so deferred retries queue behind work that became due earlier instead of ahead of it.
- A transient failure (connection errors, timeouts, 4xx SMTP replies, anything unclassified) is deferred with exponential backoff: `retry_base_seconds × 2^(attempts−1)`, capped at `retry_max_seconds` (defaults 5 s and 300 s).
- A permanent failure (`PermanentDeliveryError`: message construction rejected by Python's `EmailMessage`, or an SMTP 5yz recipient/sender/data rejection; 4yz replies such as 450/451 are transient and retried, corrected by task 0025) and any row that reaches `notification_max_attempts` (default 5) becomes `FAILED`, a terminal state with `failed_at` and `last_error`. Failed rows keep their payload and attempt history and are never claimed again automatically.
- `python -m app.notification.worker retry-failed [--id UUID]` deliberately returns failed rows to `PENDING` for one more cycle; the attempt count is kept, so a row that fails again returns to `FAILED` immediately.
- Event titles must be a single line, enforced by request validation and the `ck_events_title_single_line` constraint. The mailer additionally folds any CR/LF in a persisted subject into spaces, so rows stored before this rule still deliver.

## Worker process resilience

Since task 0025 the polling loop (`run_cycles`) catches any exception from a cycle, logs it, and retries with doubling backoff capped at `notification_retry_max_seconds`; a dropped database connection or deadlock no longer terminates the worker while the API keeps queueing mail.

## Consequences

Healthy mail is attempted no later than the cycle after a failing batch, regardless of batch size. Delivery remains at-least-once and asynchronous; nothing in this policy adds SMTP calls to business transactions. Operators can see why a row failed and choose to retry it. Migration `20260914_0010` folds any existing multi-line titles before adding the constraint and sets `next_attempt_at = created_at` for existing rows so their order is unchanged.
