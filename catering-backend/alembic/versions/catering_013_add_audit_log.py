"""add catering_audit_log table

Revision ID: catering_013
Revises: catering_012
Create Date: 2026-08-14 08:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_013"
down_revision: Union[str, None] = "catering_012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catering_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("entity_reference", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catering_audit_log_organization_id"), "catering_audit_log", ["organization_id"])
    op.create_index(op.f("ix_catering_audit_log_created_at"), "catering_audit_log", ["created_at"])
    op.create_index("ix_audit_org_entity", "catering_audit_log", ["organization_id", "entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_org_entity", table_name="catering_audit_log")
    op.drop_index(op.f("ix_catering_audit_log_created_at"), table_name="catering_audit_log")
    op.drop_index(op.f("ix_catering_audit_log_organization_id"), table_name="catering_audit_log")
    op.drop_table("catering_audit_log")
