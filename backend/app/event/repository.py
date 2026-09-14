import uuid

from sqlalchemy.orm import Session

from app.event.models import Event


class EventRepository:
    def add(self, session: Session, event: Event) -> None:
        session.add(event)

    def get(self, session: Session, event_id: uuid.UUID) -> Event | None:
        return session.get(Event, event_id)
