from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.common.config import get_settings
from app.common.errors import ResourceNotFoundError
from app.event.routes import router as event_router
from app.registration.routes import router as registration_router


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name)

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found(_request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/health", tags=["infrastructure"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(event_router)
    app.include_router(registration_router)

    return app


app = create_app()
