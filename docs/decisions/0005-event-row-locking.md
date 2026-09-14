# Decision 0005: Event Row Locking for Capacity

- Status: Accepted
- Date: 2026-09-14

## Decision

Use `SELECT event ... FOR UPDATE` as the serialization point for every operation that changes seat availability. While holding that lock, read the existing normalized-email registration, count confirmed registrations, and either confirm or assign the next FIFO waitlist order in one transaction.

## Consequences

Concurrent operations for one event serialize in PostgreSQL, so no process-local mutex or distributed cache is required. Different events can still allocate independently. Cancellation and promotion must reuse this exact lock discipline in task 0007.
