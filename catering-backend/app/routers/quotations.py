from datetime import datetime, timezone
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import booking_out, decode_food_requirements, format_event_location, generate_booking_requirements, inquiry_reference, log_audit, suggested_price, _price_catalog_ids
from app.models.catering_models import (
    CateringInquiry,
    CateringQuotation,
    CateringBooking,
    CateringPackage,
    CateringEquipment,
    CateringEquipmentAssignment,
    UserStub,
)
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringQuotationCreate,
    CateringQuotationDetailOut,
    CateringQuotationFromInquiryIn,
    CateringQuotationOut,
    CateringQuotationPrefillOut,
    CateringQuotationUpdate,
    CateringBookingOut,
    Page,
    StaffingOut,
)

router = APIRouter(prefix="/quotations", tags=["Quotations"])

SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "amount": CateringQuotation.total_price,
    "total_price": CateringQuotation.total_price,
    "guests": CateringQuotation.guest_count,
    "guest_count": CateringQuotation.guest_count,
    "status": CateringQuotation.status,
    "valid_until": CateringQuotation.valid_until,
    "created_at": CateringQuotation.created_at,
}
SEARCH_COLS = [CateringInquiry.customer_name]


def _quotation_total_with_addons(db: Session, org_id: UUID, pkg, guest_count: int, inquiry: CateringInquiry) -> float:
    """Compute quotation total = base package price + add-on extras."""
    base = suggested_price(pkg, guest_count)
    addon_rows = [i for i in inquiry.items if getattr(i, "kind", "") == "addon" and i.catalog_item_id]
    if not addon_rows:
        return base
    addon_total, _ = _price_catalog_ids(
        db, org_id,
        [i.catalog_item_id for i in addon_rows],
        guest_count,
        quantities={str(i.catalog_item_id): (i.quantity or 1) for i in addon_rows},
    )
    return round(base + addon_total, 2)


def _base_query(db: Session, org_id: UUID):
    return (
        db.query(CateringQuotation)
        .join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
        .filter(
            CateringQuotation.organization_id == org_id,
            CateringQuotation.deleted_at.is_(None),
            CateringInquiry.deleted_at.is_(None),
        )
    )


def _collect_customer_equipment_selections(db: Session, org_id: UUID, inquiry: CateringInquiry) -> dict:
    """Collect customer-selected equipment from both inquiry storage sources.

    One normalized reader for the unified accept-time copy pass:
      - Source A: CateringInquiryItem rows with kind='addon' and
        category='equipment' (premade-package add-ons).
      - Source B: inquiry.selected_catalog_ids JSON (pure custom-mode picks;
        non-equipment ids are dropped by the equipment-table filter below).

    Returns {CateringEquipment.id: quantity} for active catalog rows only.
    """
    selections: dict[str, int] = {}
    for item in inquiry.items:
        if item.kind == "addon" and item.category == "equipment" and item.catalog_item_id:
            key = str(item.catalog_item_id)
            selections[key] = max(selections.get(key, 0), item.quantity or 1)

    raw_ids: list = []
    if inquiry.selected_catalog_ids:
        # Stored as TEXT but written from a Python list, which psycopg2 binds
        # as a Postgres array literal ({id,id}); older rows may be JSON.
        raw = str(inquiry.selected_catalog_ids).strip()
        parsed = None
        try:
            parsed = json.loads(raw)
        except ValueError:
            pass
        if isinstance(parsed, list):
            raw_ids = parsed
        elif raw.startswith("{") and raw.endswith("}"):
            inner = raw[1:-1].strip()
            raw_ids = [p.strip().strip('"').strip("'") for p in inner.split(",")] if inner else []
    for sid in raw_ids or []:
        selections.setdefault(str(sid), 1)

    if not selections:
        return {}
    rows = db.query(CateringEquipment.id).filter(
        CateringEquipment.organization_id == org_id,
        CateringEquipment.id.in_([UUID(k) for k in selections]),
        CateringEquipment.deleted_at.is_(None),
        CateringEquipment.is_active.is_(True),
    ).all()
    return {row.id: selections[str(row.id)] for row in rows}


