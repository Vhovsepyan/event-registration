from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.notification.models import Notification, NotificationStatus
from app.notification.worker import Claim, NotificationWorker

pytestmark = pytest.mark.asyncio

LEASE_SECONDS = 60


class SharedClock:
    def __init__(self) -> None:
        # Rows are created with a database-side next_attempt_at; start slightly ahead of wall
        # time so a simulated clock still sees them as due.
        self.current = datetime.now(UTC) + timedelta(seconds=2)

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class RecordingMailer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.messages.append((recipient, subject, body))


class SlowMailer(RecordingMailer):
    """Each send takes `seconds` of simulated time; a hook can run mid-batch."""

    def __init__(self, clock: SharedClock, seconds: float, on_send: Any = None) -> None:
        super().__init__()
        self.clock = clock
        self.seconds = seconds
        self.on_send = on_send

    def send(self, recipient: str, subject: str, body: str) -> None:
        super().send(recipient, subject, body)
        self.clock.advance(self.seconds)
        if self.on_send is not None:
            self.on_send(len(self.messages))


async def queue_confirmations(client: httpx.AsyncClient, count: int) -> str:
    response = await client.post(
        "/api/events",
        json={
            "title": "Ownership Test",
            "description": "",
            "starts_at": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "capacity": count,
        },
    )
    assert response.status_code == 201
    event_id = str(response.json()["id"])
    for index in range(count):
        registration = await client.post(
            f"/api/events/{event_id}/registrations", json={"email": f"owner{index}@example.com"}
        )
        assert registration.status_code == 201
    return event_id


def worker_for(engine: Engine, mailer: Any, clock: SharedClock) -> NotificationWorker:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return NotificationWorker(factory, mailer, claim_timeout=LEASE_SECONDS, clock=clock.now)


def rows(engine: Engine) -> list[Notification]:
    with Session(engine) as session:
        return list(session.scalars(select(Notification).order_by(Notification.created_at)))


async def test_slow_batch_crossing_the_lease_is_not_resent_by_a_second_worker(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await queue_confirmations(client, 20)
    clock = SharedClock()
    second_mailer = RecordingMailer()
    second_worker = worker_for(database_engine, second_mailer, clock)

    def interleave(sent_so_far: int) -> None:
        # 16 sends × 4 s = 64 s of simulated time: the first worker's original claim time is
        # now older than the lease, which used to let a second worker reclaim the tail.
        if sent_so_far == 16:
            second_worker.process_once()

    first_mailer = SlowMailer(clock, seconds=4, on_send=interleave)
    first_worker = worker_for(database_engine, first_mailer, clock)

    first_sent = first_worker.process_once()

    deliveries = Counter(message[0] for message in first_mailer.messages + second_mailer.messages)
    assert sum(deliveries.values()) == 20
    assert max(deliveries.values()) == 1
    assert first_sent + len(second_mailer.messages) == 20
    assert len(second_mailer.messages) > 0
    for row in rows(database_engine):
        assert row.status == NotificationStatus.SENT
        assert row.attempts == 1
        assert row.claim_token is None


async def test_stale_owner_cannot_overwrite_a_newer_claim(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await queue_confirmations(client, 1)
    clock = SharedClock()
    stale_worker = worker_for(database_engine, RecordingMailer(), clock)
    current_mailer = RecordingMailer()
    current_worker = worker_for(database_engine, current_mailer, clock)

    stale_claim = stale_worker._claim_next()
    assert stale_claim is not None
    clock.advance(LEASE_SECONDS + 1)
    assert current_worker.process_once() == 1
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.SENT
    assert row.attempts == 2
    sent_at = row.sent_at

    # A late completion or failure from the previous owner is refused, not applied.
    assert stale_worker._mark_sent(stale_claim) is False
    assert stale_worker._mark_failed(stale_claim, "late failure", permanent=False) is False
    assert stale_worker._mark_failed(stale_claim, "late failure", permanent=True) is False
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.SENT
    assert row.sent_at == sent_at
    assert row.attempts == 2
    assert row.last_error is None
    assert row.failed_at is None
    assert len(current_mailer.messages) == 1


async def test_stale_owner_cannot_reset_a_row_the_new_owner_is_processing(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await queue_confirmations(client, 1)
    clock = SharedClock()
    stale_worker = worker_for(database_engine, RecordingMailer(), clock)
    current_worker = worker_for(database_engine, RecordingMailer(), clock)

    stale_claim = stale_worker._claim_next()
    assert stale_claim is not None
    clock.advance(LEASE_SECONDS + 1)
    current_claim = current_worker._claim_next()
    assert current_claim is not None
    assert current_claim.token != stale_claim.token

    assert stale_worker._mark_failed(stale_claim, "late failure", permanent=False) is False
    assert stale_worker._mark_sent(stale_claim) is False
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.PROCESSING
    assert row.claim_token == current_claim.token
    assert row.attempts == 2

    assert current_worker._mark_sent(current_claim) is True
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.SENT
    assert row.claim_token is None


async def test_abandoned_claim_is_recovered_only_after_the_lease(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await queue_confirmations(client, 1)
    clock = SharedClock()
    crashed_worker = worker_for(database_engine, RecordingMailer(), clock)
    recovering_mailer = RecordingMailer()
    recovering_worker = worker_for(database_engine, recovering_mailer, clock)

    abandoned = crashed_worker._claim_next()
    assert abandoned is not None
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.PROCESSING
    assert row.claim_token == abandoned.token

    clock.advance(LEASE_SECONDS - 1)
    assert recovering_worker.process_once() == 0
    assert recovering_mailer.messages == []

    clock.advance(2)
    assert recovering_worker.process_once() == 1
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.SENT
    assert row.attempts == 2
    assert row.claim_token is None
    assert recovering_mailer.messages[0][0] == "owner0@example.com"


async def test_send_that_outlives_its_lease_records_the_honest_at_least_once_outcome(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await queue_confirmations(client, 1)
    clock = SharedClock()
    reclaiming_mailer = RecordingMailer()
    reclaiming_worker = worker_for(database_engine, reclaiming_mailer, clock)

    def reclaim_during_send(_: int) -> None:
        clock.advance(LEASE_SECONDS + 1)
        reclaiming_worker.process_once()

    slow_mailer = SlowMailer(clock, seconds=0, on_send=reclaim_during_send)
    slow_worker = worker_for(database_engine, slow_mailer, clock)

    # The first worker's SMTP call took longer than the lease; the reclaiming worker also sent.
    # This is the documented crash/timeout boundary: two deliveries, one consistent record.
    slow_worker.process_once()

    assert len(slow_mailer.messages) == 1
    assert len(reclaiming_mailer.messages) == 1
    (row,) = rows(database_engine)
    assert row.status == NotificationStatus.SENT
    assert row.attempts == 2
    assert row.claim_token is None


async def test_claim_is_a_snapshot_owned_for_one_attempt(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    await queue_confirmations(client, 2)
    clock = SharedClock()
    worker = worker_for(database_engine, RecordingMailer(), clock)

    first = worker._claim_next()
    second = worker._claim_next()
    assert isinstance(first, Claim) and isinstance(second, Claim)
    assert first.notification_id != second.notification_id
    assert first.token != second.token
    assert worker._claim_next() is None
    claimed = {row.id: row for row in rows(database_engine)}
    assert claimed[first.notification_id].claim_token == first.token
    assert claimed[second.notification_id].claim_token == second.token
    assert all(row.status == NotificationStatus.PROCESSING for row in claimed.values())
