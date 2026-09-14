import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import get_settings
from app.db.session import get_db_session
from app.organizer.service import EventStats, OrganizerService

router = APIRouter(prefix="/api/events", tags=["organizer"])
service = OrganizerService()


@router.get("/{event_id}/stats", response_model=EventStats)
def get_event_stats(
    event_id: uuid.UUID, session: Annotated[Session, Depends(get_db_session)]
) -> EventStats:
    return service.get_stats(session, event_id)


@router.get("/{event_id}/stats/stream")
def stream_event_stats(
    request: Request,
    event_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> StreamingResponse:
    service.get_stats(session, event_id)
    stream_session_factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    events = service.stats_events(
        event_id=event_id,
        session_factory=stream_session_factory,
        is_disconnected=request.is_disconnected,
        poll_interval=get_settings().sse_poll_interval_seconds,
    )
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
