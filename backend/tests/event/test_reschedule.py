from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.notification.models import Notification, NotificationType
from app.notification.service import ReminderService

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, starts_at: datetime) -> dict[str, object]:
    response = await client.post(
        "/api/events",
        json={
            "title": "Reschedule Test",
            "description": "",
            "starts_at": starts_at.isoformat(),
            "capacity": 1,
        },
    )
    return response.json()


async def register(client: httpx.AsyncClient, event_id: object, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    return response.json()


async def test_reschedule_notifies_all_active_participants_only(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(days=3))
    cancelled = await register(client, event["id"], "cancelled@example.com")
    await register(client, event["id"], "confirmed@example.com")
    await register(client, event["id"], "waitlisted@example.com")
    await client.post(f"/api/events/{event['id']}/registrations/{cancelled['id']}/cancel")
    new_starts_at = now + timedelta(days=4)

    response = await client.patch(
        f"/api/events/{event['id']}", json={"starts_at": new_starts_at.isoformat()}
    )

    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["starts_at"]) == new_starts_at
    with Session(database_engine) as session:
        notifications = list(
            session.scalars(
                select(Notification).where(Notification.type == NotificationType.EVENT_RESCHEDULED)
            )
        )
    assert {notification.recipient for notification in notifications} == {
        "confirmed@example.com",
        "waitlisted@example.com",
    }
    old_value = datetime.fromisoformat(str(event["starts_at"])).isoformat()
    new_value = datetime.fromisoformat(response.json()["starts_at"]).isoformat()
    assert all(old_value in notification.payload["body"] for notification in notifications)
    assert all(new_value in notification.payload["body"] for notification in notifications)

    await client.patch(f"/api/events/{event['id']}", json={"starts_at": new_starts_at.isoformat()})
    with Session(database_engine) as session:
        repeated_count = len(
            list(
                session.scalars(
                    select(Notification).where(
                        Notification.type == NotificationType.EVENT_RESCHEDULED
                    )
                )
            )
        )
    assert repeated_count == 2


async def test_reschedule_creates_new_reminder_schedule(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(hours=20))
    await register(client, event["id"], "reminder@example.com")
    reminder_service = ReminderService()
    with Session(database_engine) as session, session.begin():
        reminder_service.generate_due(session, now=now)

    new_starts_at = now + timedelta(hours=22)
    await client.patch(f"/api/events/{event['id']}", json={"starts_at": new_starts_at.isoformat()})
    with Session(database_engine) as session, session.begin():
        reminder_service.generate_due(session, now=now)

    with Session(database_engine) as session:
        reminders = list(
            session.scalars(
                select(Notification).where(Notification.type == NotificationType.EVENT_REMINDER)
            )
        )
    assert len(reminders) == 2
    assert len({reminder.dedupe_key for reminder in reminders}) == 2


async def test_reschedule_rejects_past_time(client: httpx.AsyncClient) -> None:
    event = await create_event(client, datetime.now(UTC) + timedelta(days=1))

    response = await client.patch(
        f"/api/events/{event['id']}",
        json={"starts_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )

    assert response.status_code == 422
