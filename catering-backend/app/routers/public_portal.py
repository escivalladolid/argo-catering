"""Public customer portal endpoints.

The customer portal is an unauthenticated, capability-based surface. It is
narrowly scoped to the minimum operations a customer needs:

    * browse active packages and view package details (default / customization)
    * submit an inquiry (default package or controlled customization)
    * look up the status of their own inquiry (by its non-guessable reference)
    * view their quotation and accept / decline it

Security notes:
    * No internal endpoint is opened up; these are separate, public routes.
    * Every record is addressed by a non-guessable reference (UUIDv4) rather
      than a sequential id, so records cannot be enumerated.
    * The organization is resolved server-side from configuration / the
      database and is NEVER taken from the client, preserving tenant isolation.
    * Customer responses only contain customer-safe fields (no organization
      ids, user ids, audit columns, staff data, payments, or billing).
    * Customers can only select dishes configured on their package and
      currently available. Unavailable dishes are rejected (custom mode) or
      flagged for manager review (default mode). Staffing requests are
      quantity-only and availability warnings are internal.
    * Quotation acceptance / rejection reuse the exact same backend business
      logic as the internal endpoints (see app.routers.quotations) so the
      booking is always created by the backend, once.
"""
from datetime import datetime, timedelta, timezone

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.flow import decode_food_requirements, encode_food_requirements, generate_inquiry_short_reference, inquiry_reference, log_audit, payment_summary, request_customer_billing_code, verify_customer_billing_code, create_billing_access_token, decode_billing_access_token, compute_inquiry_total, _price_catalog_ids, suggested_price, compute_premade_total
from app.models.catering_models import (
    CateringBooking,
    CateringEquipment,
    CateringInquiry,
    CateringInquiryItem,
    CateringMenu,
    CateringMenuItem,
    CateringPackage,
    CateringPayment,
    CateringQuotation,
    CateringStaffMember,
    CateringVerificationCode,
    CateringVenue,
    OrganizationStub,
    PackageDerivedRatio,
    VenueBooking,
)
from app.routers.quotations import perform_accept, perform_reject
from app.routers.staffing import staffing_availability, staffing_shortfall_warning
from app.schemas.catering_schemas import (
    CustomerBookingBillingOut,
    CustomerBookingOut,
    CustomerBillingCodeRequestOut,
    CustomerBillingVerifyOut,
    CustomerCancellationOut,
    CustomerCatalogItemOut,
    CustomerCatalogOut,
    CustomerDerivedRatioOut,
    CustomerInquiryCreatedOut,
    CustomerInquirySubmit,
    CustomerInquirySummary,
    CustomerItemOut,
    CustomerAddonLineOut,
    DerivedInclusionOut,
    CustomerPackageDetailOut,
    CustomerPackageItemOut,
    CustomerPackageGroupOut,
    CustomerPackageOut,
    CustomerPaymentOut,
    CustomerPaymentSubmit,
    CustomerQuotationAcceptIn,
    CustomerQuotationOut,
    CustomerResendLinkRequest,
    CustomerStatusOut,
    CustomerVenueOut,
    FoodRequirementOut,
    StaffingOut,
)

router = APIRouter(prefix="/public", tags=["Public Portal"])

NOT_FOUND = "We couldn't find an inquiry with that reference."

# Customer inquiries that would otherwise be auto-approved are held for staff
# review when the requested staffing exceeds availability on the event date.
# Events inside this window are exempt — they are near-term and pass straight
# through as auto_approved so the team can act on them immediately.
REVIEW_EXEMPT_DAYS = 7


def get_public_org_id(db: Session = Depends(get_db)) -> UUID:
    """Resolve the tenant for the public portal (server-side, single-tenant)."""
    configured = get_settings().PUBLIC_ORGANIZATION_ID
    if configured:
        try:
            return UUID(str(configured).strip())
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The public portal is not configured correctly. Please try again later.",
            )
    org_ids = db.query(OrganizationStub.id).limit(2).all()
    if len(org_ids) == 1:
        return UUID(str(org_ids[0][0]))
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="The public portal is not available right now. Please try again later.",
    )


def parse_reference(raw: str | None, prefix: str) -> UUID | None:
    """Parse ``PREFIX-<uuid>`` (or a bare uuid) into a UUID, or None."""
    if not raw:
        return None
    value = raw.strip()
    if value.upper().startswith(prefix + "-"):
        value = value[len(prefix) + 1:]
    value = value.strip().lower().replace(" ", "")
    try:
        return UUID(value)
    except (ValueError, TypeError, AttributeError):
        return None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)


def _require_access_token(inquiry: CateringInquiry, token: str) -> None:
    """Validate the caller holds the inquiry's access token. Raises 403 on mismatch."""
    if not secrets.compare_digest(inquiry.access_token, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing access token.",
        )


def _get_inquiry(db: Session, org_id: UUID, reference: str) -> CateringInquiry:
    """Resolve an inquiry by its reference (short or UUID-based).

    Tries UUID parse first (backward compat with old emailed links), then
    falls back to an exact match on ``short_reference``.
    """
    inquiry_uuid = parse_reference(reference, "INQ")
    if inquiry_uuid is not None:
        inquiry = db.query(CateringInquiry).filter(
            CateringInquiry.id == inquiry_uuid,
            CateringInquiry.organization_id == org_id,
            CateringInquiry.deleted_at.is_(None),
        ).first()
        if inquiry:
            return inquiry

    # Fallback: try short_reference (exact match on the full reference string).
    inquiry = db.query(CateringInquiry).filter(
        CateringInquiry.short_reference == reference.strip(),
        CateringInquiry.organization_id == org_id,
        CateringInquiry.deleted_at.is_(None),
    ).first()
    if inquiry:
        return inquiry

    raise _not_found()


def _visible_quotation(db: Session, org_id: UUID, inquiry_id: UUID) -> CateringQuotation | None:
    """The customer-facing quotation (sent / accepted / rejected), newest first."""
    return (
        db.query(CateringQuotation)
        .filter(
            CateringQuotation.inquiry_id == inquiry_id,
            CateringQuotation.organization_id == org_id,
            CateringQuotation.deleted_at.is_(None),
            CateringQuotation.status.in_(["sent", "accepted", "rejected"]),
        )
        .order_by(CateringQuotation.created_at.desc())
        .first()
    )


