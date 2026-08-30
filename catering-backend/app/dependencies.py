from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.auth import get_current_user, get_token_claims
from app.database import get_db
from app.models.catering_models import Customer, UserStub

_optional_bearer = HTTPBearer(auto_error=False)


def get_org_id(
    current_user: UserStub = Depends(get_current_user),
) -> UUID:
    """Return the tenant id, sourced from the JWT ``org`` claim.

    The organization id is never trusted from the client — it comes from the
    signed token (issued by the ARGO platform) with the DB user as fallback.
    """
    claims = getattr(current_user, "_jwt_claims", {}) or {}
    raw = claims.get("org") or current_user.organization_id
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an organization",
        )
    try:
        return raw if isinstance(raw, UUID) else UUID(str(raw))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid organization in token",
        )


def get_current_customer(
    claims: dict[str, Any] = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> Customer:
    """Resolve the authenticated customer and tenant from the validated JWT.

    Only customer-scoped tokens (``type: customer`` claim) pass. Both the
    ``customer_id`` (``sub``) and ``organization_id`` (``org``) are read from
    the signed token — never from a request parameter, query string, or body.
    """
    if claims.get("type") != "customer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        customer_id = UUID(str(claims["sub"]))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    raw_org = claims.get("org")
    if raw_org is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer is not associated with an organization",
        )
    try:
        org_id = raw_org if isinstance(raw_org, UUID) else UUID(str(raw_org))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid organization in token",
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.organization_id == org_id,
            Customer.deleted_at.is_(None),
        )
        .first()
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Customer not found")

    # JWT is authoritative for the tenant, mirroring how get_current_user
    # consumes the role claim.
    customer.organization_id = org_id
    customer._jwt_claims = claims
    return customer


def get_optional_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Customer | None:
    """Resolve a customer from the JWT when a valid customer token is present.

    Used to bind new anonymous portal submissions to a logged-in customer.
    Deliberately lenient: missing, invalid, or non-customer tokens resolve to
    None so the anonymous portal flow is never broken by a stale header.
    """
    if credentials is None:
        return None
    try:
        claims = get_token_claims(credentials)
    except HTTPException:
        return None
    if claims.get("type") != "customer":
        return None
    try:
        customer_id = UUID(str(claims["sub"]))
    except (ValueError, TypeError, AttributeError):
        return None
    raw_org = claims.get("org")
    if raw_org is None:
        return None
    try:
        org_id = raw_org if isinstance(raw_org, UUID) else UUID(str(raw_org))
    except (ValueError, TypeError, AttributeError):
        return None
    return (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.organization_id == org_id,
            Customer.deleted_at.is_(None),
        )
        .first()
    )
