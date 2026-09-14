# Task 0006: Ticket Generation and Display

## Objective

Issue a unique, unpredictable, manually typeable ticket to each confirmed registration and expose ticket details by code.

## Scope

- Add Ticket persistence and migration.
- Generate cryptographically random codes from an ambiguity-reduced alphabet in grouped form.
- Create a ticket in the same allocation transaction as a newly confirmed registration.
- Keep waitlisted registrations ticketless.
- Include an optional ticket in registration responses.
- Implement `GET /api/tickets/{code}` with event and registration status details.
- Add PostgreSQL-backed ticket generation/retrieval tests.

## Out of scope

- Check-in, invalidation, cancellation/promotion, frontend screens, and notifications.

## Acceptance criteria

1. Every newly confirmed registration receives one persisted ticket.
2. Waitlisted registrations receive no ticket.
3. Ticket codes are unique, unpredictable, uppercase, ambiguity-reduced, and grouped for manual entry.
4. Ticket lookup returns ticket, event, and registration state; unknown codes return 404.
5. Tickets are created atomically with registration allocation.
6. Migration and full verification are green.
