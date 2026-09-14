import smtplib
import time
import uuid
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
from app.notification.service import ReminderService
from app.registration.models import Registration, RegistrationStatus
from app.ticket.models import Ticket

_ = database_models


class Mailer(Protocol):
    def send(self, recipient: str, subject: str, body: str) -> None: ...


class SmtpMailer:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.sender = settings.smtp_from

    def send(self, recipient: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            smtp.send_message(message)


class NotificationWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        mailer: Mailer,
        *,
        claim_timeout: float,
        reminder_lead_hours: float = 24,
    ) -> None:
        self.session_factory = session_factory
        self.mailer = mailer
        self.claim_timeout = claim_timeout
        self.reminder_lead_hours = reminder_lead_hours
        self.reminder_service = ReminderService()

    def process_once(self, batch_size: int = 20) -> int:
        with self.session_factory.begin() as session:
            self.reminder_service.generate_due(session, lead_hours=self.reminder_lead_hours)
        notifications = self._claim(batch_size)
        sent = 0
        for notification in notifications:
            try:
                self.mailer.send(
                    notification.recipient,
                    str(notification.payload.get("subject", "Event Registration")),
                    str(notification.payload.get("body", "")),
                )
            except Exception as exc:
                self._mark_failed(notification.id, str(exc))
            else:
                self._mark_sent(notification.id)
                sent += 1
        return sent

    def _claim(self, batch_size: int) -> list[Notification]:
        stale_before = datetime.now(UTC) - timedelta(seconds=self.claim_timeout)
        with self.session_factory.begin() as session:
            statement = (
                select(Notification)
                .where(
                    or_(
                        Notification.status == NotificationStatus.PENDING,
                        (
                            (Notification.status == NotificationStatus.PROCESSING)
                            & (Notification.claimed_at < stale_before)
                        ),
                    )
                )
                .order_by(Notification.created_at, Notification.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
            now = datetime.now(UTC)
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
                notification.sent_at = datetime.now(UTC)
                notification.claimed_at = None
                notification.last_error = None

    def _mark_failed(self, notification_id: uuid.UUID, error: str) -> None:
        with self.session_factory.begin() as session:
            notification = session.get(Notification, notification_id)
            if notification is not None:
                notification.status = NotificationStatus.PENDING
                notification.claimed_at = None
                notification.last_error = error[:2000]


def run_forever() -> None:
    settings = get_settings()
    worker = NotificationWorker(
        SessionLocal,
        SmtpMailer(settings),
        claim_timeout=settings.notification_claim_timeout_seconds,
        reminder_lead_hours=settings.reminder_lead_hours,
    )
    while True:
        worker.process_once(settings.notification_batch_size)
        time.sleep(settings.notification_poll_interval_seconds)


if __name__ == "__main__":
    run_forever()
