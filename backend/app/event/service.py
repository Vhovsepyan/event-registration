import uuid

from sqlalchemy.orm import Session

from app.common.errors import ResourceNotFoundError
from app.event.models import Event
from app.event.repository import EventRepository
from app.event.schemas import EventCreate


class EventService:
    def __init__(self, repository: EventRepository | None = None) -> None:
        self.repository = repository or EventRepository()

    def create(self, session: Session, data: EventCreate) -> Event:
        event = Event(**data.model_dump())
        self.repository.add(session, event)
        session.commit()
        session.refresh(event)
        return event

    def get(self, session: Session, event_id: uuid.UUID) -> Event:
        event = self.repository.get(session, event_id)
        if event is None:
            raise ResourceNotFoundError("Event", event_id)
        return event
