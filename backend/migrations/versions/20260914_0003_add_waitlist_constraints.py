"""Add waitlist constraints.

Revision ID: 20260914_0003
Revises: 20260914_0002
Create Date: 2026-09-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260914_0003"
down_revision: str | None = "20260914_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_registrations_event_waitlist_order",
        "registrations",
        ["event_id", "waitlist_order"],
    )
    op.create_check_constraint(
        "ck_registrations_status_shape",
        "registrations",
        "(status = 'WAITLISTED' AND waitlist_order IS NOT NULL AND confirmed_at IS NULL) "
        "OR (status = 'CONFIRMED' AND waitlist_order IS NULL AND confirmed_at IS NOT NULL) "
        "OR status = 'CANCELLED'",
    )
    op.create_index("ix_registrations_event_status", "registrations", ["event_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_registrations_event_status", table_name="registrations")
    op.drop_constraint("ck_registrations_status_shape", "registrations", type_="check")
    op.drop_constraint("uq_registrations_event_waitlist_order", "registrations", type_="unique")
