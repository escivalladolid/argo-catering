"""add package derived ratios, catalog pricing, and server-side price validation

Revision ID: catering_019
Revises: catering_018
Create Date: 2026-08-20 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_019"
down_revision: Union[str, None] = "catering_018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- CateringMenuItem: add price and pricing_unit ---
    op.add_column("catering_menu_items", sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("catering_menu_items", sa.Column("pricing_unit", sa.String(length=20), nullable=False, server_default="per_guest"))
    op.create_check_constraint("ck_menu_items_price_nonneg", "catering_menu_items", "price >= 0")
    op.create_check_constraint("ck_menu_items_pricing_unit", "catering_menu_items", "pricing_unit IN ('per_guest', 'flat')")

    # --- CateringEquipment: add pricing_unit ---
    op.add_column("catering_equipment", sa.Column("pricing_unit", sa.String(length=20), nullable=False, server_default="flat"))
    op.create_check_constraint("ck_equipment_pricing_unit", "catering_equipment", "pricing_unit IN ('per_guest', 'flat')")

    # --- CateringStaffMember: add rate and pricing_unit ---
    op.add_column("catering_staff_members", sa.Column("rate", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("catering_staff_members", sa.Column("pricing_unit", sa.String(length=20), nullable=False, server_default="per_guest"))
    op.create_check_constraint("ck_staff_rate_nonneg", "catering_staff_members", "rate >= 0")
    op.create_check_constraint("ck_staff_pricing_unit", "catering_staff_members", "pricing_unit IN ('per_guest', 'flat')")

    # --- CateringPackage: add min_pax and max_pax ---
    op.add_column("catering_packages", sa.Column("min_pax", sa.Integer(), nullable=True))
    op.add_column("catering_packages", sa.Column("max_pax", sa.Integer(), nullable=True))

    # --- PackageDerivedRatio (new table) ---
    op.create_table(
        "package_derived_ratios",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("package_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("catering_packages.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("item_key", sa.String(length=50), nullable=False),
        sa.Column("per_guests", sa.Integer(), nullable=False),
        sa.Column("minimum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_derived_ratio_pkg", "package_derived_ratios", ["package_id"])
    op.create_index(
        "uq_derived_ratio_pkg_key",
        "package_derived_ratios",
        ["package_id", "item_key"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_check_constraint("ck_derived_ratio_per_guests_pos", "package_derived_ratios", "per_guests > 0")
    op.create_check_constraint("ck_derived_ratio_minimum_nonneg", "package_derived_ratios", "minimum >= 0")

    # --- CateringInquiry: add server price validation columns ---
    op.add_column("catering_inquiries", sa.Column("server_calculated_total", sa.Numeric(12, 2), nullable=True))
    op.add_column("catering_inquiries", sa.Column("price_mismatch", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("catering_inquiries", sa.Column("selected_catalog_ids", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("catering_inquiries", "selected_catalog_ids")
    op.drop_column("catering_inquiries", "price_mismatch")
    op.drop_column("catering_inquiries", "server_calculated_total")

    op.drop_constraint("ck_derived_ratio_minimum_nonneg", "package_derived_ratios", type_="check")
    op.drop_constraint("ck_derived_ratio_per_guests_pos", "package_derived_ratios", type_="check")
    op.drop_constraint("uq_derived_ratio_pkg_key", "package_derived_ratios", type_="unique")
    op.drop_index("ix_derived_ratio_pkg", "package_derived_ratios")
    op.drop_table("package_derived_ratios")

    op.drop_column("catering_packages", "max_pax")
    op.drop_column("catering_packages", "min_pax")

    op.drop_constraint("ck_staff_pricing_unit", "catering_staff_members", type_="check")
    op.drop_constraint("ck_staff_rate_nonneg", "catering_staff_members", type_="check")
    op.drop_column("catering_staff_members", "pricing_unit")
    op.drop_column("catering_staff_members", "rate")

    op.drop_constraint("ck_equipment_pricing_unit", "catering_equipment", type_="check")
    op.drop_column("catering_equipment", "pricing_unit")

    op.drop_constraint("ck_menu_items_pricing_unit", "catering_menu_items", type_="check")
    op.drop_constraint("ck_menu_items_price_nonneg", "catering_menu_items", type_="check")
    op.drop_column("catering_menu_items", "pricing_unit")
    op.drop_column("catering_menu_items", "price")
