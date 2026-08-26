"""add customer_email to inquiries and reference_id to verification codes

Revision ID: catering_017
Revises: catering_016
Create Date: 2026-08-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_017"
down_revision: Union[str, None] = "catering_016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catering_inquiries",
        sa.Column("customer_email", sa.String(length=255), nullable=False, server_default="pending@placeholder.local"),
    )
    op.alter_column("catering_inquiries", "customer_email", server_default=None)

    op.alter_column("catering_verification_codes", "user_id", nullable=True)

    op.add_column(
        "catering_verification_codes",
        sa.Column("reference_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_verification_codes_reference_action",
        "catering_verification_codes",
        ["reference_id", "action"],
    )


def downgrade() -> None:
    op.drop_index("ix_verification_codes_reference_action", table_name="catering_verification_codes")
    op.drop_column("catering_verification_codes", "reference_id")
    op.drop_column("catering_inquiries", "customer_email")
