"""Add short_reference for human-friendly inquiry references

Revision ID: catering_026
Revises: catering_025
Create Date: 2026-08-23 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import secrets as _secrets

revision: str = "catering_026"
down_revision: Union[str, None] = "catering_025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_short_references(conn):
    """Generate INQ-YYYY-NNNN for every existing inquiry lacking one."""
    rows = conn.execute(
        sa.text("SELECT id, event_date FROM catering_inquiries WHERE short_reference IS NULL")
    ).fetchall()
    if not rows:
        return
    taken = set(
        r[0]
        for r in conn.execute(
            sa.text("SELECT short_reference FROM catering_inquiries WHERE short_reference IS NOT NULL")
        ).fetchall()
    )
    for rid, edate in rows:
        year = edate.year if edate else 2026
        for _ in range(50):
            candidate = f"INQ-{year}-{_secrets.randbelow(10000):04d}"
            if candidate not in taken:
                taken.add(candidate)
                break
        else:
            raise RuntimeError(f"Could not generate unique short_reference for inquiry {rid}")
        conn.execute(
            sa.text("UPDATE catering_inquiries SET short_reference = :r WHERE id = :i"),
            {"r": candidate, "i": str(rid)},
        )


def upgrade() -> None:
    op.add_column(
        "catering_inquiries",
        sa.Column("short_reference", sa.String(20), nullable=True),
    )
    op.create_index(
        "uq_inquiry_short_reference",
        "catering_inquiries",
        ["short_reference"],
        unique=True,
    )
    _backfill_short_references(op.get_bind())


def downgrade() -> None:
    op.drop_index("uq_inquiry_short_reference", table_name="catering_inquiries")
    op.drop_column("catering_inquiries", "short_reference")
