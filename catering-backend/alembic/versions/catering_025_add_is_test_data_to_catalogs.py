"""is_test_data flag on catalog tables to keep seeded test rows out of the public portal

Revision ID: catering_025
Revises: catering_024
Create Date: 2026-08-23 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_025"
down_revision: Union[str, None] = "catering_024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ["catering_staff_members", "catering_equipment", "catering_menu_items"]


def upgrade() -> None:
    for t in TABLES:
        op.add_column(
            t,
            sa.Column("is_test_data", sa.Boolean(), nullable=False, server_default=sa.text("false"),
                      comment="Seeded by automated tests; excluded from all customer-facing reads"),
        )


def downgrade() -> None:
    for t in TABLES:
        op.drop_column(t, "is_test_data")
