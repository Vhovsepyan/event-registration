"""Add the WAITLIST_JOINED notification type.

Revision ID: 20260915_0013
Revises: 20260914_0012
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260915_0013"
down_revision: str | None = "20260914_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'WAITLIST_JOINED'")


def downgrade() -> None:
    connection = op.get_bind()
    rows = connection.scalar(
        sa.text("SELECT count(*) FROM notification_outbox WHERE type = 'WAITLIST_JOINED'")
    )
    if rows:
        raise RuntimeError(
            f"{rows} WAITLIST_JOINED notification rows exist; remove them before downgrading"
        )
    op.execute("ALTER TYPE notification_type RENAME TO notification_type_old")
    sa.Enum(
        "REGISTRATION_CONFIRMED",
        "WAITLIST_PROMOTED",
        "EVENT_REMINDER",
        "EVENT_RESCHEDULED",
        name="notification_type",
    ).create(connection)
    op.execute(
        "ALTER TABLE notification_outbox ALTER COLUMN type TYPE notification_type "
        "USING type::text::notification_type"
    )
    op.execute("DROP TYPE notification_type_old")
