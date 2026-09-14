# Task 0001: Repository and Python/FastAPI Foundation

## Objective

Establish a runnable, testable backend foundation using Python 3.13.15, `uv`, and FastAPI without implementing event-registration business behavior.

## Existing work to preserve

- The `backend/`, `frontend/`, and `docs/` directories exist.
- The backend is initialized as a bare `uv` project.
- `backend/.python-version` pins Python 3.13.15.
- `backend/pyproject.toml` and `backend/uv.lock` exist.
- The root `.gitignore` and `README.md` exist.
- The frontend remains intentionally uninitialized.

## Scope

- Configure the backend as an installable Python package.
- Add the backend dependencies selected by the implementation plan: FastAPI, Uvicorn, Pydantic settings, SQLAlchemy 2.x, psycopg, and Alembic.
- Add test dependencies: pytest, pytest-asyncio, and httpx.
- Create the feature-oriented package directories required by the architecture.
- Add application configuration and database session foundations without schema or business models.
- Add an Alembic environment ready for future migrations; do not create domain tables.
- Add a minimal FastAPI application and infrastructure health endpoint.
- Add PostgreSQL-only local Docker infrastructure. Mailpit remains deferred to task 0011.
- Add smoke tests for application startup and health behavior.
- Document task-relevant architecture decisions and local commands.

## Out of scope

- Event, registration, ticket, check-in, organizer, notification, or email behavior.
- Database domain models or migrations.
- Frontend initialization.
- Authentication.

## Acceptance criteria

1. `uv run python --version` reports Python 3.13.15.
2. `uv sync` succeeds from `backend/`.
3. `uv run fastapi`/Uvicorn can import `app.main:app`.
4. `GET /health` returns HTTP 200 with a small status payload.
5. Backend tests pass through `uv run pytest`.
6. Alembic configuration loads without requiring a live database connection.
7. Docker Compose configuration for PostgreSQL validates.
8. No business functionality or frontend project is introduced.

## Verification

Run from the repository root unless noted:

```powershell
cd backend
uv sync
uv run python --version
uv run pytest
uv run alembic current
uv run python -c "from app.main import app; print(app.title)"
cd ..
docker compose config --quiet
```