def _booking_for(db: Session, org_id: UUID, quotation: CateringQuotation | None) -> CateringBooking | None:
    if not quotation:
        return None
    return (
        db.query(CateringBooking)
        .filter(
            CateringBooking.quotation_id == quotation.id,
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
        )
        .first()
    )


def _package_snapshot(db: Session, org_id: UUID, package_id: UUID | None) -> tuple[str | None, str | None]:
    """Return (name, description) for a package the customer can see, or (None, None)."""
    if not package_id:
        return None, None
    pkg = db.query(CateringPackage).filter(
        CateringPackage.id == package_id,
        CateringPackage.organization_id == org_id,
    ).first()
    if not pkg:
        return None, None
    return pkg.name, pkg.description


def _pricing_method(db: Session, org_id: UUID, package_id: UUID | None) -> str | None:
    if not package_id:
        return None
    value = (
        db.query(CateringPackage.pricing_method)
        .filter(CateringPackage.id == package_id, CateringPackage.organization_id == org_id)
        .scalar()
    )
    return value


def _require_active_package(db: Session, org_id: UUID, package_id: UUID | None) -> CateringPackage | None:
    """Validate a customer-picked package belongs to the org and is active. None stays None."""
    if package_id is None:
        return None
    pkg = db.query(CateringPackage).filter(
        CateringPackage.id == package_id,
        CateringPackage.organization_id == org_id,
        CateringPackage.deleted_at.is_(None),
        CateringPackage.is_active.is_(True),
    ).first()
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected package is not available. Please try again or submit without a package.",
        )
    return pkg


def _availability_map(db: Session, org_id: UUID, item_ids: set[UUID]) -> dict[UUID, bool]:
    """item_id -> available (item active AND menu active)."""
    if not item_ids:
        return {}
    rows = (
        db.query(CateringMenuItem.id, CateringMenuItem.is_active, CateringMenu.is_active)
        .join(CateringMenu, CateringMenuItem.menu_id == CateringMenu.id)
        .filter(
            CateringMenuItem.organization_id == org_id,
            CateringMenuItem.id.in_(item_ids),
            CateringMenuItem.deleted_at.is_(None),
            CateringMenu.deleted_at.is_(None),
        )
        .all()
    )
    return {row[0]: bool(row[1] and row[2]) for row in rows}


def _item_info(db: Session, org_id: UUID, item_ids: set[UUID]) -> dict[UUID, tuple[str, str | None]]:
    """item_id -> (name, category)."""
    if not item_ids:
        return {}
    rows = (
        db.query(CateringMenuItem.id, CateringMenuItem.name, CateringMenuItem.category)
        .filter(CateringMenuItem.organization_id == org_id, CateringMenuItem.id.in_(item_ids), CateringMenuItem.deleted_at.is_(None))
        .all()
    )
    return {row[0]: (row[1], row[2]) for row in rows}


def _validate_and_parse_selections(
    db: Session,
    org_id: UUID,
    pkg: CateringPackage | None,
    payload: CustomerInquirySubmit,
) -> tuple[list[dict], list[str]]:
    """Validate customer selections against the package and availability.

    Returns (item_snapshots, warnings). Raises HTTPException for invalid
    selections a customer is not allowed to make.
    """
    warnings: list[str] = []

    if pkg is None:
        if payload.package_mode or payload.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customizing dishes requires a selected package.",
            )
        return [], warnings

    pkg_items = {pi.menu_item_id: pi for pi in pkg.items}
    availability = _availability_map(db, org_id, set(pkg_items.keys()))
    info = _item_info(db, org_id, set(pkg_items.keys()))

    def _name(item_id: UUID) -> str:
        return info.get(item_id, ("", None))[0]

    for sel in payload.items:
        pi = pkg_items.get(sel.menu_item_id)
        if pi is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A selected dish is not part of this package.",
            )
        if not availability.get(sel.menu_item_id, False):
            if payload.package_mode == "custom":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{_name(sel.menu_item_id)} is currently unavailable.",
                )
            warnings.append(f"{_name(sel.menu_item_id)} is currently unavailable.")

    if payload.package_mode == "custom":
        groups = sorted(pkg.groups, key=lambda g: (g.sort_order, g.name))
        for grp in groups:
            option_ids = {o.menu_item_id for o in grp.options}
            selected = [s for s in payload.items if s.menu_item_id in option_ids]
            if len(selected) < grp.min_select:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Please choose at least {grp.min_select} option(s) from '{grp.name}'.",
                )
            if grp.max_select and len(selected) > grp.max_select:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Please choose at most {grp.max_select} option(s) from '{grp.name}'.",
                )
        if not pkg.has_customization and any(pi.kind == "option" for pi in pkg.items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This package cannot be customized.",
            )

    mode = payload.package_mode or "default"
    snapshots: list[dict] = []
    for idx, sel in enumerate(sorted(payload.items, key=lambda s: s.quantity)):
        pi = pkg_items.get(sel.menu_item_id)
        if mode == "custom":
            kind = "custom"
        else:
            kind = pi.kind if pi and pi.kind != "option" else "custom"
        snapshots.append(
            {
                "menu_item_id": sel.menu_item_id,
                "item_name": _name(sel.menu_item_id),
                "category": info.get(sel.menu_item_id, (None, None))[1],
                "group_name": sel.group_name,
                "kind": kind,
                "quantity": sel.quantity,
                "unit": sel.unit or (pi.unit if pi else "serving"),
                "sort_order": idx,
            }
        )
    return snapshots, warnings


