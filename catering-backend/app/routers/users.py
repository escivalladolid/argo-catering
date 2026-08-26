import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.auth import hash_password, require_role
from app.database import get_db
from app.flow import log_audit, request_verification_code, verify_code
from app.models.catering_models import UserStub
from app.rbac import VALID_ROLES, permissions_for
from app.schemas.catering_schemas import (
    UserCreateIn,
    UserCreatedOut,
    UserOut,
    UserResetOut,
    UserUpdateIn,
    VerificationCodeIn,
    VerificationCodeRequestOut,
)

router = APIRouter(prefix="/users", tags=["Users"])


def _user_out(user: UserStub) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        organization_id=user.organization_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        permissions=permissions_for(user.role),
    )


def _temporary_password() -> str:
    return secrets.token_urlsafe(9)


def _get_org_user(user_id: UUID, org_id: UUID | None, db: Session) -> UserStub:
    q = db.query(UserStub).filter(UserStub.id == user_id)
    if org_id is not None:
        q = q.filter(UserStub.organization_id == org_id)
    user = q.first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _request_code_for(user_id: UUID, current_user: UserStub, db: Session, action_name: str) -> VerificationCodeRequestOut:
    """Step-up helper: email a one-time code to the admin for a sensitive action."""
    target = _get_org_user(user_id, current_user.organization_id, db)
    action = f"{action_name}:{user_id}"
    request_verification_code(
        db,
        current_user,
        action,
        organization_id=current_user.organization_id,
        target_user=target,
    )
    db.commit()
    return VerificationCodeRequestOut()


def _verify_code_for(user_id: UUID, current_user: UserStub, db: Session, action_name: str, submitted_code: str, target: UserStub) -> None:
    action = f"{action_name}:{user_id}"
    ok = verify_code(
        db,
        current_user,
        action,
        submitted_code,
        organization_id=current_user.organization_id,
        target_user=target,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")


@router.get("", response_model=dict)
def list_users(
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
):
    q = db.query(UserStub).filter(UserStub.organization_id == current_user.organization_id)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(
            (UserStub.email.ilike(like)) | (UserStub.full_name.ilike(like))
        )
    total = q.count()
    rows = (
        q.order_by(UserStub.created_at.desc(), UserStub.email.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_user_out(u) for u in rows]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("", response_model=UserCreatedOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateIn,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    existing = db.query(UserStub).filter(UserStub.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists",
        )
    temp_password = _temporary_password()
    user = UserStub(
        email=payload.email,
        full_name=(payload.full_name or "").strip() or None,
        role=payload.role,
        hashed_password=hash_password(temp_password),
        is_active=True,
        organization_id=current_user.organization_id,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        organization_id=current_user.organization_id,
        entity_type="user",
        entity_id=user.id,
        entity_reference=user.email,
        action="user_created",
        current_user=current_user,
        summary=f"Created {payload.role} account for {user.email}",
    )
    db.commit()
    return UserCreatedOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        temporary_password=temp_password,
    )


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdateIn,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    user = _get_org_user(user_id, current_user.organization_id, db)
    if payload.role is not None and payload.role != user.role:
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role",
            )
        if not payload.verification_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A verification code is required for role changes",
            )
        _verify_code_for(user_id, current_user, db, "role_change", payload.verification_code, user)
        summary = f"Changed role of {user.email} from {user.role} to {payload.role}"
        log_audit(
            db,
            organization_id=current_user.organization_id,
            entity_type="user",
            entity_id=user.id,
            entity_reference=user.email,
            action="role_changed",
            current_user=current_user,
            summary=summary,
        )
        user.role = payload.role
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip() or None
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/{user_id}/role-change/request-code", response_model=VerificationCodeRequestOut)
def request_role_change_code(
    user_id: UUID,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    return _request_code_for(user_id, current_user, db, "role_change")


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(
    user_id: UUID,
    payload: VerificationCodeIn,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    user = _get_org_user(user_id, current_user.organization_id, db)
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    _verify_code_for(user_id, current_user, db, "deactivate", payload.verification_code, user)
    if not user.is_active:
        return _user_out(user)
    user.is_active = False
    log_audit(
        db,
        organization_id=current_user.organization_id,
        entity_type="user",
        entity_id=user.id,
        entity_reference=user.email,
        action="deactivated",
        current_user=current_user,
        summary=f"Deactivated account for {user.email}",
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/{user_id}/deactivate/request-code", response_model=VerificationCodeRequestOut)
def request_deactivate_code(
    user_id: UUID,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    return _request_code_for(user_id, current_user, db, "deactivate")


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(
    user_id: UUID,
    payload: VerificationCodeIn,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    user = _get_org_user(user_id, current_user.organization_id, db)
    _verify_code_for(user_id, current_user, db, "reactivate", payload.verification_code, user)
    if user.is_active:
        return _user_out(user)
    user.is_active = True
    log_audit(
        db,
        organization_id=current_user.organization_id,
        entity_type="user",
        entity_id=user.id,
        entity_reference=user.email,
        action="reactivated",
        current_user=current_user,
        summary=f"Reactivated account for {user.email}",
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/{user_id}/reactivate/request-code", response_model=VerificationCodeRequestOut)
def request_reactivate_code(
    user_id: UUID,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    return _request_code_for(user_id, current_user, db, "reactivate")


@router.post("/{user_id}/reset-password", response_model=UserResetOut)
def reset_user_password(
    user_id: UUID,
    payload: VerificationCodeIn,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    user = _get_org_user(user_id, current_user.organization_id, db)
    _verify_code_for(user_id, current_user, db, "reset_password", payload.verification_code, user)
    temp_password = _temporary_password()
    user.hashed_password = hash_password(temp_password)
    log_audit(
        db,
        organization_id=current_user.organization_id,
        entity_type="user",
        entity_id=user.id,
        entity_reference=user.email,
        action="password_reset",
        current_user=current_user,
        summary=f"Reset password for {user.email}",
    )
    db.commit()
    return UserResetOut(id=user.id, email=user.email, temporary_password=temp_password)


@router.post("/{user_id}/reset-password/request-code", response_model=VerificationCodeRequestOut)
def request_reset_password_code(
    user_id: UUID,
    current_user: UserStub = Depends(require_role("administrator")),
    db: Session = Depends(get_db),
):
    return _request_code_for(user_id, current_user, db, "reset_password")
