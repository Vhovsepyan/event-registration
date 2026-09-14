# Decision 0003: No Authentication in the Initial Product

- Status: Accepted
- Date: 2026-09-14

## Decision

Do not add login, user accounts, roles, or authorization to the initial implementation. The assignment explicitly permits a product without authentication, and access control is not needed to demonstrate the required registration, ticket, concurrency, notification, and live-update behavior.

## Consequences

Organizer and staff endpoints are intentionally unauthenticated for the local demonstration. Production deployment would require a separate security design before exposing those operations publicly.