def _validate_addon_selections(db, org_id, pkg, payload) -> list[dict]:
    """Validate optional add-ons on a premade package selection.

    Add-ons reuse the public catalog (dishes/equipment/staff) and are stored
    as CateringInquiryItem rows with kind='addon' so downstream consumers
    (booking detail, quotation breakdown) read them exactly like other
    inquiry items. Only allowed in default (premade) mode.

    Returns addon item snapshots. Raises HTTPException for invalid selections.
    """
    addons = payload.addon_catalog_ids or []
    if not addons:
        return []
    if pkg is None or payload.package_mode == "custom":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add-ons can only be added to a premade package selection.",
        )
    if len(addons) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many add-ons selected.",
        )
    ids = [a.catalog_item_id for a in addons]
    if len({str(i) for i in ids}) != len(ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate add-on selections are not allowed.",
        )

    from app.models.catering_models import CateringEquipment, CateringStaffMember

    dishes = {
        str(mi.id): mi.name for mi in
        db.query(CateringMenuItem.id, CateringMenuItem.name)
        .join(CateringMenu, CateringMenuItem.menu_id == CateringMenu.id)
        .filter(
            CateringMenuItem.organization_id == org_id,
            CateringMenuItem.id.in_(ids),
            CateringMenuItem.deleted_at.is_(None),
            CateringMenuItem.is_active.is_(True),
            CateringMenu.deleted_at.is_(None),
            CateringMenu.is_active.is_(True),
        ).all()
    }
    equipment = {
        str(eq.id): eq.name for eq in
        db.query(CateringEquipment.id, CateringEquipment.name)
        .filter(
            CateringEquipment.organization_id == org_id,
            CateringEquipment.id.in_(ids),
            CateringEquipment.deleted_at.is_(None),
            CateringEquipment.is_active.is_(True),
        ).all()
    }
    staff = {
        str(st.id): st.name for st in
        db.query(CateringStaffMember.id, CateringStaffMember.name)
        .filter(
            CateringStaffMember.organization_id == org_id,
            CateringStaffMember.id.in_(ids),
            CateringStaffMember.deleted_at.is_(None),
            CateringStaffMember.is_active.is_(True),
        ).all()
    }

    base_sort = len(payload.items)
    snapshots: list[dict] = []
    for idx, sel in enumerate(addons):
        sid = str(sel.catalog_item_id)
        if sid in dishes:
            item_type, name, unit = "dish", dishes[sid], "serving"
        elif sid in equipment:
            item_type, name, unit = "equipment", equipment[sid], "unit"
        elif sid in staff:
            item_type, name, unit = "staff", staff[sid], "person"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One of the selected add-ons is not available.",
            )
        snapshots.append(
            {
                "menu_item_id": UUID(sid) if item_type == "dish" else None,
                "catalog_item_id": sel.catalog_item_id,
                "item_name": name,
                "category": item_type,
                "group_name": None,
                "kind": "addon",
                "quantity": sel.quantity,
                "unit": unit,
                "sort_order": base_sort + idx,
            }
        )
    return snapshots


def _staffing_requested(payload: CustomerInquirySubmit) -> dict[str, int]:
    if not payload.staff:
        return {k: 0 for k in ("waiter_count", "bartender_count", "chef_count", "kitchen_staff_count", "support_crew_count")}
    return {
        "waiter_count": payload.staff.waiter_count,
        "bartender_count": payload.staff.bartender_count,
        "chef_count": payload.staff.chef_count,
        "kitchen_staff_count": payload.staff.kitchen_staff_count,
        "support_crew_count": payload.staff.support_crew_count,
    }


def _staffing_out(inquiry: CateringInquiry) -> StaffingOut:
    return StaffingOut(
        waiter_count=inquiry.waiter_count,
        bartender_count=inquiry.bartender_count,
        chef_count=inquiry.chef_count,
        kitchen_staff_count=inquiry.kitchen_staff_count,
        support_crew_count=inquiry.support_crew_count,
    )


def _customer_item_out(item: CateringInquiryItem) -> CustomerItemOut:
    return CustomerItemOut(
        name=item.item_name,
        category=item.category,
        group_name=item.group_name,
        quantity=item.quantity,
        unit=item.unit,
        kind=item.kind,
    )


def _included_items_for(db: Session, org_id: UUID, inquiry: CateringInquiry) -> list[CustomerItemOut]:
    """Complete package-fixed contents shown to the customer.

    Premade mode: synthesized from the package's own items (a plain premade
    inquiry stores no dish rows — the package defines them), deduped against
    any stored rows. Custom mode: the customer's selection rows as-is.
    Add-on rows are always excluded (they render under Added Extras).
    """
    stored = [_customer_item_out(i) for i in inquiry.items if getattr(i, "kind", "") != "addon"]
    if inquiry.package_mode == "custom" or not inquiry.catering_package_id:
        return stored
    pkg = db.query(CateringPackage).filter(
        CateringPackage.id == inquiry.catering_package_id,
        CateringPackage.organization_id == org_id,
        CateringPackage.deleted_at.is_(None),
    ).first()
    if not pkg:
        return stored
    from app.models.catering_models import CateringPackageItem
    pis = (
        db.query(CateringPackageItem)
        .filter(
            CateringPackageItem.package_id == pkg.id,
            CateringPackageItem.deleted_at.is_(None),
        )
        .order_by(CateringPackageItem.sort_order.asc())
        .all()
    )
    out: list[CustomerItemOut] = []
    seen_menu_ids = set()
    for pi in pis:
        if pi.menu_item_id:
            seen_menu_ids.add(pi.menu_item_id)
        if not pi.item_name:
            continue
        out.append(CustomerItemOut(
            name=pi.item_name,
            category=None,
            group_name=pi.group.name if pi.group else None,
            quantity=pi.quantity,
            unit=pi.unit,
            kind=pi.kind,
        ))
    for item_out in stored:
        row = next((i for i in inquiry.items if i.item_name == item_out.name and getattr(i, "kind", "") != "addon"), None)
        if row is not None and row.menu_item_id in seen_menu_ids:
            continue
        out.append(item_out)
    return out


def _addons_breakout(db: Session, org_id: UUID, inquiry: CateringInquiry) -> list[CustomerAddonLineOut]:
    """Itemized priced breakdown of a customer's add-on selections.

    Uses the same shared catalog-pricing helper as submit-time totals and the
    accept-time copy pass so all three always agree on the numbers.
    """
    addon_rows = [i for i in inquiry.items if getattr(i, "kind", "") == "addon" and i.catalog_item_id]
    if not addon_rows:
        return []
    _, details = _price_catalog_ids(
        db, org_id,
        [i.catalog_item_id for i in addon_rows],
        inquiry.guest_count,
        quantities={str(i.catalog_item_id): (i.quantity or 1) for i in addon_rows},
    )
    return [
        CustomerAddonLineOut(
            name=d["name"],
            item_type=d["item_type"],
            quantity=d["quantity"],
            pricing_unit=d["pricing_unit"],
            line_total=float(d["line_total"]),
        )
        for d in details
    ]


def _customer_requirements(inquiry: CateringInquiry) -> list[FoodRequirementOut]:
    return [FoodRequirementOut(**r) for r in decode_food_requirements(inquiry.food_requirements_json)]


