"""make name unique constraints partial (ignore soft-deleted rows)

Revision ID: catering_008
Revises: catering_007
Create Date: 2026-08-04 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_008"
down_revision: Union[str, None] = "catering_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table, columns, name in [
        ("catering_packages", ("organization_id", "name"), "uq_package_org_name"),
        ("catering_menus", ("organization_id", "name"), "uq_menu_org_name"),
        ("catering_menu_items", ("menu_id", "name"), "uq_menu_item_name"),
        ("catering_staff_members", ("organization_id", "name"), "uq_staff_org_name"),
        ("catering_equipment", ("organization_id", "name"), "uq_equipment_org_name"),
    ]:
        op.drop_constraint(name, table, type_="unique")
        op.create_index(
            name,
            table,
            columns,
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
            sqlite_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    for table, columns, name in [
        ("catering_equipment", ("organization_id", "name"), "uq_equipment_org_name"),
        ("catering_staff_members", ("organization_id", "name"), "uq_staff_org_name"),
        ("catering_menu_items", ("menu_id", "name"), "uq_menu_item_name"),
        ("catering_menus", ("organization_id", "name"), "uq_menu_org_name"),
        ("catering_packages", ("organization_id", "name"), "uq_package_org_name"),
    ]:
        op.drop_index(name, table_name=table)
        op.create_unique_constraint(name, table, columns)
