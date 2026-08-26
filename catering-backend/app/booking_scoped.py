"""Shared helpers and a CRUD factory for booking-scoped resources.

Booking-scoped resources (guest counts, food requirements, deliveries,
payments, ...) all live under a booking and share the same shape:
list with booking filter / search / status / sort / pagination,
plus create / get / update / soft-delete.
"""
from datetime import datetime, timezone
from typing import Callable, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user
from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringBooking, CateringInquiry, CateringQuotation, UserStub
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import require_permission
from app.schemas.catering_schemas import Page


_AUDIT_ENTITY_TYPE = {
    "CateringGuestCount": "guest_count",
    "CateringFoodRequirement": "food_requirement",
    "CateringPayment": "payment",
    "CateringStaffAssignment": "staff_assignment",
    "CateringEquipmentAssignment": "equipment_assignment",
}
_AUDIT_CREATE_ACTION = {
    "CateringPayment": "payment recorded",
}


def _audit_entity_type(model) -> str:
    return _AUDIT_ENTITY_TYPE.get(model.__name__, model.__name__.lower())


def _audit_create_action(model) -> str:
    return _AUDIT_CREATE_ACTION.get(model.__name__, "created")


def _audit_reference(record) -> str:
    cls = type(record).__name__
    if cls == "CateringGuestCount":
        return f"{record.count} guests ({record.count_type})"
    if cls == "CateringFoodRequirement":
        return (record.description or "")[:160]
    if cls == "CateringPayment":
        return f"{record.reference or record.method} {record.amount}"
    if cls == "CateringStaffAssignment":
        return getattr(record, "staff_name", None) or str(record.staff_id)
    if cls == "CateringEquipmentAssignment":
        return getattr(record, "equipment_name", None) or str(record.equipment_id)
    return str(record.id)


def _audit_summary(record, action: str) -> str:
    cls = type(record).__name__
    if cls == "CateringPayment":
        return f"Payment of \u20b1{record.amount} via {record.method or 'cash'} {action}"
    if cls == "CateringGuestCount":
        return f"{record.count} guests ({record.count_type}) {action}"
    if cls == "CateringFoodRequirement":
        return f"Food requirement {action}"
    if cls == "CateringStaffAssignment":
        return f"Staff assignment {action}"
    if cls == "CateringEquipmentAssignment":
        return f"Equipment assignment {action}"
    return f"Record {action}"


def base_query(db: Session, model, org_id: UUID):
    """Query a booking-scoped model joined to its booking -> quotation -> inquiry."""
    q = db.query(model).join(CateringBooking, CateringBooking.id == model.booking_id)
    q = q.join(CateringQuotation, CateringQuotation.id == CateringBooking.quotation_id)
    q = q.join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
    return q.filter(
        model.organization_id == org_id,
        model.deleted_at.is_(None),
        CateringBooking.organization_id == org_id,
        CateringBooking.deleted_at.is_(None),
        CateringQuotation.deleted_at.is_(None),
        CateringInquiry.deleted_at.is_(None),
    )


def get_booking(db: Session, org_id: UUID, booking_id: UUID) -> CateringBooking:
    booking = db.query(CateringBooking).filter(
        CateringBooking.id == booking_id,
        CateringBooking.organization_id == org_id,
        CateringBooking.deleted_at.is_(None),
    ).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


AfterWrite = Callable[[Session, UUID, UUID], None]


def make_booking_router(
    *,
    prefix: str,
    tag: str,
    model,
    create_schema,
    update_schema,
    out_schema,
    search_columns: list,
    sort_map: dict,
    status_column=None,
    after_write: AfterWrite | None = None,
    perm_view: str,
    perm_create: str,
    perm_update: str,
    perm_delete: str,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("/", response_model=Page[out_schema])
    def list_records(
        booking_id: UUID | None = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=500),
        search: str | None = Query(None, max_length=200),
        status: str | None = Query(None),
        sort: str | None = Query(None),
        dir: Literal["asc", "desc"] = Query("asc"),
        db: Session = Depends(get_db),
        current_user: UserStub = Depends(require_permission(perm_view)),
        org_id: UUID = Depends(get_org_id),
    ):
        q = base_query(db, model, org_id)
        if booking_id:
            q = q.filter(model.booking_id == booking_id)
        if status_column and status:
            q = apply_status(q, status, status_column)
        q = apply_search(q, search, search_columns)
        q = apply_sort(q, sort, dir, sort_map)
        return paginate(q, page, page_size)

    @router.post("/", response_model=out_schema, status_code=status.HTTP_201_CREATED)
    def create_record(
        payload: create_schema,
        db: Session = Depends(get_db),
        current_user: UserStub = Depends(require_permission(perm_create)),
        org_id: UUID = Depends(get_org_id),
    ):
        get_booking(db, org_id, payload.booking_id)
        data = payload.model_dump(exclude_unset=True)
        record = model(**data, organization_id=org_id, created_by=current_user.id)
        db.add(record)
        db.flush()
        log_audit(
            db,
            org_id,
            _audit_entity_type(model),
            record.id,
            _audit_reference(record),
            _audit_create_action(model),
            current_user,
            _audit_summary(record, _audit_create_action(model)),
        )
        db.commit()
        db.refresh(record)
        if after_write:
            after_write(db, org_id, record.booking_id)
        return record

    @router.get("/{record_id}", response_model=out_schema)
    def get_record(
        record_id: UUID,
        db: Session = Depends(get_db),
        current_user: UserStub = Depends(require_permission(perm_view)),
        org_id: UUID = Depends(get_org_id),
    ):
        record = base_query(db, model, org_id).filter(model.id == record_id).first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        return record

    @router.put("/{record_id}", response_model=out_schema)
    def update_record(
        record_id: UUID,
        payload: update_schema,
        db: Session = Depends(get_db),
        current_user: UserStub = Depends(require_permission(perm_update)),
        org_id: UUID = Depends(get_org_id),
    ):
        record = base_query(db, model, org_id).filter(model.id == record_id).first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        data = payload.model_dump(exclude_unset=True)
        if "booking_id" in data and data["booking_id"] != record.booking_id:
            get_booking(db, org_id, data["booking_id"])
        for key, value in data.items():
            setattr(record, key, value)
        record.updated_by = current_user.id
        log_audit(
            db,
            org_id,
            _audit_entity_type(model),
            record.id,
            _audit_reference(record),
            "updated",
            current_user,
            _audit_summary(record, "updated"),
        )
        db.commit()
        db.refresh(record)
        if after_write:
            after_write(db, org_id, record.booking_id)
        return record

    @router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_record(
        record_id: UUID,
        db: Session = Depends(get_db),
        current_user: UserStub = Depends(require_permission(perm_delete)),
        org_id: UUID = Depends(get_org_id),
    ):
        record = base_query(db, model, org_id).filter(model.id == record_id).first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        booking_id = record.booking_id
        record.deleted_at = datetime.now(timezone.utc)
        record.updated_by = current_user.id
        log_audit(
            db,
            org_id,
            _audit_entity_type(model),
            record.id,
            _audit_reference(record),
            "deleted",
            current_user,
            _audit_summary(record, "deleted"),
        )
        db.commit()
        if after_write:
            after_write(db, org_id, booking_id)

    return router
