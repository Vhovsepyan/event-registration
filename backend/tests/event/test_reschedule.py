import uuid
from datetime import UTC, datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.event.schemas import EventReschedule
from app.event.service import EventService
from app.notification.models import Notification, NotificationType
from app.notification.service import NotificationService, ReminderService

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


async def load_reschedule_rows(database_engine: Engine) -> list[Notification]:
    with Session(database_engine) as session:
        return list(
            session.scalars(
                select(Notification)
                .where(Notification.type == NotificationType.EVENT_RESCHEDULED)
                .order_by(Notification.created_at, Notification.id)
            )
        )


async def test_every_actual_reschedule_notifies_active_participants(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    schedule_a = now + timedelta(days=3)
    schedule_b = now + timedelta(days=4)
    event = await create_event(client, schedule_a)
    cancelled = await register(client, event["id"], "cancelled@example.com")
    await register(client, event["id"], "confirmed@example.com")
    await register(client, event["id"], "waitlisted@example.com")
    await client.post(f"/api/events/{event['id']}/registrations/{cancelled['id']}/cancel")
    assert event["schedule_revision"] == 0

    for expected_revision, starts_at in enumerate((schedule_b, schedule_a, schedule_b), start=1):
        response = await client.patch(
            f"/api/events/{event['id']}", json={"starts_at": starts_at.isoformat()}
        )
        assert response.status_code == 200
        assert response.json()["schedule_revision"] == expected_revision
        assert datetime.fromisoformat(response.json()["starts_at"]) == starts_at

    rows = await load_reschedule_rows(database_engine)
    assert len(rows) == 6
    assert {row.recipient for row in rows} == {"confirmed@example.com", "waitlisted@example.com"}
    by_recipient: dict[str, list[Notification]] = {}
    for row in rows:
        by_recipient.setdefault(row.recipient, []).append(row)
    for recipient_rows in by_recipient.values():
        assert [row.payload["schedule_revision"] for row in recipient_rows] == [1, 2, 3]
        assert [
            datetime.fromisoformat(str(row.payload["new_starts_at"])) for row in recipient_rows
        ] == [schedule_b, schedule_a, schedule_b]
        assert [
            datetime.fromisoformat(str(row.payload["old_starts_at"])) for row in recipient_rows
        ] == [schedule_a, schedule_b, schedule_a]
    assert len({row.dedupe_key for row in rows}) == 6


async def test_equivalent_time_representation_is_a_no_op(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    starts_at = (datetime.now(UTC) + timedelta(days=3)).replace(microsecond=0)
    event = await create_event(client, starts_at)
    await register(client, event["id"], "confirmed@example.com")
    same_instant_elsewhere = starts_at.astimezone(timezone(timedelta(hours=4)))
    assert same_instant_elsewhere.isoformat() != starts_at.isoformat()

    for representation in (starts_at, same_instant_elsewhere):
        response = await client.patch(
            f"/api/events/{event['id']}", json={"starts_at": representation.isoformat()}
        )
        assert response.status_code == 200
        assert response.json()["schedule_revision"] == 0
        assert datetime.fromisoformat(response.json()["starts_at"]) == starts_at

    assert await load_reschedule_rows(database_engine) == []


async def test_reschedule_rolls_back_atomically_when_notification_fails(
    client: httpx.AsyncClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    starts_at = datetime.now(UTC) + timedelta(days=3)
    event = await create_event(client, starts_at)
    await register(client, event["id"], "confirmed@example.com")
    await register(client, event["id"], "waitlisted@example.com")

    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr(NotificationService, "enqueue_event_rescheduled", explode)
    with Session(database_engine) as session, pytest.raises(RuntimeError):
        EventService().reschedule(
            session,
            uuid.UUID(str(event["id"])),
            EventReschedule(starts_at=starts_at + timedelta(days=1)),
        )

    response = await client.get(f"/api/events/{event['id']}")
    assert datetime.fromisoformat(response.json()["starts_at"]) == starts_at
    assert response.json()["schedule_revision"] == 0
    assert await load_reschedule_rows(database_engine) == []


async def test_revisited_schedule_gets_a_new_reminder_identity(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    schedule_a = now + timedelta(hours=20)
    event = await create_event(client, schedule_a)
    await register(client, event["id"], "reminder@example.com")
    reminder_service = ReminderService()

    with Session(database_engine) as session, session.begin():
        assert reminder_service.generate_due(session, now=now) == 1
    for starts_at in (now + timedelta(days=7), schedule_a):
        await client.patch(f"/api/events/{event['id']}", json={"starts_at": starts_at.isoformat()})
    with Session(database_engine) as session, session.begin():
        assert reminder_service.generate_due(session, now=now) == 1

    with Session(database_engine) as session:
        reminders = list(
            session.scalars(
                select(Notification).where(Notification.type == NotificationType.EVENT_REMINDER)
            )
        )
    assert sorted(reminder.payload["schedule_revision"] for reminder in reminders) == [0, 2]
    assert len({reminder.dedupe_key for reminder in reminders}) == 2
