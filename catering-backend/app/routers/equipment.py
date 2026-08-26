from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.booking_scoped import base_query, get_booking
from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringEquipment, CateringEquipmentAssignment, CateringInquiry, UserStub
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringEquipmentAssignmentCreate,
    CateringEquipmentAssignmentOut,
    CateringEquipmentAssignmentUpdate,
    CateringEquipmentCreate,
    CateringEquipmentOut,
    CateringEquipmentUpdate,
    Page,
)

equipment_router = APIRouter(prefix="/equipment", tags=["Equipment"])
assignment_router = APIRouter(prefix="/equipment-assignments", tags=["Equipment"])

EQUIPMENT_SORT_MAP = {
    "name": CateringEquipment.name,
    "category": CateringEquipment.category,
    "quantity": CateringEquipment.quantity,
    "unit_cost": CateringEquipment.unit_cost,
    "created_at": CateringEquipment.created_at,
}
EQUIPMENT_SEARCH_COLS = [CateringEquipment.name]

ASSIGNMENT_SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "equipment_name": CateringEquipment.name,
    "quantity": CateringEquipmentAssignment.quantity,
    "created_at": CateringEquipmentAssignment.created_at,
}
ASSIGNMENT_SEARCH_COLS = [CateringInquiry.customer_name, CateringEquipment.name]


def _equipment_base_query(db: Session, org_id: UUID):
    return db.query(CateringEquipment).filter(
        CateringEquipment.organization_id == org_id,
        CateringEquipment.deleted_at.is_(None),
    )


def _assignment_base_query(db: Session, org_id: UUID):
    q = base_query(db, CateringEquipmentAssignment, org_id)
    return q.options(joinedload(CateringEquipmentAssignment.equipment))


# ---- equipment ----

