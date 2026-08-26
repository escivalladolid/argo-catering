"""Organization-scoped audit log listing.

Append-only and internal. Requires ``Perm.AUDIT_VIEW`` (manager+). Never part
of the public portal surface.
"""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import audit_log_out
from app.models.catering_models import CateringAuditLog, UserStub
from app.paging import paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import AuditLogOut, Page

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/", response_model=Page[AuditLogOut])
def list_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    entity_type: str | None = Query(None, max_length=50),
    entity_id: UUID | None = Query(None),
    search: str | None = Query(None, max_length=200),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    dir: Literal["desc", "asc"] = Query("desc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.AUDIT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = db.query(CateringAuditLog).filter(CateringAuditLog.organization_id == org_id)
    if entity_type:
        q = q.filter(CateringAuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(CateringAuditLog.entity_id == entity_id)
    if from_date:
        q = q.filter(CateringAuditLog.created_at >= _ensure_utc(from_date))
    if to_date:
        to = _ensure_utc(to_date)
        # A date-only "to" value (midnight) should include the whole day.
        if to.hour == 0 and to.minute == 0 and to.second == 0 and to.microsecond == 0:
            to = to.replace(hour=23, minute=59, second=59, microsecond=999999)
        q = q.filter(CateringAuditLog.created_at <= to)
    if search:
        q = q.filter(
            or_(
                CateringAuditLog.entity_reference.ilike(f"%{search}%"),
                CateringAuditLog.summary.ilike(f"%{search}%"),
            )
        )
    q = q.order_by(CateringAuditLog.created_at.desc() if dir == "desc" else CateringAuditLog.created_at.asc())
    result = paginate(q, page, page_size)
    items = audit_log_out(db, result.items)
    return Page(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )
