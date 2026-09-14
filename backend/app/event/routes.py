import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.event.schemas import EventCreate, EventRead
from app.event.service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])
service = EventService()


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate, session: Annotated[Session, Depends(get_db_session)]
) -> EventRead:
    return EventRead.model_validate(service.create(session, data))


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: uuid.UUID, session: Annotated[Session, Depends(get_db_session)]
) -> EventRead:
    return EventRead.model_validate(service.get(session, event_id))