def _apply_equipment_selections(db: Session, org_id: UUID, booking: CateringBooking, equipment_qty: dict, actor) -> int:
    """Create CateringEquipmentAssignment rows for customer-selected equipment.

    Idempotent: skips equipment already assigned to the booking. Staff picks
    are informational only (coordinator assigns real people later), so nothing
    is written for them here. Returns number of assignments created.
    """
    if not equipment_qty:
        return 0
    existing = {
        a.equipment_id
        for a in db.query(CateringEquipmentAssignment).filter(
            CateringEquipmentAssignment.booking_id == booking.id,
            CateringEquipmentAssignment.organization_id == org_id,
            CateringEquipmentAssignment.deleted_at.is_(None),
        ).all()
    }
    created = 0
    for eq_id, qty in equipment_qty.items():
        if eq_id in existing:
            continue
        db.add(CateringEquipmentAssignment(
            organization_id=org_id,
            booking_id=booking.id,
            equipment_id=eq_id,
            quantity=max(1, int(qty)),
            notes="Auto-added from customer selections at quotation acceptance",
            created_by=actor.id if actor is not None else None,
        ))
        created += 1
    return created


def perform_accept(db: Session, quotation: CateringQuotation, org_id: UUID, actor, actor_role: str | None = None, version: str | None = None) -> CateringBooking:
    """Accept a quotation and create the booking (shared business logic).

    Used by both the internal (manager) endpoint and the public customer
    portal so acceptance always follows the same workflow and the booking is
    created exactly once by the backend. ``actor`` is a ``UserStub`` (internal)
    or ``None`` for customer actions; ``actor_role`` labels the actor.
    """
    if quotation.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot accept quotation with status '{quotation.status}'")
    if quotation.valid_until is not None and quotation.valid_until < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quotation has expired")

    if version is not None:
        server_version = quotation.updated_at.isoformat() if quotation.updated_at else ""
        if server_version != version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This quotation has been modified since you last loaded it. Please refresh and review the changes before accepting.",
            )

    inquiry = db.query(CateringInquiry).filter(
        CateringInquiry.id == quotation.inquiry_id,
    ).with_for_update().first()

    existing_booking = db.query(CateringBooking).filter(
        CateringBooking.quotation_id == quotation.id,
    ).first()
    if existing_booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quotation already has a booking")

    # Resolve service_style: customer override first, then inquiry-level
    # (package default set at submit), then package as final fallback.
    service_style = getattr(inquiry, "requested_service_style", None) or getattr(inquiry, "service_style", None)
    if not service_style and inquiry.catering_package_id:
        pkg = db.query(CateringPackage).filter(
            CateringPackage.id == inquiry.catering_package_id,
            CateringPackage.organization_id == org_id,
        ).first()
        service_style = getattr(pkg, "service_style", None) if pkg else None

    booking = CateringBooking(
        organization_id=org_id,
        quotation_id=quotation.id,
        event_date=inquiry.event_date,
        event_location=format_event_location(
            inquiry.event_address,
            inquiry.venue_name,
            inquiry.location_floor,
            inquiry.room_hall,
            inquiry.landmark,
            inquiry.delivery_instructions,
        ),
        event_time=inquiry.event_time,
        guest_count=quotation.guest_count,
        total_amount=quotation.total_price,
        payment_status="unpaid",
        status="pending",
        service_style=service_style,
        event_duration_hours=inquiry.event_duration_hours,
        selected_venue_id=inquiry.selected_venue_id,
        additional_notes=inquiry.additional_notes,
        dietary_notes=inquiry.dietary_notes,
        setup_notes=inquiry.setup_notes,
        created_by=actor.id if actor is not None else None,
    )
    db.add(booking)
    db.flush()

    equipment_picks = _collect_customer_equipment_selections(db, org_id, inquiry)
    equipment_copied = _apply_equipment_selections(db, org_id, booking, equipment_picks, actor)
    requirements_created = generate_booking_requirements(db, org_id, booking, inquiry, equipment_picks)

    quotation.status = "accepted"
    inquiry.status = "converted"
    customer_name = inquiry.customer_name
    log_audit(
        db,
        org_id,
        "quotation",
        quotation.id,
        customer_name,
        "accepted",
        actor,
        f"Quotation accepted for {customer_name}",
        actor_role=actor_role,
    )
    log_audit(
        db,
        org_id,
        "booking",
        booking.id,
        customer_name,
        "created",
        actor,
        f"Booking created for {customer_name}",
        actor_role=actor_role,
    )
    if equipment_copied:
        log_audit(
            db,
            org_id,
            "booking",
            booking.id,
            customer_name,
            "equipment_added_from_inquiry",
            actor,
            f"Auto-copied {equipment_copied} equipment item(s) from customer selections",
            actor_role=actor_role,
        )
    db.commit()
    db.refresh(booking)
    return booking


