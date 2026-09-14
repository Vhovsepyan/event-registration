# Multi-client live-update verification

## Automated proof

Start PostgreSQL and migrate the development database before running Playwright:

```powershell
docker compose up -d postgres
cd backend
uv run alembic upgrade head
cd ../frontend
npm run test:e2e
```

Those commands use the standard PostgreSQL port 5432. If that port is occupied, start Compose with `$env:POSTGRES_PORT = "5433"` and set `$env:DATABASE_URL = "postgresql+psycopg://event_registration:event_registration@localhost:5433/event_registration"` in the shell that runs both Alembic and Playwright.

Playwright starts the API and Vite servers, creates a unique event, and opens two isolated browser contexts. Browser A stays on the organizer dashboard. Browser B registers, receives a real ticket, and checks it in. The assertion passes only when browser A's checked-in value changes from 0 to 1 through SSE without a reload.

The default browser channel is installed Microsoft Edge. Set `PLAYWRIGHT_CHANNEL=chrome` to use installed Google Chrome instead.

## Manual equivalent

1. Start PostgreSQL, migrate, and run the backend and frontend.
2. Create an event and leave its organizer dashboard open in browser A.
3. Open the dashboard's participant link in browser B and register.
4. Copy the issued ticket code, open **Check in** in browser B, and submit it.
5. Confirm browser B shows **Check-in successful**.
6. Without refreshing browser A, confirm its **Checked in** statistic changes from 0 to 1 and its connection indicator reads **Live**.

Use a private window or separate browser profile for browser B when reproducing isolated clients manually.
