import uuid

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.errors import ResourceNotFoundError
from app.event.models import Event
from app.registration.models import Registration, RegistrationStatus
from app.ticket.models import Ticket


class EventStats(BaseModel):
    event_id: uuid.UUID
    capacity: int
    confirmed: int
    waitlisted: int
    checked_in: int


class OrganizerService:
    def get_stats(self, session: Session, event_id: uuid.UUID) -> EventStats:
        confirmed = (
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.CONFIRMED,
            )
            .scalar_subquery()
        )
        waitlisted = (
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.WAITLISTED,
            )
            .scalar_subquery()
        )
        checked_in = (
            select(func.count())
            .select_from(Ticket)
            .join(Registration, Registration.id == Ticket.registration_id)
            .where(
                Registration.event_id == event_id,
                Registration.status == RegistrationStatus.CONFIRMED,
                Ticket.checked_in_at.is_not(None),
                Ticket.invalidated_at.is_(None),
            )
            .scalar_subquery()
        )
        statement = select(
            Event.id,
            Event.capacity,
            confirmed.label("confirmed"),
            waitlisted.label("waitlisted"),
            checked_in.label("checked_in"),
        ).where(Event.id == event_id)
        row = session.execute(statement).one_or_none()
        if row is None:
            raise ResourceNotFoundError("Event", event_id)

        return EventStats(
            event_id=row.id,
            capacity=row.capacity,
            confirmed=row.confirmed,
            waitlisted=row.waitlisted,
            checked_in=row.checked_in,
        )
