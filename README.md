# Event Registration

Repository foundation for the event registration project. The backend and frontend are separate applications and will communicate over HTTP and Server-Sent Events.

## Structure

- `backend/` — Python/FastAPI backend managed with `uv`
- `frontend/` — reserved for the frontend
- `docs/` — project documentation

## Backend

The backend requires Python 3.13.15. Task 0001 provides a FastAPI application shell and PostgreSQL persistence foundation without domain or business functionality.

```powershell
cd backend
uv sync
uv run python --version
uv run pytest
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; its infrastructure health endpoint is `GET /health`.

## Local infrastructure

Docker Compose currently runs PostgreSQL. Additional local services will be added by the tasks that require them.

```powershell
docker compose up -d
```

If port 5432 is already in use, set `POSTGRES_PORT` to another host port and set the backend `DATABASE_URL` accordingly.
