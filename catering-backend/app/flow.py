"""Shared helpers for the package/inquiry/quotation/booking flow."""

import json
import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.auth import hash_password, verify_password
from app.email_templates import customer_verification, otp_verification
from app.models.catering_models import (
    BookingRequirement,
    CateringAuditLog,
    CateringEquipment,
    CateringInquiry,
    CateringPackage,
    CateringVerificationCode,
    UserStub,
)
from app.schemas.catering_schemas import AuditLogOut, CateringBookingOut

logger = logging.getLogger(__name__)


def encode_food_requirements(reqs: list[Any]) -> str:
    return json.dumps([r.model_dump() if hasattr(r, "model_dump") else r for r in reqs], ensure_ascii=False)


def decode_food_requirements(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def compute_package_price(pricing_method: str, base_price: float, guest_count: int) -> float:
    """Compute total price for a package.

    ``base_price`` is an all-inclusive rate that covers food, service, and taxes.
    When ``pricing_method`` is ``"fixed"`` the base price is returned as-is
    regardless of guest count; for ``"per_guest"`` it is multiplied by guest_count.
    """
    if pricing_method == "fixed":
        return float(base_price)
    return round(float(base_price) * guest_count, 2)


def compute_derived_quantity(item_key: str, guest_count: int, ratios: list) -> int:
    """Compute the derived quantity for an item based on package ratios.

    Args:
        item_key: e.g. 'chafing_dish', 'table', 'server', 'setup_staff'
        guest_count: number of guests
        ratios: list of PackageDerivedRatio objects (or dicts with item_key, per_guests, minimum)
    Returns:
        Derived quantity (integer, floored by minimum).
    """
    for r in ratios:
        rk = r.item_key if hasattr(r, "item_key") else r.get("item_key")
        if rk == item_key:
            pg = r.per_guests if hasattr(r, "per_guests") else r.get("per_guests", 1)
            mn = r.minimum if hasattr(r, "minimum") else r.get("minimum", 0)
            return max(mn, -(-guest_count // pg))  # ceil division
    return 0


def compute_premade_total(pkg, guest_count: int, db=None, org_id=None) -> tuple[float, list[dict]]:
    """Compute server-side total for a premade package selection.

    Returns (total, derived_items) where derived_items is a list of dicts
    describing the computed quantities for display/storage.
    """
    base_total = compute_package_price(pkg.pricing_method, pkg.base_price, guest_count)
    derived_items = []

    if db and org_id:
        from app.models.catering_models import PackageDerivedRatio
        ratios = db.query(PackageDerivedRatio).filter(
            PackageDerivedRatio.package_id == pkg.id,
            PackageDerivedRatio.organization_id == org_id,
            PackageDerivedRatio.deleted_at.is_(None),
        ).all()
    else:
        ratios = []

    for ratio in ratios:
        qty = compute_derived_quantity(ratio.item_key, guest_count, ratios)
        derived_items.append({
            "item_key": ratio.item_key,
            "quantity": qty,
            "per_guests": ratio.per_guests,
            "minimum": ratio.minimum,
        })

    return round(base_total, 2), derived_items


def _price_catalog_ids(
    db, org_id, catalog_ids: list, guest_count: int,
    quantities: dict | None = None,
) -> tuple[float, list[dict]]:
    """Price a set of catalog selections (dishes/equipment/staff).

    Shared by custom-mode totals and premade-package add-ons so both use the
    exact same per_guest/flat pricing rules. ``quantities`` maps str(id) ->
    quantity for flat-priced items (per_guest items are always priced x
    guest_count regardless of quantity). Returns (total, itemized details).
    """
    if not catalog_ids:
        return 0.0, []

    from uuid import UUID as _UUID
    from app.models.catering_models import CateringMenuItem, CateringEquipment, CateringStaffMember

    quantities = quantities or {}
    total = 0.0
    item_details = []

    menu_items = {
        str(mi.id): mi for mi in
        db.query(CateringMenuItem).filter(
            CateringMenuItem.organization_id == org_id,
            CateringMenuItem.id.in_([_UUID(str(sid)) for sid in catalog_ids]),
            CateringMenuItem.deleted_at.is_(None),
            CateringMenuItem.is_active.is_(True),
        ).all()
    }
    equipment_items = {
        str(eq.id): eq for eq in
        db.query(CateringEquipment).filter(
            CateringEquipment.organization_id == org_id,
            CateringEquipment.id.in_([_UUID(str(sid)) for sid in catalog_ids]),
            CateringEquipment.deleted_at.is_(None),
            CateringEquipment.is_active.is_(True),
        ).all()
    }
    staff_items = {
        str(st.id): st for st in
        db.query(CateringStaffMember).filter(
            CateringStaffMember.organization_id == org_id,
            CateringStaffMember.id.in_([_UUID(str(sid)) for sid in catalog_ids]),
            CateringStaffMember.deleted_at.is_(None),
            CateringStaffMember.is_active.is_(True),
        ).all()
    }

    for sid in catalog_ids:
        sid_str = str(sid)
        item_total = 0.0
        item_type = ""
        item_name = ""
        pricing_unit = ""
        unit_price = 0.0

        if sid_str in menu_items:
            mi = menu_items[sid_str]
            item_type = "dish"
            item_name = mi.name
            pricing_unit = mi.pricing_unit
            unit_price = float(mi.price)
        elif sid_str in equipment_items:
            eq = equipment_items[sid_str]
            item_type = "equipment"
            item_name = eq.name
            pricing_unit = eq.pricing_unit
            unit_price = float(eq.unit_cost)
        elif sid_str in staff_items:
            st = staff_items[sid_str]
            item_type = "staff"
            item_name = st.name
            pricing_unit = st.pricing_unit
            unit_price = float(st.rate)
        else:
            continue

        if pricing_unit == "per_guest":
            qty = 1
            item_total = unit_price * guest_count
        else:
            qty = max(1, int(quantities.get(sid_str, 1)))
            item_total = unit_price * qty

        total += item_total
        item_details.append({
            "id": sid_str,
            "name": item_name,
            "item_type": item_type,
            "pricing_unit": pricing_unit,
            "quantity": qty,
            "unit_price": round(unit_price, 2),
            "line_total": round(item_total, 2),
        })

    return round(total, 2), item_details


def compute_custom_total(db, org_id, selected_catalog_ids: list, guest_count: int) -> tuple[float, list[dict]]:
    """Compute server-side total for a custom package selection.

    Loads catalog items by ID and computes price based on pricing_unit.
    Returns (total, item_details) where item_details is itemized breakdown.
    """
    return _price_catalog_ids(db, org_id, selected_catalog_ids, guest_count)


def compute_inquiry_total(
    db, org_id, package, package_mode: str | None,
    guest_count: int, selected_catalog_ids: list | None = None,
    addon_selections: list[dict] | None = None,
) -> tuple[float, bool, list[dict]]:
    """Server-side inquiry total computation.

    ``addon_selections`` is a list of {"catalog_item_id": UUID, "quantity": int}
    for premade-package add-ons. Returns (server_total, price_mismatch_flag,
    derived_items). The mismatch flag is True if derived items are computed but
    not priced.
    """
    addon_selections = addon_selections or []
    if package and package_mode == "default":
        total, derived = compute_premade_total(package, guest_count, db=db, org_id=org_id)
        if addon_selections:
            addon_total, addon_details = _price_catalog_ids(
                db, org_id,
                [a["catalog_item_id"] for a in addon_selections],
                guest_count,
                quantities={str(a["catalog_item_id"]): a.get("quantity", 1) for a in addon_selections},
            )
            total = round(total + addon_total, 2)
            derived = derived + addon_details
        return total, False, derived
    elif package_mode == "custom" and selected_catalog_ids:
        total, details = compute_custom_total(db, org_id, selected_catalog_ids, guest_count)
        return total, False, details
    else:
        return 0.0, False, []


def suggested_price(pkg: Any, guest_count: int) -> float:
    if pkg is None:
        return 0.0
    return compute_package_price(pkg.pricing_method, pkg.base_price, guest_count)


def staffing_from_counts(waiter: int, bartender: int, chef: int, kitchen: int, support: int) -> dict[str, int]:
    return {
        "waiter_count": waiter,
        "bartender_count": bartender,
        "chef_count": chef,
        "kitchen_staff_count": kitchen,
        "support_crew_count": support,
    }


def format_event_location(
    event_address: str | None,
    venue_name: str | None = None,
    location_floor: str | None = None,
    room_hall: str | None = None,
    landmark: str | None = None,
    delivery_instructions: str | None = None,
) -> str | None:
    """Build a single carried-location block for a booking from the inquiry fields."""
    if not event_address:
        return None
    lines = [event_address.strip()]
    if venue_name:
        lines.append(f"Venue: {venue_name.strip()}")
    if location_floor:
        lines.append(f"Floor: {location_floor.strip()}")
    if room_hall:
        lines.append(f"Room / function hall: {room_hall.strip()}")
    if landmark:
        lines.append(f"Near: {landmark.strip()}")
    if delivery_instructions:
        lines.append(delivery_instructions.strip())
    return "\n".join(lines)


def payment_summary(db, org_id: UUID, booking_ids: list[UUID]) -> dict[UUID, float]:
    """booking_id -> total paid across non-deleted payments AND paid bills.

    A bill marked as paid contributes toward the booking's amount paid exactly
    like a payment record, so the billing and payment-recording flows converge
    on the same booking.payment_status instead of contradicting each other.
    """
    from sqlalchemy import func

    from app.models.catering_models import CateringBill, CateringPayment

    ids = [b for b in (booking_ids or []) if b is not None]
    if not ids:
        return {}
    totals: dict[UUID, float] = {}
    payment_rows = (
        db.query(CateringPayment.booking_id, func.coalesce(func.sum(CateringPayment.amount), 0))
        .filter(
            CateringPayment.organization_id == org_id,
            CateringPayment.booking_id.in_(ids),
            CateringPayment.deleted_at.is_(None),
        )
        .group_by(CateringPayment.booking_id)
        .all()
    )
    for booking_id, amount in payment_rows:
        totals[booking_id] = totals.get(booking_id, 0.0) + float(amount)
    bill_rows = (
        db.query(CateringBill.booking_id, func.coalesce(func.sum(CateringBill.total), 0))
        .filter(
            CateringBill.organization_id == org_id,
            CateringBill.booking_id.in_(ids),
            CateringBill.deleted_at.is_(None),
            CateringBill.status == "paid",
        )
        .group_by(CateringBill.booking_id)
        .all()
    )
    for booking_id, amount in bill_rows:
        totals[booking_id] = totals.get(booking_id, 0.0) + float(amount)
    return totals


def recompute_payment_status(db, org_id: UUID, booking_id: UUID) -> None:
    """Recompute a booking's payment_status from payments + paid bills, then commit.

    Shared by the payment-recording flow (after_write) and the billing mark-paid
    flow so both converge on the same stored booking.payment_status.
    """
    from app.models.catering_models import CateringBooking

    booking = (
        db.query(CateringBooking)
        .filter(
            CateringBooking.id == booking_id,
            CateringBooking.organization_id == org_id,
        )
        .first()
    )
    if not booking:
        return
    paid = payment_summary(db, org_id, [booking_id]).get(booking_id, 0.0)
    total = float(booking.total_amount or 0)
    if paid <= 0:
        booking.payment_status = "unpaid"
    elif paid < total:
        booking.payment_status = "partially_paid"
    else:
        booking.payment_status = "paid"
    db.commit()


def booking_payment_amounts(db, org_id: UUID, booking: Any) -> tuple[float, float]:
    """(amount_paid, remaining_balance) for a single booking."""
    paid = payment_summary(db, org_id, [booking.id]).get(booking.id, 0.0)
    total = float(booking.total_amount or 0)
    return round(paid, 2), round(total - paid, 2)


def booking_out(db, org_id: UUID, booking: Any) -> CateringBookingOut:
    """CateringBookingOut with automatically computed amount paid / balance."""
    paid, remaining = booking_payment_amounts(db, org_id, booking)
    out = CateringBookingOut.model_validate(booking)
    out.amount_paid = paid
    out.remaining_balance = remaining
    return out


def booking_out_list(db, org_id: UUID, bookings: list[Any]) -> list[CateringBookingOut]:
    """CateringBookingOut list with automatically computed amount paid / balance."""
    totals = payment_summary(db, org_id, [b.id for b in bookings])
    outs: list[CateringBookingOut] = []
    for b in bookings:
        paid = totals.get(b.id, 0.0)
        out = CateringBookingOut.model_validate(b)
        out.amount_paid = round(paid, 2)
        out.remaining_balance = round(float(b.total_amount or 0) - paid, 2)
        outs.append(out)
    return outs


# ---- audit log ----

def log_audit(
    db,
    organization_id: UUID,
    entity_type: str,
    entity_id: UUID | None,
    entity_reference: str | None,
    action: str,
    current_user: Any,
    summary: str | None = None,
    actor_role: str | None = None,
) -> CateringAuditLog:
    """Append a single row to the audit log.

    ``current_user`` may be a ``UserStub`` (internal endpoints) or ``None``
    (public / customer actions, in which case ``actor_role`` should describe
    the actor, e.g. ``"customer"``). The row is only ``add``-ed — the caller's
    surrounding transaction commits it together with the mutation it records.
    """
    actor_id = getattr(current_user, "id", None) if current_user is not None else None
    role = actor_role or (getattr(current_user, "role", None) if current_user is not None else "customer")
    entry = CateringAuditLog(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_reference=(entity_reference or "")[:255],
        action=action,
        actor_id=actor_id,
        actor_role=role or None,
        summary=summary,
    )
    db.add(entry)
    return entry


def audit_log_out(db, entries: list[CateringAuditLog]) -> list[AuditLogOut]:
    """Serialize audit rows to AuditLogOut, resolving actor emails in one query."""
    actor_ids = {e.actor_id for e in entries if e.actor_id}
    emails: dict[UUID, str] = {}
    if actor_ids:
        rows = db.query(UserStub.id, UserStub.email).filter(UserStub.id.in_(actor_ids)).all()
        emails = {user_id: email for user_id, email in rows}
    return [
        AuditLogOut(
            id=e.id,
            organization_id=e.organization_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            entity_reference=e.entity_reference,
            action=e.action,
            actor_id=e.actor_id,
            actor_role=e.actor_role,
            actor_email=emails.get(e.actor_id),
            summary=e.summary,
            created_at=e.created_at,
        )
        for e in entries
    ]


def recent_booking_activity(db, org_id: UUID, booking_id: UUID, limit: int = 10) -> list[CateringAuditLog]:
    """Audit rows relevant to a booking: its own events, the linked quotation's
    events, plus those of its booking-scoped children (payments, bills,
    deliveries, guest counts, food requirements, staff / equipment assignments),
    newest first."""
    from sqlalchemy import and_, or_

    from app.models.catering_models import (
        CateringBill,
        CateringBooking,
        CateringDelivery,
        CateringEquipmentAssignment,
        CateringFoodRequirement,
        CateringGuestCount,
        CateringPayment,
        CateringStaffAssignment,
    )

    child_models: dict[str, Any] = {
        "guest_count": CateringGuestCount,
        "food_requirement": CateringFoodRequirement,
        "payment": CateringPayment,
        "bill": CateringBill,
        "delivery": CateringDelivery,
        "staff_assignment": CateringStaffAssignment,
        "equipment_assignment": CateringEquipmentAssignment,
    }
    filters = [CateringAuditLog.entity_id == booking_id]
    booking = db.query(CateringBooking.id, CateringBooking.quotation_id).filter(
        CateringBooking.id == booking_id,
        CateringBooking.organization_id == org_id,
    ).first()
    if booking and booking.quotation_id:
        filters.append(
            and_(
                CateringAuditLog.entity_type == "quotation",
                CateringAuditLog.entity_id == booking.quotation_id,
            )
        )
    for entity_type, model in child_models.items():
        ids = [row[0] for row in db.query(model.id).filter(model.booking_id == booking_id).all()]
        if ids:
            filters.append(
                and_(
                    CateringAuditLog.entity_type == entity_type,
                    CateringAuditLog.entity_id.in_(ids),
                )
            )
    return (
        db.query(CateringAuditLog)
        .filter(
            CateringAuditLog.organization_id == org_id,
            or_(*filters),
        )
        .order_by(CateringAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )


# ---- step-up email verification ----

VERIFICATION_TTL_MINUTES = 5
VERIFICATION_RATE_LIMIT_SECONDS = 30


def request_verification_code(
    db,
    user: Any,
    action: str,
    *,
    organization_id: UUID | None = None,
    target_user: Any = None,
) -> CateringVerificationCode:
    """Generate a 6-digit code, store only its hash, and email the code.

    Rate-limits to one request per 30s per user+action (429 otherwise) and
    invalidates any prior unused code for the same user+action. Email send
    failures are logged but never crash the request — the code row is still
    stored so the flow can be exercised (and tested) without SMTP.
    """
    now = datetime.now(timezone.utc)
    latest = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.user_id == user.id,
            CateringVerificationCode.action == action,
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .first()
    )
    if latest is not None:
        created = latest.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (now - created).total_seconds()
        if age < VERIFICATION_RATE_LIMIT_SECONDS:
            wait = int(VERIFICATION_RATE_LIMIT_SECONDS - age) + 1
            raise HTTPException(
                status_code=429,
                detail=f"A verification code was already sent. Try again in {wait}s.",
            )

    db.query(CateringVerificationCode).filter(
        CateringVerificationCode.user_id == user.id,
        CateringVerificationCode.action == action,
        CateringVerificationCode.used_at.is_(None),
    ).update({"used_at": now})

    code = f"{secrets.randbelow(1_000_000):06d}"
    row = CateringVerificationCode(
        user_id=user.id,
        action=action,
        code_hash=hash_password(code),
        expires_at=now + timedelta(minutes=VERIFICATION_TTL_MINUTES),
        used_at=None,
        created_at=now,
    )
    db.add(row)

    if organization_id is not None:
        log_audit(
            db,
            organization_id=organization_id,
            entity_type="user",
            entity_id=target_user.id if target_user is not None else user.id,
            entity_reference=(target_user.email if target_user is not None else user.email),
            action="verification_requested",
            current_user=user,
            summary=f"Verification code requested for {action}",
        )

    try:
        from app.email_service import email_service
        email_service.send_template(user.email, otp_verification, code=code, background=False)
    except Exception:
        logger.exception("Could not email verification code for %s (%s)", user.email, action)

    return row


def verify_code(
    db,
    user: Any,
    action: str,
    submitted_code: str,
    *,
    organization_id: UUID | None = None,
    target_user: Any = None,
) -> bool:
    """Validate the latest unused, unexpired code for user+action.

    On a match the code is marked ``used_at`` so it cannot be reused. Returns
    True/False; the caller turns a False into an HTTP 400.
    """
    now = datetime.now(timezone.utc)
    row = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.user_id == user.id,
            CateringVerificationCode.action == action,
            CateringVerificationCode.used_at.is_(None),
            CateringVerificationCode.expires_at > now,
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .first()
    )
    if row is None:
        return False
    if not verify_password(submitted_code, row.code_hash):
        return False
    row.used_at = now
    if organization_id is not None:
        log_audit(
            db,
            organization_id=organization_id,
            entity_type="user",
            entity_id=target_user.id if target_user is not None else user.id,
            entity_reference=(target_user.email if target_user is not None else user.email),
            action="verification_used",
            current_user=user,
            summary=f"Verification code used for {action}",
        )
    return True


# ---------------------------------------------------------------------------
# Customer billing verification (reference-keyed, no user account required)
# ---------------------------------------------------------------------------

BILLING_TOKEN_TTL_MINUTES = 15
BILLING_VERIFICATION_TTL_MINUTES = 5
BILLING_RATE_LIMIT_SECONDS = 30


def request_customer_billing_code(
    db,
    reference: str,
    customer_email: str,
    *,
    organization_id: UUID | None = None,
) -> CateringVerificationCode:
    """Generate a 6-digit code for a customer billing view, email it, store hash.

    Rate-limits to one request per 30s per reference. Returns the verification
    code row. Email failures are logged but do not crash the request.
    """
    now = datetime.now(timezone.utc)
    latest = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.reference_id == reference,
            CateringVerificationCode.action == "customer_billing",
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .first()
    )
    if latest is not None:
        created = latest.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (now - created).total_seconds()
        if age < BILLING_RATE_LIMIT_SECONDS:
            wait = int(BILLING_RATE_LIMIT_SECONDS - age) + 1
            raise HTTPException(
                status_code=429,
                detail=f"A verification code was already sent. Try again in {wait}s.",
            )

    db.query(CateringVerificationCode).filter(
        CateringVerificationCode.reference_id == reference,
        CateringVerificationCode.action == "customer_billing",
        CateringVerificationCode.used_at.is_(None),
    ).update({"used_at": now})

    code = f"{secrets.randbelow(1_000_000):06d}"
    row = CateringVerificationCode(
        reference_id=reference,
        action="customer_billing",
        code_hash=hash_password(code),
        expires_at=now + timedelta(minutes=BILLING_VERIFICATION_TTL_MINUTES),
        used_at=None,
        created_at=now,
    )
    db.add(row)

    if organization_id is not None:
        log_audit(
            db,
            organization_id=organization_id,
            entity_type="inquiry",
            entity_id=None,
            entity_reference=reference,
            action="billing_code_requested",
            current_user=None,
            summary=f"Billing verification code requested for {reference}",
        )

    from app.email_service import email_service
    email_service.send_template(customer_email, otp_verification, code=code, reference=reference)

    return row


def verify_customer_billing_code(
    db,
    reference: str,
    submitted_code: str,
) -> bool:
    """Validate the latest unused, unexpired billing code for a reference.

    On a match the code is marked used. Returns True/False.
    """
    now = datetime.now(timezone.utc)
    row = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.reference_id == reference,
            CateringVerificationCode.action == "customer_billing",
            CateringVerificationCode.used_at.is_(None),
            CateringVerificationCode.expires_at > now,
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .first()
    )
    if row is None:
        return False
    if not verify_password(submitted_code, row.code_hash):
        return False
    row.used_at = now
    return True


