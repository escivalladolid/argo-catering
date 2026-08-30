"""Customer account portal endpoints (Phase 0.6).

Authenticated counterpart to the anonymous capability-based public portal.
Everything is scoped to the calling customer via ``get_current_customer`` —
the id and tenant come from the signed JWT, never from the request.

    * link an existing anonymous inquiry to the account (proving ownership
      with its emailed access token — it can only be claimed once)
    * list my inquiries / views one inquiry's full status
    * list my bookings and my payments (resolved through the inquiry chain)

New anonymous portal submissions can also be bound to the account by passing
a valid customer JWT (see ``get_optional_customer`` on POST /public/inquiries).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_customer
from app.flow import inquiry_reference, log_audit, payment_summary
from app.models.catering_models import (
    CateringBooking,
    CateringInquiry,
    CateringPayment,
    CateringQuotation,
    Customer,
)
from app.routers.public_portal import (
    NOT_FOUND,
    _booking_for,
    _get_inquiry,
    _package_snapshot,
    _require_access_token,
    _visible_quotation,
    build_customer_status,
)
from app.schemas.catering_schemas import (
    CustomerBookingListItemOut,
    CustomerInquiryLinkIn,
    CustomerInquiryLinkOut,
    CustomerInquiryListItemOut,
    CustomerPaymentListItemOut,
    CustomerStatusOut,
)

router = APIRouter(prefix="/customer", tags=["Customer Portal"])


def _mine(db: Session, org_id, customer_id, reference: str) -> CateringInquiry:
    """Resolve an inquiry owned by the calling customer, or 404.

    The 404 for a foreign or unlinked inquiry is identical to the not-found
    message so the endpoint never reveals whether a reference exists.
    """
    inquiry = _get_inquiry(db, org_id, reference)
    if inquiry.customer_id is None or inquiry.customer_id != customer_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return inquiry


@router.post("/inquiries/link", response_model=CustomerInquiryLinkOut)
def link_inquiry_to_account(
    payload: CustomerInquiryLinkIn,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Claim an anonymous inquiry for this account using its emailed access token.

    The inquiry must not already belong to an account — an inquiry can only be
    linked once, so a claimed inquiry can never be taken over.
    """
    inquiry = _get_inquiry(db, customer.organization_id, payload.reference)
    _require_access_token(inquiry, payload.access_token)
    if inquiry.customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This inquiry is already linked to an account.",
        )
    inquiry.customer_id = customer.id
    log_audit(
        db,
        customer.organization_id,
        "inquiry",
        inquiry.id,
        payload.reference,
        "linked_to_customer",
        None,
        f"Inquiry linked to customer account {customer.email}",
        actor_role="customer",
    )
    db.commit()
    return CustomerInquiryLinkOut(
        message="This inquiry is now linked to your account.",
        reference=inquiry_reference(inquiry),
    )


@router.get("/inquiries", response_model=list[CustomerInquiryListItemOut])
def list_my_inquiries(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """List the inquiries linked to this account, newest first."""
    org_id = customer.organization_id
    inquiries = (
        db.query(CateringInquiry)
        .filter(
            CateringInquiry.organization_id == org_id,
            CateringInquiry.customer_id == customer.id,
            CateringInquiry.deleted_at.is_(None),
        )
        .order_by(CateringInquiry.created_at.desc())
        .all()
    )
    booking_by_inquiry: dict = {}
    booking_ids: list = []
    for inq in inquiries:
        quotation = _visible_quotation(db, org_id, inq.id)
        booking = _booking_for(db, org_id, quotation)
        booking_by_inquiry[inq.id] = (quotation, booking)
        if booking:
            booking_ids.append(booking.id)
    paid_map = payment_summary(db, org_id, booking_ids)

    rows = []
    for inq in inquiries:
        quotation, booking = booking_by_inquiry.get(inq.id, (None, None))
        package_name, _ = _package_snapshot(db, org_id, inq.catering_package_id)
        rows.append(
            CustomerInquiryListItemOut(
                reference=inquiry_reference(inq),
                event_date=inq.event_date,
                event_type=inq.event_type,
                event_address=inq.event_address,
                venue_name=inq.venue_name,
                guest_count=inq.guest_count,
                package_name=package_name,
                status=inq.status,
                review_status=inq.review_status,
                estimated_total=float(inq.estimated_total) if inq.estimated_total else None,
                quotation_status=quotation.status if quotation else None,
                booking_status=booking.status if booking else None,
                payment_status=booking.payment_status if booking else None,
                amount_paid=round(paid_map.get(booking.id, 0.0), 2) if booking else 0,
                created_at=inq.created_at,
            )
        )
    return rows


@router.get("/inquiries/{reference}", response_model=CustomerStatusOut)
def my_inquiry_detail(
    reference: str,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """Full status view for one of my inquiries (same shape as anonymous tracking)."""
    inquiry = _mine(db, customer.organization_id, customer.id, reference)
    return build_customer_status(db, customer.organization_id, inquiry)


@router.get("/bookings", response_model=list[CustomerBookingListItemOut])
def list_my_bookings(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """List bookings made from this account's inquiries, newest first."""
    org_id = customer.organization_id
    rows = (
        db.query(CateringBooking, CateringInquiry)
        .join(CateringQuotation, CateringQuotation.id == CateringBooking.quotation_id)
        .join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
        .filter(
            CateringInquiry.organization_id == org_id,
            CateringInquiry.customer_id == customer.id,
            CateringInquiry.deleted_at.is_(None),
            CateringBooking.deleted_at.is_(None),
        )
        .order_by(CateringBooking.created_at.desc())
        .all()
    )
    paid_map = payment_summary(db, org_id, [b.id for b, _ in rows])
    return [
        CustomerBookingListItemOut(
            reference=f"BK-{b.id}",
            inquiry_reference=inquiry_reference(inq),
            event_date=b.event_date,
            event_location=b.event_location,
            event_time=b.event_time,
            guest_count=b.guest_count,
            total_amount=float(b.total_amount),
            payment_status=b.payment_status,
            status=b.status,
            service_style=b.service_style,
            coordinator_name=b.coordinator_name,
            coordinator_contact=b.coordinator_contact,
            created_at=b.created_at,
        )
        for b, inq in rows
    ]


@router.get("/payments", response_model=list[CustomerPaymentListItemOut])
def list_my_payments(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """List payments recorded against this account's bookings, newest first."""
    org_id = customer.organization_id
    rows = (
        db.query(CateringPayment, CateringInquiry)
        .join(CateringBooking, CateringBooking.id == CateringPayment.booking_id)
        .join(CateringQuotation, CateringQuotation.id == CateringBooking.quotation_id)
        .join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
        .filter(
            CateringInquiry.organization_id == org_id,
            CateringInquiry.customer_id == customer.id,
            CateringInquiry.deleted_at.is_(None),
            CateringPayment.deleted_at.is_(None),
        )
        .order_by(CateringPayment.created_at.desc())
        .all()
    )
    return [
        CustomerPaymentListItemOut(
            id=p.id,
            amount=float(p.amount),
            method=p.method,
            customer_reference=p.customer_reference,
            payment_date=p.payment_date,
            verified=p.verified,
            proof_url=p.proof_url,
            created_at=p.created_at,
            inquiry_reference=inquiry_reference(inq),
            booking_reference=f"BK-{p.booking_id}",
        )
        for p, inq in rows
    ]