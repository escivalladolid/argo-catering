"""Add payment verification fields (proof_image_path, verification_status, verified_by, verified_at)

Revision ID: catering_028
Revises: catering_027
Create Date: 2026-08-24 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "catering_028"
down_revision: Union[str, None] = "catering_027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("catering_payments", sa.Column("proof_image_path", sa.String(length=500), nullable=True))
    op.add_column("catering_payments", sa.Column("verification_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("catering_payments", sa.Column("verified_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("catering_payments", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_payments_verification_status", "catering_payments", ["organization_id", "verification_status"])
    # Backfill: payments that already had verified=True → approved
    op.execute(
        "UPDATE catering_payments SET verification_status = 'approved', verified_at = updated_at WHERE verified = true AND verification_status = 'pending'"
    )


def downgrade() -> None:
    op.drop_index("ix_payments_verification_status", table_name="catering_payments")
    op.drop_column("catering_payments", "verified_at")
    op.drop_column("catering_payments", "verified_by")
    op.drop_column("catering_payments", "verification_status")
    op.drop_column("catering_payments", "proof_image_path")