# ---------------------------------------------------------------------------
# Customer account email verification (reference-keyed, mirrors billing OTP)
# ---------------------------------------------------------------------------
# Customers are NOT ``users`` rows, so codes are keyed on ``reference_id`` =
# str(customer_id) with action='customer_verify' — the same table/mechanism
# used by the billing OTP flow, never a second verification table.
CUSTOMER_VERIFY_TTL_MINUTES = 10
CUSTOMER_VERIFY_RATE_LIMIT_SECONDS = 30


def request_customer_verification_code(
    db,
    customer_id: UUID,
    customer_email: str,
    *,
    organization_id: UUID | None = None,
) -> CateringVerificationCode:
    """Generate a 6-digit email-verification code for a customer account.

    Rate-limits to one request per 30s per customer and invalidates any prior
    unused code before issuing a new one. Email failures are logged but never
    crash the request — the code row is still stored.
    """
    now = datetime.now(timezone.utc)
    reference = str(customer_id)
    latest = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.reference_id == reference,
            CateringVerificationCode.action == "customer_verify",
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .first()
    )
    if latest is not None:
        created = latest.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (now - created).total_seconds()
        if age < CUSTOMER_VERIFY_RATE_LIMIT_SECONDS:
            wait = int(CUSTOMER_VERIFY_RATE_LIMIT_SECONDS - age) + 1
            raise HTTPException(
                status_code=429,
                detail=f"A verification code was already sent. Try again in {wait}s.",
            )

    db.query(CateringVerificationCode).filter(
        CateringVerificationCode.reference_id == reference,
        CateringVerificationCode.action == "customer_verify",
        CateringVerificationCode.used_at.is_(None),
    ).update({"used_at": now})

    code = f"{secrets.randbelow(1_000_000):06d}"
    row = CateringVerificationCode(
        reference_id=reference,
        action="customer_verify",
        code_hash=hash_password(code),
        expires_at=now + timedelta(minutes=CUSTOMER_VERIFY_TTL_MINUTES),
        used_at=None,
        created_at=now,
    )
    db.add(row)

    if organization_id is not None:
        log_audit(
            db,
            organization_id=organization_id,
            entity_type="customer",
            entity_id=customer_id,
            entity_reference=customer_email,
            action="verification_requested",
            current_user=None,
            summary="Customer email verification code requested",
        )

    from app.email_service import email_service
    email_service.send_template(
        customer_email,
        customer_verification,
        code=code,
        expires_minutes=CUSTOMER_VERIFY_TTL_MINUTES,
    )

    return row


