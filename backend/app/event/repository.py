import uuid
from datetime import datetime

from sqlalchemy import Row, ScalarSelect, func, select
from sqlalchemy.orm import Session

from app.event.models import Event
from app.registration.models import Registration, RegistrationStatus


class EventRepository:
    def add(self, session: Session, event: Event) -> None:
        session.add(event)

    def get(self, session: Session, event_id: uuid.UUID) -> Event | None:
        return session.get(Event, event_id)

    def get_for_update(self, session: Session, event_id: uuid.UUID) -> Event | None:
        statement = select(Event).where(Event.id == event_id).with_for_update()
        return session.scalar(statement)

    def list_with_counts(
        self, session: Session, *, now: datetime, include_past: bool
    ) -> list[Row[tuple[Event, int, int]]]:
        """Events soonest first with authoritative confirmed/waitlisted counts in one statement."""

        def count_of(status: RegistrationStatus) -> ScalarSelect[int]:
            return (
                select(func.count())
                .select_from(Registration)
                .where(Registration.event_id == Event.id, Registration.status == status)
                .scalar_subquery()
            )

        statement = select(
            Event,
            count_of(RegistrationStatus.CONFIRMED).label("confirmed"),
            count_of(RegistrationStatus.WAITLISTED).label("waitlisted"),
        ).order_by(Event.starts_at, Event.id)
        if not include_past:
            statement = statement.where(Event.starts_at > now)
        return list(session.execute(statement).all())
