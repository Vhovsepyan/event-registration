import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationType(StrEnum):
    REGISTRATION_CONFIRMED = "REGISTRATION_CONFIRMED"
    WAITLIST_PROMOTED = "WAITLIST_PROMOTED"
    EVENT_REMINDER = "EVENT_REMINDER"
    EVENT_RESCHEDULED = "EVENT_RESCHEDULED"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    SUPPRESSED = "SUPPRESSED"


class Notification(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
        Index("ix_notification_outbox_pending", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    registration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("registrations.id", ondelete="CASCADE"), nullable=True
    )
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        nullable=False,
        default=NotificationStatus.PENDING,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    schedule_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppressed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppression_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