def verify_customer_verification_code(
    db,
    customer_id: UUID,
    submitted_code: str,
) -> bool:
    """Validate the latest unused, unexpired verification code for a customer.

    On a match the code is marked used. Returns True/False.
    """
    now = datetime.now(timezone.utc)
    row = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.reference_id == str(customer_id),
            CateringVerificationCode.action == "customer_verify",
            CateringVerificationCode.used_at.is_(None),
            CateringVerificationCode.expires_at > now,
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .first()
    )
    if row is None:
        return False
    if not verify_password(submitted_code, row.code_hash):
        return False
    row.used_at = now
    return True


def create_billing_access_token(reference: str) -> str:
    """Mint a short-lived JWT scoped to reading billing data for *reference*."""
    from app.auth.auth import create_access_token
    return create_access_token(
        {"sub": f"billing:{reference}", "scope": "billing"},
        expires_delta=timedelta(minutes=BILLING_TOKEN_TTL_MINUTES),
    )


def decode_billing_access_token(token: str) -> str | None:
    """Decode a billing access token. Returns the reference string if valid, else None."""
    from app.config import get_settings
    settings = get_settings()
    try:
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            options={"verify_aud": True, "require_aud": True},
        )
        if payload.get("iss") != settings.JWT_ISSUER:
            return None
        sub = payload.get("sub", "")
        scope = payload.get("scope")
        if scope != "billing" or not sub.startswith("billing:"):
            return None
        return sub[len("billing:"):]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Inquiry short reference generator
