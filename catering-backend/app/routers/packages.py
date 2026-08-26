from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_org_id
from app.flow import log_audit
from app.models.catering_models import CateringMenu, CateringMenuItem, CateringPackage, CateringPackageGroup, CateringPackageItem, PackageDerivedRatio, UserStub
from app.paging import apply_search, apply_sort, paginate
from app.rbac import Perm, require_permission
from app.schemas.catering_schemas import (
    CateringPackageCreate,
    CateringPackageOut,
    CateringPackageUpdate,
    DerivedRatioIn,
    DerivedRatioOut,
    PackageDetailOut,
    PackageGroupIn,
    PackageItemIn,
    Page,
)

router = APIRouter(prefix="/packages", tags=["Packages"])

SORT_MAP = {
    "name": CateringPackage.name,
    "base_price": CateringPackage.base_price,
    "pricing_method": CateringPackage.pricing_method,
    "is_active": CateringPackage.is_active,
    "created_at": CateringPackage.created_at,
}
SEARCH_COLS = [CateringPackage.name, CateringPackage.description]


def _base_query(db: Session, org_id: UUID):
    return db.query(CateringPackage).filter(
        CateringPackage.organization_id == org_id,
        CateringPackage.deleted_at.is_(None),
    )


def load_menu_items(db: Session, org_id: UUID, ids: set[UUID]) -> dict[UUID, CateringMenuItem]:
    if not ids:
        return {}
    items = (
        db.query(CateringMenuItem)
        .join(CateringMenu, CateringMenuItem.menu_id == CateringMenu.id)
        .filter(
            CateringMenuItem.organization_id == org_id,
            CateringMenuItem.id.in_(ids),
            CateringMenuItem.deleted_at.is_(None),
            CateringMenu.deleted_at.is_(None),
            CateringMenu.is_active.is_(True),
        )
        .all()
    )
    return {it.id: it for it in items}


def _validate_builder(
    db: Session,
    org_id: UUID,
    groups: list[PackageGroupIn],
    items: list[PackageItemIn],
    has_customization: bool,
) -> dict[str, CateringPackageGroup]:
    if has_customization:
        option_items = [i for i in items if i.kind == "option"]
        if option_items and not groups:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Option items require at least one customization group")
    else:
        if any(i.kind == "option" for i in items):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Customization is disabled; option items are not allowed")

    seen_items: set[UUID] = set()
    for i in items:
        if i.menu_item_id in seen_items:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A dish cannot be added to a package more than once")
        seen_items.add(i.menu_item_id)

    loaded = load_menu_items(db, org_id, seen_items)
    missing = sorted(seen_items - set(loaded.keys()))
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Some dishes are not available: {missing[0]}")
    inactive = [i.menu_item_id for i in items if i.menu_item_id in loaded and not loaded[i.menu_item_id].is_active]
    if inactive:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only active dishes can be added to a package")

    keys: set[str] = set()
    for g in groups:
        if not g.key:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each group requires a key")
        if g.key in keys:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Duplicate group key: {g.key}")
        keys.add(g.key)

    group_by_key: dict[str, CateringPackageGroup] = {}
    for g in sorted(groups, key=lambda x: (x.sort_order, x.name)):
        grp = CateringPackageGroup(
            name=g.name,
            min_select=g.min_select,
            max_select=g.max_select,
            sort_order=g.sort_order,
        )
        group_by_key[g.key] = grp

    if groups:
        for g in sorted(groups, key=lambda x: (x.sort_order, x.name)):
            opts = [i for i in items if i.group_key == g.key and i.kind == "option"]
            if len(opts) < g.min_select:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Group '{g.name}' requires at least {g.min_select} option(s) but only {len(opts)} provided",
                )
            if g.max_select > 0 and len(opts) < g.max_select:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Group '{g.name}' needs at least {g.max_select} option(s)",
                )

    return group_by_key


