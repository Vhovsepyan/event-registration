"""Create registrations table.

Revision ID: 20260914_0002
Revises: 20260914_0001
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0002"
down_revision: str | None = "20260914_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

registration_status = postgresql.ENUM(
    "CONFIRMED", "WAITLISTED", "CANCELLED", name="registration_status", create_type=False
)


def upgrade() -> None:
    registration_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=False),
        sa.Column("status", registration_status, nullable=False),
        sa.Column("waitlist_order", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "normalized_email", name="uq_registrations_event_email"),
    )


def downgrade() -> None:
    op.drop_table("registrations")
    registration_status.drop(op.get_bind(), checkfirst=True)
