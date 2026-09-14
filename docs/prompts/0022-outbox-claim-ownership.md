# Task 0022 prompt evidence

Source: the user's instruction on 2026-09-14 to continue the implementation plan from task 0019 onward, executed with Claude Code (Claude Opus 5); the task specification was authored by the ChatGPT Astra 6 review in `docs/tasks/0022-outbox-claim-ownership.md`.

Introduce per-claim ownership tokens, claim each outbox row immediately before delivering it so a slow healthy batch cannot lose ownership of its tail, condition completion and failure updates on current ownership and state, keep crash recovery after the lease, prove slow sends across the lease with two workers, stale-owner updates, and abandoned-claim recovery deterministically against PostgreSQL, and state the honest at-least-once SMTP boundary rather than promising exactly-once delivery.