def _apply_builder(db: Session, org_id: UUID, pkg: CateringPackage, payload: Any, user_id: UUID | None) -> None:
    groups = payload.groups or []
    items = payload.items or []
    group_by_key = _validate_builder(db, org_id, groups, items, payload.has_customization)

    pkg.pricing_method = payload.pricing_method
    pkg.has_customization = payload.has_customization
    if hasattr(payload, 'min_pax') and payload.min_pax is not None:
        pkg.min_pax = payload.min_pax
    if hasattr(payload, 'max_pax') and payload.max_pax is not None:
        pkg.max_pax = payload.max_pax

    db.flush()
    for key, grp in group_by_key.items():
        grp.organization_id = org_id
        grp.package_id = pkg.id
        grp.created_by = user_id
        db.add(grp)
    db.flush()

    for idx, it in enumerate(sorted(items, key=lambda x: (x.sort_order, x.kind))):
        if it.kind == "option":
            grp = group_by_key.get(it.group_key or "")
            if grp is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Option item references an unknown group")
            group_id = grp.id
        else:
            group_id = None
        db.add(
            CateringPackageItem(
                organization_id=org_id,
                package_id=pkg.id,
                menu_item_id=it.menu_item_id,
                kind=it.kind,
                group_id=group_id,
                quantity=it.quantity,
                unit=it.unit,
                sort_order=it.sort_order,
                created_by=user_id,
            )
        )

    _apply_derived_ratios(db, org_id, pkg, payload, user_id)


def _apply_derived_ratios(db: Session, org_id: UUID, pkg: CateringPackage, payload: Any, user_id: UUID | None) -> None:
    """Apply derived ratios from a create/update payload."""
    ratios = getattr(payload, 'derived_ratios', None)
    if ratios is None:
        return
    existing = {r.item_key: r for r in pkg.derived_ratios}
    incoming_keys = {r.item_key for r in ratios}
    for key, r in existing.items():
        if key not in incoming_keys:
            db.delete(r)
    for ratio_in in ratios:
        if ratio_in.item_key in existing:
            r = existing[ratio_in.item_key]
            r.per_guests = ratio_in.per_guests
            r.minimum = ratio_in.minimum
            r.updated_by = user_id
        else:
            db.add(PackageDerivedRatio(
                organization_id=org_id,
                package_id=pkg.id,
                item_key=ratio_in.item_key,
                per_guests=ratio_in.per_guests,
                minimum=ratio_in.minimum,
                created_by=user_id,
            ))


def _replace_builder(db: Session, org_id: UUID, pkg: CateringPackage, payload: Any, user_id: UUID | None) -> None:
    db.query(CateringPackageItem).filter(CateringPackageItem.package_id == pkg.id).delete()
    db.query(CateringPackageGroup).filter(CateringPackageGroup.package_id == pkg.id).delete()
    db.query(PackageDerivedRatio).filter(PackageDerivedRatio.package_id == pkg.id).delete()
    db.flush()
    _apply_builder(db, org_id, pkg, payload, user_id)


