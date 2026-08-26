from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.auth import verify_password, create_access_token, get_current_user
from app.models.catering_models import UserStub, utcnow
from app.rbac import permissions_for
from app.schemas.catering_schemas import LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(UserStub).filter(UserStub.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact your administrator.",
        )
    user.last_login_at = utcnow()
    db.commit()
    token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
            "org": str(user.organization_id) if user.organization_id else None,
        }
    )
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: UserStub = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        organization_id=current_user.organization_id,
        permissions=permissions_for(current_user.role),
    )
