"""Payments router — replaces the generic factory with custom proof upload + verification."""
import os
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit, recompute_payment_status
from app.models.catering_models import (
    CateringBooking,
    CateringInquiry,
    CateringPayment,
    CateringQuotation,
    UserStub,
)
from app.paging import apply_search, apply_sort, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringPaymentCreate,
    CateringPaymentOut,
    CateringPaymentUpdate,
    Page,
)

router = APIRouter(prefix="/payments", tags=["Payments"])

SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "amount": CateringPayment.amount,
    "method": CateringPayment.method,
    "paid_at": CateringPayment.paid_at,
    "created_at": CateringPayment.created_at,
    "verification_status": CateringPayment.verification_status,
}
SEARCH_COLS = [CateringInquiry.customer_name, CateringPayment.reference]

PROOFS_DIR = Path(__file__).parent.parent.parent / "uploads" / "payment_proofs"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf"}


def _base_query(db: Session, org_id: UUID):
    return (
        db.query(CateringPayment)
        .join(CateringBooking, CateringBooking.id == CateringPayment.booking_id)
        .join(CateringQuotation, CateringQuotation.id == CateringBooking.quotation_id)
        .join(CateringInquiry, CateringInquiry.id == CateringQuotation.inquiry_id)
        .filter(
            CateringPayment.organization_id == org_id,
            CateringPayment.deleted_at.is_(None),
            CateringBooking.organization_id == org_id,
            CateringBooking.deleted_at.is_(None),
            CateringQuotation.deleted_at.is_(None),
            CateringInquiry.deleted_at.is_(None),
        )
    )


def _get_record(db: Session, org_id: UUID, record_id: UUID) -> CateringPayment:
    record = _base_query(db, org_id).filter(CateringPayment.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return record


def _get_booking(db: Session, org_id: UUID, booking_id: UUID):
    booking = db.query(CateringBooking).filter(
        CateringBooking.id == booking_id,
        CateringBooking.organization_id == org_id,
        CateringBooking.deleted_at.is_(None),
    ).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


@router.get("/pending-count")
def pending_count(
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    """Count of payments awaiting verification (for notification bar)."""
    count = db.query(CateringPayment).filter(
        CateringPayment.organization_id == org_id,
        CateringPayment.deleted_at.is_(None),
        CateringPayment.verification_status == "pending",
        CateringPayment.proof_url.is_not(None),
    ).count()
    return {"count": count}


@router.get("/", response_model=Page[CateringPaymentOut])
def list_records(
    booking_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    if booking_id:
        q = q.filter(CateringPayment.booking_id == booking_id)
    if status:
        if status in ("pending", "approved", "rejected"):
            q = q.filter(CateringPayment.verification_status == status)
        else:
            q = q.filter(CateringPayment.method == status)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    return paginate(q, page, page_size)


@router.post("/", response_model=CateringPaymentOut, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: CateringPaymentCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    _get_booking(db, org_id, payload.booking_id)
    data = payload.model_dump(exclude_unset=True)
    record = CateringPayment(**data, organization_id=org_id, created_by=current_user.id)
    db.add(record)
    db.flush()
    log_audit(db, org_id, "payment", record.id, f"{record.reference or record.method} {record.amount}",
              "payment recorded", current_user, f"Payment of \u20b1{record.amount} via {record.method or 'cash'} recorded")
    db.commit()
    db.refresh(record)
    recompute_payment_status(db, org_id, record.booking_id)
    return record


@router.get("/{record_id}", response_model=CateringPaymentOut)
def get_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    return _get_record(db, org_id, record_id)


@router.put("/{record_id}", response_model=CateringPaymentOut)
def update_record(
    record_id: UUID,
    payload: CateringPaymentUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    record = _get_record(db, org_id, record_id)
    data = payload.model_dump(exclude_unset=True)
    if "booking_id" in data and data["booking_id"] != record.booking_id:
        _get_booking(db, org_id, data["booking_id"])
    for key, value in data.items():
        setattr(record, key, value)
    record.updated_by = current_user.id
    log_audit(db, org_id, "payment", record.id, f"{record.reference or record.method} {record.amount}",
              "updated", current_user, f"Payment of \u20b1{record.amount} updated")
    db.commit()
    db.refresh(record)
    recompute_payment_status(db, org_id, record.booking_id)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    record = _get_record(db, org_id, record_id)
    booking_id = record.booking_id
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = current_user.id
    log_audit(db, org_id, "payment", record.id, f"{record.reference or record.method} {record.amount}",
              "deleted", current_user, f"Payment of \u20b1{record.amount} deleted")
    db.commit()
    recompute_payment_status(db, org_id, booking_id)


@router.post("/{record_id}/proof")
async def upload_proof(
    record_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    """Upload proof-of-payment image (JPG, PNG, PDF). Saves to disk and updates payment record."""
    record = _get_record(db, org_id, record_id)
    ext = Path(file.filename or "proof.jpg").suffix.lower() or ".jpg"
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed. Use JPG, PNG, or PDF.")

    PROOFS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{record_id}{ext}"
    filepath = PROOFS_DIR / filename
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB).")
    filepath.write_bytes(content)

    record.proof_image_path = str(filepath)
    record.proof_url = f"/uploads/payment_proofs/{filename}"
    if record.verification_status == "pending":
        pass  # stays pending
    else:
        record.verification_status = "pending"
        record.verified = False
        record.verified_by = None
        record.verified_at = None
    record.updated_by = current_user.id
    db.commit()
    db.refresh(record)
    log_audit(db, org_id, "payment", record.id, f"{record.reference or record.method} {record.amount}",
              "proof uploaded", current_user, f"Proof of payment uploaded for \u20b1{record.amount}")
    return {"proof_url": record.proof_url, "verification_status": record.verification_status}


class VerifyPayload:
    """Pydantic-free shim for multipart form verification."""
    pass


@router.post("/{record_id}/verify", response_model=CateringPaymentOut)
def verify_payment(
    record_id: UUID,
    action: str = Form(...),
    amount: float | None = Form(None),
    method: str | None = Form(None),
    reference: str | None = Form(None),
    notes: str | None = Form(None),
    reject_reason: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PAYMENT_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    """Approve or reject a payment. Admin can correct amount/method/reference before approving."""
    record = _get_record(db, org_id, record_id)
    if action == "approve":
        if amount is not None:
            record.amount = amount
        if method is not None:
            record.method = method
        if reference is not None:
            record.reference = reference
        if notes is not None:
            record.notes = notes
        record.verification_status = "approved"
        record.verified = True
        record.verified_by = current_user.id
        record.verified_at = datetime.now(timezone.utc)
        action_label = "approved"
    elif action == "reject":
        record.verification_status = "rejected"
        record.verified = False
        record.verified_by = current_user.id
        record.verified_at = datetime.now(timezone.utc)
        if reject_reason:
            record.notes = (record.notes or "") + f"\n[Reject reason] {reject_reason}"
        action_label = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    record.updated_by = current_user.id
    log_audit(db, org_id, "payment", record.id, f"{record.reference or record.method} {record.amount}",
              f"payment {action_label}", current_user,
              f"Payment of \u20b1{record.amount} {action_label} by admin")
    db.commit()
    db.refresh(record)
    recompute_payment_status(db, org_id, record.booking_id)
    return record
