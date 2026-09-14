import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.event.models import Event


class EventRepository:
    def add(self, session: Session, event: Event) -> None:
        session.add(event)

    def get(self, session: Session, event_id: uuid.UUID) -> Event | None:
        return session.get(Event, event_id)

    def get_for_update(self, session: Session, event_id: uuid.UUID) -> Event | None:
        statement = select(Event).where(Event.id == event_id).with_for_update()
        return session.scalar(statement)
