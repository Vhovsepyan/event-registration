from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.worker import NotificationWorker

pytestmark = pytest.mark.asyncio


class ManualClock:
    def __init__(self) -> None:
        self.current = datetime.now(UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, delta: timedelta) -> None:
        self.current += delta


class RecordingMailer:
    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        if self.failures:
            self.failures -= 1
            raise OSError("SMTP unavailable")
        self.messages.append((recipient, subject, body))


async def register_confirmed(client: httpx.AsyncClient) -> dict[str, object]:
    event_response = await client.post(
        "/api/events",
        json={
            "title": "Outbox Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": 1,
        },
    )
    registration_response = await client.post(
        f"/api/events/{event_response.json()['id']}/registrations",
        json={"email": "outbox@example.com"},
    )
    return registration_response.json()


async def test_confirmation_outbox_is_deduplicated(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    registration = await register_confirmed(client)
    await client.post(
        f"/api/events/{registration['event_id']}/registrations",
        json={"email": " OUTBOX@example.com "},
    )

    with Session(database_engine) as session:
        rows = list(session.scalars(select(Notification)))
    assert len(rows) == 1
    assert rows[0].type == NotificationType.REGISTRATION_CONFIRMED
    assert str(rows[0].registration_id) == registration["id"]
    assert rows[0].status == NotificationStatus.PENDING


async def test_worker_retries_failure_then_marks_sent(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await register_confirmed(client)
    factory = sessionmaker(bind=database_engine, expire_on_commit=False)
    mailer = RecordingMailer(failures=1)
    clock = ManualClock()
    worker = NotificationWorker(factory, mailer, claim_timeout=1, clock=clock.now)

    assert worker.process_once() == 0
    with Session(database_engine) as session:
        failed = session.scalar(select(Notification))
        assert failed is not None
        assert failed.status == NotificationStatus.PENDING
        assert failed.attempts == 1
        assert failed.last_error == "SMTP unavailable"
        assert failed.next_attempt_at == clock.now() + worker.backoff(1)

    # The retry is deferred by the backoff rather than spun immediately.
    assert worker.process_once() == 0
    clock.advance(worker.backoff(1))
    assert worker.process_once() == 1
    with Session(database_engine) as session:
        sent = session.scalar(select(Notification))
        assert sent is not None
        assert sent.status == NotificationStatus.SENT
        assert sent.attempts == 2
        assert sent.sent_at is not None
        assert sent.last_error is None
        count = session.scalar(select(func.count()).select_from(Notification))
    assert count == 1
    assert mailer.messages[0][0] == "outbox@example.com"