@router.get("/packages", response_model=list[CustomerPackageOut])
def public_packages(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Public catalog of active packages customers can pick from."""
    packages = (
        db.query(CateringPackage)
        .filter(
            CateringPackage.organization_id == org_id,
            CateringPackage.deleted_at.is_(None),
            CateringPackage.is_active.is_(True),
        )
        .order_by(CateringPackage.name.asc())
        .all()
    )
    all_item_ids = {pi.menu_item_id for pkg in packages for pi in pkg.items}
    item_info = _item_info(db, org_id, all_item_ids) if all_item_ids else {}
    return [
        CustomerPackageOut(
            id=pkg.id,
            name=pkg.name,
            description=pkg.description,
            base_price=float(pkg.base_price),
            pricing_method=pkg.pricing_method,
            has_customization=pkg.has_customization,
            min_pax=pkg.min_pax,
            max_pax=pkg.max_pax,
            service_style=pkg.service_style,
            dish_names=[
                item_info[pi.menu_item_id][0]
                for pi in sorted(pkg.items, key=lambda x: x.sort_order)
                if pi.kind == "included" and pi.menu_item_id in item_info
            ],
        )
        for pkg in packages
    ]


@router.get("/packages/{package_id}", response_model=CustomerPackageDetailOut)
def public_package_detail(
    package_id: UUID,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Public package detail: default / included dishes and customization groups."""
    pkg = _require_active_package(db, org_id, package_id)
    if not pkg:
        raise _not_found()

    availability = _availability_map(db, org_id, {pi.menu_item_id for pi in pkg.items})
    info = _item_info(db, org_id, {pi.menu_item_id for pi in pkg.items})

    def to_customer_item(pi) -> CustomerPackageItemOut:
        return CustomerPackageItemOut(
            item_id=pi.menu_item_id,
            name=info.get(pi.menu_item_id, ("", None))[0],
            quantity=pi.quantity,
            unit=pi.unit,
            available=availability.get(pi.menu_item_id, False),
        )

    default_items = [to_customer_item(pi) for pi in sorted(pkg.items, key=lambda x: x.sort_order) if pi.kind == "default"]
    included_items = [to_customer_item(pi) for pi in sorted(pkg.items, key=lambda x: x.sort_order) if pi.kind == "included"]
    groups = []
    for grp in sorted(pkg.groups, key=lambda g: (g.sort_order, g.name)):
        options = [to_customer_item(o) for o in sorted(grp.options, key=lambda x: x.sort_order)]
        groups.append(
            CustomerPackageGroupOut(
                id=grp.id,
                name=grp.name,
                min_select=grp.min_select,
                max_select=grp.max_select,
                options=options,
            )
        )
    ratios = (
        db.query(PackageDerivedRatio)
        .filter(
            PackageDerivedRatio.package_id == pkg.id,
            PackageDerivedRatio.organization_id == org_id,
            PackageDerivedRatio.deleted_at.is_(None),
        )
        .order_by(PackageDerivedRatio.item_key.asc())
        .all()
    )
    return CustomerPackageDetailOut(
        id=pkg.id,
        name=pkg.name,
        description=pkg.description,
        base_price=float(pkg.base_price),
        pricing_method=pkg.pricing_method,
        has_customization=pkg.has_customization,
        min_pax=pkg.min_pax,
        max_pax=pkg.max_pax,
        service_style=pkg.service_style,
        default_items=default_items,
        included_items=included_items,
        groups=groups,
        derived_ratios=[
            CustomerDerivedRatioOut(item_key=r.item_key, per_guests=r.per_guests, minimum=r.minimum)
            for r in ratios
        ],
    )


@router.get("/catalog-items", response_model=CustomerCatalogOut)
def public_catalog_items(
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Public catalog of dishes, equipment, and staff with pricing for custom builds.

    Rows flagged is_test_data (seeded by automated tests) never reach customers.
    """
    menu_items = (
        db.query(CateringMenuItem)
        .filter(
            CateringMenuItem.organization_id == org_id,
            CateringMenuItem.deleted_at.is_(None),
            CateringMenuItem.is_active.is_(True),
            CateringMenuItem.is_test_data.is_(False),
        )
        .order_by(CateringMenuItem.name.asc())
        .all()
    )
    equipment = (
        db.query(CateringEquipment)
        .filter(
            CateringEquipment.organization_id == org_id,
            CateringEquipment.deleted_at.is_(None),
            CateringEquipment.is_active.is_(True),
            CateringEquipment.is_test_data.is_(False),
        )
        .order_by(CateringEquipment.name.asc())
        .all()
    )
    staff = (
        db.query(CateringStaffMember)
        .filter(
            CateringStaffMember.organization_id == org_id,
            CateringStaffMember.deleted_at.is_(None),
            CateringStaffMember.is_active.is_(True),
            CateringStaffMember.is_test_data.is_(False),
        )
        .order_by(CateringStaffMember.name.asc())
        .all()
    )
    return CustomerCatalogOut(
        dishes=[
            CustomerCatalogItemOut(
                id=mi.id,
                name=mi.name,
                category=mi.category,
                price=float(mi.price),
                pricing_unit=mi.pricing_unit,
                item_type="dish",
            )
            for mi in menu_items
        ],
        equipment=[
            CustomerCatalogItemOut(
                id=eq.id,
                name=eq.name,
                category=eq.category,
                price=float(eq.unit_cost),
                pricing_unit=eq.pricing_unit,
                item_type="equipment",
            )
            for eq in equipment
        ],
        staff=[
            CustomerCatalogItemOut(
                id=st.id,
                name=st.name,
                category=st.role,
                price=float(st.rate),
                pricing_unit=st.pricing_unit,
                item_type="staff",
            )
            for st in staff
        ],
    )


@router.post("/inquiries", response_model=CustomerInquiryCreatedOut, status_code=status.HTTP_201_CREATED)
def create_public_inquiry(
    payload: CustomerInquirySubmit,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Public inquiry submission — validated, then persisted like the internal one."""
    pkg = _require_active_package(db, org_id, payload.catering_package_id)
    if pkg and payload.package_mode is None:
        payload.package_mode = "default"
    if payload.package_mode == "custom" and (pkg is None or not pkg.has_customization):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This package cannot be customized.",
        )

    if pkg and pkg.min_pax and payload.guest_count < pkg.min_pax:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{pkg.name} requires at least {pkg.min_pax} guests; you entered {payload.guest_count}.",
        )
    if pkg and pkg.max_pax and payload.guest_count > pkg.max_pax:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{pkg.name} supports at most {pkg.max_pax} guests; you entered {payload.guest_count}.",
        )

    # Resolve service_style: premade → from package; custom → from customer payload
    if payload.package_mode == "custom":
        service_style = payload.service_style
    else:
        service_style = getattr(pkg, "service_style", None) if pkg else payload.service_style

    snapshots, warnings = _validate_and_parse_selections(db, org_id, pkg, payload)
    addon_snapshots = _validate_addon_selections(db, org_id, pkg, payload)

    requested = _staffing_requested(payload)
    available = staffing_availability(db, org_id, payload.event_date)
    staff_warning = staffing_shortfall_warning(requested, available)

    flag_parts: list[str] = []
    flag_parts.extend(warnings)
    if staff_warning:
        flag_parts.append(staff_warning)

    near_term = payload.event_date <= datetime.now(timezone.utc) + timedelta(days=REVIEW_EXEMPT_DAYS)
    review_status = "pending_review" if (staff_warning and not near_term) else "auto_approved"

    venue_fee = payload.venue_fee or 0
    venue = None
    if payload.selected_venue_id:
        venue = db.query(CateringVenue).filter(
            CateringVenue.id == payload.selected_venue_id,
            CateringVenue.organization_id == org_id,
            CateringVenue.deleted_at.is_(None),
            CateringVenue.is_active.is_(True),
            CateringVenue.status == "active",
        ).first()
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected venue is not available.",
            )
        if venue_fee == 0:
            venue_fee = float(venue.fee)
        if payload.guest_count > venue.capacity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{venue.name} supports up to {venue.capacity} guests; you entered {payload.guest_count}.",
            )
        date_only = payload.event_date.replace(hour=0, minute=0, second=0, microsecond=0)
        conflict = db.query(VenueBooking).filter(
            VenueBooking.organization_id == org_id,
            VenueBooking.venue_id == venue.id,
            func.date(VenueBooking.event_date) == func.date(date_only),
            VenueBooking.deleted_at.is_(None),
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{venue.name} is already booked for {date_only.strftime('%B %d, %Y')}.",
            )

    server_total, price_mismatch, _derived = compute_inquiry_total(
        db, org_id, pkg, payload.package_mode,
        payload.guest_count, payload.selected_catalog_ids,
        addon_selections=[
            {"catalog_item_id": a.catalog_item_id, "quantity": a.quantity}
            for a in payload.addon_catalog_ids
        ] if addon_snapshots else None,
    )

    access_token = secrets.token_urlsafe(32)
    inquiry = CateringInquiry(
        organization_id=org_id,
        customer_name=payload.customer_name,
        customer_contact=payload.customer_contact,
        customer_email=payload.customer_email,
        access_token=access_token,
        short_reference=generate_inquiry_short_reference(db, payload.event_date),
        event_date=payload.event_date,
        event_time=payload.event_time,
        event_type=payload.event_type,
        event_address=payload.event_address,
        venue_name=payload.venue_name,
        venue_mode=payload.venue_mode,
        selected_venue_id=payload.selected_venue_id,
        venue_fee=venue_fee,
        location_floor=payload.location_floor,
        room_hall=payload.room_hall,
        landmark=payload.landmark,
        delivery_instructions=payload.delivery_instructions,
        guest_count=payload.guest_count,
        event_duration_hours=payload.event_duration_hours,
        catering_package_id=payload.catering_package_id,
        package_mode=payload.package_mode,
        service_style=service_style,
        requested_service_style=payload.requested_service_style,
        food_requirements_json=encode_food_requirements(payload.food_requirements),
        waiter_count=requested["waiter_count"],
        bartender_count=requested["bartender_count"],
        chef_count=requested["chef_count"],
        kitchen_staff_count=requested["kitchen_staff_count"],
        support_crew_count=requested["support_crew_count"],
        flag_note="; ".join(flag_parts) if flag_parts else None,
        notes=payload.notes,
        additional_notes=payload.additional_notes,
        dietary_notes=payload.dietary_notes,
        setup_notes=payload.setup_notes,
        estimated_total=payload.estimated_total,
        server_calculated_total=server_total,
        price_mismatch=price_mismatch,
        selected_catalog_ids=payload.selected_catalog_ids if payload.selected_catalog_ids else None,
        status="new",
        review_status=review_status,
    )
    db.add(inquiry)
    db.flush()
    if venue and payload.selected_venue_id:
        date_only = payload.event_date.replace(hour=0, minute=0, second=0, microsecond=0)
        db.add(VenueBooking(
            organization_id=org_id,
            venue_id=venue.id,
            inquiry_id=inquiry.id,
            event_date=date_only,
        ))
        db.flush()
    for snap in snapshots:
        inquiry.items.append(CateringInquiryItem(organization_id=org_id, **snap))
    for snap in addon_snapshots:
        inquiry.items.append(CateringInquiryItem(organization_id=org_id, **snap))
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        payload.customer_name,
        "created",
        None,
        f"Customer inquiry submitted by {payload.customer_name}",
        actor_role="customer",
    )
    db.commit()
    db.refresh(inquiry)

    from app.email_service import email_service
    from app.email_templates import inquiry_received
    base_url = get_settings().PUBLIC_BASE_URL.rstrip("/")
    inq_ref = inquiry_reference(inquiry)
    email_service.send_template(
        payload.customer_email,
        inquiry_received,
        name=payload.customer_name,
        reference=inq_ref,
        status_url=f"{base_url}/customer-portal.html?ref={inq_ref}&token={access_token}",
    )

    return CustomerInquiryCreatedOut(reference=inq_ref, access_token=access_token, created_at=inquiry.created_at)


