# Decision 0028: Role Separation Without Authentication

- Status: Accepted
- Date: 2026-09-15

## Context

The plan's minimum API had no event listing, so participants could only reach an event through a link the organizer copied from a dashboard, and an organizer had no way back to a dashboard except its URL. The user review asked for separate participant and organizer views.

## Decision

Keep the product unauthenticated (decision 0003) and separate the two roles by area rather than by permission:

- `/` — participant home: upcoming events, seats left or waiting-list size, direct registration links.
- `/organizer` — organizer area: create form and every event (including past) with counts and dashboard links.
- `GET /api/events` serves both, with `include_past=true` for organizers; counts come from the same registration state as the statistics endpoint.

## Consequences

A visitor can discover and join events without any organizer involvement, and an organizer can return to any dashboard. Nothing prevents a participant from opening the organizer area; that is the documented no-login scope, and the security design that would gate it remains a next step.
