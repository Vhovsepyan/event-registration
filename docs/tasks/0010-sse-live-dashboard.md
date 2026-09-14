# Task 0010: SSE Live Dashboard

## Objective

Stream changed organizer statistics to multiple browser clients using Server-Sent Events.

## Scope

- Implement `GET /api/events/{event_id}/stats/stream`.
- Emit an initial named `stats` event and new snapshots only when values change.
- Poll PostgreSQL using a fresh short-lived session per snapshot.
- Stop polling when the client disconnects.
- Configure the polling interval through environment settings.
- Add SSE formatting/endpoint and two-independent-stream tests.

## Out of scope

- Frontend EventSource integration (task 0015) and full browser proof (task 0016).
- Redis, WebSockets, or distributed pub/sub.

## Acceptance criteria

1. The endpoint uses `text/event-stream` and disables response caching.
2. Clients receive current authoritative statistics immediately.
3. Changed values are emitted without reconnecting or refreshing.
4. Two streams independently observe the same update.
5. Database polling does not retain one transaction/session for the connection lifetime.
6. Full verification is green.
