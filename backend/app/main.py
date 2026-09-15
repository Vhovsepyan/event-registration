from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import get_settings
from app.common.errors import ResourceNotFoundError
from app.db.session import get_session_factory
from app.event.routes import router as event_router
from app.organizer.routes import router as organizer_router
from app.registration.routes import router as registration_router
from app.ticket.routes import check_in_router
from app.ticket.routes import router as ticket_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found(_request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/health", tags=["infrastructure"])
    def health() -> dict[str, str]:
        """Process liveness only; never touches the database."""
        return {"status": "ok"}

    @app.get("/ready", tags=["infrastructure"])
    def ready(
        session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
    ) -> JSONResponse:
        """Readiness: the API can reach PostgreSQL right now."""
        try:
            with session_factory() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 - any failure means not ready
            return JSONResponse(
                status_code=503, content={"status": "unavailable", "reason": type(exc).__name__}
            )
        return JSONResponse(content={"status": "ready"})

    app.include_router(event_router)
    app.include_router(organizer_router)
    app.include_router(registration_router)
    app.include_router(ticket_router)
    app.include_router(check_in_router)

    return app


app = create_app()
