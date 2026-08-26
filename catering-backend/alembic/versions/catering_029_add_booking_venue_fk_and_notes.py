"""Add selected_venue_id FK to bookings + customer notes columns

Revision ID: catering_029
Revises: catering_028
Create Date: 2026-08-25 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "catering_029"
down_revision: Union[str, None] = "catering_028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Customer notes on inquiries (add first so backfill can reference them) ---
    op.add_column("catering_inquiries", sa.Column("additional_notes", sa.Text(), nullable=True))
    op.add_column("catering_inquiries", sa.Column("dietary_notes", sa.Text(), nullable=True))
    op.add_column("catering_inquiries", sa.Column("setup_notes", sa.Text(), nullable=True))

    # --- Venue FK on bookings ---
    op.add_column("catering_bookings", sa.Column("selected_venue_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("catering_venues.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_bookings_selected_venue_id", "catering_bookings", ["selected_venue_id"])

    # Backfill: copy selected_venue_id from the linked inquiry
    op.execute(
        """UPDATE catering_bookings b
           SET selected_venue_id = i.selected_venue_id
           FROM catering_quotations q, catering_inquiries i
           WHERE b.quotation_id = q.id
             AND q.inquiry_id = i.id
             AND i.selected_venue_id IS NOT NULL
             AND b.selected_venue_id IS NULL"""
    )

    # --- Customer notes on bookings ---
    op.add_column("catering_bookings", sa.Column("additional_notes", sa.Text(), nullable=True))
    op.add_column("catering_bookings", sa.Column("dietary_notes", sa.Text(), nullable=True))
    op.add_column("catering_bookings", sa.Column("setup_notes", sa.Text(), nullable=True))

    # Backfill notes from the linked inquiry
    op.execute(
        """UPDATE catering_bookings b
           SET additional_notes = i.additional_notes,
               dietary_notes    = i.dietary_notes,
               setup_notes      = i.setup_notes
           FROM catering_quotations q, catering_inquiries i
           WHERE b.quotation_id = q.id
             AND q.inquiry_id = i.id
             AND (i.additional_notes IS NOT NULL OR i.dietary_notes IS NOT NULL OR i.setup_notes IS NOT NULL)"""
    )


def downgrade() -> None:
    op.drop_column("catering_bookings", "setup_notes")
    op.drop_column("catering_bookings", "dietary_notes")
    op.drop_column("catering_bookings", "additional_notes")
    op.drop_index("ix_bookings_selected_venue_id", table_name="catering_bookings")
    op.drop_column("catering_bookings", "selected_venue_id")
    op.drop_column("catering_inquiries", "setup_notes")
    op.drop_column("catering_inquiries", "dietary_notes")
    op.drop_column("catering_inquiries", "additional_notes")
