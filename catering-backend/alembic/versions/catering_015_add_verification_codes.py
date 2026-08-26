"""add catering_verification_codes table

Revision ID: catering_015
Revises: catering_014
Create Date: 2026-08-14 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_015"
down_revision: Union[str, None] = "catering_014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catering_verification_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catering_verification_codes_user_id"), "catering_verification_codes", ["user_id"])
    op.create_index("ix_verification_codes_user_action", "catering_verification_codes", ["user_id", "action"])


def downgrade() -> None:
    op.drop_index("ix_verification_codes_user_action", table_name="catering_verification_codes")
    op.drop_index(op.f("ix_catering_verification_codes_user_id"), table_name="catering_verification_codes")
    op.drop_table("catering_verification_codes")
