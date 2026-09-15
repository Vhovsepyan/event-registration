# Deploying the demo on a Google Cloud VM

One small VM runs the whole product with Docker Compose: PostgreSQL, the migration step, the API, the notification worker, the React frontend, Mailpit as the mail sink, and Caddy for HTTPS. Nothing else is required. The same overlay was verified end to end on a developer machine (see "Local rehearsal"); the Google Cloud steps below describe the standard path and are marked where they have not yet been executed against a real project.

## What you get

- `https://<your-domain>/` — participant home, organizer area, check-in.
- `https://<your-domain>/mail` — Mailpit inbox (basic auth) showing every email the demo sends.
- `https://<your-domain>/ready` — database-aware readiness; `/health` — liveness.
- Organizer and staff screens ask for `ORGANIZER_KEY` once per browser.

Cost: an `e2-micro` in a US region is inside Google Cloud's always-free tier; the 30 GB standard disk and a static IP add a few cents to a couple of dollars per month. Mail never leaves the VM.

## 1. Create the VM (Google Cloud steps — not yet executed by the author)

```bash
gcloud compute instances create event-registration \
  --zone=us-central1-a --machine-type=e2-micro \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=30GB --tags=http-server,https-server
gcloud compute firewall-rules create allow-web --allow=tcp:80,tcp:443 --target-tags=http-server,https-server
gcloud compute addresses create event-registration-ip --region=us-central1
```

Attach the static address to the instance and point your DNS `A` record at it. Caddy obtains the certificate automatically once the name resolves to the VM.

## 2. Install Docker and get the code

```bash
gcloud compute ssh event-registration --zone=us-central1-a
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER" && newgrp docker
git clone https://github.com/Vhovsepyan/event-registration.git && cd event-registration
```

An `e2-micro` has 1 GB of memory; building the frontend image there works but takes a few minutes. Building on your laptop and pushing to Artifact Registry is optional.

## 3. Configure

```bash
cp .env.deploy.example .env.deploy
docker run --rm caddy:2 caddy hash-password --plaintext 'choose-an-inbox-password'
nano .env.deploy   # set POSTGRES_PASSWORD, SITE_ADDRESS, PUBLIC_URL, ORGANIZER_KEY, MAILPIT_UI_PASSWORD_HASH
```

Write every `$` of the bcrypt hash as `$$`; Compose interpolates the env file.

## 4. Start

```bash
docker compose --env-file .env.deploy -f docker-compose.yml -f docker-compose.deploy.yml up -d --build
docker compose --env-file .env.deploy -f docker-compose.yml -f docker-compose.deploy.yml ps
curl -s https://<your-domain>/ready
```

Order is enforced by Compose: PostgreSQL becomes healthy, `migrate` runs `alembic upgrade head` and exits 0, then `api` and `worker` start, and Caddy waits for the API's readiness check. Re-running the same command after `git pull` rebuilds and rolls the services; migrations run again before the new API starts.

## 5. Demo

Follow `docs/demo/demo-script.md`, starting at `https://<your-domain>/organizer` (enter the organizer key once) and reading the emails at `https://<your-domain>/mail`.

## Operations

- Logs: `docker compose ... logs -f api worker caddy`
- Backup: `docker compose ... exec postgres pg_dump -U event_registration event_registration > backup.sql`
- Rotate the organizer key: change `ORGANIZER_KEY` in `.env.deploy`, `up -d` again; browsers are prompted for the new key.
- Stop: `docker compose ... down` (keeps the database volume); add `-v` to erase it.

## Limitations of this setup

- Single host, no redundancy or automatic backups.
- Mailpit is the only mail transport; set `SMTP_*` in the overlay to a real provider for real recipients.
- No rate limiting at the edge (the stock Caddy image has no rate-limit module); the organizer key and the worker's delivery bounds are the only abuse controls.
- Cloud Run + Cloud SQL + a managed email provider is the production-shaped alternative and is described in README's next steps.

## Local rehearsal (executed 2026-09-15)

The overlay was run on the developer machine under an isolated Compose project name with `SITE_ADDRESS=:80`, `CADDY_HTTP_PORT=8080`, and `PUBLIC_URL=http://localhost:8080`: both images built; PostgreSQL, migrate, api (healthy via `/ready`), worker, frontend, Mailpit, and Caddy came up in order; through the proxy `/ready` reported ready, `/` and the `/organizer` deep link served the SPA, `/mail` returned 401 without and 200 with basic auth, event creation returned 401 without and 201 with the organizer key, a registration and a waitlisted registration were created, the keyed SSE stream delivered a snapshot unbuffered, check-in succeeded, the worker delivered the confirmation and waiting-list emails to Mailpit, the emails' self-service links used the public URL, and the dashboard showed the organizer-key prompt in a real browser. The stack was then removed with `down -v` without touching the development containers.