# ---------------------------------------------------------------------------
INQUIRY_REF_MAX_ATTEMPTS = 10


def generate_inquiry_short_reference(db, event_date=None) -> str:
    """Human-friendly globally-unique inquiry reference: INQ-<year>-<4 digits>.

    Same check-and-retry pattern as ``_generate_bill_number`` in
    ``routers/billing.py``.  Year is cosmetic context from the event date;
    uniqueness is global via the unique ``short_reference`` column.
    """
    year = event_date.year if event_date else datetime.now(timezone.utc).year
    for _ in range(INQUIRY_REF_MAX_ATTEMPTS):
        candidate = f"INQ-{year}-{secrets.randbelow(10000):04d}"
        exists = db.query(CateringInquiry).filter(CateringInquiry.short_reference == candidate).first()
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="Could not generate inquiry reference")


def inquiry_reference(inquiry) -> str:
    """Return the human-friendly reference for an inquiry (e.g. INQ-2026-4837).

    Falls back to the UUID-based format if short_reference hasn't been set yet.
    """
    ref = getattr(inquiry, "short_reference", None)
    return ref if ref else f"INQ-{inquiry.id}"


# ---------------------------------------------------------------------------
# Booking requirements (pre-event task checklist)
# ---------------------------------------------------------------------------
# Derived-ratio item keys that represent physical equipment the venue setup
# needs. Staffing keys (server, setup_staff) are handled by staffing, not here.
_DERIVED_EQUIPMENT_LABELS = {
    "chafing_dish": "chafing dishes",
    "table": "buffet/round tables",
    "place_setting": "place settings",
}
_DUE_OFFSETS_DAYS = {"venue": 14, "equipment": 7, "other": 3}


