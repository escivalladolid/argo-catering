"""harden money columns, add status/range constraints, add indexes

Revision ID: catering_005
Revises: catering_004
Create Date: 2026-08-03 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_005"
down_revision: Union[str, None] = "catering_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Money columns: Float -> Numeric(12,2) (Postgres float8 -> numeric cast is implicit)
    op.alter_column("catering_packages", "base_price",
                    existing_type=sa.Float(), type_=sa.Numeric(12, 2), existing_nullable=False)
    op.alter_column("catering_quotations", "total_price",
                    existing_type=sa.Float(), type_=sa.Numeric(12, 2), existing_nullable=False)
    op.alter_column("catering_bookings", "total_amount",
                    existing_type=sa.Float(), type_=sa.Numeric(12, 2), existing_nullable=False)

    # Range constraints
    op.create_check_constraint("ck_packages_base_price_nonneg", "catering_packages", "base_price >= 0")
    op.create_check_constraint("ck_quotations_total_price_nonneg", "catering_quotations", "total_price >= 0")
    op.create_check_constraint("ck_bookings_total_amount_nonneg", "catering_bookings", "total_amount >= 0")
    op.create_check_constraint("ck_inquiries_guest_count_pos", "catering_inquiries", "guest_count >= 1")
    op.create_check_constraint("ck_quotations_guest_count_pos", "catering_quotations", "guest_count >= 1")
    op.create_check_constraint("ck_bookings_guest_count_pos", "catering_bookings", "guest_count >= 1")

    # Status value constraints
    op.create_check_constraint(
        "ck_inquiries_status", "catering_inquiries",
        "status IN ('new', 'quoted', 'converted', 'closed')")
    op.create_check_constraint(
        "ck_quotations_status", "catering_quotations",
        "status IN ('draft', 'sent', 'accepted', 'rejected')")
    op.create_check_constraint(
        "ck_bookings_status", "catering_bookings",
        "status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled')")
    op.create_check_constraint(
        "ck_bookings_payment_status", "catering_bookings",
        "payment_status IN ('unpaid', 'paid', 'partially_paid', 'refunded')")

    # Missing lookup indexes
    op.create_index("ix_catering_inquiries_event_date", "catering_inquiries", ["event_date"])
    op.create_index("ix_catering_bookings_event_date", "catering_bookings", ["event_date"])
    op.create_index("ix_catering_quotations_inquiry_id", "catering_quotations", ["inquiry_id"])


def downgrade() -> None:
    op.drop_index("ix_catering_quotations_inquiry_id", table_name="catering_quotations")
    op.drop_index("ix_catering_bookings_event_date", table_name="catering_bookings")
    op.drop_index("ix_catering_inquiries_event_date", table_name="catering_inquiries")

    op.drop_constraint("ck_bookings_payment_status", "catering_bookings")
    op.drop_constraint("ck_bookings_status", "catering_bookings")
    op.drop_constraint("ck_quotations_status", "catering_quotations")
    op.drop_constraint("ck_inquiries_status", "catering_inquiries")
    op.drop_constraint("ck_bookings_guest_count_pos", "catering_bookings")
    op.drop_constraint("ck_quotations_guest_count_pos", "catering_quotations")
    op.drop_constraint("ck_inquiries_guest_count_pos", "catering_inquiries")
    op.drop_constraint("ck_bookings_total_amount_nonneg", "catering_bookings")
    op.drop_constraint("ck_quotations_total_price_nonneg", "catering_quotations")
    op.drop_constraint("ck_packages_base_price_nonneg", "catering_packages")

    op.alter_column("catering_bookings", "total_amount",
                    existing_type=sa.Numeric(12, 2), type_=sa.Float(), existing_nullable=False)
    op.alter_column("catering_quotations", "total_price",
                    existing_type=sa.Numeric(12, 2), type_=sa.Float(), existing_nullable=False)
    op.alter_column("catering_packages", "base_price",
                    existing_type=sa.Numeric(12, 2), type_=sa.Float(), existing_nullable=False)
