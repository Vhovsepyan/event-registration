# Task 0015 — Frontend integration and UX completion

## Objective

Replace the neutral React foundation with an accessible, responsive product UI that communicates with the FastAPI application over HTTP and native SSE.

## Scope

- Add an organizer event-creation screen.
- Add an event detail and participant-registration screen.
- Render confirmed and waitlisted outcomes clearly; show ticket details for confirmed registrations.
- Add a ticket lookup screen with event, code, and status.
- Add a manual staff check-in screen with success, already-used, and invalid outcomes.
- Add an organizer dashboard with capacity, confirmed, waitlisted, and checked-in values updated by `EventSource`.
- Add a small typed API client, useful loading/error states, responsive styling, and keyboard-visible focus states.
- Permit the local Vite origin through explicit backend CORS configuration.
- Add focused UI tests for registration, check-in, and organizer statistics.

## Out of scope

- Authentication, QR scanning, frontend state frameworks, UI component frameworks, and automated multi-browser proof.
- Changes to domain allocation, check-in, notification, or statistics semantics.

## Acceptance criteria

1. All five required user journeys are reachable through React Router.
2. The frontend uses `VITE_API_BASE_URL` for HTTP and SSE calls.
3. Registration outcomes distinguish confirmed and waitlisted states and confirmed users receive a ticket link/code.
4. Check-in outcomes distinguish all three API results.
5. Organizer statistics render an initial snapshot and accept live native-SSE updates without refresh.
6. The local frontend can call the backend cross-origin.
7. Focused frontend tests cover registration, check-in, and organizer statistic rendering.
8. Backend and frontend full suites, frontend build, migration check, Compose validation, and whitespace checks pass.

## Verification

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run alembic check`
- `uv run pytest`
- `npm run lint`
- `npm test -- --run`
- `npm run build`
- `docker compose --profile test config --quiet`
- `git diff --check`
