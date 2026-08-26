from typing import Literal
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth import get_current_user
from app.dependencies import get_org_id
from app.flow import (
    audit_log_out,
    booking_out,
    booking_out_list,
    booking_payment_amounts,
    compute_premade_total,
    decode_food_requirements,
    flip_overdue_requirements,
    format_event_location,
    inquiry_reference,
    log_audit,
    recent_booking_activity,
    requirement_out,
)
from app.models.catering_models import BookingRequirement, CateringBooking, CateringInquiry, CateringPackage, CateringQuotation, CateringVenue, UserStub, VenueBooking
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, ensure_permission, require_permission
from app.schemas.catering_schemas import (
    BookingRequirementCreate,
    BookingRequirementListOut,
    BookingRequirementOut,
    BookingRequirementUpdate,
    CateringBookingDetailOut,
    CateringBookingOut,
    CateringBookingTransition,
    CateringBookingUpdate,
    DerivedInclusionOut,
    Page,
    StaffingOut,
)
from app.routers.staffing import staffing_availability, staffing_shortfall_warning

router = APIRouter(prefix="/bookings", tags=["Bookings"])

SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "guests": CateringBooking.guest_count,
    "guest_count": CateringBooking.guest_count,
    "event_date": CateringBooking.event_date,
    "total_amount": CateringBooking.total_amount,
    "status": CateringBooking.status,
    "created_at": CateringBooking.created_at,
}
SEARCH_COLS = [CateringInquiry.customer_name, CateringBooking.event_location, CateringInquiry.event_address]


def _base_query(db: Session, org_id: UUID):
    return (
        db.query(CateringBooking)
        .join(CateringQuotation, CateringQuotation.id == CateringBooking.quotation_id)
        .join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
        .filter(
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringQuotation.deleted_at.is_(None),
            CateringInquiry.deleted_at.is_(None),
        )
    )


def _customer_name(db: Session, booking: CateringBooking) -> str:
    inquiry = (
        db.query(CateringInquiry)
        .join(CateringQuotation, CateringQuotation.inquiry_id == CateringInquiry.id)
        .filter(CateringQuotation.id == booking.quotation_id)
        .first()
    )
    return inquiry.customer_name if inquiry else str(booking.id)[:8]


@router.get("/", response_model=Page[CateringBookingOut])
def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    q = apply_status(q, status, CateringBooking.status)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    page = paginate(q, page, page_size)
    items = booking_out_list(db, org_id, page.items)
    return Page(
        items=items,
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        total_pages=page.total_pages,
    )


# ---- Booking requirements (pre-event checklist) ----

def _booking_context(db: Session, booking_id: UUID) -> dict:
    row = (
        db.query(CateringBooking, CateringQuotation, CateringInquiry)
        .join(CateringQuotation, CateringQuotation.id == CateringBooking.quotation_id)
        .join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
        .filter(CateringBooking.id == booking_id)
        .first()
    )
    if not row:
        return {}
    _bk, quo, inq = row
    return {
        "booking_reference": inquiry_reference(inq),
        "customer_name": inq.customer_name,
        "event_date": inq.event_date.isoformat() if inq.event_date else None,
    }


def _requirement_out(db: Session, r: BookingRequirement) -> BookingRequirementOut:
    data = requirement_out(r)
    data.update(_booking_context(db, r.booking_id))
    return BookingRequirementOut(**data)


