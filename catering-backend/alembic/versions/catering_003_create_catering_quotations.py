"""create catering_quotations table

Revision ID: catering_003
Revises: catering_002
Create Date: 2026-07-29 23:00:03.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_003"
down_revision: Union[str, None] = "catering_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catering_quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inquiry_id", sa.Uuid(), nullable=False),
        sa.Column("catering_package_id", sa.Uuid(), nullable=True),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column("total_price", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inquiry_id"], ["catering_inquiries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["catering_package_id"], ["catering_packages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catering_quotations_organization_id"), "catering_quotations", ["organization_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_catering_quotations_organization_id"), table_name="catering_quotations")
    op.drop_table("catering_quotations")
