import math
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.schemas.catering_schemas import Page


def apply_status(query: Query, status: str | None, column) -> Query:
    if status:
        return query.filter(column == status)
    return query


def apply_search(query: Query, term: str | None, columns: Iterable) -> Query:
    if term:
        return query.filter(or_(*(col.ilike(f"%{term}%") for col in columns)))
    return query


def apply_sort(query: Query, sort: str | None, direction: str, column_map: dict) -> Query:
    if sort and sort in column_map:
        col = column_map[sort]
        return query.order_by(col.desc() if direction == "desc" else col.asc())
    return query


def paginate(query: Query, page: int, page_size: int) -> Page:
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )
