"""Motor vehicles specific listing endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models import ListingCategory, ListingStatus
from backend.app.routers.listings import list_listings
from backend.app.schemas import ListingOut

router = APIRouter(prefix="/cars/listings", tags=["cars"])


@router.get("", response_model=list[ListingOut])
def get_car_listings(
    db: Session = Depends(get_db),
    status_filter: ListingStatus | None = Query(default=None, alias="status"),
    city: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
):
    """List car listings."""
    return list_listings(
        db=db,
        category=ListingCategory.car.value,
        status_filter=status_filter,
        city=city,
        min_price=min_price,
        max_price=max_price,
    )
