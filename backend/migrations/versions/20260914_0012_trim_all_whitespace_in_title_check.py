"""Reject titles that are blank after trimming all whitespace.

Revision ID: 20260914_0012
Revises: 20260914_0011
Create Date: 2026-09-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260914_0012"
down_revision: str | None = "20260914_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALL_WHITESPACE_BLANK = "length(btrim(title, E' \t\r\n')) > 0"
SPACES_ONLY_BLANK = "length(trim(title)) > 0"


def upgrade() -> None:
    # Titles that were only tabs are already impossible through the API; there is nothing to
    # normalise, so the stricter constraint can be added directly.
    op.drop_constraint("ck_events_title_not_blank", "events", type_="check")
    op.create_check_constraint("ck_events_title_not_blank", "events", ALL_WHITESPACE_BLANK)


def downgrade() -> None:
    op.drop_constraint("ck_events_title_not_blank", "events", type_="check")
    op.create_check_constraint("ck_events_title_not_blank", "events", SPACES_ONLY_BLANK)