def perform_reject(db: Session, quotation: CateringQuotation, actor, actor_role: str | None = None) -> CateringQuotation:
    """Reject a quotation and close the inquiry when no other quotation is open."""
    if quotation.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot reject quotation with status '{quotation.status}'")

    quotation.status = "rejected"
    quotation.updated_by = actor.id if actor is not None else None

    inquiry = db.query(CateringInquiry).filter(
        CateringInquiry.id == quotation.inquiry_id,
    ).first()
    customer_name = inquiry.customer_name if inquiry else str(quotation.id)[:8]
    reject_org_id = inquiry.organization_id if inquiry else None

    open_quotations = db.query(CateringQuotation).filter(
        CateringQuotation.inquiry_id == quotation.inquiry_id,
        CateringQuotation.id != quotation.id,
        CateringQuotation.deleted_at.is_(None),
        CateringQuotation.status.in_(["draft", "sent"]),
    ).count()
    if open_quotations == 0:
        if inquiry and inquiry.status != "converted":
            inquiry.status = "closed"
            inquiry.updated_by = actor.id if actor is not None else None

    log_audit(
        db,
        reject_org_id,
        "quotation",
        quotation.id,
        customer_name,
        "rejected",
        actor,
        f"Quotation for {customer_name} rejected",
        actor_role=actor_role,
    )
    db.commit()
    db.refresh(quotation)
    return quotation


def _load_package(db: Session, org_id: UUID, package_id: UUID | None) -> CateringPackage | None:
    if package_id is None:
        return None
    return (
        db.query(CateringPackage)
        .filter(CateringPackage.id == package_id, CateringPackage.organization_id == org_id, CateringPackage.deleted_at.is_(None))
        .first()
    )


def _to_quotation_detail(db: Session, org_id: UUID, quotation: CateringQuotation) -> CateringQuotationDetailOut:
    inquiry = db.query(CateringInquiry).filter(CateringInquiry.id == quotation.inquiry_id).first()
    pkg = _load_package(db, org_id, quotation.catering_package_id)
    out = CateringQuotationDetailOut.model_validate(quotation)
    out.package_name = pkg.name if pkg else None
    out.package_mode = inquiry.package_mode if inquiry else None
    out.pricing_method = pkg.pricing_method if pkg else None
    out.base_price = pkg.base_price if pkg else None
    if inquiry:
        out.customer_name = inquiry.customer_name
        out.customer_contact = inquiry.customer_contact
        out.event_date = inquiry.event_date
        out.event_time = inquiry.event_time
        out.event_type = inquiry.event_type
        out.event_address = inquiry.event_address
        out.venue_name = inquiry.venue_name
        out.location_floor = inquiry.location_floor
        out.room_hall = inquiry.room_hall
        out.landmark = inquiry.landmark
        out.delivery_instructions = inquiry.delivery_instructions
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


