"""package builder (groups/items) + inquiry flow fields (selections, requirements, staffing)

Revision ID: catering_010
Revises: catering_009
Create Date: 2026-08-12 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_010"
down_revision: Union[str, None] = "catering_009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_staff_role_check() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("catering_staff_members"):
        for c in insp.get_check_constraints("catering_staff_members"):
            if c["name"] == "ck_staff_role":
                op.drop_constraint("ck_staff_role", "catering_staff_members", type_="check")
        op.create_check_constraint(
            "ck_staff_role",
            "catering_staff_members",
            "role IN ('chef', 'server', 'crew', 'supervisor', 'driver', 'bartender', 'kitchen_staff', 'support')",
        )


def upgrade() -> None:
    # packages: pricing method + customization flag
    op.add_column("catering_packages", sa.Column("pricing_method", sa.String(length=20), nullable=False, server_default="per_guest"))
    op.add_column("catering_packages", sa.Column("has_customization", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_check_constraint("ck_packages_pricing_method", "catering_packages", "pricing_method IN ('per_guest', 'fixed')")

    # package groups (customization groups)
    op.create_table(
        "catering_package_groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("min_select", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key("fk_pkg_groups_org", "catering_package_groups", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_pkg_groups_package", "catering_package_groups", "catering_packages", ["package_id"], ["id"], ondelete="CASCADE")
    op.create_index(op.f("ix_catering_package_groups_organization_id"), "catering_package_groups", ["organization_id"])
    op.create_index(op.f("ix_catering_package_groups_package_id"), "catering_package_groups", ["package_id"])
    op.create_check_constraint("ck_package_groups_select_bounds", "catering_package_groups", "min_select >= 0 AND max_select >= min_select")

    # package items (included / default / option dishes with quantity + unit)
    op.create_table(
        "catering_package_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("menu_item_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="included"),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=30), nullable=False, server_default="serving"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key("fk_pkg_items_org", "catering_package_items", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_pkg_items_package", "catering_package_items", "catering_packages", ["package_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_pkg_items_menu_item", "catering_package_items", "catering_menu_items", ["menu_item_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_pkg_items_group", "catering_package_items", "catering_package_groups", ["group_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_catering_package_items_organization_id"), "catering_package_items", ["organization_id"])
    op.create_index(op.f("ix_catering_package_items_package_id"), "catering_package_items", ["package_id"])
    op.create_index(op.f("ix_catering_package_items_menu_item_id"), "catering_package_items", ["menu_item_id"])
    op.create_index(op.f("ix_catering_package_items_group_id"), "catering_package_items", ["group_id"])
    op.create_check_constraint("ck_package_items_kind", "catering_package_items", "kind IN ('included', 'default', 'option')")
    op.create_check_constraint("ck_package_items_quantity_pos", "catering_package_items", "quantity > 0")

    # inquiries: package mode, event type, food requirements, staffing requests, flag
    op.add_column("catering_inquiries", sa.Column("event_type", sa.String(length=50), nullable=True))
    op.add_column("catering_inquiries", sa.Column("package_mode", sa.String(length=20), nullable=True))
    op.add_column("catering_inquiries", sa.Column("food_requirements_json", sa.Text(), nullable=True))
    op.add_column("catering_inquiries", sa.Column("waiter_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("catering_inquiries", sa.Column("bartender_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("catering_inquiries", sa.Column("chef_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("catering_inquiries", sa.Column("kitchen_staff_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("catering_inquiries", sa.Column("support_crew_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("catering_inquiries", sa.Column("flag_note", sa.Text(), nullable=True))
    op.create_check_constraint("ck_inquiries_package_mode", "catering_inquiries", "package_mode IS NULL OR package_mode IN ('default', 'custom')")
    op.create_check_constraint(
        "ck_inquiries_staff_counts_nonneg",
        "catering_inquiries",
        "waiter_count >= 0 AND bartender_count >= 0 AND chef_count >= 0 AND kitchen_staff_count >= 0 AND support_crew_count >= 0",
    )

    # inquiry items: customer selections snapshot
    op.create_table(
        "catering_inquiry_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inquiry_id", sa.Uuid(), nullable=False),
        sa.Column("menu_item_id", sa.Uuid(), nullable=True),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("group_name", sa.String(length=100), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="default"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=30), nullable=False, server_default="serving"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key("fk_inquiry_items_org", "catering_inquiry_items", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_inquiry_items_inquiry", "catering_inquiry_items", "catering_inquiries", ["inquiry_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_inquiry_items_menu_item", "catering_inquiry_items", "catering_menu_items", ["menu_item_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_catering_inquiry_items_organization_id"), "catering_inquiry_items", ["organization_id"])
    op.create_index(op.f("ix_catering_inquiry_items_inquiry_id"), "catering_inquiry_items", ["inquiry_id"])
    op.create_index(op.f("ix_catering_inquiry_items_menu_item_id"), "catering_inquiry_items", ["menu_item_id"])
    op.create_check_constraint("ck_inquiry_items_kind", "catering_inquiry_items", "kind IN ('default', 'custom', 'included')")
    op.create_check_constraint("ck_inquiry_items_quantity_pos", "catering_inquiry_items", "quantity > 0")

    _replace_staff_role_check()


def downgrade() -> None:
    op.drop_constraint("ck_inquiry_items_quantity_pos", "catering_inquiry_items", type_="check")
    op.drop_constraint("ck_inquiry_items_kind", "catering_inquiry_items", type_="check")
    op.drop_index(op.f("ix_catering_inquiry_items_menu_item_id"), table_name="catering_inquiry_items")
    op.drop_index(op.f("ix_catering_inquiry_items_inquiry_id"), table_name="catering_inquiry_items")
    op.drop_index(op.f("ix_catering_inquiry_items_organization_id"), table_name="catering_inquiry_items")
    op.drop_table("catering_inquiry_items")

    op.drop_constraint("ck_inquiries_staff_counts_nonneg", "catering_inquiries", type_="check")
    op.drop_constraint("ck_inquiries_package_mode", "catering_inquiries", type_="check")
    op.drop_column("catering_inquiries", "flag_note")
    op.drop_column("catering_inquiries", "support_crew_count")
    op.drop_column("catering_inquiries", "kitchen_staff_count")
    op.drop_column("catering_inquiries", "chef_count")
    op.drop_column("catering_inquiries", "bartender_count")
    op.drop_column("catering_inquiries", "waiter_count")
    op.drop_column("catering_inquiries", "food_requirements_json")
    op.drop_column("catering_inquiries", "package_mode")
    op.drop_column("catering_inquiries", "event_type")

    op.drop_constraint("ck_package_items_quantity_pos", "catering_package_items", type_="check")
    op.drop_constraint("ck_package_items_kind", "catering_package_items", type_="check")
    op.drop_index(op.f("ix_catering_package_items_group_id"), table_name="catering_package_items")
    op.drop_index(op.f("ix_catering_package_items_menu_item_id"), table_name="catering_package_items")
    op.drop_index(op.f("ix_catering_package_items_package_id"), table_name="catering_package_items")
    op.drop_index(op.f("ix_catering_package_items_organization_id"), table_name="catering_package_items")
    op.drop_table("catering_package_items")

    op.drop_constraint("ck_package_groups_select_bounds", "catering_package_groups", type_="check")
    op.drop_index(op.f("ix_catering_package_groups_package_id"), table_name="catering_package_groups")
    op.drop_index(op.f("ix_catering_package_groups_organization_id"), table_name="catering_package_groups")
    op.drop_table("catering_package_groups")

    op.drop_constraint("ck_packages_pricing_method", "catering_packages", type_="check")
    op.drop_column("catering_packages", "has_customization")
    op.drop_column("catering_packages", "pricing_method")

    op.drop_constraint("ck_staff_role", "catering_staff_members", type_="check")
    op.create_check_constraint(
        "ck_staff_role",
        "catering_staff_members",
        "role IN ('chef', 'server', 'crew', 'supervisor', 'driver')",
    )
