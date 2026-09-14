"""Add reminder suppression state and notification schedule revision.

Revision ID: 20260914_0009
Revises: 20260914_0008
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0009"
down_revision: str | None = "20260914_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notification_status ADD VALUE IF NOT EXISTS 'SUPPRESSED'")
    op.add_column(
        "notification_outbox", sa.Column("schedule_revision", sa.Integer(), nullable=True)
    )
    op.add_column(
        "notification_outbox",
        sa.Column("suppressed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("notification_outbox", sa.Column("suppression_reason", sa.Text(), nullable=True))
    # Existing rows: use the revision recorded by task 0019 when present. Otherwise a reminder
    # whose payload time still matches the event's schedule belongs to the current revision, and
    # any other reminder describes an obsolete schedule (-1), which dispatch suppresses.
    op.execute(
        """
        UPDATE notification_outbox AS n
        SET schedule_revision = COALESCE(
            (n.payload->>'schedule_revision')::integer,
            CASE
                WHEN n.type = 'EVENT_REMINDER'
                    AND (n.payload->>'starts_at')::timestamptz = e.starts_at
                THEN e.schedule_revision
                WHEN n.type = 'EVENT_REMINDER' THEN -1
            END
        )
        FROM events AS e
        WHERE n.event_id = e.id AND n.schedule_revision IS NULL
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    suppressed = connection.scalar(
        sa.text("SELECT count(*) FROM notification_outbox WHERE status = 'SUPPRESSED'")
    )
    if suppressed:
        raise RuntimeError(
            f"{suppressed} suppressed notification rows exist; resolve them before downgrading"
        )
    op.drop_column("notification_outbox", "suppression_reason")
    op.drop_column("notification_outbox", "suppressed_at")
    op.drop_column("notification_outbox", "schedule_revision")
    op.execute("ALTER TYPE notification_status RENAME TO notification_status_old")
    sa.Enum("PENDING", "PROCESSING", "SENT", name="notification_status").create(connection)
    op.execute(
        "ALTER TABLE notification_outbox ALTER COLUMN status TYPE notification_status "
        "USING status::text::notification_status"
    )
    op.execute("DROP TYPE notification_status_old")
