import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
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
        )


class ReminderService:
    def __init__(self, notification_service: NotificationService | None = None) -> None:
        self.notification_service = notification_service or NotificationService()

    def generate_due(
        self, session: Session, *, now: datetime | None = None, lead_hours: float = 24
    ) -> int:
        current_time = now or datetime.now(UTC)
        due_before = current_time + timedelta(hours=lead_hours)
        statement = (
            select(Event, Registration, Ticket)
            .join(Registration, Registration.event_id == Event.id)
            .join(Ticket, Ticket.registration_id == Registration.id)
            .where(
                Event.starts_at > current_time,
                Event.starts_at <= due_before,
                Registration.status == RegistrationStatus.CONFIRMED,
                Ticket.invalidated_at.is_(None),
            )
        )
        due = list(session.execute(statement).tuples())
        for event, registration, ticket in due:
            self.notification_service.enqueue_event_reminder(session, event, registration, ticket)
        return len(due)
