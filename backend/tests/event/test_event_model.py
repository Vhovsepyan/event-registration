from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.event.models import Event


@pytest.mark.parametrize(
    ("title", "capacity"),
    [
        ("   ", 10),
        ("Valid title", 0),
    ],
)
def test_database_protects_event_invariants(
    database_engine: Engine, title: str, capacity: int
) -> None:
    event = Event(
        title=title,
        description="Constraint verification",
        starts_at=datetime.now(UTC) + timedelta(days=1),
        capacity=capacity,
    )

    with Session(database_engine) as session:
        session.add(event)
        with pytest.raises(IntegrityError):
            session.commit()
