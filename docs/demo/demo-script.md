# Product demo script

1. Open `http://localhost:5173` and create a future event with capacity 1.
2. Keep the organizer dashboard open and copy its **Participant page** link into another browser/private window.
3. Register the first email. Show the **Confirmed** result and manually typable ticket code.
4. Register a second email in the other browser. Show the **Waiting list** result and the live dashboard's `1 confirmed / 1 waiting` state.
5. Open **Check in**, submit the confirmed ticket, and show **Check-in successful**.
6. Submit it again and show **Already checked in**. Submit an invented code and show **Invalid ticket**.
7. Return to the organizer dashboard without refreshing it and show the checked-in count changed through SSE.
8. Open `http://localhost:8025` and show the confirmation email captured by Mailpit after the notification worker has processed it.
9. Optionally reschedule the event from the dashboard and run the worker again to show reschedule mail for both active participants.

For an automated version of the two-client check-in portion, follow `multi-client-verification.md` in this directory.
