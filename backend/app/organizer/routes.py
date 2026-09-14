import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.organizer.service import EventStats, OrganizerService

router = APIRouter(prefix="/api/events", tags=["organizer"])
service = OrganizerService()


@router.get("/{event_id}/stats", response_model=EventStats)
def get_event_stats(
    event_id: uuid.UUID, session: Annotated[Session, Depends(get_db_session)]
) -> EventStats:
    return service.get_stats(session, event_id)
