"""Preserve historical waitlist order.

Revision ID: 20260914_0005
Revises: 20260914_0004
Create Date: 2026-09-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260914_0005"
down_revision: str | None = "20260914_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_registrations_status_shape", "registrations", type_="check")
    op.create_check_constraint(
        "ck_registrations_status_shape",
        "registrations",
        "(status = 'WAITLISTED' AND waitlist_order IS NOT NULL AND confirmed_at IS NULL) "
        "OR (status = 'CONFIRMED' AND confirmed_at IS NOT NULL) "
        "OR status = 'CANCELLED'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_registrations_status_shape", "registrations", type_="check")
    op.create_check_constraint(
        "ck_registrations_status_shape",
        "registrations",
        "(status = 'WAITLISTED' AND waitlist_order IS NOT NULL AND confirmed_at IS NULL) "
        "OR (status = 'CONFIRMED' AND waitlist_order IS NULL AND confirmed_at IS NOT NULL) "
        "OR status = 'CANCELLED'",
    )
