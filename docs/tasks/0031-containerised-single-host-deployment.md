# Task 0031 — Containerised single-host deployment

- Status: OPEN
- Created: 2026-09-15T10:44:15+04:00
- Source: deployment review on 2026-09-15 (a clickable public demo on a small Google Cloud VM)

## Problem

Docker Compose currently provides only PostgreSQL and Mailpit; the API, worker, and frontend run from developer tooling. There is no container image, no HTTPS termination, and no documented way to run the whole product on one host.

## Scope

- Backend `Dockerfile` (uv, locked sync, `uvicorn` without reload) used by two Compose services, `api` and `worker`, plus a one-shot `migrate` service that runs `alembic upgrade head` before the API starts.
- Frontend `Dockerfile` (multi-stage: `npm ci` + `npm run build`, then a static server) with `VITE_API_BASE_URL` supplied at build time.
- A `docker-compose.deploy.yml` overlay adding `api`, `worker`, `migrate`, `frontend`, and `caddy` (automatic HTTPS, reverse proxy for `/api` and `/`, basic-auth in front of Mailpit's inbox, response streaming for SSE, a simple request rate limit for organizer routes if the Caddy build supports it).
- `.env.deploy.example` with every required variable: database password, `CORS_ORIGINS`, `FRONTEND_BASE_URL`, `ORGANIZER_KEY`, `MAILPIT_UI_*` credentials, domain.
- `docs/deploy/google-cloud-vm.md`: create an `e2-micro`, open 80/443, install Docker, clone, configure, `docker compose -f docker-compose.yml -f docker-compose.deploy.yml up -d`, verify `/ready`, run the demo script; cost and limitation notes (single host, Mailpit as the mail sink, no backups beyond a documented `pg_dump`).
- Local proof: the deploy overlay builds and starts on the developer machine with a self-signed/internal Caddy address; `/ready`, event creation with the organizer key, registration, worker delivery to Mailpit, and the SSE dashboard verified through the proxy.

## Acceptance criteria

1. `docker compose -f docker-compose.yml -f docker-compose.deploy.yml up -d --build` on a clean host brings up PostgreSQL, migrations, API, worker, frontend, Mailpit, and Caddy with no manual steps beyond the env file.
2. The frontend reaches the API through the same origin (no CORS surprises), SSE updates stream through the proxy, and emails are visible in the protected Mailpit inbox.
3. Organizer and staff routes require the configured key; `/ready` reflects database availability.
4. The local development workflow (`docker compose up -d` + uv + npm) is unchanged.
5. The deployment guide is verified step by step on Google Cloud (or the steps that need a real VM are marked as not yet run).

## Out of scope

- Cloud Run / Cloud SQL / managed email (documented in README as the production path), backups, monitoring, multi-host scaling.