@router.get("/", response_model=Page[CateringPackageOut])
def list_packages(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = Query(None, max_length=200),
    sort: str | None = Query(None),
    dir: Literal["asc", "desc"] = Query("asc"),
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PACKAGE_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    q = _base_query(db, org_id)
    q = apply_search(q, search, SEARCH_COLS)
    q = apply_sort(q, sort, dir, SORT_MAP)
    return paginate(q, page, page_size)


@router.post("/", response_model=CateringPackageOut, status_code=status.HTTP_201_CREATED)
def create_package(
    payload: CateringPackageCreate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PACKAGE_CREATE)),
    org_id: UUID = Depends(get_org_id),
):
    existing = db.query(CateringPackage).filter(
        CateringPackage.organization_id == org_id,
        CateringPackage.name == payload.name,
        CateringPackage.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package with this name already exists")
    pkg = CateringPackage(
        organization_id=org_id,
        name=payload.name,
        description=payload.description,
        base_price=payload.base_price,
        pricing_method=payload.pricing_method,
        has_customization=payload.has_customization,
        min_pax=payload.min_pax,
        max_pax=payload.max_pax,
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    db.add(pkg)
    db.flush()
    _apply_builder(db, org_id, pkg, payload, current_user.id)
    log_audit(
        db,
        org_id,
        "package",
        pkg.id,
        pkg.name,
        "created",
        current_user,
        f"Package '{pkg.name}' created",
    )
    db.commit()
    db.refresh(pkg)
    return pkg


@router.get("/{package_id}", response_model=CateringPackageOut)
def get_package(
    package_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PACKAGE_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    pkg = _base_query(db, org_id).filter(CateringPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return pkg


@router.get("/{package_id}/detail", response_model=PackageDetailOut)
def get_package_detail(
    package_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PACKAGE_VIEW)),
    org_id: UUID = Depends(get_org_id),
):
    pkg = (
        _base_query(db, org_id)
        .filter(CateringPackage.id == package_id)
        .options(joinedload(CateringPackage.groups).joinedload(CateringPackageGroup.options), joinedload(CateringPackage.items))
        .first()
    )
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return pkg


@router.put("/{package_id}", response_model=CateringPackageOut)
def update_package(
    package_id: UUID,
    payload: CateringPackageUpdate,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PACKAGE_UPDATE)),
    org_id: UUID = Depends(get_org_id),
):
    pkg = _base_query(db, org_id).filter(CateringPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data:
        existing = db.query(CateringPackage).filter(
            CateringPackage.organization_id == org_id,
            CateringPackage.name == update_data["name"],
            CateringPackage.id != package_id,
            CateringPackage.deleted_at.is_(None),
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Package with this name already exists")
        pkg.name = update_data["name"]
    if "description" in update_data:
        pkg.description = update_data["description"]
    if "base_price" in update_data:
        pkg.base_price = update_data["base_price"]
    if "pricing_method" in update_data:
        pkg.pricing_method = update_data["pricing_method"]
    if "has_customization" in update_data:
        pkg.has_customization = update_data["has_customization"]
    if "min_pax" in update_data:
        pkg.min_pax = update_data["min_pax"]
    if "max_pax" in update_data:
        pkg.max_pax = update_data["max_pax"]
    if "is_active" in update_data:
        pkg.is_active = update_data["is_active"]
    if "service_style" in update_data:
        pkg.service_style = update_data["service_style"]

    if "groups" in update_data or "items" in update_data or "derived_ratios" in update_data:
        builder_payload = type("BuilderPayload", (), {
            "groups": payload.groups if payload.groups is not None else [],
            "items": payload.items if payload.items is not None else [],
            "has_customization": payload.has_customization if payload.has_customization is not None else pkg.has_customization,
            "pricing_method": payload.pricing_method if payload.pricing_method is not None else pkg.pricing_method,
            "derived_ratios": payload.derived_ratios if payload.derived_ratios is not None else [],
            "min_pax": payload.min_pax,
            "max_pax": payload.max_pax,
        })()
        _replace_builder(db, org_id, pkg, builder_payload, current_user.id)

    pkg.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "package",
        pkg.id,
        pkg.name,
        "updated",
        current_user,
        f"Package '{pkg.name}' updated",
    )
    db.commit()
    db.refresh(pkg)
    return pkg


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserStub = Depends(require_permission(Perm.PACKAGE_DELETE)),
    org_id: UUID = Depends(get_org_id),
):
    pkg = _base_query(db, org_id).filter(CateringPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    from datetime import datetime, timezone
    pkg.deleted_at = datetime.now(timezone.utc)
    pkg.is_active = False
    pkg.updated_by = current_user.id
    log_audit(
        db,
        org_id,
        "package",
        pkg.id,
        pkg.name,
        "deleted",
        current_user,
        f"Package '{pkg.name}' deleted",
    )
    db.commit()
