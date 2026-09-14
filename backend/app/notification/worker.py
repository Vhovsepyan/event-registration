import argparse
import smtplib
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.common.config import Settings, get_settings
from app.db import models as database_models
from app.db.session import SessionLocal
from app.event.models import Event
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.service import NotificationService, ReminderService
from app.registration.models import Registration, RegistrationStatus
from app.ticket.models import Ticket

_ = database_models


class PermanentDeliveryError(Exception):
    """The message can never be delivered as stored; retrying would not help."""


class Mailer(Protocol):
    def send(self, recipient: str, subject: str, body: str) -> None: ...


def single_line(value: str) -> str:
    """Render header text safely: fold any CR/LF into spaces instead of failing forever."""
    return " ".join(part for part in value.splitlines() if part.strip()) or value.strip()


class SmtpMailer:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.sender = settings.smtp_from

    def send(self, recipient: str, subject: str, body: str) -> None:
        try:
            message = EmailMessage()
            message["From"] = self.sender
            message["To"] = recipient
            message["Subject"] = single_line(subject)
            message.set_content(body)
        except (ValueError, TypeError) as exc:
            raise PermanentDeliveryError(f"message construction failed: {exc}") from exc
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.send_message(message)
        except (
            smtplib.SMTPRecipientsRefused,
            smtplib.SMTPSenderRefused,
            smtplib.SMTPDataError,
            smtplib.SMTPNotSupportedError,
        ) as exc:
            raise PermanentDeliveryError(f"SMTP rejected the message: {exc}") from exc


class NotificationWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        mailer: Mailer,
        *,
        claim_timeout: float,
        reminder_lead_hours: float = 24,
        max_attempts: int = 5,
        retry_base_seconds: float = 5.0,
        retry_max_seconds: float = 300.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.mailer = mailer
        self.claim_timeout = claim_timeout
        self.reminder_lead_hours = reminder_lead_hours
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds
        self.retry_max_seconds = retry_max_seconds
        self.clock = clock or (lambda: datetime.now(UTC))
        self.reminder_service = ReminderService()

    def process_once(self, batch_size: int = 20) -> int:
        with self.session_factory.begin() as session:
            self.reminder_service.generate_due(
                session, now=self.clock(), lead_hours=self.reminder_lead_hours
            )
        notifications = self._claim(batch_size)
        sent = 0
        for notification in notifications:
            try:
                self.mailer.send(
                    notification.recipient,
                    str(notification.payload.get("subject", "Event Registration")),
                    str(notification.payload.get("body", "")),
                )
            except PermanentDeliveryError as exc:
                self._mark_failed(notification.id, str(exc), permanent=True)
            except Exception as exc:
                self._mark_failed(notification.id, str(exc), permanent=False)
            else:
                self._mark_sent(notification.id)
                sent += 1
        return sent

    def backoff(self, attempts: int) -> timedelta:
        seconds = min(self.retry_base_seconds * 2 ** (attempts - 1), self.retry_max_seconds)
        return timedelta(seconds=seconds)

    def _claim(self, batch_size: int) -> list[Notification]:
        now = self.clock()
        stale_before = now - timedelta(seconds=self.claim_timeout)
        with self.session_factory.begin() as session:
            statement = (
                select(Notification)
                .where(
                    or_(
                        (Notification.status == NotificationStatus.PENDING)
                        & (Notification.next_attempt_at <= now),
                        (
                            (Notification.status == NotificationStatus.PROCESSING)
                            & (Notification.claimed_at < stale_before)
                        ),
                    )
                )
                # Deferred retries sort behind work that became due earlier, so a failing
                # batch cannot occupy every cycle ahead of newer healthy mail.
                .order_by(Notification.next_attempt_at, Notification.created_at, Notification.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
            claimed: list[Notification] = []
            for notification in session.scalars(statement):
                obsolete = self._obsolete_reason(session, notification)
                if obsolete is not None:
                    notification.status = NotificationStatus.SUPPRESSED
                    notification.suppressed_at = now
                    notification.suppression_reason = obsolete
                    notification.claimed_at = None
                    continue
                notification.status = NotificationStatus.PROCESSING
                notification.claimed_at = now
                notification.attempts += 1
                claimed.append(notification)
            return claimed

    def _obsolete_reason(self, session: Session, notification: Notification) -> str | None:
        """Re-check reminder intent against current state immediately before delivery.

        Business transactions suppress PENDING reminders when they cancel a registration or
        move an event, and reminder generation share-locks the Event row, so this is the last
        gate against intent that was generated or resurrected concurrently. A change that
        commits after this check, while SMTP is accepting the message, cannot be recalled.
        """
        if notification.type != NotificationType.EVENT_REMINDER:
            return None
        event = session.get(Event, notification.event_id)
        if event is None or event.schedule_revision != notification.schedule_revision:
            return "event schedule changed before delivery"
        registration = session.get(Registration, notification.registration_id)
        if registration is None or registration.status != RegistrationStatus.CONFIRMED:
            return "registration no longer confirmed before delivery"
        ticket = session.scalar(select(Ticket).where(Ticket.registration_id == registration.id))
        if ticket is None or ticket.invalidated_at is not None:
            return "ticket invalidated before delivery"
        return None

    def _mark_sent(self, notification_id: uuid.UUID) -> None:
        with self.session_factory.begin() as session:
            notification = session.get(Notification, notification_id)
            if notification is not None:
                notification.status = NotificationStatus.SENT
                notification.sent_at = self.clock()
                notification.claimed_at = None
                notification.last_error = None

    def _mark_failed(self, notification_id: uuid.UUID, error: str, *, permanent: bool) -> None:
        with self.session_factory.begin() as session:
            notification = session.get(Notification, notification_id)
            if notification is None:
                return
            notification.claimed_at = None
            notification.last_error = error[:2000]
            if permanent or notification.attempts >= self.max_attempts:
                notification.status = NotificationStatus.FAILED
                notification.failed_at = self.clock()
            else:
                notification.status = NotificationStatus.PENDING
                notification.next_attempt_at = self.clock() + self.backoff(notification.attempts)


def build_worker(settings: Settings) -> NotificationWorker:
    return NotificationWorker(
        SessionLocal,
        SmtpMailer(settings),
        claim_timeout=settings.notification_claim_timeout_seconds,
        reminder_lead_hours=settings.reminder_lead_hours,
        max_attempts=settings.notification_max_attempts,
        retry_base_seconds=settings.notification_retry_base_seconds,
        retry_max_seconds=settings.notification_retry_max_seconds,
    )


def run_forever() -> None:
    settings = get_settings()
    worker = build_worker(settings)
    while True:
        worker.process_once(settings.notification_batch_size)
        time.sleep(settings.notification_poll_interval_seconds)


def retry_failed(notification_id: uuid.UUID | None) -> int:
    with SessionLocal.begin() as session:
        return NotificationService().retry_failed(session, notification_id)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Notification outbox worker")
    commands = parser.add_subparsers(dest="command")
    retry = commands.add_parser(
        "retry-failed", help="return FAILED outbox rows to PENDING for one more delivery cycle"
    )
    retry.add_argument("--id", type=uuid.UUID, default=None, help="retry only this outbox row")
    arguments = parser.parse_args(argv)
    if arguments.command == "retry-failed":
        print(f"requeued {retry_failed(arguments.id)} failed notification(s)")
    else:
        run_forever()


if __name__ == "__main__":
    main()
