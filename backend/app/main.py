from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.config import get_settings
from app.common.errors import ResourceNotFoundError
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
        return {"status": "ok"}

    app.include_router(event_router)
    app.include_router(organizer_router)
    app.include_router(registration_router)
    app.include_router(ticket_router)
    app.include_router(check_in_router)

    return app


app = create_app()
