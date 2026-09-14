# Decision 0002: React Frontend

- Status: Accepted
- Date: 2026-09-14

## Context

The product needs an independently runnable browser application with multiple screens and live organizer updates. The implementation plan requires React, TypeScript, Vite, and React Router.

## Decision

Use React with TypeScript for typed component composition, Vite for the development/build toolchain, and React Router for client-side screen routing. Keep the frontend as a separate application that communicates with the backend only through HTTP and SSE.

## Consequences

Frontend concerns remain isolated from the Python package and can be developed, tested, built, and served independently. Native `EventSource` will be added when task 0010 introduces SSE behavior; no general-purpose state or UI framework is added at foundation stage.
