import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.event.models import Event
from app.event.schemas import EventReschedule
from app.event.service import EventService
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.service import NotificationService, ReminderService
from app.notification.worker import NotificationWorker
from app.registration.models import Registration, RegistrationStatus
from app.registration.repository import RegistrationRepository

pytestmark = pytest.mark.asyncio


class RecordingMailer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> None:
        self.messages.append((recipient, subject, body))


async def create_event(
    client: httpx.AsyncClient, starts_at: datetime, capacity: int = 1
) -> dict[str, object]:
    response = await client.post(
        "/api/events",
        json={
            "title": "Reminder Lifecycle",
            "description": "",
            "starts_at": starts_at.isoformat(),
            "capacity": capacity,
        },
    )
    assert response.status_code == 201
    return response.json()


async def register(client: httpx.AsyncClient, event_id: object, email: str) -> dict[str, object]:
    response = await client.post(f"/api/events/{event_id}/registrations", json={"email": email})
    assert response.status_code == 201
    return response.json()


def generate(engine: Engine, now: datetime) -> int:
    with Session(engine) as session, session.begin():
        return ReminderService().generate_due(session, now=now)


def reminders(engine: Engine) -> list[Notification]:
    with Session(engine) as session:
        return list(
            session.scalars(
                select(Notification)
                .where(Notification.type == NotificationType.EVENT_REMINDER)
                .order_by(Notification.created_at, Notification.id)
            )
        )


def worker_for(engine: Engine) -> tuple[NotificationWorker, RecordingMailer]:
    mailer = RecordingMailer()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return NotificationWorker(factory, mailer, claim_timeout=60), mailer


def delivered_reminders(mailer: RecordingMailer) -> list[tuple[str, str, str]]:
    # The worker also delivers pending confirmation/reschedule mail; only reminders matter here.
    return [message for message in mailer.messages if message[1].startswith("Reminder:")]


async def test_queued_reminder_is_suppressed_by_cancellation(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(hours=23))
    registration = await register(client, event["id"], "cancelled@example.com")
    assert generate(database_engine, now) == 1

    response = await client.post(
        f"/api/events/{event['id']}/registrations/{registration['id']}/cancel"
    )
    assert response.status_code == 200
    worker, mailer = worker_for(database_engine)
    worker.process_once()

    (reminder,) = reminders(database_engine)
    assert reminder.status == NotificationStatus.SUPPRESSED
    assert reminder.suppression_reason == "registration cancelled"
    assert reminder.suppressed_at is not None
    assert reminder.attempts == 0
    assert delivered_reminders(mailer) == []


