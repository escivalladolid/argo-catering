from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.booking_scoped import base_query, get_booking
from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringBooking, CateringInquiry, CateringStaffAssignment, CateringStaffMember, UserStub
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringStaffAssignmentCreate,
    CateringStaffAssignmentOut,
    CateringStaffAssignmentUpdate,
    CateringStaffMemberCreate,
    CateringStaffMemberOut,
    CateringStaffMemberUpdate,
    Page,
    StaffingOut,
)

staff_router = APIRouter(prefix="/staff", tags=["Staffing"])
assignment_router = APIRouter(prefix="/staff-assignments", tags=["Staffing"])

# Customer-requested role counts map onto staff member roles.
REQUEST_ROLE_TO_STAFF_ROLE = {
    "waiter_count": "server",
    "bartender_count": "bartender",
    "chef_count": "chef",
    "kitchen_staff_count": "kitchen_staff",
    "support_crew_count": "support",
}

STAFF_SORT_MAP = {
    "name": CateringStaffMember.name,
    "role": CateringStaffMember.role,
    "created_at": CateringStaffMember.created_at,
}
STAFF_SEARCH_COLS = [CateringStaffMember.name, CateringStaffMember.phone]

ASSIGNMENT_SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "staff_name": CateringStaffMember.name,
    "shift_start": CateringStaffAssignment.shift_start,
    "created_at": CateringStaffAssignment.created_at,
}
ASSIGNMENT_SEARCH_COLS = [CateringInquiry.customer_name, CateringStaffMember.name]


def _staff_base_query(db: Session, org_id: UUID):
    return db.query(CateringStaffMember).filter(
        CateringStaffMember.organization_id == org_id,
        CateringStaffMember.deleted_at.is_(None),
    )


def _assignment_base_query(db: Session, org_id: UUID):
    q = base_query(db, CateringStaffAssignment, org_id)
    return q.options(joinedload(CateringStaffAssignment.staff))


def staffing_availability(db: Session, org_id: UUID, event_date: datetime) -> dict[str, int]:
    """Internal availability per customer-requested role on a given date.

    A staff member is 'available' if active and not already assigned to a
    shift on that date. Only used internally; never shown to customers.
    """
    active_roles = (
        db.query(CateringStaffMember.role, func.count())
        .filter(
            CateringStaffMember.organization_id == org_id,
            CateringStaffMember.deleted_at.is_(None),
            CateringStaffMember.is_active.is_(True),
        )
        .group_by(CateringStaffMember.role)
        .all()
    )
    total_by_role = dict(active_roles)

    assigned_rows = (
        db.query(CateringStaffMember.role, func.count(func.distinct(CateringStaffAssignment.staff_id)))
        .join(CateringStaffAssignment, CateringStaffAssignment.staff_id == CateringStaffMember.id)
        .filter(
            CateringStaffAssignment.organization_id == org_id,
            CateringStaffAssignment.deleted_at.is_(None),
            func.date(CateringStaffAssignment.shift_start) == func.date(event_date),
        )
        .group_by(CateringStaffMember.role)
        .all()
    )
    assigned_by_role = dict(assigned_rows)

    result: dict[str, int] = {}
    for request_key, staff_role in REQUEST_ROLE_TO_STAFF_ROLE.items():
        total = total_by_role.get(staff_role, 0)
        assigned = assigned_by_role.get(staff_role, 0)
        result[request_key] = max(total - assigned, 0)
    return result


def staffing_shortfall_warning(requested: dict[str, int], available: dict[str, int]) -> str | None:
    parts = []
    for key in REQUEST_ROLE_TO_STAFF_ROLE:
        needed = requested.get(key, 0)
        have = available.get(key, 0)
        if needed > have:
            label = key.replace("_count", "").replace("_", " ")
            parts.append(f"{needed} {label} requested, {have} available")
    if not parts:
        return None
    return "Insufficient staff availability: " + "; ".join(parts) + "."


# ---- staff members ----

