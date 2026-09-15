import smtplib
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import Settings
from app.event.models import Event
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.service import NotificationService
from app.notification.worker import NotificationWorker, PermanentDeliveryError, SmtpMailer

pytestmark = pytest.mark.asyncio


class ManualClock:
    def __init__(self) -> None:
        # Rows the worker itself generates get a database-side next_attempt_at; start slightly
        # ahead of wall time so a frozen test clock still sees them as due.
        self.current = datetime.now(UTC) + timedelta(seconds=2)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class SelectiveMailer:
    """Fails for recipients with a given prefix until `recover()` is called."""

    def __init__(self, failing_prefix: str, error: Exception) -> None:
        self.failing_prefix = failing_prefix
        self.error: Exception | None = error
        self.messages: list[tuple[str, str, str]] = []

    def recover(self) -> None:
        self.error = None

    def send(self, recipient: str, subject: str, body: str) -> None:
        if self.error is not None and recipient.startswith(self.failing_prefix):
            raise self.error
        self.messages.append((recipient, subject, body))


class FakeSmtp:
    """Stands in for smtplib.SMTP; records built messages without any network."""

    sent: list[EmailMessage] = []
    refuse = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def send_message(self, message: EmailMessage) -> None:
        if FakeSmtp.refuse:
            raise smtplib.SMTPRecipientsRefused({message["To"]: (550, b"no such user")})
        FakeSmtp.sent.append(message)


