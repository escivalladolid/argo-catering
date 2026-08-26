from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.auth.auth import get_current_user
from app.models.catering_models import UserStub


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
