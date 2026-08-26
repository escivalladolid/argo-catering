"""add event_duration_hours to inquiries and bookings

Revision ID: catering_022
Revises: catering_021
Create Date: 2026-08-21 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_022"
down_revision: Union[str, None] = "catering_021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("catering_inquiries", sa.Column("event_duration_hours", sa.Numeric(4, 1), nullable=True))
    op.add_column("catering_bookings", sa.Column("event_duration_hours", sa.Numeric(4, 1), nullable=True))


def downgrade() -> None:
    op.drop_column("catering_bookings", "event_duration_hours")
    op.drop_column("catering_inquiries", "event_duration_hours")
