from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import decode_food_requirements, encode_food_requirements, generate_inquiry_short_reference, log_audit
from app.models.catering_models import (
    CateringInquiry,
    CateringInquiryItem,
    CateringMenuItem,
    CateringPackage,
    UserStub,
)
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringInquiryCreate,
    CateringInquiryDetailOut,
    CateringInquiryOut,
    CateringInquiryUpdate,
    InquiryItemIn,
    InquiryReviewRejectIn,
    Page,
    StaffingOut,
)

router = APIRouter(prefix="/inquiries", tags=["Inquiries"])

SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "customer_name": CateringInquiry.customer_name,
    "guests": CateringInquiry.guest_count,
    "guest_count": CateringInquiry.guest_count,
    "event_date": CateringInquiry.event_date,
    "status": CateringInquiry.status,
    "created_at": CateringInquiry.created_at,
}
SEARCH_COLS = [CateringInquiry.customer_name, CateringInquiry.customer_contact]


def _base_query(db: Session, org_id: UUID):
    return db.query(CateringInquiry).filter(
        CateringInquiry.organization_id == org_id,
        CateringInquiry.deleted_at.is_(None),
    )


def _validate_package(db: Session, org_id: UUID, package_id: UUID | None) -> UUID | None:
    if package_id is None:
        return None
    pkg = db.query(CateringPackage).filter(
        CateringPackage.id == package_id,
        CateringPackage.organization_id == org_id,
        CateringPackage.deleted_at.is_(None),
        CateringPackage.is_active.is_(True),
    ).first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or inactive package")
    return package_id


def _enforce_package_pax_range(db: Session, org_id: UUID, package_id: UUID | None, guest_count: int) -> None:
    """Reject if guest_count falls outside the package's min_pax/max_pax range."""
    if package_id is None:
        return
    pkg = db.query(CateringPackage).filter(
        CateringPackage.id == package_id,
        CateringPackage.organization_id == org_id,
        CateringPackage.deleted_at.is_(None),
    ).first()
    if not pkg:
        return
    if pkg.min_pax and guest_count < pkg.min_pax:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{pkg.name} requires at least {pkg.min_pax} guests; you entered {guest_count}.",
        )
    if pkg.max_pax and guest_count > pkg.max_pax:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{pkg.name} supports at most {pkg.max_pax} guests; you entered {guest_count}.",
        )


def _snapshot_items(db: Session, org_id: UUID, inquiry: CateringInquiry, items: list[InquiryItemIn], user_id: UUID | None) -> None:
    if not items:
        inquiry.items.clear()
        db.flush()
        return
    ids = {i.menu_item_id for i in items}
    menu_items = (
        db.query(CateringMenuItem)
        .filter(CateringMenuItem.organization_id == org_id, CateringMenuItem.id.in_(ids), CateringMenuItem.deleted_at.is_(None))
        .all()
    )
    by_id = {it.id: it for it in menu_items}
    for i in items:
        mi = by_id.get(i.menu_item_id)
        if mi is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown dish: {i.menu_item_id}")
    inquiry.items.clear()
    db.flush()
    for idx, i in enumerate(sorted(items, key=lambda x: (x.sort_order, x.item_name))):
        mi = by_id[i.menu_item_id]
        inquiry.items.append(
            CateringInquiryItem(
                organization_id=org_id,
                menu_item_id=mi.id,
                item_name=i.item_name or mi.name,
                category=i.category or mi.category,
                group_name=i.group_name,
                kind=i.kind,
                quantity=i.quantity,
                unit=i.unit,
                sort_order=i.sort_order or idx,
                created_by=user_id,
            )
        )
    db.flush()


def _apply_staff_counts(inquiry: CateringInquiry, staff: Any | None) -> None:
    inquiry.waiter_count = staff.waiter_count if staff else 0
    inquiry.bartender_count = staff.bartender_count if staff else 0
    inquiry.chef_count = staff.chef_count if staff else 0
    inquiry.kitchen_staff_count = staff.kitchen_staff_count if staff else 0
    inquiry.support_crew_count = staff.support_crew_count if staff else 0


