import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.errors import ResourceNotFoundError
from app.event.models import Event
from app.event.repository import EventRepository
from app.event.schemas import EventCreate, EventReschedule
from app.notification.service import NotificationService
from app.registration.repository import RegistrationRepository


class EventService:
    def __init__(self, repository: EventRepository | None = None) -> None:
        self.repository = repository or EventRepository()
        self.registration_repository = RegistrationRepository()
        self.notification_service = NotificationService()

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

    def reschedule(self, session: Session, event_id: uuid.UUID, data: EventReschedule) -> Event:
        with session.begin():
            event = self.repository.get_for_update(session, event_id)
            if event is None:
                raise ResourceNotFoundError("Event", event_id)
            old_starts_at: datetime = event.starts_at
            if old_starts_at != data.starts_at:
                event.starts_at = data.starts_at
                event.schedule_revision += 1
                self.notification_service.suppress_pending_reminders(
                    session,
                    event_id=event_id,
                    reason=f"event rescheduled to revision {event.schedule_revision}",
                )
                participants = self.registration_repository.list_active(session, event_id)
                for registration in participants:
                    self.notification_service.enqueue_event_rescheduled(
                        session,
                        event,
                        registration,
                        old_starts_at=old_starts_at,
                    )
                session.flush()
        session.refresh(event)
        return event
