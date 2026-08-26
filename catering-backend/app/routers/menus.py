from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringMenu, CateringMenuItem, UserStub
from app.paging import apply_search, apply_sort, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringMenuCreate,
    CateringMenuItemCreate,
    CateringMenuItemOut,
    CateringMenuItemUpdate,
    CateringMenuOut,
    CateringMenuUpdate,
    FoodItemOut,
    Page,
)

router = APIRouter(prefix="/menus", tags=["Menus"])

SORT_MAP = {
    "name": CateringMenu.name,
    "category": CateringMenu.category,
    "created_at": CateringMenu.created_at,
}
SEARCH_COLS = [CateringMenu.name, CateringMenu.description]

ITEM_SORT_MAP = {
    "name": CateringMenuItem.name,
    "category": CateringMenuItem.category,
    "sort_order": CateringMenuItem.sort_order,
}
ITEM_SEARCH_COLS = [CateringMenuItem.name, CateringMenuItem.description, CateringMenuItem.dietary_tags]


def _base_query(db: Session, org_id: UUID):
    return db.query(CateringMenu).filter(
        CateringMenu.organization_id == org_id,
        CateringMenu.deleted_at.is_(None),
    )


def _item_base_query(db: Session, org_id: UUID, menu_id: UUID):
    menu = _base_query(db, org_id).filter(CateringMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    return menu, db.query(CateringMenuItem).filter(
        CateringMenuItem.menu_id == menu_id,
        CateringMenuItem.deleted_at.is_(None),
    )


def _attach_item_counts(db: Session, org_id: UUID, menus: list[CateringMenu]) -> None:
    if not menus:
        return
    menu_ids = [m.id for m in menus]
    counts = dict(
        db.query(CateringMenuItem.menu_id, func.count())
        .filter(
            CateringMenuItem.menu_id.in_(menu_ids),
            CateringMenuItem.deleted_at.is_(None),
            CateringMenuItem.organization_id == org_id,
        )
        .group_by(CateringMenuItem.menu_id)
        .all()
    )
    for menu in menus:
        menu.item_count = counts.get(menu.id, 0)


@router.get("/", response_model=Page[CateringMenuOut])
def list_menus(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    result = paginate(q, page, page_size)
    _attach_item_counts(db, org_id, result.items)
    return result


@router.get("/foods", response_model=list[FoodItemOut])
def list_all_foods(
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    rows = (
        db.query(CateringMenuItem, CateringMenu.name)
        .join(CateringMenu, CateringMenuItem.menu_id == CateringMenu.id)
        .filter(
            CateringMenuItem.organization_id == org_id,
            CateringMenuItem.deleted_at.is_(None),
            CateringMenu.deleted_at.is_(None),
        )
        .order_by(CateringMenu.name.asc(), CateringMenuItem.sort_order.asc(), CateringMenuItem.name.asc())
        .all()
    )
    return [
        FoodItemOut(
            id=it.id,
            menu_id=it.menu_id,
            menu_name=menu_name,
            name=it.name,
            description=it.description,
            category=it.category,
            dietary_tags=it.dietary_tags,
            is_active=it.is_active,
            sort_order=it.sort_order,
        )
        for it, menu_name in rows
    ]


@router.post("/", response_model=CateringMenuOut, status_code=status.HTTP_201_CREATED)
def create_menu(
    payload: CateringMenuCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    existing = db.query(CateringMenu).filter(
        CateringMenu.organization_id == org_id,
        CateringMenu.name == payload.name,
        CateringMenu.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Menu with this name already exists")

    menu = CateringMenu(
        organization_id=org_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    db.add(menu)
    db.flush()
    for item in payload.items:
        db.add(CateringMenuItem(
            organization_id=org_id,
            menu_id=menu.id,
            name=item.name,
            description=item.description,
            category=item.category,
            dietary_tags=item.dietary_tags,
            price=item.price,
            pricing_unit=item.pricing_unit,
            is_active=item.is_active,
            sort_order=item.sort_order,
            created_by=current_user.id,
        ))
    log_audit(
        db,
        org_id,
        "menu",
        menu.id,
        menu.name,
        "created",
        current_user,
        f"Menu '{menu.name}' created with {len(payload.items)} item(s)",
    )
    db.commit()
    db.refresh(menu)
    menu.item_count = len(payload.items)
    return menu


@router.get("/{menu_id}", response_model=CateringMenuOut)
def get_menu(
    menu_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    menu = _base_query(db, org_id).filter(CateringMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    _attach_item_counts(db, org_id, [menu])
    return menu


@router.put("/{menu_id}", response_model=CateringMenuOut)
def update_menu(
    menu_id: UUID,
    payload: CateringMenuUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    menu = _base_query(db, org_id).filter(CateringMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        existing = db.query(CateringMenu).filter(
            CateringMenu.organization_id == org_id,
            CateringMenu.name == data["name"],
            CateringMenu.id != menu_id,
            CateringMenu.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Menu with this name already exists")
        menu.name = data["name"]
    if "description" in data:
        menu.description = data["description"]
    if "category" in data:
        menu.category = data["category"]
    if "is_active" in data:
        menu.is_active = data["is_active"]
    if "items" in data:
        now = datetime.now(timezone.utc)
        for item in menu.items:
            item.deleted_at = now
        for item in payload.items:
            db.add(CateringMenuItem(
                organization_id=org_id,
                menu_id=menu_id,
                name=item.name,
                description=item.description,
                category=item.category,
                dietary_tags=item.dietary_tags,
                price=item.price,
                pricing_unit=item.pricing_unit,
                is_active=item.is_active,
                sort_order=item.sort_order,
                created_by=current_user.id,
            ))
    menu.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "menu",
        menu.id,
        menu.name,
        "updated",
        current_user,
        f"Menu '{menu.name}' updated",
    )
    db.commit()
    db.refresh(menu)
    _attach_item_counts(db, org_id, [menu])
    return menu


@router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(
    menu_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    menu = _base_query(db, org_id).filter(CateringMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu not found")
    now = datetime.now(timezone.utc)
    for item in menu.items:
        item.deleted_at = now
    menu.deleted_at = now
    menu.is_active = False
    menu.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "menu",
        menu.id,
        menu.name,
        "deleted",
        current_user,
        f"Menu '{menu.name}' deleted",
    )
    db.commit()


@router.get("/{menu_id}/items", response_model=Page[CateringMenuItemOut])
def list_menu_items(
    menu_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    _menu, q = _item_base_query(db, org_id, menu_id)
    q = apply_search(q, search, ITEM_SEARCH_COLS)
    q = apply_sort(q, sort, dir, ITEM_SORT_MAP)
    return paginate(q, page, page_size)


@router.post("/{menu_id}/items", response_model=CateringMenuItemOut, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    menu_id: UUID,
    payload: CateringMenuItemCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    menu, q = _item_base_query(db, org_id, menu_id)
    item = CateringMenuItem(
        **payload.model_dump(exclude_unset=True),
        organization_id=org_id,
        menu_id=menu_id,
        created_by=current_user.id,
    )
    db.add(item)
    db.flush()
    log_audit(
        db,
        org_id,
        "menu_item",
        item.id,
        item.name,
        "created",
        current_user,
        f"Dish '{item.name}' created",
    )
    db.commit()
    db.refresh(item)
    return item


@router.put("/{menu_id}/items/{item_id}", response_model=CateringMenuItemOut)
def update_menu_item(
    menu_id: UUID,
    item_id: UUID,
    payload: CateringMenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    menu, q = _item_base_query(db, org_id, menu_id)
    item = q.filter(CateringMenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    item.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "menu_item",
        item.id,
        item.name,
        "updated",
        current_user,
        f"Dish '{item.name}' updated",
    )
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{menu_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    menu_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.MENU_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    menu, q = _item_base_query(db, org_id, menu_id)
    item = q.filter(CateringMenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    item.deleted_at = datetime.now(timezone.utc)
    item.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "menu_item",
        item.id,
        item.name,
        "deleted",
        current_user,
        f"Dish '{item.name}' deleted",
    )
    db.commit()
