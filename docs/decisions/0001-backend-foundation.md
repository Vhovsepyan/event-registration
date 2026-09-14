# Decision 0001: Backend Foundation

- Status: Accepted
- Date: 2026-09-14

## Context

The product needs a separate backend with transactional concurrency behavior, PostgreSQL persistence, and a structure that can grow by feature without becoming a collection of global technical layers.

## Decision

- Use Python 3.13.15 and FastAPI for the HTTP backend because the project plan requires them and FastAPI provides a small, typed ASGI foundation.
- Use PostgreSQL as the source of truth because later capacity and check-in invariants require database transactions, row locks, and atomic updates.
- Use a modular monolith with feature-oriented Python packages so related routes, services, repositories, schemas, and models remain together while the application stays operationally simple.
- Keep backend and frontend independently runnable and communicate only over HTTP/SSE.

## Consequences

The backend begins as one deployable application. Database-dependent integration tests will target PostgreSQL rather than substituting SQLite. No distributed messaging or microservice infrastructure is introduced.