async def create_event(
    client: httpx.AsyncClient, *, title: str, capacity: int, hours: float
) -> dict[str, object]:
    response = await client.post(
        "/api/events",
        json={
            "title": title,
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(hours=hours)).isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()


async def register(client: httpx.AsyncClient, event_id: object, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    assert response.status_code == 201
    return response.json()


def rows(engine: Engine) -> list[Notification]:
    with Session(engine) as session:
        return list(
            session.scalars(select(Notification).order_by(Notification.created_at, Notification.id))
        )


def worker_for(
    engine: Engine, mailer: Any, clock: ManualClock, **options: Any
) -> NotificationWorker:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return NotificationWorker(factory, mailer, claim_timeout=60, clock=clock.now, **options)


async def queue_healthy_intent(client: httpx.AsyncClient) -> str:
    """Create confirmation, promotion, reschedule, and (due) reminder intent for one event.

    `good-first` keeps its seat (its confirmation is healthy mail); `good-second` cancels so
    `good-third` is promoted. The cancelled participant's own confirmation is suppressed.
    """
    event = await create_event(client, title="Healthy", capacity=2, hours=23)
    await register(client, event["id"], "good-first@example.com")
    second = await register(client, event["id"], "good-second@example.com")
    await register(client, event["id"], "good-third@example.com")
    await client.post(f"/api/events/{event['id']}/registrations/{second['id']}/cancel")
    response = await client.patch(
        f"/api/events/{event['id']}",
        json={"starts_at": (datetime.now(UTC) + timedelta(hours=22)).isoformat()},
    )
    assert response.status_code == 200
    return str(event["id"])


async def test_permanent_failures_do_not_starve_healthy_mail(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    poison = await create_event(client, title="Poison", capacity=30, hours=72)
    for index in range(20):
        await register(client, poison["id"], f"poison{index}@example.com")
    healthy_event_id = await queue_healthy_intent(client)
    clock = ManualClock()
    mailer = SelectiveMailer("poison", PermanentDeliveryError("SMTP rejected the message"))
    worker = worker_for(database_engine, mailer, clock)

    first_cycle = worker.process_once()
    second_cycle = worker.process_once()
    third_cycle = worker.process_once()

    assert (first_cycle, second_cycle, third_cycle) == (0, 6, 0)
    healthy = [row for row in rows(database_engine) if str(row.event_id) == healthy_event_id]
    cancelled = [row for row in healthy if row.recipient == "good-second@example.com"]
    assert [row.status for row in cancelled] == [NotificationStatus.SUPPRESSED]
    delivered = [row for row in healthy if row.recipient != "good-second@example.com"]
    assert {row.type for row in delivered} == {
        NotificationType.REGISTRATION_CONFIRMED,
        NotificationType.WAITLIST_PROMOTED,
        NotificationType.EVENT_RESCHEDULED,
        NotificationType.EVENT_REMINDER,
    }
    assert len(delivered) == 6
    assert all(row.status == NotificationStatus.SENT and row.attempts == 1 for row in delivered)
    poisoned = [row for row in rows(database_engine) if str(row.event_id) == poison["id"]]
    assert len(poisoned) == 20
    for row in poisoned:
        assert row.status == NotificationStatus.FAILED
        assert row.attempts == 1
        assert row.failed_at is not None
        assert row.last_error == "SMTP rejected the message"
    assert len(mailer.messages) == 6


async def test_transient_failures_are_deferred_and_retried_without_starving(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    flaky = await create_event(client, title="Flaky", capacity=30, hours=72)
    for index in range(20):
        await register(client, flaky["id"], f"flaky{index}@example.com")
    healthy = await create_event(client, title="Healthy", capacity=1, hours=72)
    await register(client, healthy["id"], "good@example.com")
    clock = ManualClock()
    mailer = SelectiveMailer("flaky", OSError("SMTP unavailable"))
    worker = worker_for(database_engine, mailer, clock)

    assert worker.process_once() == 0
    deferred = [row for row in rows(database_engine) if str(row.event_id) == flaky["id"]]
    assert all(
        row.status == NotificationStatus.PENDING
        and row.attempts == 1
        and row.next_attempt_at == clock.now() + worker.backoff(1)
        for row in deferred
    )

    assert worker.process_once() == 1
    assert mailer.messages[0][0] == "good@example.com"
    others = [row for row in rows(database_engine) if row.recipient != "good@example.com"]
    assert all(row.attempts == 1 for row in others)

    mailer.recover()
    assert worker.process_once() == 0
    clock.advance(worker.backoff(1))
    assert worker.process_once() == 20
    recovered = [row for row in rows(database_engine) if str(row.event_id) == flaky["id"]]
    assert all(
        row.status == NotificationStatus.SENT and row.attempts == 2 and row.last_error is None
        for row in recovered
    )


async def test_exhausted_retries_fail_terminally_until_deliberately_retried(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event = await create_event(client, title="Exhausted", capacity=2, hours=72)
    await register(client, event["id"], "exhausted@example.com")
    await register(client, event["id"], "healthy@example.com")
    clock = ManualClock()
    mailer = SelectiveMailer("exhausted", OSError("SMTP unavailable"))
    worker = worker_for(database_engine, mailer, clock, max_attempts=2)

    assert worker.process_once() == 1
    clock.advance(worker.backoff(1))
    assert worker.process_once() == 0
    (failed,) = [row for row in rows(database_engine) if row.recipient == "exhausted@example.com"]
    assert failed.status == NotificationStatus.FAILED
    assert failed.attempts == 2
    assert failed.failed_at == clock.now()
    assert failed.last_error == "SMTP unavailable"

    clock.advance(timedelta(hours=1))
    assert worker.process_once() == 0
    (still_failed,) = [
        row for row in rows(database_engine) if row.recipient == "exhausted@example.com"
    ]
    assert still_failed.attempts == 2

    mailer.recover()
    with Session(database_engine) as session, session.begin():
        assert NotificationService().retry_failed(session, uuid.uuid4()) == 0
        assert NotificationService().retry_failed(session, failed.id) == 1
    assert worker.process_once() == 1
    (delivered,) = [
        row for row in rows(database_engine) if row.recipient == "exhausted@example.com"
    ]
    assert delivered.status == NotificationStatus.SENT
    assert delivered.attempts == 3
    assert delivered.failed_at is None


async def test_persisted_multiline_subject_is_rendered_safely_by_smtp_mailer(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event = await create_event(client, title="Legacy", capacity=1, hours=72)
    with Session(database_engine) as session, session.begin():
        session.add(
            Notification(
                type=NotificationType.REGISTRATION_CONFIRMED,
                event_id=uuid.UUID(str(event["id"])),
                registration_id=None,
                recipient="legacy@example.com",
                payload={"subject": "Accepted title\r\nwith newline", "body": "Body"},
                dedupe_key="legacy-multiline-subject",
            )
        )
    FakeSmtp.sent = []
    FakeSmtp.refuse = False
    worker = worker_for(database_engine, SmtpMailer(Settings()), ManualClock())

    with patch("app.notification.worker.smtplib.SMTP", FakeSmtp):
        assert worker.process_once() == 1

    legacy = next(row for row in rows(database_engine) if row.recipient == "legacy@example.com")
    assert legacy.status == NotificationStatus.SENT
    (message,) = FakeSmtp.sent
    assert message["Subject"] == "Accepted title with newline"


async def test_smtp_mailer_classifies_permanent_failures() -> None:
    mailer = SmtpMailer(Settings())
    FakeSmtp.sent = []
    FakeSmtp.refuse = True
    with (
        patch("app.notification.worker.smtplib.SMTP", FakeSmtp),
        pytest.raises(PermanentDeliveryError, match="SMTP rejected"),
    ):
        mailer.send("refused@example.com", "Subject", "Body")
    FakeSmtp.refuse = False

    with (
        patch("app.notification.worker.smtplib.SMTP", FakeSmtp),
        pytest.raises(PermanentDeliveryError, match="message construction failed"),
    ):
        mailer.send("bad\nrecipient@example.com", "Subject", "Body")
    assert FakeSmtp.sent == []

    with (
        patch("app.notification.worker.smtplib.SMTP", side_effect=OSError("connection refused")),
        pytest.raises(OSError, match="connection refused"),
    ):
        mailer.send("ok@example.com", "Subject", "Body")


@pytest.mark.parametrize("title", ["Accepted title\nwith newline", "Carriage\rreturn"])
async def test_titles_with_line_breaks_are_rejected(
    client: httpx.AsyncClient, database_engine: Engine, title: str
) -> None:
    response = await client.post(
        "/api/events",
        json={
            "title": title,
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "capacity": 1,
        },
    )
    assert response.status_code == 422

    with Session(database_engine) as session:
        session.add(
            Event(
                title=title,
                description="",
                starts_at=datetime.now(UTC) + timedelta(days=1),
                capacity=1,
            )
        )
        with pytest.raises(IntegrityError, match="ck_events_title_single_line"):
            session.commit()
