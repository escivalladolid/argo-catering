from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringVenue, UserStub
from app.paging import apply_search, apply_sort, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    Page,
    VenueCreate,
    VenueOut,
    VenueUpdate,
)

router = APIRouter(prefix="/venues", tags=["Venues"])

SORT_MAP = {
    "name": CateringVenue.name,
    "capacity": CateringVenue.capacity,
    "fee": CateringVenue.fee,
    "status": CateringVenue.status,
    "is_active": CateringVenue.is_active,
    "created_at": CateringVenue.created_at,
}
SEARCH_COLS = [CateringVenue.name, CateringVenue.description]


def _base_query(db: Session, org_id: UUID):
    return db.query(CateringVenue).filter(
        CateringVenue.organization_id == org_id,
        CateringVenue.deleted_at.is_(None),
    )


@router.get("/", response_model=Page[VenueOut])
def list_venues(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.VENUE_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    return paginate(q, page, page_size)


@router.post("/", response_model=VenueOut, status_code=status.HTTP_201_CREATED)
def create_venue(
    payload: VenueCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.VENUE_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    existing = db.query(CateringVenue).filter(
        CateringVenue.organization_id == org_id,
        CateringVenue.name == payload.name,
        CateringVenue.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A venue with this name already exists")
    venue = CateringVenue(
        organization_id=org_id,
        name=payload.name,
        capacity=payload.capacity,
        fee=payload.fee,
        description=payload.description,
        address=payload.address,
        parking_capacity=payload.parking_capacity,
        status=payload.status,
        is_active=payload.status == "active",
        created_by=current_user.id,
    )
    db.add(venue)
    log_audit(
        db,
        org_id,
        "venue",
        venue.id,
        venue.name,
        "created",
        current_user,
        f"Venue '{venue.name}' created",
    )
    db.commit()
    db.refresh(venue)
    return venue


@router.get("/{venue_id}", response_model=VenueOut)
def get_venue(
    venue_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.VENUE_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    venue = _base_query(db, org_id).filter(CateringVenue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    return venue


@router.patch("/{venue_id}", response_model=VenueOut)
def update_venue(
    venue_id: UUID,
    payload: VenueUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.VENUE_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    venue = _base_query(db, org_id).filter(CateringVenue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = db.query(CateringVenue).filter(
            CateringVenue.organization_id == org_id,
            CateringVenue.name == update_data["name"],
            CateringVenue.id != venue_id,
            CateringVenue.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A venue with this name already exists")
        venue.name = update_data["name"]
    if "capacity" in update_data:
        venue.capacity = update_data["capacity"]
    if "fee" in update_data:
        venue.fee = update_data["fee"]
    if "description" in update_data:
        venue.description = update_data["description"]
    if "address" in update_data:
        venue.address = update_data["address"]
    if "parking_capacity" in update_data:
        venue.parking_capacity = update_data["parking_capacity"]
    if "status" in update_data:
        venue.status = update_data["status"]
        venue.is_active = update_data["status"] == "active"
    venue.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "venue",
        venue.id,
        venue.name,
        "updated",
        current_user,
        f"Venue '{venue.name}' updated",
    )
    db.commit()
    db.refresh(venue)
    return venue


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_venue(
    venue_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.VENUE_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    venue = _base_query(db, org_id).filter(CateringVenue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    from datetime import datetime, timezone
    venue.deleted_at = datetime.now(timezone.utc)
    venue.is_active = False
    venue.status = "inactive"
    venue.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "venue",
        venue.id,
        venue.name,
        "deleted",
        current_user,
        f"Venue '{venue.name}' deleted",
    )
    db.commit()
