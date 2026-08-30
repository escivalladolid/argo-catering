"""add customers table + nullable customer_id links to inquiries/quotations/bookings/payments

Revision ID: catering_030
Revises: catering_029
Create Date: 2026-08-30 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "catering_030"
down_revision: Union[str, None] = "catering_029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_LINK_TABLES = [
    "catering_inquiries",
    "catering_quotations",
    "catering_bookings",
    "catering_payments",
]


def upgrade() -> None:
    # --- customers table (soft-delete convention + partial unique org+email) ---
    op.create_table(
        "customers",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customers_organization_id"), "customers", ["organization_id"])
    op.create_index(
        "uq_customers_org_email",
        "customers",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    # --- nullable, denormalized customer_id links (existing rows stay NULL) ---
    for table in FK_LINK_TABLES:
        op.add_column(
            table,
            sa.Column(
                "customer_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("customers.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(f"ix_{table}_customer_id", table, ["customer_id"])


def downgrade() -> None:
    for table in reversed(FK_LINK_TABLES):
        op.drop_index(f"ix_{table}_customer_id", table_name=table)
        op.drop_column(table, "customer_id")
    op.drop_index("uq_customers_org_email", table_name="customers")
    op.drop_index(op.f("ix_customers_organization_id"), table_name="customers")
    op.drop_table("customers")