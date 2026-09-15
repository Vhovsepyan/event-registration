# Decision 0029: Email Links as the Participant's Identity

- Status: Accepted
- Date: 2026-09-15

## Context

There are no accounts (decision 0003). After closing the browser a participant had no way back to their registration except re-entering the same email on the event page, and a waitlisted participant received no email at all until promotion.

## Decision

Every participant email carries a self-service link `/events/{event_id}/registrations/{registration_id}`; the registration id acts as the possession-based identity for viewing and cancelling that registration, the same way the ticket code does for check-in. Joining the waiting list sends a `WAITLIST_JOINED` email with the participant's place in line so the link is available to everyone who registered, not only to confirmed participants.

## Consequences

Cancellation days later works from any email, with unchanged FIFO promotion. The link is unguessable (UUID) but not secret-rotated; anyone holding it can cancel that registration, which matches the product's no-login scope and is stated in README's limitations. Mailpit stays the default mail sink; `SMTP_STARTTLS`/`SMTP_USERNAME`/`SMTP_PASSWORD` allow a real provider without code changes.
