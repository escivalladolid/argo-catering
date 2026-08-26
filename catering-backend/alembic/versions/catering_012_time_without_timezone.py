"""store event_time as plain wall-clock time (drop timezone)

Revision ID: catering_012
Revises: catering_011
Create Date: 2026-08-13 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_012"
down_revision: Union[str, None] = "catering_011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL converts TIMETZ -> TIME using the session TimeZone, preserving
    # the wall-clock value the user entered.
    op.alter_column(
        "catering_inquiries",
        "event_time",
        existing_type=sa.Time(timezone=True),
        type_=sa.Time(timezone=False),
        existing_nullable=True,
    )
    op.alter_column(
        "catering_bookings",
        "event_time",
        existing_type=sa.Time(timezone=True),
        type_=sa.Time(timezone=False),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "catering_bookings",
        "event_time",
        existing_type=sa.Time(timezone=False),
        type_=sa.Time(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "catering_inquiries",
        "event_time",
        existing_type=sa.Time(timezone=False),
        type_=sa.Time(timezone=True),
        existing_nullable=True,
    )
