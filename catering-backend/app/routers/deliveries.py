from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.booking_scoped import base_query, get_booking
from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringDelivery, CateringInquiry, UserStub
from app.paging import apply_search, apply_sort, apply_status, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import CateringDeliveryCreate, CateringDeliveryOut, CateringDeliveryUpdate, Page

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])

SORT_MAP = {
    "name": CateringInquiry.customer_name,
    "scheduled_at": CateringDelivery.scheduled_at,
    "status": CateringDelivery.status,
    "created_at": CateringDelivery.created_at,
}
SEARCH_COLS = [
    CateringInquiry.customer_name,
    CateringDelivery.delivery_address,
    CateringDelivery.contact_name,
    CateringDelivery.contact_phone,
]


@router.get("/", response_model=Page[CateringDeliveryOut])
def list_deliveries(
    booking_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = base_query(db, CateringDelivery, org_id)
    if booking_id:
        q = q.filter(CateringDelivery.booking_id == booking_id)
    q = apply_status(q, status, CateringDelivery.status)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    return paginate(q, page, page_size)


def _delivery_reference(delivery: CateringDelivery) -> str:
    return delivery.delivery_address or delivery.contact_name or str(delivery.id)[:8]


@router.post("/", response_model=CateringDeliveryOut, status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: CateringDeliveryCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    get_booking(db, org_id, payload.booking_id)
    delivery = CateringDelivery(
        **payload.model_dump(exclude_unset=True),
        organization_id=org_id,
        created_by=current_user.id,
    )
    db.add(delivery)
    db.flush()
    log_audit(
        db,
        org_id,
        "delivery",
        delivery.id,
        _delivery_reference(delivery),
        "created",
        current_user,
        "Delivery scheduled",
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.get("/{delivery_id}", response_model=CateringDeliveryOut)
def get_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    delivery = base_query(db, CateringDelivery, org_id).filter(CateringDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return delivery


@router.put("/{delivery_id}", response_model=CateringDeliveryOut)
def update_delivery(
    delivery_id: UUID,
    payload: CateringDeliveryUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    delivery = base_query(db, CateringDelivery, org_id).filter(CateringDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(delivery, key, value)
    delivery.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "delivery",
        delivery.id,
        _delivery_reference(delivery),
        "updated",
        current_user,
        "Delivery updated",
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    delivery = base_query(db, CateringDelivery, org_id).filter(CateringDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    delivery.deleted_at = datetime.now(timezone.utc)
    delivery.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "delivery",
        delivery.id,
        _delivery_reference(delivery),
        "deleted",
        current_user,
        "Delivery deleted",
    )
    db.commit()


@router.post("/{delivery_id}/advance", response_model=CateringDeliveryOut)
def advance_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_ADVANCE)),
    org_id: UUID = Depends(get_org_id),
):
    delivery = base_query(db, CateringDelivery, org_id).filter(CateringDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    next_status = {"scheduled": "in_transit", "in_transit": "delivered", "delayed": "in_transit"}.get(delivery.status)
    if next_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot advance delivery with status '{delivery.status}'",
        )
    delivery.status = next_status
    delivery.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "delivery",
        delivery.id,
        _delivery_reference(delivery),
        f"advanced to {next_status}",
        current_user,
        f"Delivery advanced to '{next_status}'",
    )
    db.commit()
    db.refresh(delivery)
    return delivery


@router.post("/{delivery_id}/cancel", response_model=CateringDeliveryOut)
def cancel_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.DELIVERY_CANCEL)),
    org_id: UUID = Depends(get_org_id),
):
    delivery = base_query(db, CateringDelivery, org_id).filter(CateringDelivery.id == delivery_id).first()
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    if delivery.status in ("delivered", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel delivery with status '{delivery.status}'",
        )
    delivery.status = "cancelled"
    delivery.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "delivery",
        delivery.id,
        _delivery_reference(delivery),
        "cancelled",
        current_user,
        "Delivery cancelled",
    )
    db.commit()
    db.refresh(delivery)
    return delivery