def _to_detail_out(db: Session, org_id: UUID, inquiry: CateringInquiry) -> CateringInquiryDetailOut:
    out = CateringInquiryDetailOut.model_validate(inquiry)
    out.food_requirements = decode_food_requirements(inquiry.food_requirements_json)
    out.items = inquiry.items
    out.staffing = StaffingOut(
        waiter_count=inquiry.waiter_count,
        bartender_count=inquiry.bartender_count,
        chef_count=inquiry.chef_count,
        kitchen_staff_count=inquiry.kitchen_staff_count,
        support_crew_count=inquiry.support_crew_count,
    )
    return out


@router.get("/", response_model=Page[CateringInquiryOut])
def list_inquiries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    q = q.filter(CateringInquiry.review_status != "pending_review")
    q = apply_status(q, status, CateringInquiry.status)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    return paginate(q, page, page_size)


@router.post("/", response_model=CateringInquiryOut, status_code=status.HTTP_201_CREATED)
def create_inquiry(
    payload: CateringInquiryCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = CateringInquiry(
        organization_id=org_id,
        customer_name=payload.customer_name,
        customer_contact=payload.customer_contact,
        event_date=payload.event_date,
        event_time=payload.event_time,
        event_type=payload.event_type,
        event_address=payload.event_address,
        venue_name=payload.venue_name,
        location_floor=payload.location_floor,
        room_hall=payload.room_hall,
        landmark=payload.landmark,
        delivery_instructions=payload.delivery_instructions,
        guest_count=payload.guest_count,
        catering_package_id=_validate_package(db, org_id, payload.catering_package_id),
        package_mode=payload.package_mode,
        food_requirements_json=encode_food_requirements(payload.food_requirements),
        notes=payload.notes,
        additional_notes=payload.additional_notes,
        dietary_notes=payload.dietary_notes,
        setup_notes=payload.setup_notes,
        short_reference=generate_inquiry_short_reference(db, payload.event_date),
        status="new",
        created_by=current_user.id,
    )
    _enforce_package_pax_range(db, org_id, payload.catering_package_id, payload.guest_count)
    _apply_staff_counts(inquiry, payload.staff)
    db.add(inquiry)
    db.flush()
    _snapshot_items(db, org_id, inquiry, payload.items, current_user.id)
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        inquiry.customer_name,
        "created",
        current_user,
        f"Inquiry created for {inquiry.customer_name} ({inquiry.guest_count} guests)",
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


def _get_pending_review_query(db: Session, org_id: UUID):
    return (
        db.query(CateringInquiry)
        .filter(
            CateringInquiry.organization_id == org_id,
            CateringInquiry.deleted_at.is_(None),
            CateringInquiry.review_status == "pending_review",
        )
    )


@router.get("/pending-review", response_model=Page[CateringInquiryOut])
def list_pending_review_inquiries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    """Customer inquiries held for staff review (staff and above)."""
    q = _get_pending_review_query(db, org_id).order_by(CateringInquiry.event_date.asc())
    return paginate(q, page, page_size)


@router.post("/{inquiry_id}/approve-review", response_model=CateringInquiryOut)
def approve_inquiry_review(
    inquiry_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    """Release a held inquiry into the normal quotation flow."""
    inquiry = _base_query(db, org_id).filter(CateringInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    if inquiry.review_status != "pending_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry is not pending review")
    inquiry.review_status = "approved"
    inquiry.review_reason = None
    inquiry.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        inquiry.customer_name,
        "review_approved",
        current_user,
        f"Inquiry for {inquiry.customer_name} approved for review",
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.post("/{inquiry_id}/reject-review", response_model=CateringInquiryOut)
def reject_inquiry_review(
    inquiry_id: UUID,
    payload: InquiryReviewRejectIn,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    """Decline a held inquiry; the customer sees a distinct declined message."""
    inquiry = _base_query(db, org_id).filter(CateringInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    if inquiry.review_status != "pending_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry is not pending review")
    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A reason is required to reject an inquiry")
    inquiry.review_status = "rejected"
    inquiry.review_reason = reason
    inquiry.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        inquiry.customer_name,
        "review_rejected",
        current_user,
        f"Inquiry for {inquiry.customer_name} rejected during review",
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.get("/{inquiry_id}", response_model=CateringInquiryOut)
def get_inquiry(
    inquiry_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = _base_query(db, org_id).filter(CateringInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    return inquiry


@router.get("/{inquiry_id}/detail", response_model=CateringInquiryDetailOut)
def get_inquiry_detail(
    inquiry_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = _base_query(db, org_id).filter(CateringInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    return _to_detail_out(db, org_id, inquiry)


@router.put("/{inquiry_id}", response_model=CateringInquiryOut)
def update_inquiry(
    inquiry_id: UUID,
    payload: CateringInquiryUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = _base_query(db, org_id).filter(CateringInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "customer_name" in update_data:
        inquiry.customer_name = update_data["customer_name"]
    if "customer_contact" in update_data:
        inquiry.customer_contact = update_data["customer_contact"]
    if "event_date" in update_data:
        inquiry.event_date = update_data["event_date"]
    if "event_time" in update_data:
        inquiry.event_time = update_data["event_time"]
    if "event_type" in update_data:
        inquiry.event_type = update_data["event_type"]
    if "event_address" in update_data:
        inquiry.event_address = update_data["event_address"]
    if "venue_name" in update_data:
        inquiry.venue_name = update_data["venue_name"]
    if "location_floor" in update_data:
        inquiry.location_floor = update_data["location_floor"]
    if "room_hall" in update_data:
        inquiry.room_hall = update_data["room_hall"]
    if "landmark" in update_data:
        inquiry.landmark = update_data["landmark"]
    if "delivery_instructions" in update_data:
        inquiry.delivery_instructions = update_data["delivery_instructions"]
    if "guest_count" in update_data:
        inquiry.guest_count = update_data["guest_count"]
    if "catering_package_id" in update_data:
        inquiry.catering_package_id = _validate_package(db, org_id, update_data["catering_package_id"])
    if "package_mode" in update_data:
        inquiry.package_mode = update_data["package_mode"]
    if "food_requirements" in update_data:
        inquiry.food_requirements_json = encode_food_requirements(update_data["food_requirements"])
    if "staff" in update_data:
        _apply_staff_counts(inquiry, update_data["staff"])
    if "items" in update_data:
        _snapshot_items(db, org_id, inquiry, update_data["items"], current_user.id)
    if "notes" in update_data:
        inquiry.notes = update_data["notes"]
    if "additional_notes" in update_data:
        inquiry.additional_notes = update_data["additional_notes"]
    if "dietary_notes" in update_data:
        inquiry.dietary_notes = update_data["dietary_notes"]
    if "setup_notes" in update_data:
        inquiry.setup_notes = update_data["setup_notes"]
    _enforce_package_pax_range(db, org_id, inquiry.catering_package_id, inquiry.guest_count)
    inquiry.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        inquiry.customer_name,
        "updated",
        current_user,
        f"Inquiry for {inquiry.customer_name} updated",
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.delete("/{inquiry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inquiry(
    inquiry_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.INQUIRY_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    from app.models.catering_models import CateringQuotation

    inquiry = _base_query(db, org_id).filter(CateringInquiry.id == inquiry_id).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    now = datetime.now(timezone.utc)
    for quotation in inquiry.quotations:
        quotation.deleted_at = now
    inquiry.deleted_at = now
    inquiry.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        inquiry.customer_name,
        "deleted",
        current_user,
        f"Inquiry for {inquiry.customer_name} deleted",
    )
    db.commit()
