"""add users.organization_id for real tenant resolution

Revision ID: catering_006
Revises: catering_005
Create Date: 2026-08-03 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_006"
down_revision: Union[str, None] = "catering_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET organization_id = (SELECT id FROM organizations ORDER BY name LIMIT 1)
        WHERE organization_id IS NULL
        """
    )
    op.alter_column("users", "organization_id", existing_type=sa.Uuid(), nullable=False)
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"])
    op.create_foreign_key(
        "fk_users_organization", "users", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_organization", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_column("users", "organization_id")
