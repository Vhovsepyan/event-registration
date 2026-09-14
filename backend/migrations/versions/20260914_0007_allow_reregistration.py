"""Allow registration after a prior cancellation.

Revision ID: 20260914_0007
Revises: 20260914_0006
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0007"
down_revision: str | None = "20260914_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_registrations_event_email", "registrations", type_="unique")
    op.create_index(
        "uq_registrations_active_event_email",
        "registrations",
        ["event_id", "normalized_email"],
        unique=True,
        postgresql_where=sa.text("status IN ('CONFIRMED', 'WAITLISTED')"),
    )


def downgrade() -> None:
    op.drop_index("uq_registrations_active_event_email", table_name="registrations")
    op.create_unique_constraint(
        "uq_registrations_event_email",
        "registrations",
        ["event_id", "normalized_email"],
    )
