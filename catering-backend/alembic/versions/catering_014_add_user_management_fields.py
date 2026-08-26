"""add user management fields

Revision ID: catering_014
Revises: catering_013
Create Date: 2026-08-14 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_014"
down_revision: Union[str, None] = "catering_013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE users SET created_at = now(), updated_at = now() "
        "WHERE created_at IS NULL OR updated_at IS NULL"
    )
    op.alter_column("users", "created_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column("users", "updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "created_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "full_name")
