from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.notification.models import Notification, NotificationType
from app.notification.service import ReminderService

pytestmark = pytest.mark.asyncio


async def test_due_reminder_is_idempotent_and_excludes_waitlist(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    event_response = await client.post(
        "/api/events",
        json={
            "title": "Reminder Test",
            "description": "",
            "starts_at": (now + timedelta(hours=23)).isoformat(),
            "capacity": 1,
        },
    )
    event_id = event_response.json()["id"]
    confirmed_response = await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "confirmed@example.com"}
    )
    await client.post(
        f"/api/events/{event_id}/registrations", json={"email": "waitlisted@example.com"}
    )
    confirmed = confirmed_response.json()
    service = ReminderService()

    for _ in range(2):
        with Session(database_engine) as session, session.begin():
            assert service.generate_due(session, now=now) == 1

    with Session(database_engine) as session:
        reminders = list(
            session.scalars(
                select(Notification).where(Notification.type == NotificationType.EVENT_REMINDER)
            )
        )

    assert len(reminders) == 1
    reminder = reminders[0]
    starts_at = datetime.fromisoformat(event_response.json()["starts_at"]).isoformat()
    assert reminder.recipient == "confirmed@example.com"
    assert reminder.payload["ticket_code"] == confirmed["ticket"]["code"]
    assert starts_at in str(reminder.payload["body"])


async def test_event_outside_window_has_no_reminder(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    event_response = await client.post(
        "/api/events",
        json={
            "title": "Later Event",
            "description": "",
            "starts_at": (now + timedelta(hours=25)).isoformat(),
            "capacity": 1,
        },
    )
    await client.post(
        f"/api/events/{event_response.json()['id']}/registrations",
        json={"email": "later@example.com"},
    )

    with Session(database_engine) as session, session.begin():
        generated = ReminderService().generate_due(session, now=now)

    assert generated == 0
