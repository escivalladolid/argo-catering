"""Role-Based Access Control.

Single source of truth for the catering module's permission model.

Roles are assigned by the parent ARGO identity platform and delivered in the
JWT (``role`` claim). The module never trusts a role/org sent by the client;
it reads them from the signed token (see ``app.auth.auth.get_current_user``
and ``app.dependencies.get_org_id``).

Design:
    * Permissions are fine-grained ``resource:action`` strings.
    * ``ROLE_PERMISSIONS`` maps each role to the permissions it holds.
    * ``require_permission`` is a FastAPI dependency used on mutating and
      read endpoints; it raises HTTP 403 when the caller lacks permission.
    * ``ensure_permission`` is the non-dependency variant used when the
      required permission depends on record state (e.g. booking transitions).
    * Only ``settings:configure`` is reserved here, pre-wired for the planned
      settings module. It is not yet checked by any endpoint; the Users &
      Roles page is enforced server-side as administrator-only.
"""
from typing import Iterable

from fastapi import Depends, HTTPException, status

from app.auth.auth import get_current_user
from app.models.catering_models import UserStub


class Perm:
    # Dashboard / navigation
    DASHBOARD_VIEW = "dashboard:view"

    # Audit log / activity trail (manager+ only)
    AUDIT_VIEW = "audit:view"

    # Inquiries
    INQUIRY_VIEW = "inquiry:view"
    INQUIRY_CREATE = "inquiry:create"
    INQUIRY_UPDATE = "inquiry:update"
    INQUIRY_DELETE = "inquiry:delete"

    # Quotations
    QUOTATION_VIEW = "quotation:view"
    QUOTATION_CREATE = "quotation:create"
    QUOTATION_UPDATE = "quotation:update"
    QUOTATION_SEND = "quotation:send"
    QUOTATION_APPROVE = "quotation:approve"
    QUOTATION_REJECT = "quotation:reject"
    QUOTATION_DELETE = "quotation:delete"

    # Bookings
    BOOKING_VIEW = "booking:view"
    BOOKING_CONFIRM = "booking:confirm"
    BOOKING_CANCEL = "booking:cancel"
    BOOKING_UPDATE = "booking:update"
    BOOKING_UPDATE_PROGRESS = "booking:update_progress"

    # Packages
    PACKAGE_VIEW = "package:view"
    PACKAGE_CREATE = "package:create"
    PACKAGE_UPDATE = "package:update"
    PACKAGE_DELETE = "package:delete"

    # Venues
    VENUE_VIEW = "venue:view"
    VENUE_CREATE = "venue:create"
    VENUE_UPDATE = "venue:update"
    VENUE_DELETE = "venue:delete"

    # Menus & items
    MENU_VIEW = "menu:view"
    MENU_CREATE = "menu:create"
    MENU_UPDATE = "menu:update"
    MENU_DELETE = "menu:delete"

    # Guest counts
    GUEST_COUNT_VIEW = "guest_count:view"
    GUEST_COUNT_CREATE = "guest_count:create"
    GUEST_COUNT_UPDATE = "guest_count:update"
    GUEST_COUNT_DELETE = "guest_count:delete"

    # Food requirements
    FOOD_REQUIREMENT_VIEW = "food_requirement:view"
    FOOD_REQUIREMENT_CREATE = "food_requirement:create"
    FOOD_REQUIREMENT_UPDATE = "food_requirement:update"
    FOOD_REQUIREMENT_DELETE = "food_requirement:delete"

    # Staffing
    STAFF_VIEW = "staff:view"
    STAFF_CREATE = "staff:create"
    STAFF_UPDATE = "staff:update"
    STAFF_DELETE = "staff:delete"
    STAFF_ASSIGNMENT_VIEW = "staff_assignment:view"
    STAFF_ASSIGNMENT_CREATE = "staff_assignment:create"
    STAFF_ASSIGNMENT_UPDATE = "staff_assignment:update"
    STAFF_ASSIGNMENT_DELETE = "staff_assignment:delete"

    # Equipment
    EQUIPMENT_VIEW = "equipment:view"
    EQUIPMENT_CREATE = "equipment:create"
    EQUIPMENT_UPDATE = "equipment:update"
    EQUIPMENT_DELETE = "equipment:delete"
    EQUIPMENT_ASSIGNMENT_VIEW = "equipment_assignment:view"
    EQUIPMENT_ASSIGNMENT_CREATE = "equipment_assignment:create"
    EQUIPMENT_ASSIGNMENT_UPDATE = "equipment_assignment:update"
    EQUIPMENT_ASSIGNMENT_DELETE = "equipment_assignment:delete"

    # Deliveries
    DELIVERY_VIEW = "delivery:view"
    DELIVERY_CREATE = "delivery:create"
    DELIVERY_UPDATE = "delivery:update"
    DELIVERY_ADVANCE = "delivery:advance"
    DELIVERY_CANCEL = "delivery:cancel"
    DELIVERY_DELETE = "delivery:delete"

    # Payments
    PAYMENT_VIEW = "payment:view"
    PAYMENT_CREATE = "payment:create"
    PAYMENT_UPDATE = "payment:update"
    PAYMENT_DELETE = "payment:delete"

    # Billing
    BILL_VIEW = "bill:view"
    BILL_CREATE = "bill:create"
    BILL_UPDATE = "bill:update"
    BILL_SEND = "bill:send"
    BILL_MARK_PAID = "bill:mark_paid"
    BILL_VOID = "bill:void"
    BILL_DELETE = "bill:delete"

    # Planned module (RBAC pre-wired, not yet built)
    # The Users & Roles page is the only surface needing this today; it is
    # enforced server-side as administrator-only. Kept here so the settings
    # hook can be wired in when the module is built.
    SETTINGS_CONFIGURE = "settings:configure"


