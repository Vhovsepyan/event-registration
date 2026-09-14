import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.registration.models import Registration


class RegistrationRepository:
    def get_by_email(
        self, session: Session, event_id: uuid.UUID, normalized_email: str
    ) -> Registration | None:
        statement = select(Registration).where(
            Registration.event_id == event_id,
            Registration.normalized_email == normalized_email,
        )
        return session.scalar(statement)

    def add(self, session: Session, registration: Registration) -> None:
        session.add(registration)

    def get(
        self, session: Session, event_id: uuid.UUID, registration_id: uuid.UUID
    ) -> Registration | None:
        statement = select(Registration).where(
            Registration.id == registration_id,
            Registration.event_id == event_id,
        )
        return session.scalar(statement)

    def count_confirmed(self, session: Session, event_id: uuid.UUID) -> int:
        statement = (
            select(func.count())
            .select_from(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == "CONFIRMED",
            )
        )
        return session.scalar(statement) or 0

    def next_waitlist_order(self, session: Session, event_id: uuid.UUID) -> int:
        statement = select(func.max(Registration.waitlist_order)).where(
            Registration.event_id == event_id
        )
        return (session.scalar(statement) or 0) + 1

    def first_waitlisted(self, session: Session, event_id: uuid.UUID) -> Registration | None:
        statement = (
            select(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status == "WAITLISTED",
            )
            .order_by(Registration.waitlist_order)
            .limit(1)
        )
        return session.scalar(statement)

    def list_active(self, session: Session, event_id: uuid.UUID) -> list[Registration]:
        statement = (
            select(Registration)
            .where(
                Registration.event_id == event_id,
                Registration.status.in_(["CONFIRMED", "WAITLISTED"]),
            )
            .order_by(Registration.created_at, Registration.id)
        )
        return list(session.scalars(statement))
