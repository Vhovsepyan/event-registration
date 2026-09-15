# Task 0029 — Registration self-service and waitlist email

- Status: OPEN
- Created: 2026-09-15T10:06:36+04:00
- Source: user product review on 2026-09-15 — "how can a participant cancel the registration?" and "participant doesn't receive email"

## Problem

- The **Cancel participation** action exists only on the result screen shown immediately after registering. A participant who returns later can only reach it by re-entering the same email on the event page (the idempotent register call returns the existing registration), which nobody would guess.
- Waitlisted participants receive no email at all until they are promoted, so they have no record of their place in line and no link back.
- Emails are delivered to the local Mailpit sink (http://localhost:8025), which is by design and permitted by the assignment, but the README explains it only in the run section; a first-time user registering with a personal address expects an inbox message.

## Scope

- Registration self-service page `/events/{event_id}/registrations/{registration_id}` showing the event, current status, ticket (when confirmed), and the cancel action with the existing confirmation/pending/error handling; the existing `GET` registration lookup or a new read endpoint backs it.
- Every participant email (confirmation, promotion, reminder, reschedule) includes the self-service link.
- A `WAITLIST_JOINED` notification when a registration is waitlisted: position in line, event time, and the self-service link; deduplicated per registration and suppressed on cancellation like the other participant mail.
- "Already registered? Enter your email to open your registration" wording on the event page.
- README opens with where emails go (Mailpit) and how to inspect them; optional `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_STARTTLS` settings for pointing the worker at a real provider, off by default.
- Tests: waitlist email creation/dedupe/suppression, links present in templates, self-service page component tests, Playwright cancellation scenario driven through the self-service page.

## Acceptance criteria

1. A participant can open the self-service link from any email and cancel, days after registering, with the same FIFO promotion behaviour.
2. Waitlisted participants receive exactly one waitlist email per registration attempt, and none after cancelling.
3. All participant emails carry a working self-service link.
4. Mailpit's role is stated at the top of the README; real SMTP credentials are optional and never required.
5. Backend, frontend, and Playwright suites are green.

## Out of scope

- Accounts, magic-link login, or per-email registration lists across events.
