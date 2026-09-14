"""ChatGPT Astra 6 review: isolated PostgreSQL reproductions, not acceptance tests.

Run from backend: ./.venv/Scripts/python.exe ../docs/reviews/astra6-reproduce.py
Only a fresh random schema in event_registration_test is created and removed.
Assertions originally described the reviewed bugs. Tasks 0019-0022 corrected each case, so the
assertions now describe the fixed behavior; the pytest suites are the authoritative regression tests.
"""

import json
import sys
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db import models
from app.event.schemas import EventCreate, EventReschedule
from app.event.service import EventService
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.service import ReminderService
from app.notification.worker import NotificationWorker, SmtpMailer
from app.common.config import Settings
from app.registration.schemas import RegistrationCreate
from app.registration.service import RegistrationService


@contextmanager
def isolated_database():
    url = "postgresql+psycopg://event_registration:event_registration@localhost:5434/event_registration_test"
    admin = create_engine(url)
    schema = "astra6_review_" + uuid.uuid4().hex
    with admin.begin() as connection:
        assert connection.scalar(text("select current_database()")) == "event_registration_test"
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def create(factory, *, hours=72, title="Astra review", capacity=30):
    with factory() as session:
        return EventService().create(session, EventCreate(
            title=title, starts_at=datetime.now(UTC) + timedelta(hours=hours), capacity=capacity
        ))


def register(factory, event, email):
    with factory() as session:
        return RegistrationService().register(session, event.id, RegistrationCreate(email=email))


def reschedule(factory, event, starts_at):
    with factory() as session:
        return EventService().reschedule(session, event.id, EventReschedule(starts_at=starts_at))


class RecordingMailer:
    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append((recipient, subject, body))


def reschedule_revisit():
    with isolated_database() as factory:
        event = create(factory)
        register(factory, event, "confirmed@example.com")
        b = event.starts_at + timedelta(days=1)
        for starts_at in (b, event.starts_at, b):
            reschedule(factory, event, starts_at)
        with factory() as session:
            rows = list(session.scalars(select(Notification).where(
                Notification.type == NotificationType.EVENT_RESCHEDULED
            )))
        # Task 0019: every actual change now notifies the active participant.
        assert len(rows) == 3
        return {"actual_schedule_changes": 3, "expected_notifications": 3, "actual_notifications": len(rows)}


def stale_reminder(cancel=False):
    with isolated_database() as factory:
        event = create(factory, hours=23)
        registration = register(factory, event, "stale@example.com")
        with factory.begin() as session:
            ReminderService().generate_due(session)
        if cancel:
            with factory() as session:
                RegistrationService().cancel(session, event.id, registration.id)
        else:
            reschedule(factory, event, event.starts_at + timedelta(days=7))
        mailer = RecordingMailer()
        NotificationWorker(factory, mailer, claim_timeout=60).process_once()
        old_reminders = [message for message in mailer.messages if "Reminder:" in message[1]]
        # Task 0020: the obsolete reminder is suppressed instead of delivered.
        assert old_reminders == []
        return {"change": "cancelled" if cancel else "postponed_7_days", "stale_reminders_delivered": len(old_reminders)}


def poison_starvation():
    with isolated_database() as factory:
        # Task 0021: titles with line breaks are rejected at the API and database boundaries.
        try:
            EventCreate(
                title="Accepted title\nwith newline",
                starts_at=datetime.now(UTC) + timedelta(hours=72),
                capacity=30,
            )
        except ValidationError:
            title_rejected = True
        else:
            title_rejected = False
        event = create(factory, title="Poison")
        for index in range(20):
            register(factory, event, f"poison{index}@example.com")
        # Simulate already persisted rows that can never be rendered as a valid message.
        with factory.begin() as session:
            session.execute(
                update(Notification)
                .where(Notification.event_id == event.id)
                .values(recipient="poison\n" + Notification.recipient)
            )
        normal = create(factory)
        good = register(factory, normal, "good@example.com")
        # Real message construction rejects these recipients before any SMTP connection.
        # Any unexpected SMTP connection fails immediately without external delivery.
        worker = NotificationWorker(factory, SmtpMailer(Settings()), claim_timeout=60)
        with patch("app.notification.worker.smtplib.SMTP", side_effect=AssertionError("Unexpected SMTP attempt")):
            for _ in range(3):
                worker.process_once()
        with factory() as session:
            rows = list(session.scalars(select(Notification)))
        good_row = next(row for row in rows if row.registration_id == good.id)
        bad_rows = [row for row in rows if row.registration_id != good.id]
        # Task 0021: the healthy row is attempted on the second cycle and the permanently failing
        # rows are terminal after one attempt instead of occupying every cycle.
        assert title_rejected
        assert good_row.attempts == 1
        assert all(row.status == NotificationStatus.FAILED and row.attempts == 1 for row in bad_rows)
        return {"cycles": 3, "permanently_failing_old_rows": 20, "healthy_notification_attempts": good_row.attempts, "failed_rows": len(bad_rows), "error": bad_rows[0].last_error}


def slow_batch_duplicate():
    with isolated_database() as factory:
        event = create(factory, hours=23)
        for index in range(20):
            register(factory, event, f"slow{index}@example.com")
        with factory.begin() as session:
            session.execute(update(Notification).values(status=NotificationStatus.SENT))
        # Task 0022: the worker takes an injectable clock, so the simulated time is passed in
        # instead of patching the module. It starts slightly ahead of wall time because the
        # reminders generated inside the cycle get a database-side next_attempt_at.
        instant = datetime.now(UTC) + timedelta(seconds=2)

        class Clock:
            current = instant

            @classmethod
            def now(cls, tz=None):
                return cls.current

        second_mailer = RecordingMailer()
        second_worker = NotificationWorker(factory, second_mailer, claim_timeout=60, clock=Clock.now)

        class SlowMailer(RecordingMailer):
            def send(self, recipient, subject, body):
                super().send(recipient, subject, body)
                Clock.current += timedelta(seconds=4)
                if len(self.messages) == 16:
                    second_worker.process_once()

        first_mailer = SlowMailer()
        first_worker = NotificationWorker(factory, first_mailer, claim_timeout=60, clock=Clock.now)
        first_worker.process_once()
        counts = Counter(message[0] for message in first_mailer.messages + second_mailer.messages)
        duplicates = sum(count - 1 for count in counts.values())
        # Task 0022: each row is claimed immediately before its own send, so the second worker
        # takes only unclaimed rows and nothing is delivered twice.
        assert duplicates == 0
        assert sum(counts.values()) == 20
        return {"participants": 20, "reminder_deliveries": sum(counts.values()), "duplicates_without_crash": duplicates, "simulated_seconds_per_send": 4}


if __name__ == "__main__":
    for name, reproduce in (
        ("reschedule_revisit", reschedule_revisit),
        ("stale_reminder_after_reschedule", stale_reminder),
        ("stale_reminder_after_cancel", lambda: stale_reminder(cancel=True)),
        ("poison_starvation", poison_starvation),
        ("slow_batch_duplicate", slow_batch_duplicate),
    ):
        print(json.dumps({"case": name, **reproduce()}), flush=True)
