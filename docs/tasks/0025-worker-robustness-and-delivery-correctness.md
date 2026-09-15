# Task 0025 — Worker robustness and delivery correctness

- Status: DONE (2026-09-15, task 0025 commit)
- Created: 2026-09-15
- Source: second external review round (GPT 5.6 ultra findings 1, 2, secondary 1 and 5; Copilot Opus 5 findings 1 and 2), verified against the code on 2026-09-15

## Problems and evidence

1. `run_forever` in `backend/app/notification/worker.py` is a bare `while True`. Any exception escaping `process_once` — a dropped PostgreSQL connection, a deadlock, a transient DNS error — terminates the worker process while the API keeps queueing mail.
2. `SmtpMailer.send` converts every `SMTPRecipientsRefused`, `SMTPSenderRefused`, and `SMTPDataError` into `PermanentDeliveryError` without inspecting the reply code. Temporary 4xx replies (450 mailbox busy, 451 greylisting) therefore become terminal `FAILED` rows, contradicting decision 0021.
3. The dispatch gate `_obsolete_reason` checks schedule revision, registration status, and ticket validity but never the clock, so a reminder queued while the worker was down is delivered after the event has already started.
4. Cancellation suppresses only reminders. A `REGISTRATION_CONFIRMED` or `WAITLIST_PROMOTED` row still queued when the participant cancels is delivered afterwards with a ticket that is already invalid.
5. Every actual reschedule creates a new outbox row per active participant (task 0019, required). With no authentication (decision 0003), a client alternating two dates in a loop can generate unbounded outbound mail; nothing bounds delivery to the worker's cadence.

## Acceptance criteria

1. The worker loop survives exceptions from a cycle: it logs them, waits with bounded backoff, and continues; a healthy cycle resets the backoff. Prove with a loop test where the first cycle raises and the next succeeds.
2. SMTP replies are classified by code: 5xx recipient/sender/data rejections are permanent; 4xx replies are transient and retried with the existing backoff. Prove both for `SMTPRecipientsRefused` and `SMTPDataError`/`SMTPSenderRefused`.
3. A reminder whose event `starts_at` is not in the future at claim time is suppressed with an auditable reason, never sent.
4. Cancelling a registration suppresses its `PENDING` confirmation and promotion rows in the same transaction, with an auditable reason; the promotion path for the next waitlisted participant is unchanged.
5. When a new reschedule notice is queued for a recipient, older `PENDING` reschedule notices for the same recipient and event are suppressed as superseded, so a burst of PATCHes yields one delivered email carrying the current schedule. Intent rows for every change are still recorded (task 0019 identity is unchanged). Document the bound in decisions 0003 and 0019.
6. PostgreSQL suite, worker tests, and browser proofs stay green.

## Resolution

- `run_cycles` wraps each cycle: an escaping exception is logged with `logger.exception`, the loop sleeps with doubling backoff capped at `notification_retry_max_seconds`, and a healthy cycle resets the delay to the poll interval. `run_forever` delegates to it and configures logging. Test: two failing cycles then two healthy ones yield sleeps `[2, 4, 2, 2]`.
- `SmtpMailer.send` classifies by reply code (`_is_permanent_reply`: 5yz). `SMTPRecipientsRefused` is permanent only if every recipient code is 5yz; `SMTPSenderRefused`/`SMTPDataError` use `smtp_code`; 4yz replies propagate as transient and are retried with the existing backoff. Tests cover 450/451/550/553/554 and an end-to-end 451-then-success delivery.
- `_obsolete_reason` suppresses a reminder whose event `starts_at <= clock()` with `event already started before delivery`.
- `NotificationService.suppress_pending` is the general primitive; `suppress_pending_for_cancelled_registration` retires `PENDING` reminder, confirmation, and promotion rows for a cancelled registration in the cancel transaction. Promotion of the next participant is unchanged (tested: first cancels before confirmation, second is promoted and cancels before promotion, third is promoted and delivered).
- `enqueue_event_rescheduled` suppresses older `PENDING` reschedule notices for the same event and registration as `superseded by schedule revision N` before inserting the new one. Every change still gets its own row and revision key (task 0019); delivery is bounded to one email per recipient per worker cycle. Decisions 0003 and 0019 updated.

## Out of scope

- Authentication or rate limiting at the API edge (documented next steps).
