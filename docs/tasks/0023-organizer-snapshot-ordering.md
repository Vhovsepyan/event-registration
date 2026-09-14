# Task 0023 — P2: Never let an older HTTP snapshot replace a newer SSE snapshot

- Status: DONE (2026-09-14, task 0023 commit)
- Priority: P2
- Created: 2026-09-14T18:31:44+04:00
- Source: [review](../reviews/2026-09-14-astra6-review.md), "Other observations, below P1"

## Problem and evidence

`frontend/src/pages/OrganizerPage.tsx` starts the initial HTTP requests and the `EventSource` subscription concurrently, and both callbacks call `setStats`. If the HTTP statistics response resolves after the first SSE snapshot and carries older counts, it overwrites the live value. Because the stream emits only changes relative to what it already sent, it will not re-send the correct value until another mutation or a reconnect, so the dashboard can show stale counts indefinitely.

## Acceptance criteria

1. Once any SSE `stats` snapshot has been applied, a later-resolving initial HTTP statistics response must not replace it.
2. The initial HTTP snapshot still renders when it arrives before the stream connects, so the dashboard is not blank while SSE is connecting or blocked.
3. Event details from the HTTP response continue to render regardless of ordering.
4. Add a component test with a delayed HTTP statistics response that resolves after an SSE snapshot and assert the live values remain.
5. Existing organizer, registration, and check-in component tests, lint, build, and the Playwright two-client proof remain green.

## Resolution

- `OrganizerPage` tracks whether a live SSE snapshot has been applied inside the effect; the initial HTTP statistics response updates event details unconditionally but sets statistics only while no live snapshot has arrived. The stream's own first snapshot is at least as fresh as any HTTP response started before it, and any later change is re-emitted by the stream, so ignoring a late HTTP snapshot is self-consistent.
- Component test `does not let a late initial HTTP snapshot replace a newer SSE snapshot` in `frontend/src/ProductFlows.test.tsx` holds the HTTP statistics promise, delivers an SSE snapshot, then resolves the stale HTTP response and asserts the live value and the event title remain. The test was confirmed to fail against the previous implementation.

## Out of scope

- Server-side sequence numbers or changes to the SSE payload.
- Replacing the initial HTTP snapshot entirely.
