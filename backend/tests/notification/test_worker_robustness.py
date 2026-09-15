import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import Settings
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.worker import (
    NotificationWorker,
    PermanentDeliveryError,
    SmtpMailer,
    run_cycles,
)

pytestmark = pytest.mark.asyncio


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime.now(UTC) + timedelta(seconds=2)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class RecordingMailer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.messages.append((recipient, subject, body))


class ReplyingSmtp:
    """Fake smtplib.SMTP raising a configured reply for the next send."""

    error: Exception | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "ReplyingSmtp":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def send_message(self, message: EmailMessage) -> None:
        if ReplyingSmtp.error is not None:
            raise ReplyingSmtp.error


async def create_event(
    client: httpx.AsyncClient, *, capacity: int = 1, hours: float = 48
) -> dict[str, object]:
    response = await client.post(
        "/api/events",
        json={
            "title": "Robustness",
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


def worker_for(engine: Engine, mailer: Any, clock: ManualClock) -> NotificationWorker:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return NotificationWorker(factory, mailer, claim_timeout=60, clock=clock.now)


async def test_run_cycles_survives_a_failing_cycle_and_backs_off() -> None:
    outcomes: list[Any] = [OSError("connection reset by peer"), OSError("deadlock"), None, None]
    calls: list[int] = []
    sleeps: list[float] = []

    class FlakyWorker:
        def process_once(self, batch_size: int) -> int:
            calls.append(batch_size)
            outcome = outcomes.pop(0)
            if outcome is not None:
                raise outcome
            return 0

    run_cycles(
        FlakyWorker(),  # type: ignore[arg-type]
        batch_size=7,
        poll_interval=2.0,
        max_backoff=5.0,
        sleep=sleeps.append,
        keep_running=lambda: bool(outcomes),
    )

    assert calls == [7, 7, 7, 7]
    # Two failures back off (2s, then 4s), a healthy cycle resets to the poll interval.
    assert sleeps == [2.0, 4.0, 2.0, 2.0]


@pytest.mark.parametrize(
    ("error", "permanent"),
    [
        (smtplib.SMTPRecipientsRefused({"a@example.com": (451, b"greylisted, try later")}), False),
        (smtplib.SMTPRecipientsRefused({"a@example.com": (550, b"no such user")}), True),
        (smtplib.SMTPDataError(451, b"temporary local problem"), False),
        (smtplib.SMTPDataError(554, b"message rejected"), True),
        (smtplib.SMTPSenderRefused(450, b"try again", "events@example.local"), False),
        (smtplib.SMTPSenderRefused(553, b"sender not allowed", "events@example.local"), True),
    ],
)
async def test_smtp_replies_are_classified_by_code(error: Exception, permanent: bool) -> None:
    mailer = SmtpMailer(Settings())
    ReplyingSmtp.error = error
    with patch("app.notification.worker.smtplib.SMTP", ReplyingSmtp):
        if permanent:
            with pytest.raises(PermanentDeliveryError):
                mailer.send("a@example.com", "Subject", "Body")
        else:
            with pytest.raises(type(error)):
                mailer.send("a@example.com", "Subject", "Body")
    ReplyingSmtp.error = None


async def test_transient_smtp_reply_is_retried_not_failed(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event = await create_event(client)
    await register(client, event["id"], "greylisted@example.com")
    clock = ManualClock()
    worker = worker_for(database_engine, SmtpMailer(Settings()), clock)

    ReplyingSmtp.error = smtplib.SMTPRecipientsRefused({"greylisted@example.com": (451, b"later")})
    with patch("app.notification.worker.smtplib.SMTP", ReplyingSmtp):
        assert worker.process_once() == 0
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.PENDING
    assert row.attempts == 1
    assert "451" in str(row.last_error)

    ReplyingSmtp.error = None
    clock.advance(worker.backoff(1))
    with patch("app.notification.worker.smtplib.SMTP", ReplyingSmtp):
        assert worker.process_once() == 1
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.SENT


async def test_overdue_reminder_is_suppressed_at_dispatch(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event = await create_event(client, hours=23)
    await register(client, event["id"], "late@example.com")
    clock = ManualClock()
    mailer = RecordingMailer()
    worker = worker_for(database_engine, mailer, clock)
    # Generate the reminder while due, but simulate the worker being down until after start.
    with Session(database_engine) as session, session.begin():
        assert worker.reminder_service.generate_due(session, now=clock.now()) == 1
    clock.advance(timedelta(hours=24))

    worker.process_once()

    reminder = next(
        row for row in rows(database_engine) if row.type == NotificationType.EVENT_REMINDER
    )
    assert reminder.status == NotificationStatus.SUPPRESSED
    assert reminder.suppression_reason == "event already started before delivery"
    assert all(not subject.startswith("Reminder:") for _, subject, _ in mailer.messages)


async def test_cancellation_before_delivery_suppresses_confirmation_and_promotion(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event = await create_event(client, capacity=1)
    first = await register(client, event["id"], "first@example.com")
    second = await register(client, event["id"], "second@example.com")
    await register(client, event["id"], "third@example.com")
    # first cancels before its confirmation was sent; second is promoted and cancels before its
    # promotion was sent; third is promoted in turn.
    await client.post(f"/api/events/{event['id']}/registrations/{first['id']}/cancel")
    await client.post(f"/api/events/{event['id']}/registrations/{second['id']}/cancel")
    mailer = RecordingMailer()
    worker = worker_for(database_engine, mailer, ManualClock())

    assert worker.process_once() == 2

    by_recipient: dict[str, list[Notification]] = {}
    for row in rows(database_engine):
        by_recipient.setdefault(row.recipient, []).append(row)
    assert [(r.type, r.status) for r in by_recipient["first@example.com"]] == [
        (NotificationType.REGISTRATION_CONFIRMED, NotificationStatus.SUPPRESSED)
    ]
    assert [(r.type, r.status) for r in by_recipient["second@example.com"]] == [
        (NotificationType.WAITLIST_JOINED, NotificationStatus.SUPPRESSED),
        (NotificationType.WAITLIST_PROMOTED, NotificationStatus.SUPPRESSED),
    ]
    assert [(r.type, r.status) for r in by_recipient["third@example.com"]] == [
        (NotificationType.WAITLIST_JOINED, NotificationStatus.SENT),
        (NotificationType.WAITLIST_PROMOTED, NotificationStatus.SENT),
    ]
    assert all(
        r.suppression_reason == "registration cancelled"
        for r in rows(database_engine)
        if r.status == NotificationStatus.SUPPRESSED
    )
    assert [message[0] for message in mailer.messages] == ["third@example.com"] * 2


async def test_burst_of_reschedules_delivers_only_the_latest_notice(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    event = await create_event(client, capacity=1)
    await register(client, event["id"], "confirmed@example.com")
    await register(client, event["id"], "waitlisted@example.com")
    base = datetime.fromisoformat(str(event["starts_at"]))
    schedules = [base + timedelta(days=1), base, base + timedelta(days=2)]
    for starts_at in schedules:
        response = await client.patch(
            f"/api/events/{event['id']}", json={"starts_at": starts_at.isoformat()}
        )
        assert response.status_code == 200
    mailer = RecordingMailer()
    worker = worker_for(database_engine, mailer, ManualClock())

    worker.process_once()

    notices = [
        row for row in rows(database_engine) if row.type == NotificationType.EVENT_RESCHEDULED
    ]
    assert len(notices) == 6, "every actual change is still recorded"
    for recipient in ("confirmed@example.com", "waitlisted@example.com"):
        own = [row for row in notices if row.recipient == recipient]
        assert [row.status for row in own] == [
            NotificationStatus.SUPPRESSED,
            NotificationStatus.SUPPRESSED,
            NotificationStatus.SENT,
        ]
        assert [row.suppression_reason for row in own[:2]] == [
            "superseded by schedule revision 2",
            "superseded by schedule revision 3",
        ]
    delivered = [message for message in mailer.messages if message[1].startswith("New event time")]
    assert len(delivered) == 2
    assert all(schedules[-1].isoformat() in body for _, _, body in delivered)
