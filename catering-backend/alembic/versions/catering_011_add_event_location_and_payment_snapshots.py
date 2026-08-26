"""event location/time on inquiries + bookings (carried from inquiry)

Revision ID: catering_011
Revises: catering_010
Create Date: 2026-08-12 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_011"
down_revision: Union[str, None] = "catering_010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_inquiry_address() -> None:
    """Move a legacy 'Location: ...' line from notes into event_address."""
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, notes FROM catering_inquiries "
            "WHERE notes IS NOT NULL AND notes ILIKE 'Location:%'"
        )
    ).fetchall()
    for row_id, notes in rows:
        addr = notes.split("\n", 1)[0].replace("Location:", "", 1).strip()
        bind.execute(
            sa.text("UPDATE catering_inquiries SET event_address = :a WHERE id = :i"),
            {"a": addr or None, "i": row_id},
        )


def upgrade() -> None:
    # inquiries: required-by-API event address + optional location details + event time
    op.add_column("catering_inquiries", sa.Column("event_address", sa.String(length=255), nullable=True))
    op.add_column("catering_inquiries", sa.Column("event_time", sa.Time(timezone=True), nullable=True))
    op.add_column("catering_inquiries", sa.Column("venue_name", sa.String(length=255), nullable=True))
    op.add_column("catering_inquiries", sa.Column("location_floor", sa.String(length=100), nullable=True))
    op.add_column("catering_inquiries", sa.Column("room_hall", sa.String(length=255), nullable=True))
    op.add_column("catering_inquiries", sa.Column("landmark", sa.String(length=255), nullable=True))
    op.add_column("catering_inquiries", sa.Column("delivery_instructions", sa.Text(), nullable=True))
    op.create_index(op.f("ix_catering_inquiries_event_address"), "catering_inquiries", ["event_address"])
    _backfill_inquiry_address()

    # bookings: carry the address (formatted block) + event time from the inquiry
    op.alter_column(
        "catering_bookings",
        "event_location",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.add_column("catering_bookings", sa.Column("event_time", sa.Time(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("catering_bookings", "event_time")
    op.alter_column(
        "catering_bookings",
        "event_location",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )

    op.drop_index(op.f("ix_catering_inquiries_event_address"), table_name="catering_inquiries")
    op.drop_column("catering_inquiries", "delivery_instructions")
    op.drop_column("catering_inquiries", "landmark")
    op.drop_column("catering_inquiries", "room_hall")
    op.drop_column("catering_inquiries", "location_floor")
    op.drop_column("catering_inquiries", "venue_name")
    op.drop_column("catering_inquiries", "event_time")
    op.drop_column("catering_inquiries", "event_address")