# -- Resend status link (recovery for customers who lost the original email) --
# Same DB-cooldown pattern as billing codes (flow.request_customer_billing_code):
# ledger rows in catering_verification_codes with action='resend_link'.
RESEND_COOLDOWN_SECONDS = 60
RESEND_DAILY_MAX = 5
RESEND_MAX_INQUIRIES = 5
GENERIC_RESEND_MESSAGE = "If we found a matching inquiry, we've sent a link to that email."


@router.post("/inquiries/resend-link")
def resend_status_link(
    payload: CustomerResendLinkRequest,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Email the private tracking link(s) for inquiries tied to one address.

    The response NEVER reveals whether a match exists (anti-enumeration), and
    it is identical for zero matches. Emails always go to the stored
    ``customer_email`` of each matched inquiry — which is by definition the
    address that was looked up — and reuse each inquiry's existing
    ``access_token``; no token rotation.
    """
    email = payload.email.strip().lower()
    now = datetime.now(timezone.utc)

    recent = (
        db.query(CateringVerificationCode)
        .filter(
            CateringVerificationCode.action == "resend_link",
            CateringVerificationCode.reference_id == email,
            CateringVerificationCode.created_at >= now - timedelta(hours=24),
        )
        .order_by(CateringVerificationCode.created_at.desc())
        .all()
    )
    if recent:
        latest = recent[0].created_at
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        age = (now - latest).total_seconds()
        if age < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - age) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Please wait before requesting another email. Try again in {wait}s.",
            )
        if len(recent) >= RESEND_DAILY_MAX:
            raise HTTPException(
                status_code=429,
                detail="Too many resend requests for this email today. Please try again later.",
            )

    matches = (
        db.query(CateringInquiry)
        .filter(
            CateringInquiry.organization_id == org_id,
            func.lower(CateringInquiry.customer_email) == email,
        )
        .order_by(CateringInquiry.created_at.desc())
        .limit(RESEND_MAX_INQUIRIES)
        .all()
    )
    if matches:
        from app.email_service import email_service
        from app.email_templates import resend_link

        base_url = get_settings().PUBLIC_BASE_URL.rstrip("/")
        items = [
            {
                "reference": inquiry_reference(m),
                "event_date": m.event_date.strftime("%b %d, %Y") if m.event_date else "",
                # Sent to the inquiry's own stored address; reuses its existing token.
                "status_url": f"{base_url}/customer-portal.html?ref={inquiry_reference(m)}&token={m.access_token}",
            }
            for m in matches
        ]
        email_service.send_template(matches[0].customer_email, resend_link, items=items)

    # Ledger row is written whether or not a match existed: request frequency
    # stays rate-limited uniformly, so response timing/behavior can't be used
    # to probe which emails have inquiries.
    db.add(CateringVerificationCode(
        user_id=None,
        reference_id=email,
        action="resend_link",
        code_hash=secrets.token_hex(16),
        expires_at=now + timedelta(seconds=RESEND_COOLDOWN_SECONDS),
    ))
    db.commit()
    return {"message": GENERIC_RESEND_MESSAGE}


@router.get("/inquiries/{reference}", response_model=CustomerStatusOut)
def public_inquiry_status(
    reference: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    inquiry = _get_inquiry(db, org_id, reference)
    if not secrets.compare_digest(inquiry.access_token, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing access token.",
        )
    quotation = _visible_quotation(db, org_id, inquiry.id)
    booking = _booking_for(db, org_id, quotation)
    inquiry_pkg_name, _ = _package_snapshot(db, org_id, inquiry.catering_package_id)
    quotation_pkg_name, quotation_pkg_desc = _package_snapshot(db, org_id, quotation.catering_package_id if quotation else None)

    addons = _addons_breakout(db, org_id, inquiry)
    included_items = _included_items_for(db, org_id, inquiry)

    effective_service_style = (
        getattr(inquiry, "requested_service_style", None) or inquiry.service_style
    )
    if not effective_service_style and inquiry.catering_package_id:
        _pkg = db.query(CateringPackage).filter(
            CateringPackage.id == inquiry.catering_package_id,
            CateringPackage.organization_id == org_id,
        ).first()
        effective_service_style = getattr(_pkg, "service_style", None) if _pkg else None

    package_base_price = None
    derived_inclusions: list[DerivedInclusionOut] = []
    if quotation and quotation.catering_package_id:
        _qpkg = db.query(CateringPackage).filter(
            CateringPackage.id == quotation.catering_package_id,
            CateringPackage.organization_id == org_id,
        ).first()
        if _qpkg:
            package_base_price = suggested_price(_qpkg, quotation.guest_count)
            if (inquiry.package_mode or "default") != "custom":
                _, _derived = compute_premade_total(_qpkg, quotation.guest_count, db=db, org_id=org_id)
                derived_inclusions = [
                    DerivedInclusionOut(item_key=d["item_key"], quantity=d["quantity"])
                    for d in _derived
                ]

    return CustomerStatusOut(
        inquiry=CustomerInquirySummary(
            reference=inquiry_reference(inquiry),
            customer_name=inquiry.customer_name,
            event_date=inquiry.event_date,
            event_time=inquiry.event_time,
            event_type=inquiry.event_type,
            event_address=inquiry.event_address,
            venue_name=inquiry.venue_name,
            venue_mode=inquiry.venue_mode,
            location_floor=inquiry.location_floor,
            room_hall=inquiry.room_hall,
            landmark=inquiry.landmark,
            delivery_instructions=inquiry.delivery_instructions,
            guest_count=inquiry.guest_count,
            event_duration_hours=float(inquiry.event_duration_hours) if inquiry.event_duration_hours else None,
            package_name=inquiry_pkg_name,
            package_mode=inquiry.package_mode,
            items=included_items,
            addons=addons,
            food_requirements=_customer_requirements(inquiry),
            staffing=_staffing_out(inquiry),
            notes=inquiry.notes,
            estimated_total=float(inquiry.estimated_total) if inquiry.estimated_total else None,
            venue_fee=float(inquiry.venue_fee or 0),
            status=inquiry.status,
            review_status=inquiry.review_status,
            review_reason=inquiry.review_reason,
            created_at=inquiry.created_at,
        ),
        quotation=(
            CustomerQuotationOut(
                reference=f"QUO-{quotation.id}",
                inquiry_reference=inquiry_reference(inquiry),
                guest_count=quotation.guest_count,
                total_price=quotation.total_price,
                pricing_method=_pricing_method(db, org_id, quotation.catering_package_id),
                package_name=quotation_pkg_name,
                package_description=quotation_pkg_desc,
                event_date=inquiry.event_date,
                event_time=inquiry.event_time,
                event_type=inquiry.event_type,
                event_address=inquiry.event_address,
                venue_name=inquiry.venue_name,
                location_floor=inquiry.location_floor,
                room_hall=inquiry.room_hall,
                landmark=inquiry.landmark,
                delivery_instructions=inquiry.delivery_instructions,
                items=included_items,
                addons=addons,
                derived_inclusions=derived_inclusions,
                service_style=effective_service_style,
                requested_service_style=getattr(inquiry, "requested_service_style", None),
                package_base_price=package_base_price,
                food_requirements=_customer_requirements(inquiry),
                staffing=_staffing_out(inquiry),
                status=quotation.status,
                valid_until=quotation.valid_until,
                created_at=quotation.created_at,
                updated_at=quotation.updated_at,
            )
            if quotation
            else None
        ),
        booking=(
            CustomerBookingOut(
                reference=f"BK-{booking.id}",
                event_date=booking.event_date,
                event_location=booking.event_location,
                event_time=booking.event_time,
                guest_count=booking.guest_count,
                total_amount=booking.total_amount,
                status=booking.status,
                service_style=booking.service_style,
                coordinator_name=booking.coordinator_name,
                coordinator_contact=booking.coordinator_contact,
                created_at=booking.created_at,
            )
            if booking
            else None
        ),
    )


@router.post(
    "/inquiries/{reference}/quotations/{quotation_reference}/accept",
    response_model=CustomerBookingOut,
)
def public_accept_quotation(
    reference: str,
    quotation_reference: str,
    payload: CustomerQuotationAcceptIn = CustomerQuotationAcceptIn(),
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    inquiry = _get_inquiry(db, org_id, reference)
    _require_access_token(inquiry, token)
    quotation_uuid = parse_reference(quotation_reference, "QUO")
    if quotation_uuid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    quotation = (
        db.query(CateringQuotation)
        .filter(
            CateringQuotation.id == quotation_uuid,
            CateringQuotation.inquiry_id == inquiry.id,
            CateringQuotation.organization_id == org_id,
            CateringQuotation.deleted_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    booking = perform_accept(db, quotation, org_id, None, actor_role="customer", version=payload.version)
    return CustomerBookingOut(
        reference=f"BK-{booking.id}",
        event_date=booking.event_date,
        event_location=booking.event_location,
        event_time=booking.event_time,
        guest_count=booking.guest_count,
        total_amount=booking.total_amount,
        status=booking.status,
        coordinator_name=booking.coordinator_name,
        coordinator_contact=booking.coordinator_contact,
        created_at=booking.created_at,
    )


@router.post(
    "/inquiries/{reference}/quotations/{quotation_reference}/reject",
    response_model=CustomerQuotationOut,
)
def public_reject_quotation(
    reference: str,
    quotation_reference: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    inquiry = _get_inquiry(db, org_id, reference)
    _require_access_token(inquiry, token)
    quotation_uuid = parse_reference(quotation_reference, "QUO")
    if quotation_uuid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
    quotation = db.query(CateringQuotation).filter(
        CateringQuotation.id == quotation_uuid,
        CateringQuotation.inquiry_id == inquiry.id,
        CateringQuotation.organization_id == org_id,
        CateringQuotation.deleted_at.is_(None),
    ).first()
    if not quotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")

    quotation = perform_reject(db, quotation, None, actor_role="customer")
    return CustomerQuotationOut(
        reference=f"QUO-{quotation.id}",
        inquiry_reference=inquiry_reference(inquiry),
        guest_count=quotation.guest_count,
        total_price=quotation.total_price,
        status=quotation.status,
        valid_until=quotation.valid_until,
        created_at=quotation.created_at,
    )


# ---------------------------------------------------------------------------
# Billing verification gate (account-free, email-code based)
# ---------------------------------------------------------------------------

def _mask_email(email: str) -> str:
    """Mask an email for display: j***@domain."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return (local[0] if local else "*") + "***@" + domain


@router.post(
    "/inquiries/{reference}/billing/request-code",
    response_model=CustomerBillingCodeRequestOut,
)
def request_billing_code(
    reference: str,
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    inquiry = _get_inquiry(db, org_id, reference)
    if not inquiry.customer_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email address is associated with this inquiry.",
        )
    request_customer_billing_code(
        db,
        reference,
        inquiry.customer_email,
        organization_id=org_id,
    )
    db.commit()
    return CustomerBillingCodeRequestOut(
        message="A verification code has been sent to your email.",
        masked_email=_mask_email(inquiry.customer_email),
    )


@router.post(
    "/inquiries/{reference}/billing/verify",
    response_model=CustomerBillingVerifyOut,
)
def verify_billing_code(
    reference: str,
    code: str = Query(..., min_length=6, max_length=6),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    inquiry = _get_inquiry(db, org_id, reference)
    ok = verify_customer_billing_code(db, reference, code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        reference,
        "billing_verified",
        None,
        f"Billing access verified for {reference}",
    )
    db.commit()
    token = create_billing_access_token(reference)
    from app.flow import BILLING_TOKEN_TTL_MINUTES
    return CustomerBillingVerifyOut(
        token=token,
        expires_in=BILLING_TOKEN_TTL_MINUTES * 60,
    )


@router.get(
    "/inquiries/{reference}/billing",
    response_model=CustomerBookingBillingOut,
)
def get_billing(
    reference: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    token_ref = decode_billing_access_token(token)
    if token_ref is None or token_ref != reference:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired billing access token.",
        )
    inquiry = _get_inquiry(db, org_id, reference)
    quotation = _visible_quotation(db, org_id, inquiry.id)
    booking = _booking_for(db, org_id, quotation)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No booking exists for this inquiry yet.",
        )
    paid = payment_summary(db, org_id, [booking.id]).get(booking.id, 0.0)
    return CustomerBookingBillingOut(
        total_amount=booking.total_amount,
        amount_paid=round(paid, 2),
        remaining_balance=round(float(booking.total_amount or 0) - paid, 2),
        payment_status=booking.payment_status,
        status=booking.status,
    )


# ---------------------------------------------------------------------------
# Public venue catalog
# ---------------------------------------------------------------------------

@router.get("/venues", response_model=list[CustomerVenueOut])
def public_venues(
    event_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """List active venues the customer can choose from.

    When ``event_date`` is provided, each venue includes an ``available``
    flag that is ``False`` when the venue is already booked on that date.
    """
    venues = (
        db.query(CateringVenue)
        .filter(
            CateringVenue.organization_id == org_id,
            CateringVenue.deleted_at.is_(None),
            CateringVenue.is_active.is_(True),
            CateringVenue.status == "active",
        )
        .order_by(CateringVenue.name.asc())
        .all()
    )
    booked: set[UUID] = set()
    if event_date and venues:
        date_only = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
        rows = (
            db.query(VenueBooking.venue_id)
            .filter(
                VenueBooking.organization_id == org_id,
                VenueBooking.deleted_at.is_(None),
                func.date(VenueBooking.event_date) == func.date(date_only),
            )
            .all()
        )
        booked = {r[0] for r in rows}
    return [
        CustomerVenueOut(
            id=v.id,
            name=v.name,
            capacity=v.capacity,
            fee=float(v.fee),
            description=v.description,
            address=v.address,
            parking_capacity=v.parking_capacity,
            status=v.status,
            available=v.id not in booked if event_date else None,
        )
        for v in venues
    ]


# ---------------------------------------------------------------------------
# Customer payment submission (behind billing gate)
# ---------------------------------------------------------------------------

def _billing_require_booking(db, org_id: UUID, reference: str, token: str) -> tuple[CateringInquiry, CateringBooking]:
    """Validate billing token and return (inquiry, booking). Raises HTTPException on failure."""
    token_ref = decode_billing_access_token(token)
    if token_ref is None or token_ref != reference:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired billing access token.",
        )
    inquiry = _get_inquiry(db, org_id, reference)
    quotation = _visible_quotation(db, org_id, inquiry.id)
    booking = _booking_for(db, org_id, quotation)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No booking exists for this inquiry yet.",
        )
    return inquiry, booking


