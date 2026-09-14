"""Create notification outbox.

Revision ID: 20260914_0006
Revises: 20260914_0005
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0006"
down_revision: str | None = "20260914_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

notification_type = postgresql.ENUM(
    "REGISTRATION_CONFIRMED",
    "WAITLIST_PROMOTED",
    "EVENT_REMINDER",
    "EVENT_RESCHEDULED",
    name="notification_type",
    create_type=False,
)
notification_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "SENT", name="notification_status", create_type=False
)


def upgrade() -> None:
    notification_type.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("registration_id", sa.Uuid(), nullable=True),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dedupe_key", sa.String(length=500), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_notification_outbox_dedupe_key"),
    )
    op.create_index(
        "ix_notification_outbox_pending",
        "notification_outbox",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_pending", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_type.drop(op.get_bind(), checkfirst=True)
