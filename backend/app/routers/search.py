from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import Listing, ListingCategory, ListingStatus, ModerationStatus
from backend.app.schemas import SearchResponse


router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def global_search(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="location, make, model, brand"),
    category: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    year: int | None = Query(default=None),
    make: str | None = Query(default=None),
    model: str | None = Query(default=None),
    condition: str | None = Query(default=None),
    bedrooms: int | None = Query(default=None),
    map_bbox: str | None = Query(default=None, description="minLng,minLat,maxLng,maxLat"),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    conditions = [Listing.status == ListingStatus.active, Listing.moderation_status == ModerationStatus.approved]

    if q:
        wildcard = f"%{q}%"
        conditions.append(
            or_(
                Listing.title.ilike(wildcard),
                Listing.location_city.ilike(wildcard),
                Listing.location_country.ilike(wildcard),
                Listing.make.ilike(wildcard),
                Listing.model.ilike(wildcard),
            )
        )
    if category:
        try:
            parsed_category = ListingCategory(category.strip().lower())
        except ValueError:
            return SearchResponse(total=0, results=[])
        conditions.append(Listing.category == parsed_category)
    if min_price is not None:
        conditions.append(Listing.price >= min_price)
    if max_price is not None:
        conditions.append(Listing.price <= max_price)
    if year is not None:
        conditions.append(Listing.year == year)
    if make:
        conditions.append(Listing.make.ilike(f"%{make}%"))
    if model:
        conditions.append(Listing.model.ilike(f"%{model}%"))
    if condition:
        conditions.append(Listing.condition.ilike(f"%{condition}%"))
    if bedrooms is not None:
        conditions.append(Listing.bedrooms == bedrooms)
    if map_bbox:
        try:
            parts = [float(p.strip()) for p in map_bbox.split(",")]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="map_bbox must be minLng,minLat,maxLng,maxLat") from exc
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="map_bbox must include exactly 4 numeric values")
        min_lng, min_lat, max_lng, max_lat = parts
        conditions.append(Listing.longitude.between(min_lng, max_lng))
        conditions.append(Listing.latitude.between(min_lat, max_lat))

    query = (
        db.query(Listing)
        .filter(and_(*conditions))
        .order_by(Listing.is_featured.desc(), Listing.published_at.desc(), Listing.created_at.desc())
    )
    total = query.count()
    results = query.offset(offset).limit(limit).all()
    return SearchResponse(total=total, results=results)


@router.get("/autocomplete")
def autocomplete(db: Session = Depends(get_db), q: str = Query(min_length=2, max_length=60)):
    wildcard = f"%{q}%"
    rows = (
        db.query(Listing.make, Listing.model, Listing.location_city)
        .filter(
            or_(
                Listing.make.ilike(wildcard),
                Listing.model.ilike(wildcard),
                Listing.location_city.ilike(wildcard),
            )
        )
        .limit(20)
        .all()
    )
    suggestions = sorted(
        {
            value
            for row in rows
            for value in [row[0], row[1], row[2]]
            if value and q.lower() in value.lower()
        }
    )
    return {"q": q, "suggestions": suggestions[:10]}


@router.get("/facets")
def facets(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
):
    conditions = [Listing.status == ListingStatus.active, Listing.moderation_status == ModerationStatus.approved]
    if category:
        try:
            conditions.append(Listing.category == ListingCategory(category.strip().lower()))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")

    category_counts = (
        db.query(Listing.category, func.count(Listing.id))
        .filter(and_(*conditions))
        .group_by(Listing.category)
        .all()
    )
    make_counts = (
        db.query(Listing.make, func.count(Listing.id))
        .filter(and_(*conditions), Listing.make.is_not(None))
        .group_by(Listing.make)
        .order_by(func.count(Listing.id).desc())
        .limit(20)
        .all()
    )
    condition_counts = (
        db.query(Listing.condition, func.count(Listing.id))
        .filter(and_(*conditions), Listing.condition.is_not(None))
        .group_by(Listing.condition)
        .all()
    )
    return {
        "category": [{"value": row[0], "count": row[1]} for row in category_counts],
        "make": [{"value": row[0], "count": row[1]} for row in make_counts],
        "condition": [{"value": row[0], "count": row[1]} for row in condition_counts],
    }