@staff_router.get("/", response_model=Page[CateringStaffMemberOut])
def list_staff(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _staff_base_query(db, org_id)
    if status:
        q = q.filter(CateringStaffMember.role == status)
    q = apply_search(q, search, STAFF_SEARCH_COLS)
    q = apply_sort(q, sort, dir, STAFF_SORT_MAP)
    return paginate(q, page, page_size)


@staff_router.post("/", response_model=CateringStaffMemberOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: CateringStaffMemberCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    existing = db.query(CateringStaffMember).filter(
        CateringStaffMember.organization_id == org_id,
        CateringStaffMember.name == payload.name,
        CateringStaffMember.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Staff member with this name already exists")
    staff = CateringStaffMember(
        **payload.model_dump(exclude_unset=True),
        organization_id=org_id,
        created_by=current_user.id,
    )
    db.add(staff)
    db.flush()
    log_audit(
        db,
        org_id,
        "staff_member",
        staff.id,
        staff.name,
        "created",
        current_user,
        f"Staff member '{staff.name}' created",
    )
    db.commit()
    db.refresh(staff)
    return staff


@staff_router.get("/availability", response_model=StaffingOut)
def staff_availability(
    event_date: datetime = Query(...),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    return StaffingOut(**staffing_availability(db, org_id, event_date))


@staff_router.get("/{staff_id}", response_model=CateringStaffMemberOut)
def get_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    staff = _staff_base_query(db, org_id).filter(CateringStaffMember.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return staff


@staff_router.put("/{staff_id}", response_model=CateringStaffMemberOut)
def update_staff(
    staff_id: UUID,
    payload: CateringStaffMemberUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    staff = _staff_base_query(db, org_id).filter(CateringStaffMember.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        existing = db.query(CateringStaffMember).filter(
            CateringStaffMember.organization_id == org_id,
            CateringStaffMember.name == data["name"],
            CateringStaffMember.id != staff_id,
            CateringStaffMember.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Staff member with this name already exists")
        staff.name = data["name"]
    if "role" in data:
        staff.role = data["role"]
    if "phone" in data:
        staff.phone = data["phone"]
    if "rate" in data:
        staff.rate = data["rate"]
    if "pricing_unit" in data:
        staff.pricing_unit = data["pricing_unit"]
    if "is_active" in data:
        staff.is_active = data["is_active"]
    staff.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "staff_member",
        staff.id,
        staff.name,
        "updated",
        current_user,
        f"Staff member '{staff.name}' updated",
    )
    db.commit()
    db.refresh(staff)
    return staff


@staff_router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    staff = _staff_base_query(db, org_id).filter(CateringStaffMember.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    now = datetime.now(timezone.utc)
    for assignment in db.query(CateringStaffAssignment).filter(
        CateringStaffAssignment.staff_id == staff_id,
        CateringStaffAssignment.organization_id == org_id,
        CateringStaffAssignment.deleted_at.is_(None),
    ).all():
        assignment.deleted_at = now
    staff.deleted_at = now
    staff.is_active = False
    staff.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "staff_member",
        staff.id,
        staff.name,
        "deleted",
        current_user,
        f"Staff member '{staff.name}' deleted",
    )
    db.commit()


# ---- staff assignments ----

@assignment_router.get("/", response_model=Page[CateringStaffAssignmentOut])
def list_assignments(
    booking_id: UUID | None = None,
    staff_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_ASSIGNMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _assignment_base_query(db, org_id)
    if booking_id:
        q = q.filter(CateringStaffAssignment.booking_id == booking_id)
    if staff_id:
        q = q.filter(CateringStaffAssignment.staff_id == staff_id)
    q = apply_search(q, search, ASSIGNMENT_SEARCH_COLS)
    q = apply_sort(q, sort, dir, ASSIGNMENT_SORT_MAP)
    return paginate(q, page, page_size)


@assignment_router.post("/", response_model=CateringStaffAssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: CateringStaffAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_ASSIGNMENT_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    get_booking(db, org_id, payload.booking_id)
    staff = db.query(CateringStaffMember).filter(
        CateringStaffMember.id == payload.staff_id,
        CateringStaffMember.organization_id == org_id,
        CateringStaffMember.deleted_at.is_(None),
    ).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    assignment = CateringStaffAssignment(
        **payload.model_dump(exclude_unset=True),
        organization_id=org_id,
        created_by=current_user.id,
    )
    db.add(assignment)
    db.flush()
    if assignment.role == "supervisor":
        booking = db.query(CateringBooking).filter(CateringBooking.id == payload.booking_id).first()
        if booking:
            booking.coordinator_name = staff.name
            booking.coordinator_contact = staff.phone
    log_audit(
        db,
        org_id,
        "staff_assignment",
        assignment.id,
        staff.name,
        "created",
        current_user,
        f"Staff member '{staff.name}' assigned to booking",
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@assignment_router.get("/{assignment_id}", response_model=CateringStaffAssignmentOut)
def get_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_ASSIGNMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    assignment = _assignment_base_query(db, org_id).filter(CateringStaffAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


@assignment_router.put("/{assignment_id}", response_model=CateringStaffAssignmentOut)
def update_assignment(
    assignment_id: UUID,
    payload: CateringStaffAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_ASSIGNMENT_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    assignment = _assignment_base_query(db, org_id).filter(CateringStaffAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    data = payload.model_dump(exclude_unset=True)
    if "staff_id" in data:
        staff = db.query(CateringStaffMember).filter(
            CateringStaffMember.id == data["staff_id"],
            CateringStaffMember.organization_id == org_id,
            CateringStaffMember.deleted_at.is_(None),
        ).first()
        if not staff:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
        assignment.staff_id = data["staff_id"]
    if "shift_start" in data:
        assignment.shift_start = data["shift_start"]
    if "shift_end" in data:
        assignment.shift_end = data["shift_end"]
    if "role" in data:
        assignment.role = data["role"]
    if "notes" in data:
        assignment.notes = data["notes"]
    if assignment.role == "supervisor":
        booking = db.query(CateringBooking).filter(CateringBooking.id == assignment.booking_id).first()
        if booking:
            resolved_staff = staff if "staff_id" in data else db.query(CateringStaffMember).filter(CateringStaffMember.id == assignment.staff_id).first()
            if resolved_staff:
                booking.coordinator_name = resolved_staff.name
                booking.coordinator_contact = resolved_staff.phone
    assignment.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "staff_assignment",
        assignment.id,
        getattr(assignment, "staff_name", None) or str(assignment.staff_id),
        "updated",
        current_user,
        "Staff assignment updated",
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@assignment_router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.STAFF_ASSIGNMENT_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    assignment = _assignment_base_query(db, org_id).filter(CateringStaffAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    assignment.deleted_at = datetime.now(timezone.utc)
    assignment.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "staff_assignment",
        assignment.id,
        getattr(assignment, "staff_name", None) or str(assignment.staff_id),
        "deleted",
        current_user,
        "Staff assignment removed",
    )
    db.commit()
