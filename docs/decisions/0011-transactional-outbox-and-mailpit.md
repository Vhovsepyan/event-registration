# Decision 0011: Transactional Outbox and Mailpit

- Status: Accepted
- Date: 2026-09-14

## Decision

Write notification intent to PostgreSQL in the same transaction as registration/promotion state, then let a separate polling worker deliver it over SMTP. Use a unique semantic dedupe key for operations that must generate at most one row. Use Mailpit locally as a safe SMTP sink with a browser inbox.

## Consequences

Business commits never depend on SMTP availability, crashes cannot lose committed notification intent, and delivery failures can retry. Delivery is at-least-once at the SMTP boundary. Mailpit prevents accidental external mail during development and makes messages easy to demonstrate.