def _requirement_due_date(event_date: datetime | None, category: str) -> date | None:
    """Due date = event date minus a category-specific lead time, never in the past."""
    if event_date is None:
        return None
    due = (event_date.date() if isinstance(event_date, datetime) else event_date) - timedelta(
        days=_DUE_OFFSETS_DAYS.get(category, 3)
    )
    today = datetime.now(timezone.utc).date()
    return due if due >= today else today


def generate_booking_requirements(db, org_id, booking, inquiry, equipment_picks=None) -> int:
    """Auto-generate the pre-event checklist for a freshly created booking.

    Driven by what the customer actually ordered:
    - a named/selected venue -> one 'venue' requirement
    - customer equipment picks (addon items copied to assignments) -> one
      'equipment' requirement per equipment type
    - package derived ratios for physical equipment -> one requirement each

    Returns the number of rows created. Idempotent per booking via
    (category, lower(description)) dedupe.
    """
    rows: list[tuple[str, str]] = []  # (category, description)

    venue_name = getattr(inquiry, "venue_name", None)
    selected_venue_id = getattr(inquiry, "selected_venue_id", None)
    if venue_name or selected_venue_id:
        label = (venue_name or "").strip() or "selected venue"
        rows.append(("venue", f"Confirm venue reservation: {label}"))

    delivery_instructions = getattr(inquiry, "delivery_instructions", None)
    if delivery_instructions and delivery_instructions.strip():
        rows.append(("venue", f"Delivery instructions: {delivery_instructions.strip()[:200]}"))

    if equipment_picks is None:
        equipment_picks = {}
    if equipment_picks:
        eq_ids = [eid for eid in equipment_picks.keys()]
        names = {
            e.id: e.name
            for e in db.query(CateringEquipment).filter(
                CateringEquipment.organization_id == org_id,
                CateringEquipment.id.in_(eq_ids),
            ).all()
        }
        for eid, qty in equipment_picks.items():
            name = names.get(eid, "Equipment")
            rows.append(("equipment", f"Reserve {max(1, int(qty))}\u00d7 {name}"))

    package_id = getattr(inquiry, "catering_package_id", None)
    guest_count = getattr(booking, "guest_count", 0) or 0
    if package_id:
        pkg = db.query(CateringPackage).filter(
            CateringPackage.id == package_id,
            CateringPackage.organization_id == org_id,
            CateringPackage.deleted_at.is_(None),
        ).first()
        if pkg:
            for ratio in pkg.derived_ratios:
                if ratio.deleted_at is not None:
                    continue
                label = _DERIVED_EQUIPMENT_LABELS.get(ratio.item_key)
                if not label:
                    continue
                qty = compute_derived_quantity(ratio.item_key, guest_count, [ratio])
                if qty > 0:
                    rows.append(("equipment", f"Prepare {qty}\u00d7 {label}"))

    existing = {
        (r.category, (r.description or "").lower())
        for r in db.query(BookingRequirement).filter(
            BookingRequirement.booking_id == booking.id,
            BookingRequirement.deleted_at.is_(None),
        ).all()
    }
    created = 0
    for category, description in rows:
        key = (category, description.lower())
        if key in existing:
            continue
        existing.add(key)
        db.add(BookingRequirement(
            organization_id=org_id,
            booking_id=booking.id,
            description=description[:255],
            category=category,
            due_date=_requirement_due_date(getattr(booking, "event_date", None), category),
            status="pending",
        ))
        created += 1
    if created:
        db.flush()
    return created


def flip_overdue_requirements(db: Session, org_id: UUID) -> int:
    """Flip pending requirements past their due_date to overdue.

    Cheap enough to run on every dashboard / requirements list load.
    Returns the number of rows flipped.
    """
    today = datetime.now(timezone.utc).date()
    rows = db.query(BookingRequirement).filter(
        BookingRequirement.organization_id == org_id,
        BookingRequirement.deleted_at.is_(None),
        BookingRequirement.status == "pending",
        BookingRequirement.due_date.is_not(None),
        BookingRequirement.due_date < today,
    ).all()
    for r in rows:
        r.status = "overdue"
    if rows:
        db.commit()
    return len(rows)


def requirement_out(r: BookingRequirement) -> dict:
    """Serialize a requirement row (booking context added separately by routers)."""
    return {
        "id": r.id,
        "booking_id": r.booking_id,
        "description": r.description,
        "category": r.category,
        "due_date": r.due_date.isoformat() if r.due_date else None,
        "status": r.status,
        "completed_by": r.completed_by,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
