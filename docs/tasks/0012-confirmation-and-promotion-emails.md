# Task 0012: Confirmation and Promotion Emails

## Objective

Produce useful confirmed-registration and waitlist-promotion emails containing event and ticket details, then deliver them through the outbox worker to Mailpit.

## Scope

- Centralize typed email content rendering for confirmation and promotion.
- Include event title, scheduled time, and manually typeable ticket code.
- Add specialized notification enqueue methods and use them in registration/promotion transactions.
- Test both notification types and rendered content.
- Verify real SMTP delivery and inspection through Mailpit.

## Out of scope

- HTML email, attachments, reminders, and reschedule emails.

## Acceptance criteria

1. Confirmed registration creates a confirmation email payload with event/time/ticket.
2. FIFO promotion creates a distinct promotion email payload with event/time/ticket.
3. Repeated operations remain deduplicated.
4. The worker delivers messages to Mailpit and marks rows sent.
5. Full verification is green.
