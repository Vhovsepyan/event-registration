ChatGPT Astra 6 review

# Task 0022 — P1: Keep live worker claims from expiring during a batch

- Status: OPEN
- Priority: P1
- Created: 2026-09-14T17:27:36+04:00
- Reviewed commit: `75581e6`
- Source: [review](../reviews/2026-09-14-astra6-review.md)

## Problem and evidence

All 20 default batch rows receive one claim timestamp before sequential delivery (`backend/app/notification/worker.py:91`). With the default 60-second lease and four-second successful sends, another worker can reclaim remaining rows while the first is still healthy. The first worker continues sending detached claimed objects. Completion and failure updates (`:100`, `:109`) check only row ID, so an expired owner can overwrite a newer owner's state.

Case `slow_batch_duplicate` runs two actual worker instances against PostgreSQL and advances only the worker clock. Twenty due reminders produced 25 recording-mailer deliveries with no crash or transport failure. Four-second sends are within the configured SMTP timeout. This is preventable lease overlap, separate from the documented crash-after-SMTP-acceptance limitation.

## Acceptance criteria

1. Use per-claim ownership tokens and condition completion/failure updates on current ownership and state.
2. Claim just before delivery, renew leases, or otherwise prevent a healthy sequential batch from losing ownership while waiting to send.
3. A worker that loses its claim must not knowingly send the remaining stale batch or reset a row completed by a newer owner.
4. Add deterministic PostgreSQL tests for slow sends crossing the lease, two workers, stale-owner completion/failure, and abandoned-claim recovery.
5. Preserve recovery after a real crash and explicitly retain the honest at-least-once SMTP boundary; this task does not promise universal exactly-once SMTP delivery.

## Verification

Convert the linked diagnostic scenario into regression tests asserting the corrected behavior. Run the PostgreSQL suite, relevant worker tests, migration checks when needed, and existing frontend/browser checks if affected. The review reproduction is [here](../reviews/astra6-reproduce.py); it currently asserts the observed defective behavior and is not a passing acceptance test.
