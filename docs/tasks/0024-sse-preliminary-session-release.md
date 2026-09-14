# Task 0024 — P2: Release the SSE route's preliminary database session before streaming

- Status: OPEN
- Priority: P2
- Created: 2026-09-14T18:31:44+04:00
- Source: [review](../reviews/2026-09-14-astra6-review.md), "Other observations, below P1"

## Problem and evidence

`GET /api/events/{event_id}/stats/stream` in `backend/app/organizer/routes.py` takes the request-scoped `get_db_session` yield dependency and runs a preliminary `get_stats` on it to return 404 for unknown events. FastAPI keeps yield dependencies open for the whole request, so that session and its pooled PostgreSQL connection stay checked out for the lifetime of the stream even though polling uses separate short-lived sessions. This contradicts task 0010's criterion that polling must not retain one session/transaction for the connection lifetime, and every connected organizer pins one pool connection.

## Acceptance criteria

1. The preliminary existence check runs in a session that is closed before the streaming response starts; no pooled connection is held for the lifetime of the stream between polls.
2. Unknown events still return HTTP 404 before any stream bytes are sent.
3. Polling still uses one short-lived session per snapshot from the same configured engine, including the overridden engine in tests.
4. Add a PostgreSQL test that proves the pool has no checked-out connection while a stream is open between polls, and a 404 test for the stream route.
5. Existing SSE, organizer, and browser proofs remain green.

## Out of scope

- Changing the polling design, interval, or payload.
