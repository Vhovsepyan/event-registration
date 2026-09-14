# Decision 0022: Per-Row Claim Ownership in the Outbox Worker

- Status: Accepted
- Date: 2026-09-14

## Context

The worker claimed a whole batch with one lease timestamp and then delivered the rows one by one. A batch of slow but healthy sends could take longer than the lease, so a second worker reclaimed the unsent tail while the first worker kept sending from its detached list, and completion/failure updates matched on row ID alone, letting an expired owner overwrite a newer owner's state. Twenty reminders became twenty-five deliveries with no crash involved.

## Decision

- A worker claims **one row at a time, immediately before sending it**. The claim transaction selects the next due row with `FOR UPDATE SKIP LOCKED`, re-verifies reminder applicability (decision 0020), stamps `claimed_at`, increments `attempts`, and stores a fresh random `claim_token`. The lease therefore only ever has to cover one SMTP call, not a batch; a cycle is still bounded by the batch size.
- Completion and failure are **conditioned on ownership**: `UPDATE ... WHERE id = :id AND claim_token = :token AND status = 'PROCESSING'`. A worker whose token no longer matches gets zero rows, logs that its claim was taken over, and changes nothing. The newer owner records the outcome.
- Recovery after a real crash is unchanged: a `PROCESSING` row whose `claimed_at` is older than the lease is reclaimable with a new token.

## Remaining boundary

Delivery is still at-least-once at the SMTP boundary. If a single SMTP call outlives the lease, or the worker dies after SMTP accepts the message but before the ownership-conditioned `SENT` update commits, another worker reclaims the row and sends it again. The database record stays consistent (one row, the newer owner's outcome, an honest attempt count), but the recipient can receive the message twice. Closing that window would require exactly-once semantics from the mail transport, which SMTP does not offer; this task does not claim it.

## Consequences

A healthy sequential batch can no longer lose ownership of work it is still doing, two workers share unclaimed work without duplicating it, and stale owners cannot reset or overwrite rows. Migration `20260914_0011` adds the nullable `claim_token` column; rows in flight during deployment carry no token and are reclaimed after their lease like any abandoned claim.