@router.get("/requirements/all", response_model=BookingRequirementListOut)
def list_all_requirements(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    """Cross-booking requirements view sorted by due date (soonest/most-overdue first)."""
    flip_overdue_requirements(db, org_id)
    q = db.query(BookingRequirement).filter(
        BookingRequirement.organization_id == org_id,
        BookingRequirement.deleted_at.is_(None),
    )
    if status_filter in ("pending", "done", "overdue"):
        q = q.filter(BookingRequirement.status == status_filter)
    elif status_filter == "upcoming":
        from datetime import date as _date
        q = q.filter(
            BookingRequirement.status == "pending",
            BookingRequirement.due_date.is_not(None),
            BookingRequirement.due_date >= _date.today(),
        )
    rows = q.order_by(BookingRequirement.due_date.asc().nullslast(), BookingRequirement.created_at.asc()).limit(200).all()
    return BookingRequirementListOut(items=[_requirement_out(db, r) for r in rows], total=len(rows))


@router.patch("/requirements/{requirement_id}", response_model=BookingRequirementOut)
def update_requirement(
    requirement_id: UUID,
    payload: BookingRequirementUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    req = db.query(BookingRequirement).filter(
        BookingRequirement.id == requirement_id,
        BookingRequirement.organization_id == org_id,
        BookingRequirement.deleted_at.is_(None),
    ).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    if payload.description is not None:
        req.description = payload.description.strip()
    if payload.category is not None:
        req.category = payload.category
    if payload.due_date is not None:
        req.due_date = payload.due_date.date() if isinstance(payload.due_date, datetime) else payload.due_date
    if payload.status is not None:
        if payload.status == "done":
            req.status = "done"
            req.completed_by = current_user.id
            req.completed_at = datetime.now(timezone.utc)
        else:
            req.status = payload.status
            req.completed_by = None
            req.completed_at = None
    db.commit()
    db.refresh(req)
    log_audit(db, org_id, "booking", req.booking_id, "requirement updated", current_user,
              f"Updated requirement '{req.description[:80]}'", actor_role=getattr(current_user, "role", None))
    return _requirement_out(db, req)


@router.post("/requirements/{requirement_id}/complete", response_model=BookingRequirementOut)
def complete_requirement(
    requirement_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    req = db.query(BookingRequirement).filter(
        BookingRequirement.id == requirement_id,
        BookingRequirement.organization_id == org_id,
        BookingRequirement.deleted_at.is_(None),
    ).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement not found")
    if req.status != "done":
        req.status = "done"
        req.completed_by = current_user.id
        req.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(req)
        log_audit(db, org_id, "booking", req.booking_id, "requirement completed", current_user,
                  f"Completed requirement '{req.description[:80]}'", actor_role=getattr(current_user, "role", None))
    return _requirement_out(db, req)


@router.get("/{booking_id}/requirements", response_model=BookingRequirementListOut)
def list_booking_requirements(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    flip_overdue_requirements(db, org_id)
    rows = db.query(BookingRequirement).filter(
        BookingRequirement.booking_id == booking_id,
        BookingRequirement.deleted_at.is_(None),
    ).order_by(
        BookingRequirement.category.asc(),
        BookingRequirement.due_date.asc().nullslast(),
    ).all()
    return BookingRequirementListOut(items=[_requirement_out(db, r) for r in rows], total=len(rows))


@router.post("/{booking_id}/requirements", response_model=BookingRequirementOut, status_code=status.HTTP_201_CREATED)
def create_booking_requirement(
    booking_id: UUID,
    payload: BookingRequirementCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    req = BookingRequirement(
        organization_id=org_id,
        booking_id=booking_id,
        description=payload.description.strip(),
        category=payload.category,
        due_date=payload.due_date.date() if isinstance(payload.due_date, datetime) else payload.due_date,
        status="pending",
        created_by=current_user.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    log_audit(db, org_id, "booking", booking_id, "requirement added", current_user,
              f"Added requirement '{req.description[:80]}'", actor_role=getattr(current_user, "role", None))
    return _requirement_out(db, req)


@router.get("/{booking_id}", response_model=CateringBookingOut)
def get_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking_out(db, org_id, booking)


@router.get("/{booking_id}/detail", response_model=CateringBookingDetailOut)
def get_booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    quotation = db.query(CateringQuotation).filter(CateringQuotation.id == booking.quotation_id).first()
    inquiry = db.query(CateringInquiry).filter(CateringInquiry.id == quotation.inquiry_id).first()
    pkg = None
    if inquiry and inquiry.catering_package_id:
        pkg = (
            db.query(CateringPackage)
            .filter(CateringPackage.id == inquiry.catering_package_id, CateringPackage.organization_id == org_id)
            .first()
        )

    out = CateringBookingDetailOut.model_validate(booking)
    paid, remaining = booking_payment_amounts(db, org_id, booking)
    out.amount_paid = paid
    out.remaining_balance = remaining
    out.selected_venue_id = booking.selected_venue_id or (inquiry.selected_venue_id if inquiry else None)
    out.customer_name = inquiry.customer_name if inquiry else None
    out.customer_contact = inquiry.customer_contact if inquiry else None
    out.event_type = inquiry.event_type if inquiry else None
    out.event_address = inquiry.event_address if inquiry else None
    out.venue_name = inquiry.venue_name if inquiry else None
    out.location_floor = inquiry.location_floor if inquiry else None
    out.room_hall = inquiry.room_hall if inquiry else None
    out.landmark = inquiry.landmark if inquiry else None
    out.delivery_instructions = inquiry.delivery_instructions if inquiry else None
    # If a venue is assigned on the booking, override venue_name from the venue record
    if booking.selected_venue_id:
        venue = db.query(CateringVenue).filter(
            CateringVenue.id == booking.selected_venue_id,
            CateringVenue.organization_id == org_id,
        ).first()
        if venue:
            out.venue_name = venue.name
    out.package_name = pkg.name if pkg else None
    out.package_mode = inquiry.package_mode if inquiry else None
    if inquiry:
        out.food_requirements = decode_food_requirements(inquiry.food_requirements_json)
        out.items = inquiry.items
        requested = {
            "waiter_count": inquiry.waiter_count,
            "bartender_count": inquiry.bartender_count,
            "chef_count": inquiry.chef_count,
            "kitchen_staff_count": inquiry.kitchen_staff_count,
            "support_crew_count": inquiry.support_crew_count,
        }
        out.staffing = StaffingOut(**requested)
        available = staffing_availability(db, org_id, booking.event_date)
        out.staffing_available = StaffingOut(**available)
        out.staffing_warning = staffing_shortfall_warning(requested, available)
        if pkg and (inquiry.package_mode or "default") != "custom":
            _, _derived = compute_premade_total(pkg, booking.guest_count, db=db, org_id=org_id)
            out.derived_inclusions = [
                DerivedInclusionOut(item_key=d["item_key"], quantity=d["quantity"])
                for d in _derived
            ]
    out.recent_activity = audit_log_out(db, recent_booking_activity(db, org_id, booking.id))
    return out


@router.put("/{booking_id}", response_model=CateringBookingOut)
def update_booking(
    booking_id: UUID,
    payload: CateringBookingUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    data = payload.model_dump(exclude_unset=True)
    if "coordinator_name" in data:
        booking.coordinator_name = data["coordinator_name"]
    if "coordinator_contact" in data:
        booking.coordinator_contact = data["coordinator_contact"]
    if "additional_notes" in data:
        booking.additional_notes = data["additional_notes"]
    if "dietary_notes" in data:
        booking.dietary_notes = data["dietary_notes"]
    if "setup_notes" in data:
        booking.setup_notes = data["setup_notes"]
    booking.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "booking",
        booking.id,
        _customer_name(db, booking),
        "updated",
        current_user,
        "Booking details updated",
    )
    db.commit()
    db.refresh(booking)
    return booking_out(db, org_id, booking)


class AssignVenueIn(BaseModel):
    selected_venue_id: UUID | None = None


@router.post("/{booking_id}/assign-venue", response_model=CateringBookingDetailOut)
def assign_booking_venue(
    booking_id: UUID,
    payload: AssignVenueIn,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    quotation = db.query(CateringQuotation).filter(CateringQuotation.id == booking.quotation_id).first()
    inquiry = db.query(CateringInquiry).filter(CateringInquiry.id == quotation.inquiry_id).first() if quotation else None

    new_venue_id = payload.selected_venue_id

    if new_venue_id is not None:
        venue = db.query(CateringVenue).filter(
            CateringVenue.id == new_venue_id,
            CateringVenue.organization_id == org_id,
            CateringVenue.deleted_at.is_(None),
            CateringVenue.is_active.is_(True),
        ).first()
        if not venue:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found or inactive")

        date_only = booking.event_date.replace(hour=0, minute=0, second=0, microsecond=0)
        conflict = db.query(VenueBooking).filter(
            VenueBooking.organization_id == org_id,
            VenueBooking.venue_id == new_venue_id,
            func.date(VenueBooking.event_date) == func.date(date_only),
            VenueBooking.deleted_at.is_(None),
            VenueBooking.inquiry_id != (inquiry.id if inquiry else None),
        ).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{venue.name} is already booked for {date_only.strftime('%B %d, %Y')}")

        if inquiry:
            existing_vb = db.query(VenueBooking).filter(
                VenueBooking.inquiry_id == inquiry.id,
            ).first()
            if existing_vb:
                existing_vb.venue_id = new_venue_id
                existing_vb.event_date = date_only
                existing_vb.deleted_at = None
            else:
                db.add(VenueBooking(
                    organization_id=org_id,
                    venue_id=new_venue_id,
                    inquiry_id=inquiry.id,
                    event_date=date_only,
                ))

        booking.selected_venue_id = new_venue_id
        booking.event_location = format_event_location(
            inquiry.event_address if inquiry else None,
            venue.name,
            inquiry.location_floor if inquiry else None,
            inquiry.room_hall if inquiry else None,
            inquiry.landmark if inquiry else None,
            inquiry.delivery_instructions if inquiry else None,
        ) if inquiry else venue.name
    else:
        if inquiry:
            db.query(VenueBooking).filter(
                VenueBooking.inquiry_id == inquiry.id,
            ).update({"deleted_at": func.now()})
        booking.selected_venue_id = None
        if inquiry:
            booking.event_location = format_event_location(
                inquiry.event_address,
                inquiry.venue_name,
                inquiry.location_floor,
                inquiry.room_hall,
                inquiry.landmark,
                inquiry.delivery_instructions,
            )

    booking.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "booking",
        booking.id,
        _customer_name(db, booking),
        "venue_assigned" if new_venue_id else "venue_cleared",
        current_user,
        f"Venue {'assigned' if new_venue_id else 'cleared'} for booking",
    )
    db.commit()
    db.refresh(booking)
    return get_booking_detail(booking_id, db, current_user, org_id)


TRANSITIONS = {
    "pending": "confirmed",
    "confirmed": "in_progress",
    "in_progress": "completed",
}


@router.post("/{booking_id}/transition", response_model=CateringBookingOut)
def transition_booking(
    booking_id: UUID,
    payload: CateringBookingTransition | None = None,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(get_current_user),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    next_status = TRANSITIONS.get(booking.status)
    if next_status is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot transition booking with status '{booking.status}'")

    if booking.status == "pending":
        ensure_permission(current_user, Perm.BOOKING_CONFIRM)
        if booking.payment_status == "unpaid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot confirm booking: no payment has been recorded. At least one payment is required before confirmation.",
            )
    else:
        ensure_permission(current_user, Perm.BOOKING_UPDATE_PROGRESS)

    booking.status = next_status
    booking.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "booking",
        booking.id,
        _customer_name(db, booking),
        f"status changed to {next_status}",
        current_user,
        f"Booking status changed to '{next_status}'",
    )
    db.commit()
    db.refresh(booking)

    if next_status == "confirmed":
        from app.email_service import email_service
        from app.email_templates import booking_confirmed
        from app.config import get_settings
        from app.models.catering_models import CateringQuotation
        quo = db.query(CateringQuotation).filter(CateringQuotation.id == booking.quotation_id).first()
        inq = db.query(CateringInquiry).filter(CateringInquiry.id == quo.inquiry_id).first() if quo else None
        if inq and inq.customer_email:
            base_url = get_settings().PUBLIC_BASE_URL.rstrip("/")
            email_service.send_template(
                inq.customer_email,
                booking_confirmed,
                name=inq.customer_name,
                reference=f"BK-{str(booking.id)[:8]}",
                event_date=booking.event_date.strftime("%b %d, %Y") if booking.event_date else "TBD",
                venue=booking.event_location or "TBD",
                coordinator=booking.coordinator_name or "To be assigned",
                coordinator_contact=booking.coordinator_contact or "\u2014",
                details_url=f"{base_url}/customer-portal.html?ref={inquiry_reference(inq)}",
            )

    return booking_out(db, org_id, booking)


@router.post("/{booking_id}/cancel", response_model=CateringBookingOut)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BOOKING_CANCEL)),
    org_id: UUID = Depends(get_org_id),
):
    booking = _base_query(db, org_id).filter(CateringBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.status in ("completed", "cancelled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel booking with status '{booking.status}'")
    booking.status = "cancelled"
    booking.payment_status = "unpaid"
    booking.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "booking",
        booking.id,
        _customer_name(db, booking),
        "cancelled",
        current_user,
        "Booking cancelled",
    )
    db.commit()
    db.refresh(booking)
    return booking_out(db, org_id, booking)
