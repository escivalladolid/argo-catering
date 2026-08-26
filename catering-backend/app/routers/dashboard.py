from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import flip_overdue_requirements, inquiry_reference, payment_summary
from app.models.catering_models import (
    BookingRequirement,
    CateringBill,
    CateringBooking,
    CateringDelivery,
    CateringEquipmentAssignment,
    CateringInquiry,
    CateringPayment,
    CateringQuotation,
    CateringStaffAssignment,
    UserStub,
)
from app.rbac import Perm, require_permission
from app.models.catering_models import CateringAuditLog
from app.schemas.catering_schemas import (
    DashboardActivityItem,
    DashboardActivityOut,
    DashboardAttentionGroup,
    DashboardAttentionItem,
    DashboardAttentionOut,
    DashboardStatsOut,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_MANAGER_GROUPS = {"pending_approval", "missing_resources", "balance_due", "overdue_bills", "payment_verifications", "requirements_overdue"}
_STAFF_GROUPS = {"pending_review"}


def _ref(prefix: str, rid: UUID) -> str:
    return f"{prefix}-{rid}"


def _item(kind: str, rid: UUID, title: str, subtitle: str | None = None, at=None, status: str | None = None, reference: str | None = None, **meta) -> DashboardAttentionItem:
    return DashboardAttentionItem(
        kind=kind,
        reference=reference or _ref({"inquiry": "INQ", "quotation": "QUO", "booking": "BK", "delivery": "DLV", "bill": "BILL"}.get(kind, kind.upper()), rid),
        title=title,
        subtitle=subtitle,
        at=at,
        status=status,
        meta={"id": str(rid), **meta},
    )


def _build_groups(db: Session, org_id: UUID, now: datetime) -> list[DashboardAttentionGroup]:
    base: list[DashboardAttentionGroup] = []

    # 1. Needs a quotation — customer inquiries in "new" with no usable quotation.
    #    Shown immediately (oldest first) so fresh submissions act like notifications.
    inquiries = (
        db.query(CateringInquiry)
        .filter(
            CateringInquiry.organization_id == org_id,
            CateringInquiry.deleted_at.is_(None),
            CateringInquiry.status == "new",
            CateringInquiry.review_status.notin_(("pending_review", "rejected")),
        )
        .order_by(CateringInquiry.created_at.asc())
        .limit(20)
        .all()
    )
    inquiry_ids = [inq.id for inq in inquiries]
    draft_quoted: set[UUID] = set()
    if inquiry_ids:
        quoted_ids = (
            db.query(CateringQuotation.inquiry_id)
            .filter(
                CateringQuotation.organization_id == org_id,
                CateringQuotation.inquiry_id.in_(inquiry_ids),
                CateringQuotation.deleted_at.is_(None),
            )
            .all()
        )
        draft_quoted = {row[0] for row in quoted_ids}
    needs_quo = [
        _item(
            "inquiry",
            inq.id,
            inq.customer_name,
            subtitle=f"{inq.guest_count} guests · {_fmt_iso(inq.event_date)}",
            at=inq.created_at,
            status=inq.status,
            reference=inquiry_reference(inq),
        )
        for inq in inquiries
        if inq.id not in draft_quoted
    ]
    base.append(
        DashboardAttentionGroup(
            key="needs_quotation",
            title="Needs a quotation",
            icon="bi-chat-left-text",
            description="Customer inquiries waiting for a quotation",
            actionable=True,
            items=needs_quo,
            total=len(needs_quo),
        )
    )

    # 1b. Pending review — customer inquiries held for staffing review.
    pending_review = (
        db.query(CateringInquiry)
        .filter(
            CateringInquiry.organization_id == org_id,
            CateringInquiry.deleted_at.is_(None),
            CateringInquiry.review_status == "pending_review",
        )
        .order_by(CateringInquiry.event_date.asc())
        .limit(20)
        .all()
    )
    pr_items = [
        _item(
            "inquiry",
            inq.id,
            inq.customer_name,
            subtitle=f"{inq.guest_count} guests · {_fmt_iso(inq.event_date)}",
            at=inq.event_date,
            status=inq.status,
            reference=inquiry_reference(inq),
        )
        for inq in pending_review
    ]
    base.append(
        DashboardAttentionGroup(
            key="pending_review",
            title="Pending review",
            icon="bi-shield-check",
            description="Customer inquiries flagged for staffing review",
            actionable=True,
            items=pr_items,
            total=len(pr_items),
        )
    )

    # 2. Awaiting customer response — sent quotations.
    quotations = (
        db.query(CateringQuotation)
        .filter(
            CateringQuotation.organization_id == org_id,
            CateringQuotation.deleted_at.is_(None),
            CateringQuotation.status == "sent",
        )
        .order_by(CateringQuotation.valid_until.asc())
        .limit(20)
        .all()
    )
    awaiting = [
        _item(
            "quotation",
            q.id,
            q.inquiry.customer_name if q.inquiry else "—",
            subtitle=f"{_fmt_price(float(q.total_price))} · valid until {_fmt_iso(q.valid_until) if q.valid_until else '—'}",
            at=q.valid_until or q.created_at,
            status=q.status,
            inquiry_id=str(q.inquiry_id),
        )
        for q in quotations
    ]
    base.append(
        DashboardAttentionGroup(
            key="awaiting_customer",
            title="Awaiting customer response",
            icon="bi-hourglass-split",
            description="Sent quotations waiting for the customer to accept or decline",
            actionable=True,
            items=awaiting,
            total=len(awaiting),
        )
    )

    # 3. Happening soon — events within the next 48 hours.
    horizon = now + timedelta(hours=48)
    bookings = (
        db.query(CateringBooking)
        .filter(
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringBooking.event_date >= now,
            CateringBooking.event_date <= horizon,
            CateringBooking.status.in_(["confirmed", "in_progress"]),
        )
        .order_by(CateringBooking.event_date.asc())
        .limit(20)
        .all()
    )
    happening = [
        _item(
            "booking",
            b.id,
            b.event_location or "Booked event",
            subtitle=f"{b.guest_count} guests · {_fmt_price(float(b.total_amount))}",
            at=b.event_date,
            status=b.status,
        )
        for b in bookings
    ]
    base.append(
        DashboardAttentionGroup(
            key="happening_soon",
            title="Happening soon",
            icon="bi-calendar-event",
            description="Confirmed or in-progress events within the next 48 hours",
            actionable=True,
            items=happening,
            total=len(happening),
        )
    )

    # 4. Deliveries needing action.
    deliveries = (
        db.query(CateringDelivery)
        .filter(
            CateringDelivery.organization_id == org_id,
            CateringDelivery.deleted_at.is_(None),
            CateringDelivery.status.in_(["scheduled", "in_transit"]),
            CateringDelivery.scheduled_at >= now,
            CateringDelivery.scheduled_at <= horizon,
        )
        .order_by(CateringDelivery.scheduled_at.asc())
        .limit(20)
        .all()
    )
    dlv_items = [
        _item(
            "delivery",
            d.id,
            d.contact_name or "Delivery",
            subtitle=f"{d.delivery_address or '—'} · {d.status.replace('_', ' ')}",
            at=d.scheduled_at,
            status=d.status,
            booking_id=str(d.booking_id),
        )
        for d in deliveries
    ]
    base.append(
        DashboardAttentionGroup(
            key="deliveries",
            title="Deliveries needing action",
            icon="bi-truck",
            description="Scheduled or in-transit deliveries within the next 48 hours",
            actionable=True,
            items=dlv_items,
            total=len(dlv_items),
        )
    )

    # ---- Manager / administrator only groups ----

    # 5. Pending approval — sent quotations awaiting management sign-off.
    sent = (
        db.query(CateringQuotation)
        .filter(
            CateringQuotation.organization_id == org_id,
            CateringQuotation.deleted_at.is_(None),
            CateringQuotation.status == "sent",
        )
        .order_by(CateringQuotation.created_at.asc())
        .limit(20)
        .all()
    )
    pending = [
        _item(
            "quotation",
            q.id,
            q.inquiry.customer_name if q.inquiry else "—",
            subtitle=f"{_fmt_price(float(q.total_price))} · {_fmt_iso(q.created_at)}",
            at=q.created_at,
            status=q.status,
            inquiry_id=str(q.inquiry_id),
        )
        for q in sent
    ]
    base.append(
        DashboardAttentionGroup(
            key="pending_approval",
            title="Pending approval",
            icon="bi-file-earmark-check",
            description="Sent quotations that need your approval to become bookings",
            actionable=True,
            items=pending,
            total=len(pending),
        )
    )

    # 6. Missing staff / equipment.
    active_bookings = (
        db.query(CateringBooking)
        .filter(
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringBooking.status.in_(["confirmed", "in_progress"]),
        )
        .all()
    )
    missing: list[DashboardAttentionItem] = []
    for b in active_bookings:
        staff_count = (
            db.query(CateringStaffAssignment)
            .filter(CateringStaffAssignment.organization_id == org_id, CateringStaffAssignment.booking_id == b.id, CateringStaffAssignment.deleted_at.is_(None))
            .count()
        )
        equip_count = (
            db.query(CateringEquipmentAssignment)
            .filter(CateringEquipmentAssignment.organization_id == org_id, CateringEquipmentAssignment.booking_id == b.id, CateringEquipmentAssignment.deleted_at.is_(None))
            .count()
        )
        missing_parts: list[str] = []
        if staff_count == 0:
            missing_parts.append("staff")
        if equip_count == 0:
            missing_parts.append("equipment")
        if missing_parts:
            missing.append(
                _item(
                    "booking",
                    b.id,
                    b.event_location or "Booked event",
                    subtitle=f"Missing {', '.join(missing_parts)} · {_fmt_iso(b.event_date)}",
                    at=b.event_date,
                    status=b.status,
                )
            )
    missing = missing[:20]
    base.append(
        DashboardAttentionGroup(
            key="missing_resources",
            title="Missing staff / equipment",
            icon="bi-exclamation-triangle",
            description="Confirmed events with no staff or equipment assigned yet",
            actionable=True,
            items=missing,
            total=len(missing),
        )
    )

    # 7. Completed — balance due.
    completed = (
        db.query(CateringBooking)
        .filter(
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringBooking.status == "completed",
            CateringBooking.payment_status != "paid",
        )
        .order_by(CateringBooking.event_date.asc())
        .limit(20)
        .all()
    )
    balance = []
    paid_map = payment_summary(db, org_id, [b.id for b in completed])
    for b in completed:
        remaining = round(float(b.total_amount or 0) - paid_map.get(b.id, 0.0), 2)
        if remaining > 0:
            balance.append(
                _item(
                    "booking",
                    b.id,
                    b.event_location or "Booked event",
                    subtitle=f"{_fmt_price(remaining)} remaining · {b.payment_status.replace('_', ' ')}",
                    at=b.event_date,
                    status=b.payment_status,
                )
            )
    base.append(
        DashboardAttentionGroup(
            key="balance_due",
            title="Completed — balance due",
            icon="bi-cash-stack",
            description="Completed events that are not fully paid",
            actionable=True,
            items=balance,
            total=len(balance),
        )
    )

    # 8. Overdue bills — sent bills past their due date (mirrors billing._apply_overdue).
    overdue = (
        db.query(CateringBill)
        .filter(
            CateringBill.organization_id == org_id,
            CateringBill.deleted_at.is_(None),
            CateringBill.status == "sent",
            CateringBill.due_date.is_not(None),
            CateringBill.due_date < now,
        )
        .order_by(CateringBill.due_date.asc())
        .limit(20)
        .all()
    )
    overdue_items = [
        _item(
            "bill",
            b.id,
            b.bill_number,
            subtitle=f"{_fmt_price(float(b.total))} · due {_fmt_iso(b.due_date)}",
            at=b.due_date,
            status=b.status,
            booking_id=str(b.booking_id),
        )
        for b in overdue
    ]
    base.append(
        DashboardAttentionGroup(
            key="overdue_bills",
            title="Overdue bills",
            icon="bi-exclamation-octagon",
            description="Sent bills past their due date",
            actionable=True,
            items=overdue_items,
            total=len(overdue_items),
        )
    )

    # 9. Proof-of-payment uploads awaiting verification (customer action done,
    #    admin verification pending).
    unverified = (
        db.query(CateringPayment, CateringBooking)
        .join(CateringBooking, CateringBooking.id == CateringPayment.booking_id)
        .filter(
            CateringPayment.organization_id == org_id,
            CateringPayment.deleted_at.is_(None),
            CateringPayment.verification_status == "pending",
            CateringPayment.proof_url.is_not(None),
        )
        .order_by(CateringPayment.created_at.asc())
        .limit(20)
        .all()
    )
    pay_items = [
        _item(
            "payment",
            p.id,
            b.event_location or "Booking payment",
            subtitle=f"{_fmt_price(float(p.amount))} · proof uploaded {_fmt_iso(p.created_at)}",
            at=p.created_at,
            status="awaiting_verification",
            booking_id=str(b.id),
        )
        for p, b in unverified
    ]
    base.append(
        DashboardAttentionGroup(
            key="payment_verifications",
            title="Payments awaiting verification",
            icon="bi-receipt",
            description="Customer proof-of-payment uploads that need to be verified",
            actionable=True,
            items=pay_items,
            total=len(pay_items),
        )
    )

    # 10. Overdue / soon-due booking requirements (pre-event checklist).
    flip_overdue_requirements(db, org_id)
    week_ahead = now + timedelta(days=7)
    req_rows = (
        db.query(BookingRequirement, CateringBooking)
        .join(CateringBooking, CateringBooking.id == BookingRequirement.booking_id)
        .filter(
            BookingRequirement.organization_id == org_id,
            BookingRequirement.deleted_at.is_(None),
            BookingRequirement.status != "done",
            CateringBooking.deleted_at.is_(None),
        )
        .order_by(BookingRequirement.due_date.asc().nullslast())
        .limit(50)
        .all()
    )
    today = now.date()
    req_items = []
    for r, b in req_rows:
        if r.status == "overdue" or (r.due_date is not None and r.due_date < today):
            urgency = "overdue"
        elif r.due_date is not None and r.due_date <= week_ahead.date():
            urgency = "due this week"
        else:
            continue
        req_items.append(
            _item(
                "booking",
                b.id,
                b.event_location or "Booked event",
                subtitle=f"{r.description[:80]} · {urgency}",
                at=datetime.combine(r.due_date, datetime.min.time(), tzinfo=timezone.utc) if r.due_date else None,
                status=r.status if r.status == "overdue" else "pending",
                requirement_id=str(r.id),
            )
        )
    req_items.sort(key=lambda it: (it.at is None, it.at))
    base.append(
        DashboardAttentionGroup(
            key="requirements_overdue",
            title="Requirements overdue",
            icon="bi-list-check",
            description="Pre-event tasks past their due date or due within 7 days",
            actionable=True,
            items=req_items,
            total=len(req_items),
        )
    )

    return base


def _fmt_iso(dt) -> str:
    return dt.isoformat() if dt is not None else ""


def _fmt_price(value: float) -> str:
    if value == int(value):
        return f"₱{int(value):,}"
    return f"₱{value:,.2f}"


@router.get("/attention", response_model=DashboardAttentionOut)
def dashboard_attention(
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DASHBOARD_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    now = datetime.now(timezone.utc)
    groups = _build_groups(db, org_id, now)
    role = getattr(current_user, "role", "")
    if role not in ("manager", "administrator"):
        groups = [g for g in groups if g.key not in _MANAGER_GROUPS]
    if role == "viewer":
        groups = [g for g in groups if g.key not in _STAFF_GROUPS]
        for group in groups:
            group.actionable = False
    return DashboardAttentionOut(groups=[g for g in groups if g.items])


@router.get("/stats", response_model=DashboardStatsOut)
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DASHBOARD_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)

    # Inquiries
    total_inquiries = (
        db.query(CateringInquiry)
        .filter(CateringInquiry.organization_id == org_id, CateringInquiry.deleted_at.is_(None))
        .count()
    )

    # Quotations — total + by status
    quo_query = db.query(CateringQuotation).filter(
        CateringQuotation.organization_id == org_id,
        CateringQuotation.deleted_at.is_(None),
    )
    total_quotations = quo_query.count()
    quo_rows = db.query(CateringQuotation.status).filter(
        CateringQuotation.organization_id == org_id,
        CateringQuotation.deleted_at.is_(None),
    ).all()
    quotations_by_status: dict[str, int] = {}
    for (status,) in quo_rows:
        quotations_by_status[status] = quotations_by_status.get(status, 0) + 1

    # Bookings — total + by status + revenue + upcoming
    bk_query = db.query(CateringBooking).filter(
        CateringBooking.organization_id == org_id,
        CateringBooking.deleted_at.is_(None),
    )
    total_bookings = bk_query.count()
    bk_rows = db.query(CateringBooking.status).filter(
        CateringBooking.organization_id == org_id,
        CateringBooking.deleted_at.is_(None),
    ).all()
    bookings_by_status: dict[str, int] = {}
    for (status,) in bk_rows:
        bookings_by_status[status] = bookings_by_status.get(status, 0) + 1

    # Revenue = sum of total_amount for non-cancelled bookings
    total_revenue = (
        db.query(func.coalesce(func.sum(CateringBooking.total_amount), 0.0))
        .filter(
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringBooking.status != "cancelled",
        )
        .scalar()
    )

    upcoming_bookings_30d = (
        db.query(CateringBooking)
        .filter(
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringBooking.event_date >= now,
            CateringBooking.event_date <= thirty_days,
            CateringBooking.status.in_(["confirmed", "in_progress", "pending"]),
        )
        .count()
    )

    return DashboardStatsOut(
        total_inquiries=total_inquiries,
        total_quotations=total_quotations,
        quotations_by_status=quotations_by_status,
        total_bookings=total_bookings,
        bookings_by_status=bookings_by_status,
        total_revenue=float(total_revenue),
        upcoming_bookings_30d=upcoming_bookings_30d,
    )


@router.get("/activity", response_model=DashboardActivityOut)
def dashboard_activity(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DASHBOARD_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    entries = (
        db.query(CateringAuditLog)
        .filter(CateringAuditLog.organization_id == org_id)
        .order_by(CateringAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    items = []
    for e in entries:
        actor_email = None
        if e.actor_id:
            actor = db.query(UserStub).filter(UserStub.id == e.actor_id).first()
            actor_email = actor.email if actor else None
        items.append(
            DashboardActivityItem(
                id=e.id,
                entity_type=e.entity_type,
                entity_reference=e.entity_reference,
                action=e.action,
                actor_email=actor_email,
                actor_role=e.actor_role,
                summary=e.summary,
                created_at=e.created_at,
            )
        )
    return DashboardActivityOut(items=items)
