import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.common.auth import require_organizer_key
from app.common.config import get_settings
from app.db.session import get_db_session, get_session_factory
from app.organizer.service import EventStats, OrganizerService

router = APIRouter(prefix="/api/events", tags=["organizer"])
service = OrganizerService()


@router.get(
    "/{event_id}/stats", response_model=EventStats, dependencies=[Depends(require_organizer_key)]
)
def get_event_stats(
    event_id: uuid.UUID, session: Annotated[Session, Depends(get_db_session)]
) -> EventStats:
    return service.get_stats(session, event_id)


@router.get("/{event_id}/stats/stream", dependencies=[Depends(require_organizer_key)])
def stream_event_stats(
    request: Request,
    event_id: uuid.UUID,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> StreamingResponse:
    # Verify the event in a session that is closed before the response starts, so no pooled
    # connection is held for the stream lifetime; every poll opens its own short-lived session.
    with session_factory() as session:
        service.get_stats(session, event_id)
    events = service.stats_events(
        event_id=event_id,
        session_factory=session_factory,
        is_disconnected=request.is_disconnected,
        poll_interval=get_settings().sse_poll_interval_seconds,
    )
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
