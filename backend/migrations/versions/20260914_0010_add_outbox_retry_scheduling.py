"""Add outbox retry scheduling, terminal failures, and single-line titles.

Revision ID: 20260914_0010
Revises: 20260914_0009
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0010"
down_revision: str | None = "20260914_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notification_status ADD VALUE IF NOT EXISTS 'FAILED'")
    op.add_column(
        "notification_outbox",
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Rows queued before this migration keep their original order.
    op.execute("UPDATE notification_outbox SET next_attempt_at = created_at")
    op.drop_index("ix_notification_outbox_pending", table_name="notification_outbox")
    op.create_index(
        "ix_notification_outbox_pending",
        "notification_outbox",
        ["status", "next_attempt_at"],
    )
    # Titles with embedded line breaks were accepted before; fold them so the constraint can be
    # added without losing events. Persisted email subjects are rendered safely by the mailer.
    op.execute(
        "UPDATE events SET title = regexp_replace(title, E'[\\r\\n]+', ' ', 'g') "
        "WHERE position(chr(10) in title) > 0 OR position(chr(13) in title) > 0"
    )
    op.create_check_constraint(
        "ck_events_title_single_line",
        "events",
        "position(chr(10) in title) = 0 AND position(chr(13) in title) = 0",
    )


def downgrade() -> None:
    connection = op.get_bind()
    failed = connection.scalar(
        sa.text("SELECT count(*) FROM notification_outbox WHERE status = 'FAILED'")
    )
    if failed:
        raise RuntimeError(
            f"{failed} failed notification rows exist; resolve them before downgrading"
        )
    op.drop_constraint("ck_events_title_single_line", "events", type_="check")
    op.drop_index("ix_notification_outbox_pending", table_name="notification_outbox")
    op.create_index(
        "ix_notification_outbox_pending",
        "notification_outbox",
        ["status", "created_at"],
    )
    op.drop_column("notification_outbox", "failed_at")
    op.drop_column("notification_outbox", "next_attempt_at")
    op.execute("ALTER TYPE notification_status RENAME TO notification_status_old")
    sa.Enum("PENDING", "PROCESSING", "SENT", "SUPPRESSED", name="notification_status").create(
        connection
    )
    op.execute(
        "ALTER TABLE notification_outbox ALTER COLUMN status TYPE notification_status "
        "USING status::text::notification_status"
    )
    op.execute("DROP TYPE notification_status_old")
