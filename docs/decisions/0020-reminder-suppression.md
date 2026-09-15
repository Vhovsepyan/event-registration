# Decision 0020: Reminder Suppression and the In-flight SMTP Boundary

- Status: Accepted
- Date: 2026-09-14

## Context

Reminder eligibility was decided once, at generation, and the worker later sent the stored payload unconditionally. A participant who cancelled, or an event that was postponed, still received the old reminder with an invalid ticket or the wrong date.

## Decision

Reminder intent is checked three times, and obsolete intent ends in an auditable terminal state instead of being deleted.

1. **Generation** share-locks the due Event rows (`SELECT ... FOR SHARE`) before selecting confirmed, ticketed registrations. Registration, cancellation, promotion, and rescheduling all take the Event row `FOR UPDATE`, so generation and those changes serialize on the same lock: generation that waits sees the committed new state, and a change that waits sees the committed generated rows and suppresses them.
2. **Business transactions** mark `PENDING` reminders `SUPPRESSED` in the same transaction that cancels a registration (`registration cancelled`) or moves an event (`event rescheduled to revision N`). Each outbox row stores the `schedule_revision` it was generated for.
3. **Dispatch** re-verifies every claimed reminder against current state (event revision unchanged, event not yet started, registration still `CONFIRMED`, ticket not invalidated) inside the claim transaction and suppresses it with a `before delivery` reason if anything changed.

Since task 0025 cancellation also suppresses the registration's still-unsent confirmation and promotion rows, so a participant who cancels before the worker runs does not receive mail describing a ticket that is already invalid.

`SUPPRESSED` is terminal. Rows keep their payload, dedupe key, `suppressed_at`, and `suppression_reason` for audit, and they never retry.

## Remaining boundary

Once a worker has verified and claimed a row, the message goes to SMTP immediately. A cancellation or reschedule that commits after that verification and before SMTP accepts the message cannot recall it; the participant then also receives the promotion, cancellation-free confirmation, or reschedule mail that describes the newer state. Business transactions therefore leave `PROCESSING` rows alone, so a row that was actually handed to SMTP is recorded as `SENT`, never falsely as suppressed. Closing this window would require holding a database lock across the SMTP call, which the outbox design deliberately avoids.

## Consequences

A postponed event receives exactly one reminder for its current revision when the new schedule enters the lead window. A cancelled participant receives no reminder; a later re-registration is a new registration with its own reminder. Migration `20260914_0009` adds the state and back-fills revisions for existing rows; a reminder whose stored time no longer matches its event is tagged `-1` and suppressed at dispatch. Downgrading requires resolving any `SUPPRESSED` rows first.
