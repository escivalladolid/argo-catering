from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.auth import create_customer_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_customer
from app.flow import (
    request_customer_verification_code,
    verify_customer_verification_code,
)
from app.models.catering_models import Customer, utcnow
from app.routers.public_portal import get_public_org_id
from app.schemas.catering_schemas import (
    CustomerOut,
    CustomerRegisterIn,
    CustomerRegisterOut,
    CustomerVerifyIn,
    LoginIn,
    TokenOut,
)

router = APIRouter(prefix="/customer", tags=["Customer Auth"])


def _get_customer_by_email(db: Session, org_id: UUID, email: str) -> Customer | None:
    return (
        db.query(Customer)
        .filter(
            Customer.organization_id == org_id,
            Customer.email == email,
            Customer.deleted_at.is_(None),
        )
        .first()
    )


def _customer_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        organization_id=customer.organization_id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        verified_at=customer.verified_at,
        created_at=customer.created_at,
    )


@router.post("/register", response_model=CustomerRegisterOut, status_code=status.HTTP_201_CREATED)
def register_customer(
    payload: CustomerRegisterIn,
    db: Session = Depends(get_db),
    public_org_id: UUID = Depends(get_public_org_id),
):
    """Create a customer account and email a verification code.

    The organization is resolved server-side (PUBLIC_ORGANIZATION_ID /
    exactly-one-org) — it is never accepted from the request body.
    """
    existing = _get_customer_by_email(db, public_org_id, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        )

    customer = Customer(
        organization_id=public_org_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        verified_at=None,
    )
    db.add(customer)
    db.flush()

    request_customer_verification_code(
        db,
        customer.id,
        customer.email,
        organization_id=public_org_id,
    )
    db.commit()
    return CustomerRegisterOut()


@router.post("/verify", response_model=CustomerOut)
def verify_customer_email(
    payload: CustomerVerifyIn,
    db: Session = Depends(get_db),
    public_org_id: UUID = Depends(get_public_org_id),
):
    """Confirm a customer's email with the 6-digit code sent at registration."""
    customer = _get_customer_by_email(db, public_org_id, payload.email)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    ok = verify_customer_verification_code(db, customer.id, payload.verification_code)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )

    customer.verified_at = utcnow()
    db.commit()
    db.refresh(customer)
    return _customer_out(customer)


@router.post("/login", response_model=TokenOut)
def login_customer(
    payload: LoginIn,
    db: Session = Depends(get_db),
    public_org_id: UUID = Depends(get_public_org_id),
):
    """Authenticate a customer and return a customer-scoped JWT."""
    customer = _get_customer_by_email(db, public_org_id, payload.email)
    if customer is None or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if customer.verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified yet. Check your email for the verification code.",
        )

    token = create_customer_access_token(customer.id, customer.organization_id)
    return TokenOut(access_token=token)


@router.get("/me", response_model=CustomerOut)
def get_me(customer: Customer = Depends(get_current_customer)):
    """Protected test route proving get_current_customer works in isolation."""
    return _customer_out(customer)