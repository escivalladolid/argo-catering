import uuid
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.booking_scoped import base_query, get_booking
from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit, inquiry_reference, recompute_payment_status
from app.config import get_settings
from app.models.catering_models import CateringBill, CateringBillItem, CateringInquiry, UserStub
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringBillCreate,
    CateringBillItemCreate,
    CateringBillItemOut,
    CateringBillItemUpdate,
    CateringBillOut,
    CateringBillUpdate,
    Page,
)

router = APIRouter(prefix="/billing", tags=["Billing"])

SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "bill_number": CateringBill.bill_number,
    "total": CateringBill.total,
    "due_date": CateringBill.due_date,
    "status": CateringBill.status,
    "created_at": CateringBill.created_at,
}
SEARCH_COLS = [CateringInquiry.customer_name, CateringBill.bill_number]


def _generate_bill_number(db: Session) -> str:
    for _ in range(10):
        number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        exists = db.query(CateringBill).filter(CateringBill.bill_number == number).first()
        if not exists:
            return number
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate bill number")


def _recompute_totals(db: Session, bill: CateringBill) -> None:
    subtotal = 0.0
    for item in bill.items:
        if item.deleted_at is None:
            item.amount = round(float(item.quantity) * float(item.unit_price), 2)
            subtotal += item.amount
    bill.subtotal = round(subtotal, 2)
    total = subtotal - float(bill.discount or 0) + float(bill.tax or 0)
    bill.total = max(0.0, round(total, 2))


def _apply_overdue(bills) -> None:
    now = datetime.now(timezone.utc)
    for bill in bills:
        if bill.status == "sent" and bill.due_date is not None and bill.due_date < now:
            bill.status = "overdue"


def _validate_status_flow(bill: CateringBill, allowed_from: tuple[str, ...], detail: str) -> None:
    if bill.status not in allowed_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


