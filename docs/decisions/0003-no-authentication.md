# Decision 0003: No Authentication in the Initial Product

- Status: Accepted
- Date: 2026-09-14

## Decision

Do not add login, user accounts, roles, or authorization to the initial implementation. The assignment explicitly permits a product without authentication, and access control is not needed to demonstrate the required registration, ticket, concurrency, notification, and live-update behavior.

## Consequences

Organizer and staff endpoints are intentionally unauthenticated for the local demonstration. Production deployment would require a separate security design before exposing those operations publicly.

Addendum 2026-09-15 (task 0025): because rescheduling is unauthenticated and every actual change must notify participants, a client looping between two dates could otherwise amplify into unbounded outbound mail. Delivery is therefore bounded: a new reschedule notice supersedes any still-unsent notice for the same recipient, so a burst of changes yields one email per recipient per worker cycle carrying the current schedule. Rate limiting at the API edge remains a documented next step.
