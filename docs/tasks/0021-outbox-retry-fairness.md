ChatGPT Astra 6 review

# Task 0021 — P1: Prevent failing messages from starving the outbox

- Status: DONE (2026-09-14, task 0021 commit)
- Priority: P1
- Created: 2026-09-14T17:27:36+04:00
- Reviewed commit: `75581e6`
- Source: [review](../reviews/2026-09-14-astra6-review.md)

## Problem and evidence

The worker selects the oldest PENDING rows with a fixed batch limit (`backend/app/notification/worker.py:78`), then immediately returns failures to PENDING without a retry date or terminal state (`:109`). A permanently failing oldest batch occupies every subsequent cycle and prevents all newer email from being attempted.

A concrete trigger is accepted event titles containing embedded LF/CR: the templates copy the title into Subject, and Python EmailMessage rejects it. Register 20 participants for such an event, then one for a normal event. With the default batch size, three cycles retried all 20 bad rows three times while the healthy notification had zero attempts.

Case `poison_starvation` uses real SmtpMailer header construction; no SMTP connection is needed to trigger the failure.

## Acceptance criteria

1. Make retries fair: persist a next-attempt time/backoff and provide bounded or terminal handling for permanent failures so later healthy mail progresses.
2. Reject or safely render CR/LF in title-derived email subjects; account for already persisted bad payloads.
3. Retain failed intent, attempts, and error diagnostics, and provide a documented deliberate retry mechanism where appropriate.
4. Add a PostgreSQL worker test with at least one full batch of permanent failures followed by healthy confirmation, promotion, reminder, and reschedule intent.
5. Prove transient failures still retry successfully and failed rows do not spin continuously or starve healthy work.

## Resolution

- Migration `20260914_0010` adds `next_attempt_at` (back-filled to `created_at`), `failed_at`, the terminal `FAILED` status, re-keys the pending index on `(status, next_attempt_at)`, folds existing multi-line titles, and adds `ck_events_title_single_line`.
- The worker claims only due rows ordered by `next_attempt_at`, defers transient failures with capped exponential backoff, and marks permanent failures (`PermanentDeliveryError`) or exhausted attempts `FAILED` with `failed_at` and `last_error`. Settings: `notification_max_attempts`, `notification_retry_base_seconds`, `notification_retry_max_seconds`.
- `SmtpMailer` folds CR/LF in persisted subjects, raises `PermanentDeliveryError` for message-construction and 5xx rejections, and leaves connection errors transient. `EventCreate` rejects titles containing CR/LF.
- `NotificationService.retry_failed` and `python -m app.notification.worker retry-failed [--id UUID]` provide the deliberate retry path; see decision 0021.
- Tests in `backend/tests/notification/test_outbox_fairness.py`: a full batch of 20 permanent failures followed by healthy confirmation, promotion, reminder, and reschedule intent (all delivered on the next cycle, poison rows terminal after one attempt); 20 transient failures deferred while healthy mail proceeds, then retried successfully after the backoff; attempt exhaustion and deliberate retry; a persisted multi-line subject delivered through the real `EmailMessage` path; permanent/transient classification; API and database rejection of multi-line titles. The existing fail-then-succeed retry test now advances an injected clock across the backoff.

## Verification

Convert the linked diagnostic scenario into regression tests asserting the corrected behavior. Run the PostgreSQL suite, relevant worker tests, migration checks when needed, and existing frontend/browser checks if affected. The review reproduction is [here](../reviews/astra6-reproduce.py); it currently asserts the observed defective behavior and is not a passing acceptance test.
