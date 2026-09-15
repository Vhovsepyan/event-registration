# Task 0030 — Organizer key for staff routes and a readiness check

- Status: DONE (2026-09-15, task 0030 commit)
- Created: 2026-09-15T10:44:15+04:00
- Source: deployment review on 2026-09-15 (preparing a public demo deployment)

## Problem

Decision 0003 leaves the product without accounts, which is fine on localhost. Exposed on the internet, anyone could create events, reschedule them (sending real email to participants), read live statistics, and check tickets in. Separately, `/health` deliberately never touches the database, so a deployment has no endpoint that tells it the API can actually serve.

## Scope

- `ORGANIZER_KEY` setting (unset by default). When set, organizer and staff routes require it: `POST /api/events`, `PATCH /api/events/{id}`, `GET /api/events/{id}/stats`, `GET /api/events/{id}/stats/stream`, and `POST /api/check-ins`. The key is accepted in the `X-Organizer-Key` header, or as the `organizer_key` query parameter for the SSE stream because `EventSource` cannot send headers. Comparison is constant-time; a wrong or missing key returns 401 with a clear message.
- Participant routes stay open: event list and detail, registration, registration lookup, cancellation, ticket lookup.
- Frontend: organizer and check-in screens ask for the key once when the API answers 401, keep it in `localStorage`, send it on every organizer/staff request and on the stream URL, and offer a way to forget it.
- `GET /ready` executes `SELECT 1` through the configured engine and returns 200 `{"status": "ready"}` or 503 with the failure class; `/health` remains a process-liveness check.
- Decision 0003 revised; README documents the key and the readiness endpoint.

## Acceptance criteria

1. With no key configured, behaviour, tests, and the browser proofs are unchanged.
2. With a key configured, every protected route rejects a missing or wrong key with 401 and accepts the correct header (and the query parameter on the stream); participant routes need nothing.
3. The frontend organizer and check-in areas work end to end once the key has been entered, without re-prompting on every action, and the dashboard stream connects with it.
4. `/ready` returns 200 against a reachable database and 503 when the database is unavailable.
5. Backend, frontend, and Playwright suites are green.

## Resolution

- `Settings.organizer_key` (env `ORGANIZER_KEY`, unset by default). `app/common/auth.py::require_organizer_key` is a FastAPI dependency on `POST /api/events`, `PATCH /api/events/{id}`, `GET .../stats`, `GET .../stats/stream`, and `POST /api/check-ins`; it accepts `X-Organizer-Key` or the `organizer_key` query parameter, compares with `secrets.compare_digest`, and answers 401 with `WWW-Authenticate: X-Organizer-Key`.
- `GET /ready` runs `SELECT 1` through the session factory and returns 200 or 503 with the exception class; `/health` is unchanged.
- Frontend: `api.ts` stores the key in `localStorage`, sends the header on every request, appends the query parameter to the stream URL, and raises `UnauthorizedError` on 401; `useOrganizerKeyGate` plus `OrganizerKeyPrompt` gate the organizer area, the dashboard, and check-in, rerunning data loads after the key is saved and offering to forget a rejected key.
- Tests: with a key configured, all five protected routes reject missing/wrong keys and accept the header (query parameter for the stream) while six participant routes stay open; `/ready` 200 and 503 against an unreachable engine (backend 104). Prompt-on-401, retry with header, stream URL with key, and forget-rejected-key (frontend 23). Playwright unchanged with no key (2 passed), and a live instance started with `ORGANIZER_KEY` returned 401/201/200/401 for create-without-key/create-with-key/public-list/check-in-without-key with `/ready` reporting ready.

## Follow-up fix (2026-09-15T12:17:04+04:00)

The user entered a key containing Cyrillic characters; browsers cannot put non-Latin-1 text in a header, so `fetch` threw `Cannot convert value ... to ByteString`, and because the stored key was attached to every request the whole application broke without ever showing the prompt. Fix: `Settings.organizer_key` is validated at startup (printable ASCII, no spaces); the prompt rejects such keys with a clear message; `getOrganizerKey` discards a stored key that is not header-safe so requests proceed without it and the prompt reappears. Tests: four rejected configured keys plus an accepted one (backend); a stored Cyrillic key dropped before the request and rejected on entry (frontend).

## Out of scope

- Accounts, sessions, per-organizer ownership, rate limiting (edge concern, task 0031 notes), key rotation.
