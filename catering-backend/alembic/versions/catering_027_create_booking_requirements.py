"""Create booking_requirements table (pre-event task checklist per booking)

Revision ID: catering_027
Revises: catering_026
Create Date: 2026-08-24 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "catering_027"
down_revision: Union[str, None] = "catering_026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "booking_requirements",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False, server_default="other"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("completed_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("category IN ('venue', 'equipment', 'other')", name="ck_booking_requirements_category"),
        sa.CheckConstraint("status IN ('pending', 'done', 'overdue')", name="ck_booking_requirements_status"),
    )
    op.create_index(
        "ix_booking_requirements_org_status",
        "booking_requirements",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_booking_requirements_org_status", table_name="booking_requirements")
    op.drop_table("booking_requirements")