async def test_postponed_event_gets_one_reminder_for_the_new_schedule(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    old_starts_at = now + timedelta(hours=23)
    event = await create_event(client, old_starts_at)
    await register(client, event["id"], "postponed@example.com")
    assert generate(database_engine, now) == 1

    new_starts_at = now + timedelta(days=7)
    response = await client.patch(
        f"/api/events/{event['id']}", json={"starts_at": new_starts_at.isoformat()}
    )
    assert response.status_code == 200
    worker, mailer = worker_for(database_engine)
    worker.process_once()
    assert delivered_reminders(mailer) == []
    (old_reminder,) = reminders(database_engine)
    assert old_reminder.status == NotificationStatus.SUPPRESSED
    assert old_reminder.suppression_reason == "event rescheduled to revision 1"

    later = new_starts_at - timedelta(hours=23)
    assert generate(database_engine, later) == 1
    assert generate(database_engine, later) == 1
    rows = reminders(database_engine)
    assert len(rows) == 2
    current = next(row for row in rows if row.status == NotificationStatus.PENDING)
    assert current.schedule_revision == 1
    assert worker.process_once() == 1
    reminder_messages = delivered_reminders(mailer)
    assert len(reminder_messages) == 1
    assert new_starts_at.isoformat() in reminder_messages[0][2]
    assert old_starts_at.isoformat() not in reminder_messages[0][2]


async def test_reregistration_after_cancellation_gets_its_own_reminder(
    client: httpx.AsyncClient, database_engine: Engine
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(hours=23))
    original = await register(client, event["id"], "again@example.com")
    assert generate(database_engine, now) == 1
    await client.post(f"/api/events/{event['id']}/registrations/{original['id']}/cancel")
    current = await register(client, event["id"], "again@example.com")
    assert current["id"] != original["id"]
    assert current["status"] == "CONFIRMED"

    assert generate(database_engine, now) == 1
    worker, mailer = worker_for(database_engine)
    worker.process_once()

    rows = {str(row.registration_id): row for row in reminders(database_engine)}
    assert rows[original["id"]].status == NotificationStatus.SUPPRESSED
    assert rows[current["id"]].status == NotificationStatus.SENT
    reminder_messages = delivered_reminders(mailer)
    assert len(reminder_messages) == 1
    assert current["ticket"]["code"] in reminder_messages[0][2]
    assert original["ticket"]["code"] not in reminder_messages[0][2]


@pytest.mark.parametrize(
    ("mutation", "expected_reason", "current_reminders"),
    [
        (
            update(Event).values(schedule_revision=Event.schedule_revision + 1),
            "event schedule changed before delivery",
            1,
        ),
        (
            update(Registration).values(status=RegistrationStatus.CANCELLED),
            "registration no longer confirmed before delivery",
            0,
        ),
    ],
)
async def test_dispatch_suppresses_resurrected_obsolete_reminders(
    client: httpx.AsyncClient,
    database_engine: Engine,
    mutation: object,
    expected_reason: str,
    current_reminders: int,
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(hours=23))
    await register(client, event["id"], "stale@example.com")
    assert generate(database_engine, now) == 1
    (stale,) = reminders(database_engine)
    # Change state directly, bypassing the business transactions that suppress PENDING
    # reminders, so the queued row no longer matches current state when the worker claims it.
    with Session(database_engine) as session, session.begin():
        session.execute(mutation)

    worker, mailer = worker_for(database_engine)
    worker.process_once()

    rows = {row.id: row for row in reminders(database_engine)}
    assert rows[stale.id].status == NotificationStatus.SUPPRESSED
    assert rows[stale.id].suppression_reason == expected_reason
    assert rows[stale.id].attempts == 0
    # A bumped revision with the event still due legitimately yields one reminder for the
    # current schedule; a cancelled registration yields none.
    assert len(delivered_reminders(mailer)) == current_reminders
    assert [row.status for row in rows.values() if row.id != stale.id] == [
        NotificationStatus.SENT
    ] * current_reminders


def wait_until_blocked(worker: threading.Thread, seconds: float = 0.5) -> None:
    worker.join(seconds)
    assert worker.is_alive(), "operation did not wait for the Event row lock"


async def test_generation_waiting_on_reschedule_sees_the_new_schedule(
    client: httpx.AsyncClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(hours=23))
    await register(client, event["id"], "overlap@example.com")
    event_id = uuid.UUID(str(event["id"]))
    lock_held = threading.Event()
    release = threading.Event()
    original_list_active = RegistrationRepository.list_active

    def hold_lock(self: RegistrationRepository, session: Session, key: uuid.UUID) -> list:
        lock_held.set()
        assert release.wait(10)
        return original_list_active(self, session, key)

    monkeypatch.setattr(RegistrationRepository, "list_active", hold_lock)
    generated: list[int] = []

    def reschedule() -> None:
        with Session(database_engine) as session:
            EventService().reschedule(
                session, event_id, EventReschedule(starts_at=now + timedelta(days=7))
            )

    def generate_reminders() -> None:
        generated.append(generate(database_engine, now))

    rescheduler = threading.Thread(target=reschedule)
    rescheduler.start()
    assert lock_held.wait(10)
    generator = threading.Thread(target=generate_reminders)
    generator.start()
    await asyncio.to_thread(wait_until_blocked, generator)
    release.set()
    await asyncio.to_thread(rescheduler.join, 10)
    await asyncio.to_thread(generator.join, 10)

    assert generated == [0]
    assert reminders(database_engine) == []


async def test_reschedule_waiting_on_generation_suppresses_its_output(
    client: httpx.AsyncClient, database_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    event = await create_event(client, now + timedelta(hours=23))
    await register(client, event["id"], "overlap@example.com")
    event_id = uuid.UUID(str(event["id"]))
    lock_held = threading.Event()
    release = threading.Event()
    original_enqueue = NotificationService.enqueue_event_reminder

    def hold_lock(self: NotificationService, *args: object, **kwargs: object) -> None:
        lock_held.set()
        assert release.wait(10)
        original_enqueue(self, *args, **kwargs)

    monkeypatch.setattr(NotificationService, "enqueue_event_reminder", hold_lock)
    generated: list[int] = []

    def generate_reminders() -> None:
        generated.append(generate(database_engine, now))

    def reschedule() -> None:
        with Session(database_engine) as session:
            EventService().reschedule(
                session, event_id, EventReschedule(starts_at=now + timedelta(days=7))
            )

    generator = threading.Thread(target=generate_reminders)
    generator.start()
    assert lock_held.wait(10)
    rescheduler = threading.Thread(target=reschedule)
    rescheduler.start()
    await asyncio.to_thread(wait_until_blocked, rescheduler)
    release.set()
    await asyncio.to_thread(generator.join, 10)
    await asyncio.to_thread(rescheduler.join, 10)

    assert generated == [1]
    (reminder,) = reminders(database_engine)
    assert reminder.schedule_revision == 0
    assert reminder.status == NotificationStatus.SUPPRESSED
    assert reminder.suppression_reason == "event rescheduled to revision 1"
    worker, mailer = worker_for(database_engine)
    worker.process_once()
    assert delivered_reminders(mailer) == []
