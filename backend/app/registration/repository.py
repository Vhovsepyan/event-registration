import uuid

from sqlalchemy import select
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
