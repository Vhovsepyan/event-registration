import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.notification.models import Notification, NotificationStatus, NotificationType


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
