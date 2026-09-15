import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.common.config import Settings
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.service import ReminderService
from app.notification.worker import SmtpMailer

pytestmark = pytest.mark.asyncio


async def create_event(client: httpx.AsyncClient, *, capacity: int, hours: float = 48) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Self Service",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(hours=hours)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def register(client: httpx.AsyncClient, event_id: str, email: str) -> dict[str, Any]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    assert response.status_code == 201
    return response.json()


def rows(engine: Engine, notification_type: NotificationType) -> list[Notification]:
    with Session(engine) as session:
        return list(
            session.scalars(
                select(Notification)
                .where(Notification.type == notification_type)
                .order_by(Notification.created_at)
            )
        )


def manage_url(event_id: str, registration_id: str) -> str:
    return f"http://localhost:5173/events/{event_id}/registrations/{registration_id}"


async def test_waitlisted_registration_gets_one_waitlist_email_with_its_position(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id = await create_event(client, capacity=1)
    await register(client, event_id, "seated@example.com")
    first = await register(client, event_id, "first-waiting@example.com")
    second = await register(client, event_id, "second-waiting@example.com")
    await register(client, event_id, " FIRST-WAITING@example.com ")  # idempotent repeat

    joined = rows(database_engine, NotificationType.WAITLIST_JOINED)
    assert [(str(row.registration_id), row.payload["waitlist_position"]) for row in joined] == [
        (first["id"], 1),
        (second["id"], 2),
    ]
    assert all(row.status == NotificationStatus.PENDING for row in joined)
    assert "Your place in line: 2" in str(joined[1].payload["body"])
    assert manage_url(event_id, second["id"]) in str(joined[1].payload["body"])
    assert (
        rows(database_engine, NotificationType.REGISTRATION_CONFIRMED)[0]
        .payload["body"]
        .count("registrations/")
        == 1
    )


async def test_cancelling_a_waitlisted_registration_suppresses_its_waitlist_email(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id = await create_event(client, capacity=1)
    await register(client, event_id, "seated@example.com")
    waiting = await register(client, event_id, "waiting@example.com")

    response = await client.post(f"/api/events/{event_id}/registrations/{waiting['id']}/cancel")

    assert response.status_code == 200
    (joined,) = rows(database_engine, NotificationType.WAITLIST_JOINED)
    assert joined.status == NotificationStatus.SUPPRESSED
    assert joined.suppression_reason == "registration cancelled"


async def test_every_participant_email_links_to_the_self_service_page(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event_id = await create_event(client, capacity=1, hours=23)
    seated = await register(client, event_id, "seated@example.com")
    waiting = await register(client, event_id, "waiting@example.com")
    with Session(database_engine) as session, session.begin():
        ReminderService().generate_due(session, now=datetime.now(UTC))
    await client.patch(
        f"/api/events/{event_id}",
        json={"starts_at": (datetime.now(UTC) + timedelta(hours=22)).isoformat()},
    )
    await client.post(f"/api/events/{event_id}/registrations/{seated['id']}/cancel")

    with Session(database_engine) as session:
        notifications = list(session.scalars(select(Notification)))
    assert {n.type for n in notifications} == {
        NotificationType.REGISTRATION_CONFIRMED,
        NotificationType.WAITLIST_JOINED,
        NotificationType.EVENT_REMINDER,
        NotificationType.EVENT_RESCHEDULED,
        NotificationType.WAITLIST_PROMOTED,
    }
    for notification in notifications:
        expected = manage_url(event_id, str(notification.registration_id))
        assert expected in str(notification.payload["body"]), notification.type
    promoted = next(n for n in notifications if n.type == NotificationType.WAITLIST_PROMOTED)
    assert str(promoted.registration_id) == waiting["id"]


async def test_registration_lookup_returns_current_state_or_404(
    client: httpx.AsyncClient,
) -> None:
    event_id = await create_event(client, capacity=1)
    registration = await register(client, event_id, "lookup@example.com")

    found = await client.get(f"/api/events/{event_id}/registrations/{registration['id']}")
    assert found.status_code == 200
    assert found.json() == registration

    await client.post(f"/api/events/{event_id}/registrations/{registration['id']}/cancel")
    cancelled = await client.get(f"/api/events/{event_id}/registrations/{registration['id']}")
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["ticket"]["invalidated_at"] is not None

    other_event = await create_event(client, capacity=1)
    wrong_event = await client.get(f"/api/events/{other_event}/registrations/{registration['id']}")
    assert wrong_event.status_code == 404
    unknown = await client.get(f"/api/events/{event_id}/registrations/{uuid.uuid4()}")
    assert unknown.status_code == 404


class RecordingSmtp:
    calls: list[tuple[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        RecordingSmtp.calls.append(("connect", args))

    def __enter__(self) -> "RecordingSmtp":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def starttls(self) -> None:
        RecordingSmtp.calls.append(("starttls", None))

    def login(self, username: str, password: str) -> None:
        RecordingSmtp.calls.append(("login", (username, password)))

    def send_message(self, message: EmailMessage) -> None:
        RecordingSmtp.calls.append(("send", message["To"]))


async def test_smtp_mailer_uses_starttls_and_login_only_when_configured() -> None:
    RecordingSmtp.calls = []
    with patch("app.notification.worker.smtplib.SMTP", RecordingSmtp):
        SmtpMailer(Settings()).send("plain@example.com", "Subject", "Body")
        SmtpMailer(
            Settings(smtp_starttls=True, smtp_username="mailer", smtp_password="secret")
        ).send("secure@example.com", "Subject", "Body")

    assert [call[0] for call in RecordingSmtp.calls] == [
        "connect",
        "send",
        "connect",
        "starttls",
        "login",
        "send",
    ]
    assert ("login", ("mailer", "secret")) in RecordingSmtp.calls
