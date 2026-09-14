import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.event.models import Event
from app.notification.models import Notification, NotificationStatus, NotificationType
from app.notification.templates import registration_confirmed_email, waitlist_promoted_email
from app.registration.models import Registration
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