@router.get("/from-inquiry/{inquiry_id}", response_model=CateringQuotationPrefillOut)
def prefill_quotation_from_inquiry(
    inquiry_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = (
        db.query(CateringInquiry)
        .filter(CateringInquiry.id == inquiry_id, CateringInquiry.organization_id == org_id, CateringInquiry.deleted_at.is_(None))
        .first()
    )
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    pkg = _load_package(db, org_id, inquiry.catering_package_id)
    return CateringQuotationPrefillOut(
        inquiry_id=inquiry.id,
        inquiry_status=inquiry.status,
        customer_name=inquiry.customer_name,
        customer_contact=inquiry.customer_contact,
        event_date=inquiry.event_date,
        event_time=inquiry.event_time,
        event_type=inquiry.event_type,
        event_address=inquiry.event_address,
        venue_name=inquiry.venue_name,
        location_floor=inquiry.location_floor,
        room_hall=inquiry.room_hall,
        landmark=inquiry.landmark,
        delivery_instructions=inquiry.delivery_instructions,
        guest_count=inquiry.guest_count,
        catering_package_id=inquiry.catering_package_id,
        package_name=pkg.name if pkg else None,
        package_mode=inquiry.package_mode,
        pricing_method=pkg.pricing_method if pkg else None,
        base_price=pkg.base_price if pkg else None,
        suggested_total=_quotation_total_with_addons(db, org_id, pkg, inquiry.guest_count, inquiry),
        food_requirements=decode_food_requirements(inquiry.food_requirements_json),
        items=inquiry.items,
        staffing=StaffingOut(
            waiter_count=inquiry.waiter_count,
            bartender_count=inquiry.bartender_count,
            chef_count=inquiry.chef_count,
            kitchen_staff_count=inquiry.kitchen_staff_count,
            support_crew_count=inquiry.support_crew_count,
        ),
        flag_note=inquiry.flag_note,
        notes=inquiry.notes,
    )


@router.post("/from-inquiry/{inquiry_id}", response_model=CateringQuotationOut, status_code=status.HTTP_201_CREATED)
def create_quotation_from_inquiry(
    inquiry_id: UUID,
    payload: CateringQuotationFromInquiryIn,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = (
        db.query(CateringInquiry)
        .filter(CateringInquiry.id == inquiry_id, CateringInquiry.organization_id == org_id, CateringInquiry.deleted_at.is_(None))
        .first()
    )
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    if inquiry.status in ("converted", "closed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry is already converted or closed")
    if inquiry.status == "quoted":
        existing = db.query(CateringQuotation).filter(
            CateringQuotation.inquiry_id == inquiry.id,
            CateringQuotation.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This inquiry already has a quotation — edit or resend the existing one instead")
    if inquiry.review_status == "pending_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry is under review and cannot be quoted yet")
    if inquiry.review_status == "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry was rejected during review and cannot be quoted")

    guest_count = payload.guest_count or inquiry.guest_count
    pkg = _load_package(db, org_id, inquiry.catering_package_id)
    if payload.total_price is None:
        if pkg is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Inquiry has no package; a total price is required")
        total_price = _quotation_total_with_addons(db, org_id, pkg, guest_count, inquiry)
    else:
        total_price = payload.total_price

    quotation = CateringQuotation(
        organization_id=org_id,
        inquiry_id=inquiry.id,
        catering_package_id=inquiry.catering_package_id,
        guest_count=guest_count,
        total_price=total_price,
        status="draft",
        valid_until=payload.valid_until,
        created_by=current_user.id,
    )
    db.add(quotation)
    db.flush()
    inquiry.status = "quoted"
    inquiry.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "quotation",
        quotation.id,
        inquiry.customer_name,
        "created",
        current_user,
        f"Draft quotation created for {inquiry.customer_name} (\u20b1{total_price:,.2f})",
    )
    db.commit()
    db.refresh(quotation)
    return quotation


