# Decision 0003: No Authentication in the Initial Product

- Status: Accepted
- Date: 2026-09-14

## Decision

Do not add login, user accounts, roles, or authorization to the initial implementation. The assignment explicitly permits a product without authentication, and access control is not needed to demonstrate the required registration, ticket, concurrency, notification, and live-update behavior.

## Consequences

Organizer and staff endpoints are intentionally unauthenticated for the local demonstration. Production deployment would require a separate security design before exposing those operations publicly.

Revision 2026-09-15 (task 0030): before a public demo deployment, organizer and staff routes (event creation, rescheduling, statistics, the live stream, and check-in) can be protected by a single shared secret, `ORGANIZER_KEY`, sent as the `X-Organizer-Key` header (or the `organizer_key` query parameter for the browser's `EventSource`). It is not authentication in the account sense — there is still one role, no identity, and no per-organizer ownership — but it keeps an internet-facing demo from being driven by strangers. Unset locally, so the no-login development experience is unchanged. Participant routes remain open by design; registrations and tickets are protected by unguessable identifiers (decision 0029).

Addendum 2026-09-15 (task 0025): because rescheduling is unauthenticated and every actual change must notify participants, a client looping between two dates could otherwise amplify into unbounded outbound mail. Delivery is therefore bounded: a new reschedule notice supersedes any still-unsent notice for the same recipient, so a burst of changes yields one email per recipient per worker cycle carrying the current schedule. Rate limiting at the API edge remains a documented next step.
