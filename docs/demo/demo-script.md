# Product demo script

1. Open `http://localhost:5173` and create a future event with capacity 1. Keep the organizer dashboard open so its live counts remain visible throughout the demo.
2. Open the dashboard's **Participant page** link in a second browser/private window. Register `first@example.com`, show **Confirmed**, and record its ticket as the old ticket.
3. Open the participant link in another isolated tab/window, register `second@example.com`, and show **Waiting list**. The organizer dashboard changes to `1 confirmed / 1 waiting` without refresh.
4. On the first participant result, choose **Cancel participation**, decline the confirmation once to show that nothing changes, then choose it again and confirm. Show **Your participation is cancelled**, the message that the previous ticket is no longer active, and the absence of an active ticket link.
5. Show the automatic FIFO result: `second@example.com` is promoted, and the organizer dashboard changes to `1 confirmed / 0 waiting`. Run the notification worker and show the promotion email and newly issued ticket in Mailpit at `http://localhost:8025`.
6. On the cancelled first-participant page, choose **Register again**. Because the promoted participant holds the only seat, show that this new attempt is **Waiting list**, not the stale cancelled result. The organizer dashboard returns to `1 confirmed / 1 waiting`.
7. Open **Check in**, submit the first participant's old ticket, and show **Invalid ticket**.
8. Open a fresh participant page and submit `second@example.com` to retrieve its current confirmed result without creating a duplicate. Cancel it. Show that the re-registered `first@example.com` attempt is promoted in FIFO order and receives a different current ticket in its promotion email.
9. Submit the first participant's new ticket at **Check in** and show **Check-in successful**. Submit it again and show **Already checked in**; also submit an invented code and show **Invalid ticket**.
10. Without refreshing the organizer dashboard, show its checked-in count and active registration counts changing through SSE during the flow.
11. In Mailpit, show the original confirmation, each applicable FIFO promotion, and that ticket codes correspond to the current attempts. Notification intent is deduplicated in PostgreSQL; SMTP transport remains at-least-once.
12. Optionally reschedule the event from the dashboard and run the worker again to show reschedule mail for active participants only.

For automated versions of the two-client check-in/SSE proof and participant cancellation/re-registration proof, follow `multi-client-verification.md` in this directory.
