# Task 0031 — Containerised single-host deployment

- Status: DONE (2026-09-15, task 0031 commit; Google Cloud steps documented, not yet executed)
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

## Resolution

- `backend/Dockerfile` (python 3.13.15 slim + uv, locked non-dev sync, non-root, `uvicorn` with proxy headers) used by `migrate`, `api`, and `worker`; `frontend/Dockerfile` (node 22 build with `VITE_API_BASE_URL=""` for same-origin, nginx with SPA fallback and immutable asset caching).
- `docker-compose.deploy.yml` overlay: internal-only PostgreSQL and Mailpit (`MP_WEBROOT=/mail`), `migrate` gated on PostgreSQL health, `api`/`worker` gated on the migration's success, API health check on `/ready`, Caddy on 80/443 with `deploy/Caddyfile` (automatic HTTPS for a hostname, `/mail*` behind `basic_auth`, `/api/*` + health/docs proxied unbuffered for SSE, everything else to the frontend). `.env.deploy.example` lists every variable, including the `$$` escaping for the bcrypt hash.
- `docs/deploy/google-cloud-vm.md`: VM/firewall/IP creation, Docker install, configuration, start, demo, operations, limitations, and the executed local rehearsal.
- Local rehearsal under an isolated Compose project (`-p er-deploy`, port 8080): images built; all seven services healthy in order; through the proxy: `/ready`, SPA deep link, Mailpit 401/200, create 401/201 with the organizer key, registration + waitlist, keyed SSE snapshot, check-in success, both emails delivered with `PUBLIC_URL`-based self-service links, dashboard key prompt in a real browser; torn down with `down -v` leaving the development containers untouched.
- Acceptance criterion 5: the Google Cloud commands are standard `gcloud` steps but were not run against a real project in this task; the guide says so explicitly.

## Out of scope

- Cloud Run / Cloud SQL / managed email (documented in README as the production path), backups, monitoring, multi-host scaling.
