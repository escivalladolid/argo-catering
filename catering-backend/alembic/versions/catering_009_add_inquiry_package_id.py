"""add catering_package_id to catering_inquiries (customer package choice)

Revision ID: catering_009
Revises: catering_008
Create Date: 2026-08-12 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_009"
down_revision: Union[str, None] = "catering_008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catering_inquiries",
        sa.Column("catering_package_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_catering_inquiries_catering_package_id"),
        "catering_inquiries",
        ["catering_package_id"],
    )
    op.create_foreign_key(
        "fk_catering_inquiries_catering_package_id",
        "catering_inquiries",
        "catering_packages",
        ["catering_package_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_catering_inquiries_catering_package_id",
        "catering_inquiries",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_catering_inquiries_catering_package_id"),
        table_name="catering_inquiries",
    )
    op.drop_column("catering_inquiries", "catering_package_id")
