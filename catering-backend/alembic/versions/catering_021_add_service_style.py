"""add service_style to packages, bookings, and inquiries

Revision ID: catering_021
Revises: catering_020
Create Date: 2026-08-20 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "catering_021"
down_revision: Union[str, None] = "catering_020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- CateringPackage: add service_style ---
    op.add_column("catering_packages", sa.Column("service_style", sa.String(length=20), nullable=True))
    op.execute("UPDATE catering_packages SET service_style = 'buffet' WHERE service_style IS NULL")
    op.create_check_constraint(
        "ck_packages_service_style",
        "catering_packages",
        "service_style IS NULL OR service_style IN ('buffet', 'plated', 'cocktail', 'banquet')",
    )

    # --- CateringInquiry: add service_style ---
    op.add_column("catering_inquiries", sa.Column("service_style", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_inquiries_service_style",
        "catering_inquiries",
        "service_style IS NULL OR service_style IN ('buffet', 'plated', 'cocktail', 'banquet')",
    )

    # --- CateringBooking: add service_style ---
    op.add_column("catering_bookings", sa.Column("service_style", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_bookings_service_style",
        "catering_bookings",
        "service_style IS NULL OR service_style IN ('buffet', 'plated', 'cocktail', 'banquet')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_bookings_service_style", "catering_bookings", type_="check")
    op.drop_column("catering_bookings", "service_style")

    op.drop_constraint("ck_inquiries_service_style", "catering_inquiries", type_="check")
    op.drop_column("catering_inquiries", "service_style")

    op.drop_constraint("ck_packages_service_style", "catering_packages", type_="check")
    op.drop_column("catering_packages", "service_style")
