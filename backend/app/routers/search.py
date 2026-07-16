"""Search endpoints for listings discovery and filter metadata."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import ListingCategory
from backend.app.schemas import SearchResponse
from backend.app.services.search_indexer.service import SearchService


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
    """Run filtered listing search over publicly visible inventory."""
    parsed_category = None
    if category:
        try:
            parsed_category = ListingCategory(category.strip().lower())
        except ValueError:
            return SearchResponse(total=0, results=[])

    parsed_map_bbox = None
    if map_bbox:
        try:
            parts = [float(p.strip()) for p in map_bbox.split(",")]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="map_bbox must be minLng,minLat,maxLng,maxLat") from exc
        if len(parts) != 4:
            raise HTTPException(status_code=400, detail="map_bbox must include exactly 4 numeric values")
        parsed_map_bbox = tuple(parts)

    total, results = SearchService.search_listings(
        db=db,
        q=q,
        category=parsed_category,
        min_price=min_price,
        max_price=max_price,
        year=year,
        make=make,
        model=model,
        condition=condition,
        bedrooms=bedrooms,
        map_bbox=parsed_map_bbox,
        limit=limit,
        offset=offset
    )
    return SearchResponse(total=total, results=results)


@router.get("/autocomplete")
def autocomplete(db: Session = Depends(get_db), q: str = Query(min_length=2, max_length=60)):
    """Return lightweight typeahead suggestions from make/model/city fields."""
    suggestions = SearchService.get_autocomplete_suggestions(db, q)
    return {"q": q, "suggestions": suggestions}


@router.get("/facets")
def facets(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
):
    """Return aggregated facet counts used by client-side search filters."""
    parsed_category = None
    if category:
        try:
            parsed_category = ListingCategory(category.strip().lower())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")

    return SearchService.get_facets(db, category=parsed_category)
