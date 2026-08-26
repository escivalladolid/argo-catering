"""add inquiry review status columns

Revision ID: catering_016
Revises: catering_015
Create Date: 2026-08-16 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_016"
down_revision: Union[str, None] = "catering_015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catering_inquiries",
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="auto_approved"),
    )
    op.add_column(
        "catering_inquiries",
        sa.Column("review_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catering_inquiries", "review_reason")
    op.drop_column("catering_inquiries", "review_status")
