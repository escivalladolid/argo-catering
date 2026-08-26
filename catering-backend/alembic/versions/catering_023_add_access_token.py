"""add access_token to catering_inquiries

Revision ID: catering_023
Revises: catering_022
Create Date: 2026-08-22 12:00:00.000000
"""
from typing import Sequence, Union

import secrets
from alembic import op
import sqlalchemy as sa


revision: str = "catering_023"
down_revision: Union[str, None] = "catering_022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column as nullable first
    op.add_column("catering_inquiries", sa.Column("access_token", sa.String(64), nullable=True))
    op.create_index("ix_catering_inquiries_access_token", "catering_inquiries", ["access_token"], unique=False)

    # Backfill existing rows with random tokens
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM catering_inquiries WHERE access_token IS NULL")).fetchall()
    for row in rows:
        token = secrets.token_urlsafe(32)
        conn.execute(
            sa.text("UPDATE catering_inquiries SET access_token = :token WHERE id = :id"),
            {"token": token, "id": row[0]},
        )

    # Now make it NOT NULL
    op.alter_column("catering_inquiries", "access_token", nullable=False, server_default="")


def downgrade() -> None:
    op.drop_index("ix_catering_inquiries_access_token", table_name="catering_inquiries")
    op.drop_column("catering_inquiries", "access_token")
