import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.event.models import Event
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.templates import (
    event_reminder_email,
    event_rescheduled_email,
    registration_confirmed_email,
    waitlist_promoted_email,
)
from app.registration.models import Registration, RegistrationStatus
from app.ticket.models import Ticket


class NotificationService:
    def enqueue(
        self,
        session: Session,
        *,
        notification_type: NotificationType,
        event_id: uuid.UUID,
        registration_id: uuid.UUID | None,
        recipient: str,
        payload: dict[str, object],
        dedupe_key: str,
        schedule_revision: int | None = None,
    ) -> None:
        statement = (
            insert(Notification)
            .values(
                id=uuid.uuid4(),
                type=notification_type,
                event_id=event_id,
                registration_id=registration_id,
                recipient=recipient,
                payload=payload,
                dedupe_key=dedupe_key,
                schedule_revision=schedule_revision,
                status=NotificationStatus.PENDING,
                attempts=0,
            )
            .on_conflict_do_nothing(index_elements=[Notification.dedupe_key])
        )
        session.execute(statement)

    def enqueue_registration_confirmed(
        self,
        session: Session,
        event: Event,
        registration: Registration,
        ticket: Ticket,
    ) -> None:
        content = registration_confirmed_email(event, ticket)
        self.enqueue(
            session,
            notification_type=NotificationType.REGISTRATION_CONFIRMED,
            event_id=event.id,
            registration_id=registration.id,
            recipient=registration.email,
            payload={
                "subject": content.subject,
                "body": content.body,
                "ticket_code": ticket.code,
            },
            dedupe_key=f"registration-confirmed:{registration.id}",
        )

    def enqueue_waitlist_promoted(
        self,
        session: Session,
        event: Event,
        registration: Registration,
        ticket: Ticket,
    ) -> None:
        content = waitlist_promoted_email(event, ticket)
        self.enqueue(
            session,
            notification_type=NotificationType.WAITLIST_PROMOTED,
            event_id=event.id,
            registration_id=registration.id,
            recipient=registration.email,
            payload={
                "subject": content.subject,
                "body": content.body,
                "ticket_code": ticket.code,
            },
            dedupe_key=f"waitlist-promoted:{registration.id}",
        )

    def enqueue_event_reminder(
        self,
        session: Session,
        event: Event,
        registration: Registration,
        ticket: Ticket,
    ) -> None:
        content = event_reminder_email(event, ticket)
        self.enqueue(
            session,
            notification_type=NotificationType.EVENT_REMINDER,
            event_id=event.id,
            registration_id=registration.id,
            recipient=registration.email,
            payload={
                "subject": content.subject,
                "body": content.body,
                "ticket_code": ticket.code,
                "starts_at": event.starts_at.isoformat(),
                "schedule_revision": event.schedule_revision,
            },
            dedupe_key=(
                f"event-reminder:{event.id}:{registration.id}:"
                f"{event.starts_at.isoformat()}:r{event.schedule_revision}"
            ),
            schedule_revision=event.schedule_revision,
        )

    def enqueue_event_rescheduled(
        self,
        session: Session,
        event: Event,
        registration: Registration,
        *,
        old_starts_at: datetime,
    ) -> None:
        old_value = old_starts_at.isoformat()
        new_value = event.starts_at.isoformat()
        content = event_rescheduled_email(event, old_value, new_value)
        # Every actual change is recorded, but only the latest unsent notice is delivered: an
        # older PENDING notice would describe a schedule that is already out of date, and
        # bounding delivery to one email per worker cycle keeps an unauthenticated PATCH loop
        # from amplifying into unbounded outbound mail (decision 0003).
        self.suppress_pending(
            session,
            notification_types=(NotificationType.EVENT_RESCHEDULED,),
            reason=f"superseded by schedule revision {event.schedule_revision}",
            event_id=event.id,
            registration_id=registration.id,
        )
        self.enqueue(
            session,
            notification_type=NotificationType.EVENT_RESCHEDULED,
            event_id=event.id,
            registration_id=registration.id,
            recipient=registration.email,
            payload={
                "subject": content.subject,
                "body": content.body,
                "old_starts_at": old_value,
                "new_starts_at": new_value,
                "schedule_revision": event.schedule_revision,
                "registration_status": registration.status.value,
            },
            dedupe_key=(
                f"event-rescheduled:{event.id}:{registration.id}:r{event.schedule_revision}"
            ),
            schedule_revision=event.schedule_revision,
        )

    def suppress_pending(
        self,
        session: Session,
        *,
        notification_types: tuple[NotificationType, ...],
        reason: str,
        event_id: uuid.UUID | None = None,
        registration_id: uuid.UUID | None = None,
    ) -> int:
        """Retire unsent rows whose intent no longer applies.

        Only PENDING rows are touched: a PROCESSING row is owned by a worker that already
        verified it and is handing it to SMTP, which cannot be recalled.
        """
        if event_id is None and registration_id is None:
            raise ValueError("suppression requires an event or registration scope")
        statement = (
            update(Notification)
            .where(
                Notification.type.in_(notification_types),
                Notification.status == NotificationStatus.PENDING,
            )
            .values(
                status=NotificationStatus.SUPPRESSED,
                suppressed_at=datetime.now(UTC),
                suppression_reason=reason,
                claimed_at=None,
            )
        )
        if event_id is not None:
            statement = statement.where(Notification.event_id == event_id)
        if registration_id is not None:
            statement = statement.where(Notification.registration_id == registration_id)
        return session.execute(statement).rowcount

    def suppress_pending_reminders(
        self,
        session: Session,
        *,
        reason: str,
        event_id: uuid.UUID | None = None,
        registration_id: uuid.UUID | None = None,
    ) -> int:
        return self.suppress_pending(
            session,
            notification_types=(NotificationType.EVENT_REMINDER,),
            reason=reason,
            event_id=event_id,
            registration_id=registration_id,
        )

    def suppress_pending_for_cancelled_registration(
        self, session: Session, registration_id: uuid.UUID
    ) -> int:
        """A cancelled participant must not receive a reminder, confirmation, or promotion
        that describes a seat and ticket they no longer hold."""
        return self.suppress_pending(
            session,
            notification_types=(
                NotificationType.EVENT_REMINDER,
                NotificationType.REGISTRATION_CONFIRMED,
                NotificationType.WAITLIST_PROMOTED,
            ),
            reason="registration cancelled",
            registration_id=registration_id,
        )

    def retry_failed(self, session: Session, notification_id: uuid.UUID | None = None) -> int:
        """Deliberately return FAILED rows to the queue for one more delivery cycle.

        Attempts and the last error are retained for audit; a row that fails again is marked
        FAILED immediately because it already reached the attempt limit.
        """
        statement = (
            update(Notification)
            .where(Notification.status == NotificationStatus.FAILED)
            .values(
                status=NotificationStatus.PENDING,
                next_attempt_at=datetime.now(UTC),
                failed_at=None,
                claimed_at=None,
                claim_token=None,
            )
        )
        if notification_id is not None:
            statement = statement.where(Notification.id == notification_id)
        return session.execute(statement).rowcount