@router.post(
    "/inquiries/{reference}/payments",
    response_model=CustomerPaymentOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_customer_payment(
    reference: str,
    payload: CustomerPaymentSubmit,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Customer submits a payment record (pending verification)."""
    inquiry, booking = _billing_require_booking(db, org_id, reference, token)

    payment = CateringPayment(
        organization_id=org_id,
        booking_id=booking.id,
        amount=payload.amount,
        method=payload.method,
        reference=payload.customer_reference,
        paid_at=payload.payment_date or datetime.now(timezone.utc),
        payment_date=payload.payment_date,
        customer_reference=payload.customer_reference,
        notes=payload.notes,
        verified=False,
    )
    db.add(payment)
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        reference,
        "payment_submitted",
        None,
        f"Customer submitted payment of {payload.amount} via {payload.method}",
        actor_role="customer",
    )
    db.commit()
    db.refresh(payment)
    return CustomerPaymentOut(
        id=payment.id,
        amount=float(payment.amount),
        method=payment.method,
        customer_reference=payment.customer_reference,
        payment_date=payment.payment_date,
        verified=payment.verified,
        proof_url=payment.proof_url,
        created_at=payment.created_at,
    )


@router.get(
    "/inquiries/{reference}/payments",
    response_model=list[CustomerPaymentOut],
)
def list_customer_payments(
    reference: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """List payments for a booking (behind billing gate)."""
    inquiry, booking = _billing_require_booking(db, org_id, reference, token)

    payments = (
        db.query(CateringPayment)
        .filter(
            CateringPayment.booking_id == booking.id,
            CateringPayment.organization_id == org_id,
            CateringPayment.deleted_at.is_(None),
        )
        .order_by(CateringPayment.created_at.desc())
        .all()
    )
    return [
        CustomerPaymentOut(
            id=p.id,
            amount=float(p.amount),
            method=p.method,
            customer_reference=p.customer_reference,
            payment_date=p.payment_date,
            verified=p.verified,
            proof_url=p.proof_url,
            created_at=p.created_at,
        )
        for p in payments
    ]


@router.post(
    "/inquiries/{reference}/upload-proof",
    status_code=status.HTTP_201_CREATED,
)
async def upload_proof_of_payment(
    reference: str,
    token: str = Query(...),
    payment_id: UUID = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Upload proof of payment file (JPG, PNG, PDF)."""
    inquiry, booking = _billing_require_booking(db, org_id, reference, token)

    allowed = {"image/jpeg", "image/png", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPG, PNG, and PDF files are accepted.",
        )

    MAX_PROOF_BYTES = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_PROOF_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large. Maximum size is 5 MB.",
        )

    payment = db.query(CateringPayment).filter(
        CateringPayment.id == payment_id,
        CateringPayment.booking_id == booking.id,
        CateringPayment.organization_id == org_id,
        CateringPayment.deleted_at.is_(None),
    ).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

    import os
    from pathlib import Path
    upload_dir = Path(__file__).parent.parent.parent / "uploads" / "proofs"
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    filename = f"{payment_id}.{ext}"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(content)

    proof_url = f"/uploads/proofs/{filename}"
    payment.proof_url = proof_url
    db.commit()

    return {"proof_url": proof_url}


# ---------------------------------------------------------------------------
# Customer cancellation
# ---------------------------------------------------------------------------

@router.post(
    "/inquiries/{reference}/cancel",
    response_model=CustomerCancellationOut,
)
def cancel_inquiry(
    reference: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Customer cancels their inquiry (only before quotation is sent)."""
    inquiry = _get_inquiry(db, org_id, reference)
    _require_access_token(inquiry, token)
    quotation = _visible_quotation(db, org_id, inquiry.id)
    if quotation and quotation.status in ("sent", "accepted"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This inquiry already has a quotation. Please request a cancellation instead.",
        )
    if inquiry.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This inquiry is already closed.",
        )

    inquiry.status = "closed"
    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        reference,
        "cancelled_by_customer",
        None,
        f"Inquiry cancelled by customer",
        actor_role="customer",
    )
    db.commit()
    return CustomerCancellationOut(
        message="Your inquiry has been cancelled.",
        status="closed",
    )


@router.post(
    "/inquiries/{reference}/booking/cancel-request",
    response_model=CustomerCancellationOut,
)
def request_booking_cancellation(
    reference: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    org_id: UUID = Depends(get_public_org_id),
):
    """Customer requests a cancellation (after quotation/booking exists — staff reviews)."""
    inquiry = _get_inquiry(db, org_id, reference)
    _require_access_token(inquiry, token)
    quotation = _visible_quotation(db, org_id, inquiry.id)
    booking = _booking_for(db, org_id, quotation)

    if booking and booking.status in ("in_progress", "completed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancellation cannot be requested for events in progress or completed.",
        )

    log_audit(
        db,
        org_id,
        "inquiry",
        inquiry.id,
        reference,
        "cancellation_requested",
        None,
        f"Customer requested cancellation for {reference}",
        actor_role="customer",
    )
    db.commit()

    from app.email_service import email_service
    from app.email_templates import cancellation
    base_url = get_settings().PUBLIC_BASE_URL.rstrip("/")
    email_service.send_template(
        inquiry.customer_email,
        cancellation,
        name=inquiry.customer_name,
        reference=reference,
        status_url=f"{base_url}/customer-portal.html?ref={reference}&token={inquiry.access_token}",
    )

    return CustomerCancellationOut(
        message="Your cancellation request has been submitted. Our staff will review and contact you.",
        status="cancellation_requested",
    )