@router.get("/", response_model=Page[CateringQuotationOut])
def list_quotations(
    inquiry_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    if inquiry_id:
        q = q.filter(CateringQuotation.inquiry_id == inquiry_id)
    q = apply_status(q, status, CateringQuotation.status)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    return paginate(q, page, page_size)


@router.post("/", response_model=CateringQuotationOut, status_code=status.HTTP_201_CREATED)
def create_quotation(
    payload: CateringQuotationCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    inquiry = db.query(CateringInquiry).filter(
        CateringInquiry.id == payload.inquiry_id,
        CateringInquiry.organization_id == org_id,
        CateringInquiry.deleted_at.is_(None),
    ).first()
    if not inquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found")
    if inquiry.status in ("converted", "closed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry is already converted or closed")
    if inquiry.status == "quoted":
        existing = db.query(CateringQuotation).filter(
            CateringQuotation.inquiry_id == inquiry.id,
            CateringQuotation.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This inquiry already has a quotation — edit or resend the existing one instead")
    if inquiry.review_status == "pending_review":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry is under review and cannot be quoted yet")
    if inquiry.review_status == "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquiry was rejected during review and cannot be quoted")

    package_id = payload.catering_package_id or inquiry.catering_package_id
    pkg = _load_package(db, org_id, package_id)
    if payload.total_price is None:
        if pkg is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Inquiry has no package; a total price is required")
        total_price = _quotation_total_with_addons(db, org_id, pkg, payload.guest_count, inquiry)
    else:
        total_price = payload.total_price

    quotation = CateringQuotation(
        organization_id=org_id,
        inquiry_id=payload.inquiry_id,
        catering_package_id=package_id,
        guest_count=payload.guest_count,
        total_price=total_price,
        status="draft",
        valid_until=payload.valid_until,
        created_by=current_user.id,
    )
    db.add(quotation)
    db.flush()
    inquiry.status = "quoted"
    inquiry.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "quotation",
        quotation.id,
        inquiry.customer_name,
        "created",
        current_user,
        f"Draft quotation created for {inquiry.customer_name} (\u20b1{total_price:,.2f})",
    )
    db.commit()
    db.refresh(quotation)
    return quotation


@router.get("/{quotation_id}", response_model=CateringQuotationOut)
def get_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    return quotation


@router.get("/{quotation_id}/detail", response_model=CateringQuotationDetailOut)
def get_quotation_detail(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    return _to_quotation_detail(db, org_id, quotation)


@router.put("/{quotation_id}", response_model=CateringQuotationOut)
def update_quotation(
    quotation_id: UUID,
    payload: CateringQuotationUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    if quotation.status not in ("draft", "sent"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot edit quotation with status '{quotation.status}'")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return quotation

    if "catering_package_id" in update_data:
        quotation.catering_package_id = update_data["catering_package_id"]
    if "guest_count" in update_data:
        quotation.guest_count = update_data["guest_count"]
    if "total_price" in update_data:
        quotation.total_price = update_data["total_price"]
    if "valid_until" in update_data:
        quotation.valid_until = update_data["valid_until"]

    quotation.updated_by = current_user.id

    inquiry = db.query(CateringInquiry).filter(CateringInquiry.id == quotation.inquiry_id).first()
    customer_name = inquiry.customer_name if inquiry else str(quotation.id)[:8]
    changes = ", ".join(k.replace("_", " ") for k in update_data.keys())
    log_audit(
        db,
        org_id,
        "quotation",
        quotation.id,
        customer_name,
        "updated",
        current_user,
        f"Quotation for {customer_name} updated ({changes})",
    )
    db.commit()
    db.refresh(quotation)
    return quotation


@router.post("/{quotation_id}/send", response_model=CateringQuotationOut)
def send_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_SEND)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    if quotation.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot send quotation with status '{quotation.status}'")

    inquiry = db.query(CateringInquiry).filter(CateringInquiry.id == quotation.inquiry_id).first()
    customer_name = inquiry.customer_name if inquiry else str(quotation.id)[:8]
    quotation.status = "sent"
    quotation.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "quotation",
        quotation.id,
        customer_name,
        "sent",
        current_user,
        f"Quotation for {customer_name} sent to customer",
    )
    db.commit()
    db.refresh(quotation)

    from app.email_service import email_service
    from app.email_templates import quotation_ready
    from app.config import get_settings
    customer_email = inquiry.customer_email if inquiry else None
    if customer_email:
        ref_str = f"QUO-{str(quotation.id)[:8]}"
        valid_str = quotation.valid_until.strftime("%b %d, %Y") if quotation.valid_until else "—"
        base_url = get_settings().PUBLIC_BASE_URL.rstrip("/")
        access_token = inquiry.access_token if inquiry else ""
        email_service.send_template(
            customer_email,
            quotation_ready,
            name=customer_name,
            reference=ref_str,
            line_items=[("Guest count", str(quotation.guest_count)), ("Total price", f"₱{quotation.total_price:,.2f}")],
            total=f"₱{quotation.total_price:,.2f}",
            valid_until=valid_str,
            accept_url=f"{base_url}/customer-portal.html?ref={inquiry_reference(inquiry)}&token={access_token}",
        )

    return quotation


@router.post("/{quotation_id}/accept", response_model=CateringBookingOut)
def accept_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_APPROVE)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).with_for_update().first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    booking = perform_accept(db, quotation, org_id, current_user)
    return booking_out(db, org_id, booking)


@router.post("/{quotation_id}/reject", response_model=CateringQuotationOut)
def reject_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_REJECT)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    return perform_reject(db, quotation, current_user)


@router.delete("/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quotation(
    quotation_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.QUOTATION_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    quotation = _base_query(db, org_id).filter(CateringQuotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    if quotation.status not in ("draft", "sent", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete quotation with status '{quotation.status}'",
        )

    now = datetime.now(timezone.utc)
    quotation.deleted_at = now
    quotation.updated_by = current_user.id

    inquiry = db.query(CateringInquiry).filter(CateringInquiry.id == quotation.inquiry_id).first()
    customer_name = inquiry.customer_name if inquiry else str(quotation.id)[:8]
    log_audit(
        db,
        org_id,
        "quotation",
        quotation.id,
        customer_name,
        "deleted",
        current_user,
        f"Quotation for {customer_name} deleted",
    )

    remaining = db.query(CateringQuotation).filter(
        CateringQuotation.inquiry_id == quotation.inquiry_id,
        CateringQuotation.id != quotation.id,
        CateringQuotation.deleted_at.is_(None),
    ).count()
    if remaining == 0:
        inquiry = db.query(CateringInquiry).filter(
            CateringInquiry.id == quotation.inquiry_id,
        ).first()
        if inquiry and inquiry.status == "quoted":
            inquiry.status = "new"
            inquiry.updated_by = current_user.id

    db.commit()