VIEWER = {
    Perm.DASHBOARD_VIEW,
    Perm.INQUIRY_VIEW,
    Perm.QUOTATION_VIEW,
    Perm.BOOKING_VIEW,
    Perm.PACKAGE_VIEW,
    Perm.MENU_VIEW,
    Perm.VENUE_VIEW,
}

STAFF = VIEWER | {
    Perm.INQUIRY_CREATE,
    Perm.INQUIRY_UPDATE,
    Perm.QUOTATION_CREATE,
    Perm.QUOTATION_UPDATE,
    Perm.QUOTATION_SEND,
    Perm.BOOKING_UPDATE_PROGRESS,
    Perm.GUEST_COUNT_VIEW,
    Perm.GUEST_COUNT_CREATE,
    Perm.GUEST_COUNT_UPDATE,
    Perm.FOOD_REQUIREMENT_VIEW,
    Perm.FOOD_REQUIREMENT_CREATE,
    Perm.FOOD_REQUIREMENT_UPDATE,
    Perm.EQUIPMENT_VIEW,
    Perm.DELIVERY_VIEW,
    Perm.DELIVERY_CREATE,
    Perm.DELIVERY_UPDATE,
    Perm.DELIVERY_ADVANCE,
    Perm.DELIVERY_CANCEL,
    Perm.EQUIPMENT_ASSIGNMENT_VIEW,
    Perm.EQUIPMENT_ASSIGNMENT_CREATE,
    Perm.EQUIPMENT_ASSIGNMENT_UPDATE,
    Perm.PAYMENT_VIEW,
    Perm.PAYMENT_CREATE,
    Perm.BILL_VIEW,
    Perm.BILL_CREATE,
    Perm.BILL_UPDATE,
}

MANAGER = STAFF | {
    Perm.INQUIRY_DELETE,
    Perm.QUOTATION_APPROVE,
    Perm.QUOTATION_REJECT,
    Perm.QUOTATION_DELETE,
    Perm.BOOKING_CONFIRM,
    Perm.BOOKING_CANCEL,
    Perm.BOOKING_UPDATE,
    Perm.GUEST_COUNT_DELETE,
    Perm.FOOD_REQUIREMENT_DELETE,
    Perm.STAFF_VIEW,
    Perm.STAFF_CREATE,
    Perm.STAFF_UPDATE,
    Perm.STAFF_ASSIGNMENT_VIEW,
    Perm.STAFF_ASSIGNMENT_CREATE,
    Perm.STAFF_ASSIGNMENT_UPDATE,
    Perm.STAFF_ASSIGNMENT_DELETE,
    Perm.EQUIPMENT_CREATE,
    Perm.EQUIPMENT_UPDATE,
    Perm.EQUIPMENT_DELETE,
    Perm.EQUIPMENT_ASSIGNMENT_DELETE,
    Perm.DELIVERY_DELETE,
    Perm.PAYMENT_UPDATE,
    Perm.PAYMENT_DELETE,
    Perm.BILL_SEND,
    Perm.BILL_MARK_PAID,
    Perm.BILL_VOID,
    Perm.BILL_DELETE,
    Perm.AUDIT_VIEW,
    Perm.VENUE_CREATE,
    Perm.VENUE_UPDATE,
    Perm.VENUE_DELETE,
}

ADMINISTRATOR = MANAGER | {
    Perm.PACKAGE_CREATE,
    Perm.PACKAGE_UPDATE,
    Perm.PACKAGE_DELETE,
    Perm.MENU_CREATE,
    Perm.MENU_UPDATE,
    Perm.MENU_DELETE,
    Perm.STAFF_DELETE,
    Perm.SETTINGS_CONFIGURE,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": VIEWER,
    "staff": STAFF,
    "manager": MANAGER,
    "administrator": ADMINISTRATOR,
}

VALID_ROLES = frozenset(ROLE_PERMISSIONS)


def permissions_for(role: str) -> list[str]:
    """Return the sorted permission list a role holds (safe for any input)."""
    return sorted(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, *perms: str) -> bool:
    """True when the role holds ANY of the given permissions."""
    if not perms:
        return role in VALID_ROLES
    held = ROLE_PERMISSIONS.get(role, set())
    return any(p in held for p in perms)


def ensure_permission(user: UserStub, *perms: str) -> None:
    """Raise 403 unless the user's role holds one of the permissions."""
    if not has_permission(getattr(user, "role", ""), *perms):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def require_permission(*perms: str):
    """FastAPI dependency factory enforcing that the caller holds a permission."""

    def dependency(
        current_user: UserStub = Depends(get_current_user),
    ) -> UserStub:
        ensure_permission(current_user, *perms)
        return current_user

    return dependency
