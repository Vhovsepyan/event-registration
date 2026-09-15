# Task 0028 — Event discovery by role

- Status: DONE (2026-09-15, task 0028 commit)
- Created: 2026-09-15T10:06:36+04:00
- Source: user product review on 2026-09-15 — "there is no event list for organizer and for participants; participants can't see the events to register"

## Problem

The implementation plan's minimum API (§15) defines only create and get-by-id for events, so the only way into an event is a link the organizer copies from the dashboard. A visitor opening the application cold sees the organizer's create form and has no way to find an event to register for; an organizer who closes the tab has no way back to a dashboard except the URL.

## Decision context

Authentication remains out of scope (decision 0003). "Roles" are therefore separate areas of the same unauthenticated application, not permissions: a participant area for discovering and joining events and an organizer area for creating and monitoring them.

## Scope

- `GET /api/events` returning upcoming events ordered by start time with authoritative confirmed/waitlisted counts and seats left; `include_past=true` returns every event for organizers.
- Participant home at `/`: upcoming events with time, seats left or waiting-list size, and a link to each event's registration page. Empty state when nothing is scheduled.
- Organizer area at `/organizer`: the existing create form plus a list of all events (including past) with counts and links to each live dashboard.
- Header navigation: Events, Organizer, Check in. Existing routes (`/events/:id`, `/events/:id/organizer`, `/tickets/:code`, `/check-in`) are unchanged.
- Backend tests for ordering, the upcoming filter, counts after registration/cancellation, and the empty case; component tests for both lists; the Playwright scenarios updated to start at `/organizer`.
- README routes, demo script, and the API summary updated; decision 0028 records the role separation.

## Acceptance criteria

1. `GET /api/events` lists upcoming events soonest first with `confirmed`, `waitlisted`, and `seats_left` derived from registration state; past events appear only with `include_past=true`.
2. A visitor at `/` can find an upcoming event and reach its registration page without any link from the organizer.
3. An organizer at `/organizer` can create an event and open any existing event's dashboard.
4. Counts on both lists match the organizer statistics endpoint for the same event.
5. Backend, frontend, and Playwright suites are green; documentation matches the new routes.

## Resolution

- `GET /api/events[?include_past=true]` (`EventRepository.list_with_counts`, one statement with scalar-subquery counts) returns `EventSummary` rows: the event plus `confirmed`, `waitlisted`, and `seats_left`, soonest first. Tests: empty list, ordering and counts before/after cancellation cross-checked against `/stats`, and the upcoming filter.
- Frontend: `/` is the participant home (`EventsPage`) listing upcoming events with seats left or waiting-list size and Register / Join waiting list links; `/organizer` keeps the create form and adds "Your events" (all events, counts, Open dashboard links). Header: Events, Organizer, Check in. Shared `EventList` component; three new component tests plus updated routing tests.
- Playwright scenarios start at `/organizer`; `PLAYWRIGHT_REUSE_SERVERS=1` lets the suite run against an API and Vite server that are already running.
- README routes/API/demo script updated; decision 0028 records role separation without authentication.

## Out of scope

- Authentication, per-organizer ownership, editing or deleting events, pagination (the lists are for a local product; ordering and filtering are in place for it).
- Invitation emails (a participant has no identity before registering; task 0029 covers post-registration mail).
