"""create catering_bookings table

Revision ID: catering_004
Revises: catering_003
Create Date: 2026-07-29 23:00:04.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_004"
down_revision: Union[str, None] = "catering_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catering_bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_location", sa.String(length=255), nullable=True),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("payment_status", sa.String(length=50), nullable=False, server_default="unpaid"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quotation_id"], ["catering_quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_id", name="uq_booking_quotation"),
    )
    op.create_index(op.f("ix_catering_bookings_organization_id"), "catering_bookings", ["organization_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_catering_bookings_organization_id"), table_name="catering_bookings")
    op.drop_table("catering_bookings")
