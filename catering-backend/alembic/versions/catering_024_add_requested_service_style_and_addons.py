"""requested_service_style on inquiries, catalog_item_id + addon kind on inquiry items

Revision ID: catering_024
Revises: catering_023
Create Date: 2026-08-23 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_024"
down_revision: Union[str, None] = "catering_023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catering_inquiries",
        sa.Column("requested_service_style", sa.String(20), nullable=True,
                  comment="Customer-requested override of package default service style"),
    )
    op.add_column(
        "catering_inquiry_items",
        sa.Column("catalog_item_id", sa.UUID(), nullable=True,
                  comment="Original dish/equipment/staff catalog UUID for customer-added extras"),
    )
    op.create_index("ix_catering_inquiry_items_catalog_item_id", "catering_inquiry_items", ["catalog_item_id"])
    op.drop_constraint("ck_inquiry_items_kind", "catering_inquiry_items", type_="check")
    op.create_check_constraint(
        "ck_inquiry_items_kind",
        "catering_inquiry_items",
        "kind IN ('default', 'custom', 'included', 'addon')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_inquiry_items_kind", "catering_inquiry_items", type_="check")
    op.create_check_constraint(
        "ck_inquiry_items_kind",
        "catering_inquiry_items",
        "kind IN ('default', 'custom', 'included')",
    )
    op.drop_index("ix_catering_inquiry_items_catalog_item_id", table_name="catering_inquiry_items")
    op.drop_column("catering_inquiry_items", "catalog_item_id")
    op.drop_column("catering_inquiries", "requested_service_style")
