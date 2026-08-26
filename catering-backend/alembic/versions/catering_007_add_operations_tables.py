"""add operations tables (menus, guest counts, food requirements, staffing, equipment, deliveries, payments, billing)

Revision ID: catering_007
Revises: catering_006
Create Date: 2026-08-04 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_007"
down_revision: Union[str, None] = "catering_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Menus ---
    op.create_table(
        "catering_menus",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "name", name="uq_menu_org_name"),
        sa.CheckConstraint("category IN ('lunch', 'dinner', 'breakfast', 'cocktail', 'custom')", name="ck_menus_category"),
    )
    op.create_table(
        "catering_menu_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("menu_id", sa.Uuid(), sa.ForeignKey("catering_menus.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("dietary_tags", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("menu_id", "name", name="uq_menu_item_name"),
        sa.CheckConstraint("category IN ('starter', 'main', 'dessert', 'beverage', 'other')", name="ck_menu_items_category"),
    )

    # --- Guest counts ---
    op.create_table(
        "catering_guest_counts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("count_type", sa.String(30), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("count >= 1", name="ck_guest_counts_count_pos"),
        sa.CheckConstraint("count_type IN ('estimated', 'guaranteed', 'actual')", name="ck_guest_counts_type"),
    )

    # --- Food requirements ---
    op.create_table(
        "catering_food_requirements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("requirement_type", sa.String(30), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("requirement_type IN ('vegetarian', 'vegan', 'halal', 'gluten_free', 'allergy', 'other')", name="ck_food_req_type"),
        sa.CheckConstraint("guest_count IS NULL OR guest_count >= 1", name="ck_food_req_guest_count"),
    )

    # --- Staffing ---
    op.create_table(
        "catering_staff_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "name", name="uq_staff_org_name"),
        sa.CheckConstraint("role IN ('chef', 'server', 'crew', 'supervisor', 'driver')", name="ck_staff_role"),
    )
    op.create_table(
        "catering_staff_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("staff_id", sa.Uuid(), sa.ForeignKey("catering_staff_members.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("shift_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shift_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("role", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Equipment ---
    op.create_table(
        "catering_equipment",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "name", name="uq_equipment_org_name"),
        sa.CheckConstraint("quantity >= 0", name="ck_equipment_quantity_nonneg"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_equipment_unit_cost_nonneg"),
        sa.CheckConstraint("category IN ('kitchen', 'service', 'venue', 'transport', 'other')", name="ck_equipment_category"),
    )
    op.create_table(
        "catering_equipment_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("equipment_id", sa.Uuid(), sa.ForeignKey("catering_equipment.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity >= 1", name="ck_equip_assign_quantity_pos"),
    )

    # --- Deliveries ---
    op.create_table(
        "catering_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_address", sa.String(255), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('scheduled', 'in_transit', 'delivered', 'delayed', 'cancelled')", name="ck_deliveries_status"),
    )

    # --- Payments ---
    op.create_table(
        "catering_payments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount_nonneg"),
        sa.CheckConstraint("method IN ('cash', 'bank_transfer', 'card', 'gcash', 'check', 'other')", name="ck_payments_method"),
    )

    # --- Billing ---
    op.create_table(
        "catering_bills",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("booking_id", sa.Uuid(), sa.ForeignKey("catering_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bill_number", sa.String(50), nullable=False),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "bill_number", name="uq_bill_org_number"),
        sa.CheckConstraint("status IN ('draft', 'sent', 'paid', 'overdue', 'void')", name="ck_bills_status"),
        sa.CheckConstraint("subtotal >= 0 AND tax >= 0 AND discount >= 0 AND total >= 0", name="ck_bills_totals_nonneg"),
    )
    op.create_table(
        "catering_bill_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bill_id", sa.Uuid(), sa.ForeignKey("catering_bills.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity >= 0 AND unit_price >= 0 AND amount >= 0", name="ck_bill_items_nonneg"),
    )


def downgrade() -> None:
    op.drop_table("catering_bill_items")
    op.drop_table("catering_bills")
    op.drop_table("catering_payments")
    op.drop_table("catering_deliveries")
    op.drop_table("catering_equipment_assignments")
    op.drop_table("catering_equipment")
    op.drop_table("catering_staff_assignments")
    op.drop_table("catering_staff_members")
    op.drop_table("catering_food_requirements")
    op.drop_table("catering_guest_counts")
    op.drop_table("catering_menu_items")
    op.drop_table("catering_menus")
