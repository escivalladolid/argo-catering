"""add venues, venue mode on inquiries, coordinator on bookings, customer payment fields

Revision ID: catering_018
Revises: catering_017
Create Date: 2026-08-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_018"
down_revision: Union[str, None] = "catering_017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- CateringVenue ---
    op.create_table(
        "catering_venues",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("info", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_venues_org", "catering_venues", ["organization_id"])
    op.create_index(
        "uq_venue_org_name",
        "catering_venues",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # --- CateringInquiry: venue_mode, selected_venue_id, venue_fee, estimated_total ---
    op.add_column("catering_inquiries", sa.Column("venue_mode", sa.String(length=20), nullable=True))
    op.add_column("catering_inquiries", sa.Column("selected_venue_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("catering_venues.id", ondelete="SET NULL"), nullable=True, index=True))
    op.add_column("catering_inquiries", sa.Column("venue_fee", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("catering_inquiries", sa.Column("estimated_total", sa.Numeric(12, 2), nullable=True))

    # --- CateringBooking: coordinator_name, coordinator_contact ---
    op.add_column("catering_bookings", sa.Column("coordinator_name", sa.String(length=255), nullable=True))
    op.add_column("catering_bookings", sa.Column("coordinator_contact", sa.String(length=255), nullable=True))

    # --- CateringPayment: payment_date, customer_reference, proof_url, verified + maya method ---
    op.add_column("catering_payments", sa.Column("payment_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("catering_payments", sa.Column("customer_reference", sa.String(length=255), nullable=True))
    op.add_column("catering_payments", sa.Column("proof_url", sa.String(length=500), nullable=True))
    op.add_column("catering_payments", sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # Drop old method check constraint, re-create with 'maya' added
    op.execute("ALTER TABLE catering_payments DROP CONSTRAINT IF EXISTS ck_payments_method")
    op.execute(
        "ALTER TABLE catering_payments ADD CONSTRAINT ck_payments_method "
        "CHECK (method IN ('cash', 'bank_transfer', 'card', 'gcash', 'check', 'other', 'maya'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE catering_payments DROP CONSTRAINT IF EXISTS ck_payments_method")
    op.execute(
        "ALTER TABLE catering_payments ADD CONSTRAINT ck_payments_method "
        "CHECK (method IN ('cash', 'bank_transfer', 'card', 'gcash', 'check', 'other'))"
    )
    op.drop_column("catering_payments", "verified")
    op.drop_column("catering_payments", "proof_url")
    op.drop_column("catering_payments", "customer_reference")
    op.drop_column("catering_payments", "payment_date")
    op.drop_column("catering_bookings", "coordinator_contact")
    op.drop_column("catering_bookings", "coordinator_name")
    op.drop_column("catering_inquiries", "estimated_total")
    op.drop_column("catering_inquiries", "venue_fee")
    op.drop_column("catering_inquiries", "selected_venue_id")
    op.drop_column("catering_inquiries", "venue_mode")
    op.drop_index("uq_venue_org_name", table_name="catering_venues")
    op.drop_index("ix_venues_org", table_name="catering_venues")
    op.drop_table("catering_venues")
