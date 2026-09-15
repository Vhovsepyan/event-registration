import argparse
import logging
import smtplib
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import Update, or_, select, update
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
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Claim:
    """A single outbox row owned by this worker for one delivery attempt."""

    notification_id: uuid.UUID
    token: uuid.UUID
    recipient: str
    subject: str
    body: str


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
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.starttls = settings.smtp_starttls

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
                if self.starttls:
                    smtp.starttls()
                if self.username:
                    smtp.login(self.username, self.password or "")
                smtp.send_message(message)
        except smtplib.SMTPRecipientsRefused as exc:
            codes = [code for code, _ in exc.recipients.values()]
            if codes and all(_is_permanent_reply(code) for code in codes):
                raise PermanentDeliveryError(f"SMTP rejected the recipient: {exc}") from exc
            raise  # 4xx: the server asked us to try again later
        except (smtplib.SMTPSenderRefused, smtplib.SMTPDataError) as exc:
            if _is_permanent_reply(exc.smtp_code):
                raise PermanentDeliveryError(f"SMTP rejected the message: {exc}") from exc
            raise
        except smtplib.SMTPNotSupportedError as exc:
            raise PermanentDeliveryError(f"SMTP rejected the message: {exc}") from exc


def _is_permanent_reply(code: int) -> bool:
    """RFC 5321: 5yz replies are permanent negative completion; 4yz are transient."""
    return 500 <= code <= 599


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
        sent = 0
        for _ in range(batch_size):
            # Each row is claimed immediately before its own send, so a lease only ever has to
            # cover one delivery and a slow batch cannot outlive the ownership of its tail.
            claim = self._claim_next()
            if claim is None:
                break
            try:
                self.mailer.send(claim.recipient, claim.subject, claim.body)
            except PermanentDeliveryError as exc:
                self._mark_failed(claim, str(exc), permanent=True)
            except Exception as exc:
                self._mark_failed(claim, str(exc), permanent=False)
            else:
                self._mark_sent(claim)
                sent += 1
        return sent

    def backoff(self, attempts: int) -> timedelta:
        seconds = min(self.retry_base_seconds * 2 ** (attempts - 1), self.retry_max_seconds)
        return timedelta(seconds=seconds)

    def _claim_next(self) -> Claim | None:
        now = self.clock()
        stale_before = now - timedelta(seconds=self.claim_timeout)
        with self.session_factory.begin() as session:
            while True:
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
                    .order_by(
                        Notification.next_attempt_at, Notification.created_at, Notification.id
                    )
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                notification = session.scalar(statement)
                if notification is None:
                    return None
                obsolete = self._obsolete_reason(session, notification)
                if obsolete is not None:
                    notification.status = NotificationStatus.SUPPRESSED
                    notification.suppressed_at = now
                    notification.suppression_reason = obsolete
                    notification.claimed_at = None
                    notification.claim_token = None
                    session.flush()
                    continue
                token = uuid.uuid4()
                notification.status = NotificationStatus.PROCESSING
                notification.claimed_at = now
                notification.claim_token = token
                notification.attempts += 1
                return Claim(
                    notification_id=notification.id,
                    token=token,
                    recipient=notification.recipient,
                    subject=str(notification.payload.get("subject", "Event Registration")),
                    body=str(notification.payload.get("body", "")),
                )

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
        if event.starts_at <= self.clock():
            return "event already started before delivery"
        registration = session.get(Registration, notification.registration_id)
        if registration is None or registration.status != RegistrationStatus.CONFIRMED:
            return "registration no longer confirmed before delivery"
        ticket = session.scalar(select(Ticket).where(Ticket.registration_id == registration.id))
        if ticket is None or ticket.invalidated_at is not None:
            return "ticket invalidated before delivery"
        return None

    def _owned(self, claim: Claim) -> Update:
        """Only the worker holding the current token may finish a PROCESSING row.

        If the lease expired and another worker reclaimed the row, that worker owns the
        outcome; a late completion or failure from the previous owner must not overwrite it.
        """
        return update(Notification).where(
            Notification.id == claim.notification_id,
            Notification.claim_token == claim.token,
            Notification.status == NotificationStatus.PROCESSING,
        )

    def _mark_sent(self, claim: Claim) -> bool:
        with self.session_factory.begin() as session:
            updated = session.execute(
                self._owned(claim).values(
                    status=NotificationStatus.SENT,
                    sent_at=self.clock(),
                    claimed_at=None,
                    claim_token=None,
                    last_error=None,
                )
            ).rowcount
        if updated == 0:
            logger.warning(
                "notification %s was sent but its claim had been taken over; "
                "the current owner records the outcome (at-least-once delivery boundary)",
                claim.notification_id,
            )
        return updated == 1

    def _mark_failed(self, claim: Claim, error: str, *, permanent: bool) -> bool:
        with self.session_factory.begin() as session:
            notification = session.scalar(
                select(Notification)
                .where(
                    Notification.id == claim.notification_id,
                    Notification.claim_token == claim.token,
                    Notification.status == NotificationStatus.PROCESSING,
                )
                .with_for_update()
            )
            if notification is None:
                logger.warning(
                    "notification %s failed but its claim had been taken over; leaving the "
                    "current owner's state untouched",
                    claim.notification_id,
                )
                return False
            notification.claimed_at = None
            notification.claim_token = None
            notification.last_error = error[:2000]
            if permanent or notification.attempts >= self.max_attempts:
                notification.status = NotificationStatus.FAILED
                notification.failed_at = self.clock()
            else:
                notification.status = NotificationStatus.PENDING
                notification.next_attempt_at = self.clock() + self.backoff(notification.attempts)
            return True


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


def run_cycles(
    worker: NotificationWorker,
    *,
    batch_size: int,
    poll_interval: float,
    max_backoff: float,
    sleep: Callable[[float], None] = time.sleep,
    keep_running: Callable[[], bool] = lambda: True,
) -> None:
    """Poll until told to stop, surviving any failure of a single cycle.

    A dropped database connection, a deadlock, or a DNS hiccup must not end the process
    while the API keeps queueing mail; the cycle is logged and retried with bounded backoff.
    """
    delay = poll_interval
    while keep_running():
        try:
            worker.process_once(batch_size)
        except Exception:
            logger.exception("notification cycle failed; retrying in %.1fs", delay)
            sleep(delay)
            delay = min(delay * 2, max_backoff)
            continue
        delay = poll_interval
        sleep(poll_interval)


def run_forever() -> None:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    run_cycles(
        build_worker(settings),
        batch_size=settings.notification_batch_size,
        poll_interval=settings.notification_poll_interval_seconds,
        max_backoff=settings.notification_retry_max_seconds,
    )


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
