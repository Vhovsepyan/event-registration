# Decision 0010: Server-Sent Events for Live Statistics

- Status: Accepted
- Date: 2026-09-14

## Decision

Use Server-Sent Events for organizer statistics because updates flow only from server to browser. Each connection periodically reads one authoritative PostgreSQL snapshot and emits only changes.

## Consequences

The browser can use native `EventSource`, reconnect automatically, and avoid a WebSocket protocol. Polling adds a small bounded database read per connected organizer and works across multiple application processes without Redis because PostgreSQL remains the shared source of truth. Since task 0024 the route's existence pre-check also runs in a session closed before streaming starts, so a connected organizer holds a pooled connection only while a snapshot is being read.
