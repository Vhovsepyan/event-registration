import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.auth import require_organizer_key
from app.db.session import get_db_session
from app.event.schemas import EventCreate, EventRead, EventReschedule, EventSummary
from app.event.service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])
service = EventService()


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_organizer_key)],
)
def create_event(
    data: EventCreate, session: Annotated[Session, Depends(get_db_session)]
) -> EventRead:
    return EventRead.model_validate(service.create(session, data))


@router.get("", response_model=list[EventSummary])
def list_events(
    session: Annotated[Session, Depends(get_db_session)], include_past: bool = False
) -> list[EventSummary]:
    return service.list(session, include_past=include_past)


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: uuid.UUID, session: Annotated[Session, Depends(get_db_session)]
) -> EventRead:
    return EventRead.model_validate(service.get(session, event_id))


@router.patch(
    "/{event_id}", response_model=EventRead, dependencies=[Depends(require_organizer_key)]
)
def reschedule_event(
    event_id: uuid.UUID,
    data: EventReschedule,
    session: Annotated[Session, Depends(get_db_session)],
) -> EventRead:
    return EventRead.model_validate(service.reschedule(session, event_id, data))
