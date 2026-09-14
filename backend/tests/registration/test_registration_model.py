import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.event.models import Event
from app.registration.models import Registration, RegistrationStatus


def test_database_enforces_unique_event_email(database_engine: Engine) -> None:
    event = Event(
        title="Unique registration",
        description="",
        starts_at=datetime.now(UTC) + timedelta(days=2),
        capacity=2,
    )
    with Session(database_engine) as session:
        session.add(event)
        session.flush()
        for email in ("person@example.com", "PERSON@example.com"):
            session.add(
                Registration(
                    id=uuid.uuid4(),
                    event_id=event.id,
                    email=email,
                    normalized_email="person@example.com",
                    status=RegistrationStatus.CONFIRMED,
                    confirmed_at=datetime.now(UTC),
                )
            )
            if email == "person@example.com":
                session.flush()

        with pytest.raises(IntegrityError):
            session.commit()
