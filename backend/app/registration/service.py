import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.common.errors import ResourceNotFoundError
from app.event.repository import EventRepository
from app.registration.models import Registration, RegistrationStatus
from app.registration.repository import RegistrationRepository
from app.registration.schemas import RegistrationCreate


def normalize_email(email: str) -> str:
    return email.strip().casefold()


class RegistrationService:
    def __init__(self, repository: RegistrationRepository | None = None) -> None:
        self.repository = repository or RegistrationRepository()
        self.event_repository = EventRepository()

    def register(
        self, session: Session, event_id: uuid.UUID, data: RegistrationCreate
    ) -> Registration:
        email = str(data.email).strip()
        normalized_email = normalize_email(email)
        with session.begin():
            event = self.event_repository.get_for_update(session, event_id)
            if event is None:
                raise ResourceNotFoundError("Event", event_id)

            registration = self.repository.get_by_email(session, event_id, normalized_email)
            if registration is None:
                confirmed_count = self.repository.count_confirmed(session, event_id)
                has_capacity = confirmed_count < event.capacity
                registration = Registration(
                    event_id=event_id,
                    email=email,
                    normalized_email=normalized_email,
                    status=(
                        RegistrationStatus.CONFIRMED
                        if has_capacity
                        else RegistrationStatus.WAITLISTED
                    ),
                    confirmed_at=datetime.now(UTC) if has_capacity else None,
                    waitlist_order=(
                        None
                        if has_capacity
                        else self.repository.next_waitlist_order(session, event_id)
                    ),
                )
                self.repository.add(session, registration)
                session.flush()

        session.refresh(registration)
        return registration
