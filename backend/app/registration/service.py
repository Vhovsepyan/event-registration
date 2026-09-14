import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.common.errors import ResourceNotFoundError
from app.event.models import Event
from app.registration.models import Registration, RegistrationStatus
from app.registration.repository import RegistrationRepository
from app.registration.schemas import RegistrationCreate


def normalize_email(email: str) -> str:
    return email.strip().casefold()


class RegistrationService:
    def __init__(self, repository: RegistrationRepository | None = None) -> None:
        self.repository = repository or RegistrationRepository()

    def register(
        self, session: Session, event_id: uuid.UUID, data: RegistrationCreate
    ) -> Registration:
        if session.get(Event, event_id) is None:
            raise ResourceNotFoundError("Event", event_id)

        email = str(data.email).strip()
        normalized_email = normalize_email(email)
        existing = self.repository.get_by_email(session, event_id, normalized_email)
        if existing is not None:
            return existing

        registration = Registration(
            event_id=event_id,
            email=email,
            normalized_email=normalized_email,
            status=RegistrationStatus.CONFIRMED,
            confirmed_at=datetime.now(UTC),
        )
        self.repository.add(session, registration)
        session.commit()
        session.refresh(registration)
        return registration