class ReminderService:
    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    def generate_due(
        self, session: Session, *, now: datetime | None = None, lead_hours: float = 24
    ) -> int:
        current_time = now or datetime.now(UTC)
        due_before = current_time + timedelta(hours=lead_hours)
        # Share-lock the due Event rows first. Registration, cancellation, promotion, and
        # rescheduling all take the Event row FOR UPDATE, so this statement waits for any
        # in-flight seat or schedule change to commit and re-reads the row's new version,
        # and those operations wait for this generation to commit before they suppress.
        due_events = list(
            session.scalars(
                select(Event)
                .where(Event.starts_at > current_time, Event.starts_at <= due_before)
                .order_by(Event.id)
                .with_for_update(read=True)
            )
        )
        if not due_events:
            return 0
        statement = (
            select(Event, Registration, Ticket)
            .join(Registration, Registration.event_id == Event.id)
            .join(Ticket, Ticket.registration_id == Registration.id)
            .where(
                Event.id.in_([event.id for event in due_events]),
                Registration.status == RegistrationStatus.CONFIRMED,
                Ticket.invalidated_at.is_(None),
            )
        )
        due = list(session.execute(statement).tuples())
        for event, registration, ticket in due:
            self.notification_service.enqueue_event_reminder(session, event, registration, ticket)
        return len(due)
