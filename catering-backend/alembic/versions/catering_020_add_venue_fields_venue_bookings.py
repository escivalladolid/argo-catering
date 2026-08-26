"""add venue description/address/parking/status, venue_bookings table

Revision ID: catering_020
Revises: catering_019
Create Date: 2026-08-20 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_020"
down_revision: Union[str, None] = "catering_019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- CateringVenue: rename info -> description, add address/parking_capacity/status ---
    op.add_column("catering_venues", sa.Column("description", sa.Text(), nullable=True))
    op.execute("UPDATE catering_venues SET description = info WHERE info IS NOT NULL")
    op.drop_column("catering_venues", "info")

    op.add_column("catering_venues", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("catering_venues", sa.Column("parking_capacity", sa.Integer(), nullable=True))
    op.add_column("catering_venues", sa.Column("status", sa.String(length=20), nullable=False, server_default="active"))
    op.create_check_constraint("ck_venues_status", "catering_venues", "status IN ('active', 'inactive')")

    # --- Venue bookings (date-based availability) ---
    op.create_table(
        "venue_bookings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("venue_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("catering_venues.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("inquiry_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("catering_inquiries.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_venue_booking_date",
        "venue_bookings",
        ["venue_id", "event_date"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_venue_booking_date", table_name="venue_bookings")
    op.drop_table("venue_bookings")

    op.drop_constraint("ck_venues_status", "catering_venues", type_="check")
    op.drop_column("catering_venues", "status")
    op.drop_column("catering_venues", "parking_capacity")
    op.drop_column("catering_venues", "address")

    op.add_column("catering_venues", sa.Column("info", sa.Text(), nullable=True))
    op.execute("UPDATE catering_venues SET info = description WHERE description IS NOT NULL")
    op.drop_column("catering_venues", "description")