@router.get("/", response_model=Page[CateringBillOut])
def list_bills(
    booking_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = base_query(db, CateringBill, org_id)
    if booking_id:
        q = q.filter(CateringBill.booking_id == booking_id)
    if status == "overdue":
        now = datetime.now(timezone.utc)
        q = q.filter(
            CateringBill.status == "sent",
            CateringBill.due_date.isnot(None),
            CateringBill.due_date < now,
        )
    else:
        q = apply_status(q, status, CateringBill.status)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    result = paginate(q, page, page_size)
    _apply_overdue(result.items)
    return result


@router.post("/", response_model=CateringBillOut, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: CateringBillCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    get_booking(db, org_id, payload.booking_id)
    bill = CateringBill(
        organization_id=org_id,
        booking_id=payload.booking_id,
        bill_number=_generate_bill_number(db),
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        tax=payload.tax,
        discount=payload.discount,
        notes=payload.notes,
        status="draft",
        created_by=current_user.id,
    )
    db.add(bill)
    db.flush()
    for item in payload.items:
        db.add(CateringBillItem(
            organization_id=org_id,
            bill_id=bill.id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=round(float(item.quantity) * float(item.unit_price), 2),
            created_by=current_user.id,
        ))
    db.flush()
    _recompute_totals(db, bill)
    log_audit(
        db,
        org_id,
        "bill",
        bill.id,
        bill.bill_number,
        "created",
        current_user,
        f"Bill {bill.bill_number} created for booking",
    )
    db.commit()
    db.refresh(bill)
    return bill


@router.get("/{bill_id}", response_model=CateringBillOut)
def get_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _apply_overdue([bill])
    return bill


@router.put("/{bill_id}", response_model=CateringBillOut)
def update_bill(
    bill_id: UUID,
    payload: CateringBillUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft", "sent", "overdue"), f"Cannot edit bill with status '{bill.status}'")
    data = payload.model_dump(exclude_unset=True)
    if "issue_date" in data:
        bill.issue_date = data["issue_date"]
    if "due_date" in data:
        bill.due_date = data["due_date"]
    if "tax" in data:
        bill.tax = data["tax"]
    if "discount" in data:
        bill.discount = data["discount"]
    if "notes" in data:
        bill.notes = data["notes"]
    if "items" in data:
        now = datetime.now(timezone.utc)
        for item in bill.items:
            item.deleted_at = now
        for item in data["items"]:
            db.add(CateringBillItem(
                organization_id=org_id,
                bill_id=bill_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=round(float(item.quantity) * float(item.unit_price), 2),
                created_by=current_user.id,
            ))
        db.flush()
        db.expire(bill, ["items"])
    _recompute_totals(db, bill)
    bill.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "bill",
        bill.id,
        bill.bill_number,
        "updated",
        current_user,
        f"Bill {bill.bill_number} updated",
    )
    db.commit()
    db.refresh(bill)
    return bill


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft", "sent", "overdue", "void"), f"Cannot delete bill with status '{bill.status}'")
    now = datetime.now(timezone.utc)
    for item in bill.items:
        item.deleted_at = now
    bill.deleted_at = now
    bill.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "bill",
        bill.id,
        bill.bill_number,
        "deleted",
        current_user,
        f"Bill {bill.bill_number} deleted",
    )
    db.commit()


@router.get("/{bill_id}/items", response_model=Page[CateringBillItemOut])
def list_bill_items(
    bill_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    q = db.query(CateringBillItem).filter(
        CateringBillItem.bill_id == bill_id,
        CateringBillItem.deleted_at.is_(None),
    )
    return paginate(q, page, page_size)


@router.post("/{bill_id}/items", response_model=CateringBillItemOut, status_code=status.HTTP_201_CREATED)
def create_bill_item(
    bill_id: UUID,
    payload: CateringBillItemCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft", "sent", "overdue"), f"Cannot edit bill with status '{bill.status}'")
    item = CateringBillItem(
        organization_id=org_id,
        bill_id=bill_id,
        description=payload.description,
        quantity=payload.quantity,
        unit_price=payload.unit_price,
        amount=round(float(payload.quantity) * float(payload.unit_price), 2),
        created_by=current_user.id,
    )
    db.add(item)
    db.flush()
    log_audit(
        db,
        org_id,
        "bill_item",
        item.id,
        item.description,
        "created",
        current_user,
        f"Line item '{item.description}' added to bill {bill.bill_number}",
    )
    _recompute_totals(db, bill)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{bill_id}/items/{item_id}", response_model=CateringBillItemOut)
def update_bill_item(
    bill_id: UUID,
    item_id: UUID,
    payload: CateringBillItemUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft", "sent", "overdue"), f"Cannot edit bill with status '{bill.status}'")
    item = db.query(CateringBillItem).filter(
        CateringBillItem.id == item_id,
        CateringBillItem.bill_id == bill_id,
        CateringBillItem.deleted_at.is_(None),
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill item not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    item.amount = round(float(item.quantity) * float(item.unit_price), 2)
    item.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "bill_item",
        item.id,
        item.description,
        "updated",
        current_user,
        f"Line item '{item.description}' updated on bill {bill.bill_number}",
    )
    db.flush()
    _recompute_totals(db, bill)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{bill_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill_item(
    bill_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft", "sent", "overdue"), f"Cannot edit bill with status '{bill.status}'")
    item = db.query(CateringBillItem).filter(
        CateringBillItem.id == item_id,
        CateringBillItem.bill_id == bill_id,
        CateringBillItem.deleted_at.is_(None),
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill item not found")
    item.deleted_at = datetime.now(timezone.utc)
    item.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "bill_item",
        item.id,
        item.description,
        "deleted",
        current_user,
        f"Line item '{item.description}' removed from bill {bill.bill_number}",
    )
    db.flush()
    _recompute_totals(db, bill)
    db.commit()


@router.post("/{bill_id}/send", response_model=CateringBillOut)
def send_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_SEND)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft",), f"Cannot send bill with status '{bill.status}'")
    bill.status = "sent"
    bill.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "bill",
        bill.id,
        bill.bill_number,
        "sent",
        current_user,
        f"Bill {bill.bill_number} sent to customer",
    )
    db.commit()
    db.refresh(bill)

    from app.email_service import email_service
    from app.email_templates import booking_confirmed
    from app.models.catering_models import CateringBooking, CateringInquiry, CateringQuotation
    bk = db.query(CateringBooking).filter(CateringBooking.id == bill.booking_id).first()
    if bk:
        quo = db.query(CateringQuotation).filter(CateringQuotation.id == bk.quotation_id).first()
        inq = db.query(CateringInquiry).filter(CateringInquiry.id == quo.inquiry_id).first() if quo else None
        if inq and inq.customer_email:
            ref_str = f"BK-{str(bk.id)[:8]}"
            email_service.send_template(
                inq.customer_email,
                booking_confirmed,
                name=inq.customer_name,
                reference=ref_str,
                event_date=bk.event_date.strftime("%b %d, %Y") if bk.event_date else "TBD",
                venue=bk.event_location or "TBD",
                coordinator=bk.coordinator_name or "To be assigned",
                coordinator_contact=bk.coordinator_contact or "—",
                details_url=f"{get_settings().PUBLIC_BASE_URL.rstrip('/')}/customer-portal.html?ref={inquiry_reference(inq)}",
            )

    return bill


@router.post("/{bill_id}/mark-paid", response_model=CateringBillOut)
def mark_bill_paid(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_MARK_PAID)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("sent", "overdue"), f"Cannot mark bill with status '{bill.status}' as paid")
    bill.status = "paid"
    bill.updated_by = current_user.id
    db.flush()
    log_audit(
        db,
        org_id,
        "bill",
        bill.id,
        bill.bill_number,
        "marked paid",
        current_user,
        f"Bill {bill.bill_number} marked as paid",
    )
    recompute_payment_status(db, org_id, bill.booking_id)
    db.refresh(bill)
    return bill


@router.post("/{bill_id}/void", response_model=CateringBillOut)
def void_bill(
    bill_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.BILL_VOID)),
    org_id: UUID = Depends(get_org_id),
):
    bill = base_query(db, CateringBill, org_id).filter(CateringBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    _validate_status_flow(bill, ("draft", "sent", "overdue"), f"Cannot void bill with status '{bill.status}'")
    bill.status = "void"
    bill.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "bill",
        bill.id,
        bill.bill_number,
        "voided",
        current_user,
        f"Bill {bill.bill_number} voided",
    )
    db.commit()
    db.refresh(bill)
    return bill