@equipment_router.get("/", response_model=Page[CateringEquipmentOut])
def list_equipment(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _equipment_base_query(db, org_id)
    if status:
        q = q.filter(CateringEquipment.category == status)
    q = apply_search(q, search, EQUIPMENT_SEARCH_COLS)
    q = apply_sort(q, sort, dir, EQUIPMENT_SORT_MAP)
    return paginate(q, page, page_size)


@equipment_router.post("/", response_model=CateringEquipmentOut, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: CateringEquipmentCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    existing = db.query(CateringEquipment).filter(
        CateringEquipment.organization_id == org_id,
        CateringEquipment.name == payload.name,
        CateringEquipment.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Equipment with this name already exists")
    equipment = CateringEquipment(
        **payload.model_dump(exclude_unset=True),
        organization_id=org_id,
        created_by=current_user.id,
    )
    db.add(equipment)
    db.flush()
    log_audit(
        db,
        org_id,
        "equipment",
        equipment.id,
        equipment.name,
        "created",
        current_user,
        f"Equipment '{equipment.name}' created",
    )
    db.commit()
    db.refresh(equipment)
    return equipment


@equipment_router.get("/{equipment_id}", response_model=CateringEquipmentOut)
def get_equipment(
    equipment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    equipment = _equipment_base_query(db, org_id).filter(CateringEquipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return equipment


@equipment_router.put("/{equipment_id}", response_model=CateringEquipmentOut)
def update_equipment(
    equipment_id: UUID,
    payload: CateringEquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    equipment = _equipment_base_query(db, org_id).filter(CateringEquipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        existing = db.query(CateringEquipment).filter(
            CateringEquipment.organization_id == org_id,
            CateringEquipment.name == data["name"],
            CateringEquipment.id != equipment_id,
            CateringEquipment.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Equipment with this name already exists")
        equipment.name = data["name"]
    if "category" in data:
        equipment.category = data["category"]
    if "quantity" in data:
        equipment.quantity = data["quantity"]
    if "unit_cost" in data:
        equipment.unit_cost = data["unit_cost"]
    if "pricing_unit" in data:
        equipment.pricing_unit = data["pricing_unit"]
    if "is_active" in data:
        equipment.is_active = data["is_active"]
    equipment.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "equipment",
        equipment.id,
        equipment.name,
        "updated",
        current_user,
        f"Equipment '{equipment.name}' updated",
    )
    db.commit()
    db.refresh(equipment)
    return equipment


@equipment_router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    equipment = _equipment_base_query(db, org_id).filter(CateringEquipment.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    now = datetime.now(timezone.utc)
    for assignment in db.query(CateringEquipmentAssignment).filter(
        CateringEquipmentAssignment.equipment_id == equipment_id,
        CateringEquipmentAssignment.organization_id == org_id,
        CateringEquipmentAssignment.deleted_at.is_(None),
    ).all():
        assignment.deleted_at = now
    equipment.deleted_at = now
    equipment.is_active = False
    equipment.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "equipment",
        equipment.id,
        equipment.name,
        "deleted",
        current_user,
        f"Equipment '{equipment.name}' deleted",
    )
    db.commit()


# ---- equipment assignments ----

@assignment_router.get("/", response_model=Page[CateringEquipmentAssignmentOut])
def list_assignments(
    booking_id: UUID | None = None,
    equipment_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_ASSIGNMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _assignment_base_query(db, org_id)
    if booking_id:
        q = q.filter(CateringEquipmentAssignment.booking_id == booking_id)
    if equipment_id:
        q = q.filter(CateringEquipmentAssignment.equipment_id == equipment_id)
    q = apply_search(q, search, ASSIGNMENT_SEARCH_COLS)
    q = apply_sort(q, sort, dir, ASSIGNMENT_SORT_MAP)
    return paginate(q, page, page_size)


@assignment_router.post("/", response_model=CateringEquipmentAssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: CateringEquipmentAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_ASSIGNMENT_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    get_booking(db, org_id, payload.booking_id)
    equipment = db.query(CateringEquipment).filter(
        CateringEquipment.id == payload.equipment_id,
        CateringEquipment.organization_id == org_id,
        CateringEquipment.deleted_at.is_(None),
    ).first()
    if not equipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    assignment = CateringEquipmentAssignment(
        **payload.model_dump(exclude_unset=True),
        organization_id=org_id,
        created_by=current_user.id,
    )
    db.add(assignment)
    db.flush()
    log_audit(
        db,
        org_id,
        "equipment_assignment",
        assignment.id,
        equipment.name,
        "created",
        current_user,
        f"Equipment '{equipment.name}' assigned to booking",
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@assignment_router.get("/{assignment_id}", response_model=CateringEquipmentAssignmentOut)
def get_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_ASSIGNMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    assignment = _assignment_base_query(db, org_id).filter(CateringEquipmentAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


@assignment_router.put("/{assignment_id}", response_model=CateringEquipmentAssignmentOut)
def update_assignment(
    assignment_id: UUID,
    payload: CateringEquipmentAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_ASSIGNMENT_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    assignment = _assignment_base_query(db, org_id).filter(CateringEquipmentAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    data = payload.model_dump(exclude_unset=True)
    if "equipment_id" in data:
        equipment = db.query(CateringEquipment).filter(
            CateringEquipment.id == data["equipment_id"],
            CateringEquipment.organization_id == org_id,
            CateringEquipment.deleted_at.is_(None),
        ).first()
        if not equipment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
        assignment.equipment_id = data["equipment_id"]
    if "quantity" in data:
        assignment.quantity = data["quantity"]
    if "notes" in data:
        assignment.notes = data["notes"]
    assignment.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "equipment_assignment",
        assignment.id,
        getattr(assignment, "equipment_name", None) or str(assignment.equipment_id),
        "updated",
        current_user,
        "Equipment assignment updated",
    )
    db.commit()
    db.refresh(assignment)
    return assignment


@assignment_router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.EQUIPMENT_ASSIGNMENT_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    assignment = _assignment_base_query(db, org_id).filter(CateringEquipmentAssignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    assignment.deleted_at = datetime.now(timezone.utc)
    assignment.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "equipment_assignment",
        assignment.id,
        getattr(assignment, "equipment_name", None) or str(assignment.equipment_id),
        "deleted",
        current_user,
        "Equipment assignment removed",
    )
    db.commit()
