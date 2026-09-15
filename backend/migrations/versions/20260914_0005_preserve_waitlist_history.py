"""Preserve historical waitlist order.

Revision ID: 20260914_0005
Revises: 20260914_0004
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
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
    # Promoted registrations keep their historical waitlist_order (task 0007). The pre-0005
    # constraint forbids that, so fail before touching data rather than mid-way; normalising is
    # a deliberate, lossy operator step:
    #   UPDATE registrations SET waitlist_order = NULL WHERE status = 'CONFIRMED';
    promoted = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM registrations "
            "WHERE status = 'CONFIRMED' AND waitlist_order IS NOT NULL"
        )
    )
    if promoted:
        raise RuntimeError(
            f"{promoted} confirmed registrations keep a historical waitlist_order; clear it "
            "deliberately (UPDATE registrations SET waitlist_order = NULL WHERE status = "
            "'CONFIRMED') before downgrading 20260914_0005"
        )
    op.drop_constraint("ck_registrations_status_shape", "registrations", type_="check")
    op.create_check_constraint(
        "ck_registrations_status_shape",
        "registrations",
        "(status = 'WAITLISTED' AND waitlist_order IS NOT NULL AND confirmed_at IS NULL) "
        "OR (status = 'CONFIRMED' AND waitlist_order IS NULL AND confirmed_at IS NOT NULL) "
        "OR status = 'CANCELLED'",
    )
